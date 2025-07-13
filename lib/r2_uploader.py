"""
Cloudflare R2 文件上传模块
使用 S3 兼容 API 上传文件到 Cloudflare R2 存储
"""
import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import boto3
from boto3.session import Config
from botocore.exceptions import ClientError, NoCredentialsError

# 自动加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv 未安装时的提示
    pass


@dataclass
class R2Config:
    """R2 配置"""
    account_id: str
    access_key_id: str
    secret_access_key: str
    bucket_name: str
    region: str = "auto"
    custom_domain: Optional[str] = None  # 自定义域名，可选
    
    @classmethod
    def from_env(cls) -> "R2Config":
        """从环境变量创建配置"""
        return cls(
            account_id=os.getenv("R2_ACCOUNT_ID", ""),
            access_key_id=os.getenv("R2_ACCESS_KEY_ID", ""),
            secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY", ""),
            bucket_name=os.getenv("R2_BUCKET_NAME", ""),
            region=os.getenv("R2_REGION", "auto"),
            custom_domain=os.getenv("R2_CUSTOM_DOMAIN")
        )
    
    def validate(self) -> bool:
        """验证配置是否完整"""
        required_fields = [
            self.account_id, 
            self.access_key_id, 
            self.secret_access_key, 
            self.bucket_name
        ]
        return all(field.strip() for field in required_fields)


class R2Uploader:
    """Cloudflare R2 上传器"""
    
    def __init__(self, config: R2Config):
        self.config = config
        self._client = None
        
        if not config.validate():
            raise ValueError("R2 配置不完整，请检查必要的配置字段")
    
    @property
    def client(self):
        """延迟初始化 S3 客户端"""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    def _create_client(self):
        """创建 S3 兼容的客户端用于 R2"""
        try:
            # Cloudflare R2 的正确 endpoint 格式
            endpoint_url = f"https://{self.config.account_id}.r2.cloudflarestorage.com"
            
            # 创建专用配置解决SSL问题
            r2_config = Config(
                region_name='auto',  # R2 使用 'auto' 区域
                signature_version='s3v4',
                s3={
                    'addressing_style': 'path'
                },
                retries={
                    'max_attempts': 3,
                    'mode': 'adaptive'
                }
            )
            
            client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
                region_name='auto',  # 强制使用 'auto' 区域
                config=r2_config
            )
            
            # 测试连接
            client.head_bucket(Bucket=self.config.bucket_name)
            
            return client
            
        except NoCredentialsError:
            raise ValueError("R2 凭证无效或缺失")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                raise ValueError(f"R2 存储桶 '{self.config.bucket_name}' 不存在")
            elif error_code == '403':
                raise ValueError("R2 访问被拒绝，请检查凭证和权限")
            else:
                raise ValueError(f"R2 连接失败: {e}")
    
    def upload_file(
        self, 
        local_file_path: str, 
        object_key: Optional[str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        上传文件到 R2
        
        Args:
            local_file_path: 本地文件路径
            object_key: R2 对象键，如果不指定则使用文件名
            content_type: 文件 MIME 类型
            metadata: 自定义元数据
            
        Returns:
            包含上传结果信息的字典
        """
        local_path = Path(local_file_path)
        
        if not local_path.exists():
            raise FileNotFoundError(f"本地文件不存在: {local_file_path}")
        
        # 如果没有指定对象键，使用文件名
        if object_key is None:
            object_key = local_path.name
        
        # 构建上传参数
        extra_args = {}
        
        if content_type:
            extra_args['ContentType'] = content_type
        elif object_key.endswith('.xml'):
            extra_args['ContentType'] = 'application/rss+xml'
        elif object_key.endswith('.json'):
            extra_args['ContentType'] = 'application/json'
        
        if metadata:
            extra_args['Metadata'] = metadata
        
        try:
            # 执行上传
            self.client.upload_file(
                str(local_path),
                self.config.bucket_name,
                object_key,
                ExtraArgs=extra_args if extra_args else None
            )
            
            # 构建访问 URL
            file_url = self._get_file_url(object_key)
            
            logging.info(f"文件已成功上传到 R2: {object_key}")
            
            return {
                "success": True,
                "object_key": object_key,
                "file_url": file_url,
                "bucket": self.config.bucket_name,
                "size": local_path.stat().st_size
            }
            
        except ClientError as e:
            error_msg = f"上传文件到 R2 失败: {e}"
            logging.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "object_key": object_key
            }
    
    def upload_string(
        self, 
        content: str, 
        object_key: str,
        content_type: Optional[str] = None,
        encoding: str = 'utf-8',
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        直接上传字符串内容到 R2
        
        Args:
            content: 要上传的字符串内容
            object_key: R2 对象键
            content_type: 文件 MIME 类型
            encoding: 字符编码
            metadata: 自定义元数据
            
        Returns:
            包含上传结果信息的字典
        """
        # 构建上传参数
        extra_args = {}
        
        if content_type:
            extra_args['ContentType'] = content_type
        elif object_key.endswith('.xml'):
            extra_args['ContentType'] = 'application/rss+xml'
        elif object_key.endswith('.json'):
            extra_args['ContentType'] = 'application/json'
        
        if metadata:
            extra_args['Metadata'] = metadata
        
        try:
            # 将字符串转换为字节
            content_bytes = content.encode(encoding)
            
            # 执行上传
            self.client.put_object(
                Bucket=self.config.bucket_name,
                Key=object_key,
                Body=content_bytes,
                **extra_args
            )
            
            # 构建访问 URL
            file_url = self._get_file_url(object_key)
            
            logging.info(f"内容已成功上传到 R2: {object_key}")
            
            return {
                "success": True,
                "object_key": object_key,
                "file_url": file_url,
                "bucket": self.config.bucket_name,
                "size": len(content_bytes)
            }
            
        except ClientError as e:
            error_msg = f"上传内容到 R2 失败: {e}"
            logging.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "object_key": object_key
            }
    
    def delete_file(self, object_key: str) -> Dict[str, Any]:
        """
        删除 R2 中的文件
        
        Args:
            object_key: 要删除的对象键
            
        Returns:
            删除结果
        """
        try:
            self.client.delete_object(
                Bucket=self.config.bucket_name,
                Key=object_key
            )
            
            logging.info(f"文件已从 R2 删除: {object_key}")
            
            return {
                "success": True,
                "object_key": object_key,
                "action": "deleted"
            }
            
        except ClientError as e:
            error_msg = f"删除 R2 文件失败: {e}"
            logging.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "object_key": object_key
            }
    
    def file_exists(self, object_key: str) -> bool:
        """
        检查文件是否存在于 R2 中
        
        Args:
            object_key: 对象键
            
        Returns:
            文件是否存在
        """
        try:
            self.client.head_object(
                Bucket=self.config.bucket_name,
                Key=object_key
            )
            return True
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') == '404':
                return False
            raise
    
    def list_files(self, prefix: str = "") -> list:
        """
        列出 R2 存储桶中的文件
        
        Args:
            prefix: 文件键前缀过滤
            
        Returns:
            文件列表
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=self.config.bucket_name,
                Prefix=prefix
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag'].strip('"')
                })
            
            return files
            
        except ClientError as e:
            logging.error(f"列出 R2 文件失败: {e}")
            return []
    
    def _get_file_url(self, object_key: str) -> str:
        """
        构建文件访问 URL
        
        Args:
            object_key: 对象键
            
        Returns:
            文件的公开访问 URL
        """
        if self.config.custom_domain:
            # 使用自定义域名
            return f"https://{self.config.custom_domain}/{object_key}"
        else:
            # 使用默认的 R2 域名
            return f"https://{self.config.bucket_name}.{self.config.account_id}.r2.cloudflarestorage.com/{object_key}"


def create_r2_uploader(config: Optional[R2Config] = None) -> R2Uploader:
    """
    创建 R2 上传器实例
    
    Args:
        config: R2 配置，如果不提供则从环境变量读取
        
    Returns:
        R2Uploader 实例
    """
    if config is None:
        config = R2Config.from_env()
    
    return R2Uploader(config)
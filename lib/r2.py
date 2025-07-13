"""
Minimal Cloudflare R2 client
依赖：pip install boto3 python-dotenv
"""
from __future__ import annotations
import os, boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
load_dotenv()


class R2Config:
    account_id: str = os.getenv("R2_ACCOUNT_ID", "")
    access_key: str = os.getenv("R2_ACCESS_KEY_ID", "")
    secret_key: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    bucket: str    = os.getenv("R2_BUCKET_NAME", "")
    region: str    = "auto"
    custom_domain: str | None = os.getenv("R2_CUSTOM_DOMAIN")

    @property
    def endpoint(self) -> str:
        return f"https://{self.account_id}.r2.cloudflarestorage.com"


class R2Client:
    """与 S3 语义一致，但内部已绑定 bucket，调用更简洁"""

    def __init__(self, cfg: R2Config):
        missing = [k for k, v in cfg.__dict__.items() if not v and k not in ("region", "custom_domain")]
        if missing:
            raise ValueError(f"缺少配置字段: {missing}")
        self._bucket = cfg.bucket
        self._domain = cfg.custom_domain
        self._cli = boto3.client(
            "s3",
            endpoint_url=cfg.endpoint,
            aws_access_key_id=cfg.access_key,
            aws_secret_access_key=cfg.secret_key,
            region_name=cfg.region,
            config=boto3.session.Config(signature_version="s3v4"),
        )
    # ---------- 基础操作 ----------
    def upload(self, local_path: str | None = None, *, content: str | bytes | None = None, key: str | None = None, encoding: str = "utf-8", **kwargs):
        """
        Unified upload function that handles file paths, string content, and bytes content.
        
        Args:
            local_path: Path to local file to upload
            content: String or bytes content to upload (keyword-only)
            key: Object key in bucket (defaults to basename of local_path if uploading file)
            encoding: Encoding for string content (default: utf-8)
            **kwargs: Additional arguments passed to boto3
            
        Examples:
            upload("abc.jpg")                    # Upload file from path
            upload(content="abc")                # Upload string content
            upload(content=b"abc")               # Upload bytes content
            upload("abc.jpg", key="custom-key")  # Upload file with custom key
        """
        # Validate arguments
        if (local_path is None) == (content is None):
            raise ValueError("Must provide either local_path or content parameter, not both or neither")
        
        if local_path is not None:
            # File upload mode
            key = key or os.path.basename(local_path)
            self._cli.upload_file(local_path, self._bucket, key, ExtraArgs=kwargs or None)
        else:
            # Content upload mode
            if key is None:
                raise ValueError("key parameter is required when uploading content")
            
            if isinstance(content, str):
                # String content - encode to bytes
                data = content.encode(encoding)
            elif isinstance(content, bytes):
                # Bytes content - use directly
                data = content
            else:
                raise ValueError("content must be str or bytes")
            
            self._cli.put_object(Bucket=self._bucket, Key=key, Body=data, **kwargs)

    def upload_bytes(self, data: bytes, key: str, **kwargs):
        """Legacy method - use upload(content=data, key=key) instead"""
        self.upload(content=data, key=key, **kwargs)

    def upload_string(self, content: str, key: str, encoding: str = "utf-8", **kwargs):
        """Legacy method - use upload(content=content, key=key) instead"""
        self.upload(content=content, key=key, encoding=encoding, **kwargs)

    def download(self, key: str, local_path: str):
        self._cli.download_file(self._bucket, key, local_path)

    def delete(self, key: str):
        self._cli.delete_object(Bucket=self._bucket, Key=key)

    def list(self, prefix: str = "") -> list[str]:
        resp = self._cli.list_objects_v2(Bucket=self._bucket, Prefix=prefix)
        return [o["Key"] for o in resp.get("Contents", [])]

    def presign(self, key: str, expires: int = 3600) -> str:
        return self._cli.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires,
        )

    # ---------- 工具方法 ----------
    def exists(self, key: str) -> bool:
        try:
            self._cli.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError as e:
            return e.response["Error"]["Code"] != "404"

    def get_url(self, key: str) -> str:
        """构建文件访问 URL"""
        if self._domain:
            return f"https://{self._domain}/{key}"
        else:
            return f"https://{self._bucket}.{self._cli._endpoint.host.split('.')[0]}.r2.cloudflarestorage.com/{key}"
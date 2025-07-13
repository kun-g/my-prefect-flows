"""
Minimal Cloudflare R2 client
依赖：pip install boto3 python-dotenv (可选)
"""
from __future__ import annotations
import os, typing as t
from dataclasses import dataclass
import boto3
from botocore.exceptions import ClientError

try:        # 可选：自动加载 .env
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass(frozen=True)
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
    def upload(self, local_path: str, key: str | None = None, **kwargs):
        key = key or os.path.basename(local_path)
        self._cli.upload_file(local_path, self._bucket, key, ExtraArgs=kwargs or None)

    def upload_bytes(self, data: bytes, key: str, **kwargs):
        self._cli.put_object(Bucket=self._bucket, Key=key, Body=data, **kwargs)

    def upload_string(self, content: str, key: str, encoding: str = "utf-8", **kwargs):
        self.upload_bytes(content.encode(encoding), key, **kwargs)

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


# ------ 兼容性别名 ------
R2Uploader = R2Client  # 保持向后兼容

def create_r2_uploader(config: R2Config | None = None) -> R2Client:
    """兼容函数：创建 R2 客户端实例"""
    return R2Client(config or R2Config())
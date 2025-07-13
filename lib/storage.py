"""
Storage providers following SOLID principles.
Implements StorageProvider interface for different storage backends.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
import boto3
from boto3.session import Config
from botocore.exceptions import ClientError, NoCredentialsError

from .interfaces import StorageProvider, Logger
from .config import R2Configuration


class LocalFileStorage(StorageProvider):
    """Local file system storage provider"""
    
    def __init__(self, base_path: str = ".", logger: Optional[Logger] = None):
        self.base_path = Path(base_path)
        self.logger = logger
        
        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def store(self, content: str, key: str, content_type: Optional[str] = None) -> Dict[str, Any]:
        """Store content to local file"""
        try:
            file_path = self.base_path / key
            
            # Ensure parent directories exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self._log_info(f"Content stored to local file: {file_path}")
            
            return {
                "success": True,
                "key": key,
                "file_path": str(file_path),
                "size": len(content.encode('utf-8'))
            }
            
        except Exception as e:
            error_msg = f"Failed to store content to local file: {e}"
            self._log_error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "key": key
            }
    
    def exists(self, key: str) -> bool:
        """Check if file exists"""
        file_path = self.base_path / key
        return file_path.exists()
    
    def delete(self, key: str) -> Dict[str, Any]:
        """Delete file"""
        try:
            file_path = self.base_path / key
            
            if file_path.exists():
                file_path.unlink()
                self._log_info(f"File deleted: {file_path}")
                return {
                    "success": True,
                    "key": key,
                    "action": "deleted"
                }
            else:
                return {
                    "success": False,
                    "error": "File does not exist",
                    "key": key
                }
                
        except Exception as e:
            error_msg = f"Failed to delete file: {e}"
            self._log_error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "key": key
            }
    
    def _log_info(self, message: str) -> None:
        """Log info message if logger available"""
        if self.logger:
            self.logger.info(message)
        else:
            print(message)
    
    def _log_error(self, message: str) -> None:
        """Log error message if logger available"""
        if self.logger:
            self.logger.error(message)
        else:
            print(f"ERROR: {message}")


class R2Storage(StorageProvider):
    """Cloudflare R2 storage provider"""
    
    def __init__(self, config: R2Configuration, logger: Optional[Logger] = None):
        self.config = config
        self.logger = logger
        self._client = None
        
        if not config.validate():
            raise ValueError("R2 configuration is incomplete")
    
    @property
    def client(self):
        """Lazy initialization of S3 client"""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    def store(self, content: str, key: str, content_type: Optional[str] = None) -> Dict[str, Any]:
        """Store content to R2"""
        try:
            # Prepare upload arguments
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            elif key.endswith('.xml'):
                extra_args['ContentType'] = 'application/rss+xml'
            elif key.endswith('.json'):
                extra_args['ContentType'] = 'application/json'
            
            # Convert string to bytes
            content_bytes = content.encode('utf-8')
            
            # Upload to R2
            self.client.put_object(
                Bucket=self.config.bucket_name,
                Key=key,
                Body=content_bytes,
                **extra_args
            )
            
            # Build access URL
            file_url = self._get_file_url(key)
            
            self._log_info(f"Content uploaded to R2: {key}")
            
            return {
                "success": True,
                "key": key,
                "file_url": file_url,
                "bucket": self.config.bucket_name,
                "size": len(content_bytes)
            }
            
        except Exception as e:
            error_msg = f"Failed to upload to R2: {e}"
            self._log_error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "key": key
            }
    
    def exists(self, key: str) -> bool:
        """Check if object exists in R2"""
        try:
            self.client.head_object(
                Bucket=self.config.bucket_name,
                Key=key
            )
            return True
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') == '404':
                return False
            raise
    
    def delete(self, key: str) -> Dict[str, Any]:
        """Delete object from R2"""
        try:
            self.client.delete_object(
                Bucket=self.config.bucket_name,
                Key=key
            )
            
            self._log_info(f"Object deleted from R2: {key}")
            
            return {
                "success": True,
                "key": key,
                "action": "deleted"
            }
            
        except Exception as e:
            error_msg = f"Failed to delete from R2: {e}"
            self._log_error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "key": key
            }
    
    def _create_client(self):
        """Create S3 client for R2"""
        try:
            endpoint_url = f"https://{self.config.account_id}.r2.cloudflarestorage.com"
            
            r2_config = Config(
                region_name='auto',
                signature_version='s3v4',
                s3={'addressing_style': 'path'},
                retries={'max_attempts': 3, 'mode': 'adaptive'}
            )
            
            client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
                region_name='auto',
                config=r2_config
            )
            
            # Test connection
            client.head_bucket(Bucket=self.config.bucket_name)
            
            return client
            
        except NoCredentialsError:
            raise ValueError("R2 credentials are invalid or missing")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                raise ValueError(f"R2 bucket '{self.config.bucket_name}' does not exist")
            elif error_code == '403':
                raise ValueError("R2 access denied, check credentials and permissions")
            else:
                raise ValueError(f"R2 connection failed: {e}")
    
    def _get_file_url(self, key: str) -> str:
        """Build file access URL"""
        if self.config.custom_domain:
            return f"https://{self.config.custom_domain}/{key}"
        else:
            return f"https://{self.config.bucket_name}.{self.config.account_id}.r2.cloudflarestorage.com/{key}"
    
    def _log_info(self, message: str) -> None:
        """Log info message if logger available"""
        if self.logger:
            self.logger.info(message)
        else:
            print(message)
    
    def _log_error(self, message: str) -> None:
        """Log error message if logger available"""
        if self.logger:
            self.logger.error(message)
        else:
            print(f"ERROR: {message}")


class StorageFactory:
    """Factory for creating storage providers"""
    
    @staticmethod
    def create_local_storage(base_path: str = "output", 
                           logger: Optional[Logger] = None) -> LocalFileStorage:
        """Create local file storage provider"""
        return LocalFileStorage(base_path, logger)
    
    @staticmethod
    def create_r2_storage(config: Optional[R2Configuration] = None,
                         logger: Optional[Logger] = None) -> R2Storage:
        """Create R2 storage provider"""
        if config is None:
            config = R2Configuration.from_env()
        return R2Storage(config, logger)
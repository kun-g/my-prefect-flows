"""
Storage providers following SOLID principles.
Implements StorageProvider interface for different storage backends.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional

from .interfaces import StorageProvider, Logger
from .r2 import R2Client, R2Config


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
    """Cloudflare R2 storage provider using the new R2Client"""
    
    def __init__(self, config: R2Config, logger: Optional[Logger] = None):
        self.config = config
        self.logger = logger
        self.client = R2Client(config)
    
    def store(self, content: str, key: str, content_type: Optional[str] = None) -> Dict[str, Any]:
        """Store content to R2"""
        try:
            # Prepare upload kwargs
            kwargs = {}
            if content_type:
                kwargs['ContentType'] = content_type
            elif key.endswith('.xml'):
                kwargs['ContentType'] = 'application/rss+xml'
            elif key.endswith('.json'):
                kwargs['ContentType'] = 'application/json'
            
            # Upload using the new R2Client
            self.client.upload_string(content, key, **kwargs)
            
            # Build access URL
            file_url = self.client.get_url(key)
            
            self._log_info(f"Content uploaded to R2: {key}")
            
            return {
                "success": True,
                "key": key,
                "file_url": file_url,
                "bucket": self.config.bucket,
                "size": len(content.encode('utf-8'))
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
        return self.client.exists(key)
    
    def delete(self, key: str) -> Dict[str, Any]:
        """Delete object from R2"""
        try:
            self.client.delete(key)
            
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
    def create_r2_storage(config: Optional[R2Config] = None,
                         logger: Optional[Logger] = None) -> R2Storage:
        """Create R2 storage provider"""
        if config is None:
            config = R2Config()
        return R2Storage(config, logger)
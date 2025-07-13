"""
Simple logger implementations following SOLID principles.
Implements Logger protocol for different logging backends.
"""
import logging
from datetime import datetime
from typing import Optional
from .interfaces import Logger as LoggerProtocol


class ConsoleLogger:
    """Simple console logger implementation"""
    
    def __init__(self, name: str = "app", level: str = "INFO"):
        self.name = name
        self.level = level.upper()
    
    def info(self, message: str) -> None:
        """Log info message to console"""
        self._log("INFO", message)
    
    def error(self, message: str) -> None:
        """Log error message to console"""
        self._log("ERROR", message)
    
    def debug(self, message: str) -> None:
        """Log debug message to console"""
        if self.level == "DEBUG":
            self._log("DEBUG", message)
    
    def _log(self, level: str, message: str) -> None:
        """Internal logging method"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level} - {self.name}: {message}")


class PrefectLogger:
    """Logger that uses Prefect's logging system"""
    
    def __init__(self, logger_name: str = "app"):
        self.logger_name = logger_name
        
    def info(self, message: str) -> None:
        """Log info message via Prefect"""
        print(message)  # Prefect captures print statements in flows
    
    def error(self, message: str) -> None:
        """Log error message via Prefect"""
        print(f"ERROR: {message}")
    
    def debug(self, message: str) -> None:
        """Log debug message via Prefect"""
        print(f"DEBUG: {message}")


class StandardLogger:
    """Logger using Python's standard logging module"""
    
    def __init__(self, logger_name: str = "app", level: str = "INFO"):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Add console handler if no handlers exist
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def info(self, message: str) -> None:
        """Log info message"""
        self.logger.info(message)
    
    def error(self, message: str) -> None:
        """Log error message"""
        self.logger.error(message)
    
    def debug(self, message: str) -> None:
        """Log debug message"""
        self.logger.debug(message)


class LoggerFactory:
    """Factory for creating logger instances"""
    
    @staticmethod
    def create_console_logger(name: str = "app", level: str = "INFO") -> ConsoleLogger:
        """Create console logger"""
        return ConsoleLogger(name, level)
    
    @staticmethod
    def create_prefect_logger(name: str = "app") -> PrefectLogger:
        """Create Prefect logger"""
        return PrefectLogger(name)
    
    @staticmethod
    def create_standard_logger(name: str = "app", level: str = "INFO") -> StandardLogger:
        """Create standard logger"""
        return StandardLogger(name, level)
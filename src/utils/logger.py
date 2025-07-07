# Activity logging utility

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import colorama
from colorama import Fore, Back, Style

# Initialize colorama for cross-platform colored output
colorama.init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE + Style.BRIGHT
    }
    
    def format(self, record):
        # Add color to the log level name
        log_color = self.COLORS.get(record.levelname, '')
        record.colored_levelname = f"{log_color}{record.levelname}{Style.RESET_ALL}"
        
        # Format the message
        formatted = super().format(record)
        return formatted


class FileOrganizerLogger:
    """
    Centralized logging system for File Organizer Pro
    
    Features:
    - Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - File and console output
    - Colored console output
    - Automatic log file rotation
    - Operation tracking
    """
    
    def __init__(self, name: str = "FileOrganizer", log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.logger = None
        self._setup_logging()
    
    def _setup_logging(self):
        """Initialize the logging system"""
        # Create logs directory if it doesn't exist
        self.log_dir.mkdir(exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_formatter = ColoredFormatter(
            '%(asctime)s | %(colored_levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Create file handler
        log_file = self.log_dir / f"{self.name}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def set_console_level(self, level: str):
        """Set the console output level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        if level.upper() in level_map:
            for handler in self.logger.handlers:
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                    handler.setLevel(level_map[level.upper()])
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(message, **kwargs)
    
    def log_operation_start(self, operation: str, details: str = ""):
        """Log the start of an operation"""
        message = f"🚀 Starting operation: {operation}"
        if details:
            message += f" | {details}"
        self.info(message)
    
    def log_operation_success(self, operation: str, details: str = ""):
        """Log successful completion of an operation"""
        message = f"✅ Completed operation: {operation}"
        if details:
            message += f" | {details}"
        self.info(message)
    
    def log_operation_error(self, operation: str, error: str):
        """Log operation failure"""
        message = f"❌ Failed operation: {operation} | Error: {error}"
        self.error(message)
    
    def log_file_action(self, action: str, source: str, destination: str = "", dry_run: bool = False):
        """Log file operations (move, copy, delete, etc.)"""
        prefix = "🔍 [DRY RUN] " if dry_run else "📁 "
        message = f"{prefix}{action}: {source}"
        if destination:
            message += f" → {destination}"
        self.info(message)
    
    def log_stats(self, stats_dict: dict):
        """Log operation statistics"""
        self.info("📊 Operation Statistics:")
        for key, value in stats_dict.items():
            self.info(f"   {key}: {value}")
    
    def log_dry_run_summary(self, total_files: int, actions: dict):
        """Log dry run summary"""
        self.info(f"🔍 DRY RUN SUMMARY - {total_files} files would be processed:")
        for action, count in actions.items():
            if count > 0:
                self.info(f"   {action}: {count} files")


# Global logger instance
_global_logger: Optional[FileOrganizerLogger] = None


def get_logger(name: str = "FileOrganizer", log_dir: str = "logs") -> FileOrganizerLogger:
    """
    Get or create the global logger instance
    
    Args:
        name: Logger name
        log_dir: Directory for log files
        
    Returns:
        FileOrganizerLogger instance
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = FileOrganizerLogger(name, log_dir)
    return _global_logger


def setup_logging(verbose: bool = False, log_dir: str = "logs") -> FileOrganizerLogger:
    """
    Setup logging with specified verbosity
    
    Args:
        verbose: If True, set console output to DEBUG level
        log_dir: Directory for log files
        
    Returns:
        Configured logger instance
    """
    logger = get_logger(log_dir=log_dir)
    
    if verbose:
        logger.set_console_level('DEBUG')
        logger.info("🔧 Verbose logging enabled")
    
    return logger


# Convenience functions for quick logging
def log_info(message: str):
    """Quick info logging"""
    get_logger().info(message)


def log_error(message: str):
    """Quick error logging"""
    get_logger().error(message)


def log_warning(message: str):
    """Quick warning logging"""
    get_logger().warning(message)


def log_debug(message: str):
    """Quick debug logging"""
    get_logger().debug(message)

"""
Advanced Logging System for Swiss Knife
Provides colored, structured logging with multiple output formats.
"""

import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from colorama import Fore, Back, Style, init

# Initialize colorama
init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and icons for different log levels."""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE + Style.BRIGHT,
    }
    
    ICONS = {
        'DEBUG': '🔧',
        'INFO': 'ℹ️ ',
        'WARNING': '⚠️ ',
        'ERROR': '❌',
        'CRITICAL': '🚨',
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        icon = self.ICONS.get(record.levelname, '')
        record.levelname = f"{color}{icon} {record.levelname}{Style.RESET_ALL}"
        record.msg = f"{color}{record.msg}{Style.RESET_ALL}"
        return super().format(record)


class SwissLogger:
    """Advanced logger with file and console output."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, name: str = "SwissKnife", log_dir: str = "logs", 
                 level: int = logging.INFO, log_to_file: bool = True):
        if self._initialized:
            return
            
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.handlers = []
        
        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_format = ColoredFormatter(
            '%(asctime)s | %(levelname)-20s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # File handler
        if log_to_file:
            log_path = Path(log_dir)
            log_path.mkdir(exist_ok=True)
            log_file = log_path / f"swiss_knife_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
        
        self._initialized = True
    
    def debug(self, msg: str):
        self.logger.debug(msg)
    
    def info(self, msg: str):
        self.logger.info(msg)
    
    def warning(self, msg: str):
        self.logger.warning(msg)
    
    def error(self, msg: str):
        self.logger.error(msg)
    
    def critical(self, msg: str):
        self.logger.critical(msg)
    
    def success(self, msg: str):
        """Log a success message with green checkmark."""
        self.logger.info(f"{Fore.GREEN}✅ {msg}{Style.RESET_ALL}")
    
    def section(self, title: str):
        """Print a section divider."""
        line = "═" * 50
        self.logger.info(f"\n{Fore.CYAN}{line}{Style.RESET_ALL}")
        self.logger.info(f"{Fore.CYAN}  {title.upper()}{Style.RESET_ALL}")
        self.logger.info(f"{Fore.CYAN}{line}{Style.RESET_ALL}\n")
    
    def tool_start(self, tool_name: str):
        """Log tool execution start."""
        self.logger.info(f"{Fore.MAGENTA}🔨 Starting: {tool_name}{Style.RESET_ALL}")
    
    def tool_end(self, tool_name: str, status: str = "success"):
        """Log tool execution end."""
        if status == "success":
            self.logger.info(f"{Fore.GREEN}✅ Completed: {tool_name}{Style.RESET_ALL}")
        else:
            self.logger.info(f"{Fore.RED}❌ Failed: {tool_name}{Style.RESET_ALL}")
    
    def brain_think(self, thought: str):
        """Log brain reasoning process."""
        self.logger.info(f"{Fore.BLUE}🧠 BRAIN: {thought}{Style.RESET_ALL}")
    
    def memory_op(self, operation: str, key: str):
        """Log memory operation."""
        self.logger.debug(f"{Fore.YELLOW}💾 MEMORY [{operation}]: {key}{Style.RESET_ALL}")
    
    def pipeline_step(self, step: int, total: int, description: str):
        """Log pipeline step."""
        self.logger.info(f"{Fore.CYAN}📋 Pipeline [{step}/{total}]: {description}{Style.RESET_ALL}")


# Global logger instance
log = SwissLogger()

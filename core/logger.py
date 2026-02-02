"""Structured logging configuration"""

import logging
import sys
from typing import Optional


class StructuredLogger:
    """Structured logger for consistent logging across jobs"""
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get or create a logger with consistent formatting"""
        
        logger = logging.getLogger(name)
        
        # Avoid duplicate handlers
        if logger.handlers:
            return logger
        
        logger.setLevel(logging.DEBUG)
        
        # Console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        
        # Formatter with context
        formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger

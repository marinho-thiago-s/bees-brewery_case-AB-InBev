"""Base class for all Spark jobs with common functionality"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from pyspark.sql import DataFrame
from core.storage import StorageBackend, get_storage
from core.spark_session import SparkSessionFactory
from core.logger import StructuredLogger
import logging


class BaseJob(ABC):
    """Abstract base class for all Spark data jobs"""
    
    def __init__(self, config: Dict, storage: Optional[StorageBackend] = None):
        """
        Initialize job with configuration and storage
        
        Args:
            config: Configuration dictionary with spark, storage, and api settings
            storage: Storage backend instance (if None, creates from config)
        """
        self.config = config
        self.storage = storage or get_storage(config.get("storage", {}))
        self.logger = StructuredLogger.get_logger(self.__class__.__name__)
        self.spark = SparkSessionFactory.get_or_create(config)
    
    @abstractmethod
    def execute(self) -> None:
        """Execute the job - must be implemented by subclasses"""
        pass
    
    def _validate_schema(self, df: DataFrame, expected_schema):
        """
        Validate DataFrame schema against expected schema
        
        Args:
            df: DataFrame to validate
            expected_schema: Expected StructType schema
            
        Raises:
            ValueError: If schema doesn't match
        """
        actual_schema = df.schema
        if actual_schema != expected_schema:
            raise ValueError(
                f"Schema mismatch!\n"
                f"Expected: {expected_schema}\n"
                f"Actual: {actual_schema}"
            )
    
    def _validate_not_null(self, df: DataFrame, columns: list) -> int:
        """
        Count null values in specified columns
        
        Args:
            df: DataFrame to check
            columns: List of column names to validate
            
        Returns:
            Total count of null values
        """
        from pyspark.sql.functions import col, count as spark_count, when
        
        # Count null values for each column
        null_counts = {}
        for column in columns:
            null_count = df.filter(col(column).isNull()).count()
            null_counts[column] = null_count
        
        # Sum total nulls across all columns
        total_nulls = sum(null_counts.values())
        
        if total_nulls > 0:
            self._log(f"Warning: Found {total_nulls} null values in columns {columns}: {null_counts}", level="WARNING")
        
        return total_nulls
    
    def _validate_row_count(self, df: DataFrame, min_rows: int = 1, max_rows: Optional[int] = None) -> int:
        """
        Validate row count is within acceptable range
        
        Args:
            df: DataFrame to check
            min_rows: Minimum acceptable row count
            max_rows: Maximum acceptable row count (None = no max)
            
        Returns:
            Row count
            
        Raises:
            ValueError: If row count is outside acceptable range
        """
        row_count = df.count()
        
        if row_count < min_rows:
            raise ValueError(f"Row count {row_count} is below minimum {min_rows}")
        
        if max_rows and row_count > max_rows:
            raise ValueError(f"Row count {row_count} exceeds maximum {max_rows}")
        
        return row_count
    
    def _log(self, message: str, level: str = "INFO"):
        """
        Log message with job context
        
        Args:
            message: Message to log
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        getattr(self.logger, level.lower())(
            f"[{self.__class__.__name__}] {message}"
        )
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources"""
        if exc_type:
            self._log(f"Job failed with error: {exc_val}", level="ERROR")
        else:
            self._log("Job completed successfully", level="INFO")

"""Storage abstraction layer supporting multiple backends (local, S3, GCS, Delta)"""

from abc import ABC, abstractmethod
from typing import Optional, Dict
from pyspark.sql import DataFrame
import os
import shutil
import time


class StorageBackend(ABC):
    """Abstract base class for all storage backends"""
    
    @abstractmethod
    def write(self, df: DataFrame, path: str, format: str = "parquet", mode: str = "overwrite"):
        """Write DataFrame to storage"""
        pass
    
    @abstractmethod
    def read(self, path: str, format: str = "parquet") -> DataFrame:
        """Read DataFrame from storage"""
        pass
    
    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if path exists"""
        pass
    
    @abstractmethod
    def delete(self, path: str):
        """Delete path from storage"""
        pass


class LocalStorage(StorageBackend):
    """Local filesystem storage backend"""
    
    def __init__(self, base_path: str, max_retries: int = 3):
        self.base_path = base_path
        self.max_retries = max_retries
        os.makedirs(base_path, exist_ok=True)
    
    def write(self, df: DataFrame, path: str, format: str = "parquet", mode: str = "overwrite"):
        """Write DataFrame to local filesystem with retry logic"""
        full_path = f"{self.base_path}/{path}"
        
        # Ensure parent directory exists
        parent_dir = os.path.dirname(full_path)
        os.makedirs(parent_dir, exist_ok=True)
        
        # Clean up any existing _temporary directories from failed writes
        temp_dir = f"{full_path}/_temporary"
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Could not remove temporary directory {temp_dir}: {e}")
        
        # Retry logic for write operations
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                df.write.mode(mode).format(format).save(full_path)
                return
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = 2 ** (attempt - 1)  # Exponential backoff: 1s, 2s, 4s
                    print(f"Write attempt {attempt} failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    print(f"Write failed after {self.max_retries} attempts")
        
        if last_error:
            raise last_error
    
    def read(self, path: str, format: str = "parquet") -> DataFrame:
        """Read DataFrame from local filesystem"""
        from pyspark.sql import SparkSession
        spark = SparkSession.getActiveSession()
        full_path = f"{self.base_path}/{path}"
        return spark.read.format(format).load(full_path)
    
    def exists(self, path: str) -> bool:
        """Check if path exists on local filesystem"""
        full_path = f"{self.base_path}/{path}"
        return os.path.exists(full_path)
    
    def delete(self, path: str):
        """Delete path from local filesystem"""
        full_path = f"{self.base_path}/{path}"
        if self.exists(path):
            shutil.rmtree(full_path)


class S3Storage(StorageBackend):
    """S3 storage backend (requires boto3 and AWS credentials)"""
    
    def __init__(self, bucket: str, region: str = "us-east-1"):
        self.bucket = bucket
        self.region = region
        try:
            import boto3
            self.s3_client = boto3.client("s3", region_name=region)
        except ImportError:
            raise ImportError("boto3 is required for S3Storage. Install with: pip install boto3")
    
    def write(self, df: DataFrame, path: str, format: str = "parquet", mode: str = "overwrite"):
        """Write DataFrame to S3"""
        s3_path = f"s3://{self.bucket}/{path}"
        df.write.mode(mode).format(format).save(s3_path)
    
    def read(self, path: str, format: str = "parquet") -> DataFrame:
        """Read DataFrame from S3"""
        from pyspark.sql import SparkSession
        spark = SparkSession.getActiveSession()
        s3_path = f"s3://{self.bucket}/{path}"
        return spark.read.format(format).load(s3_path)
    
    def exists(self, path: str) -> bool:
        """Check if path exists on S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=path)
            return True
        except:
            return False
    
    def delete(self, path: str):
        """Delete path from S3"""
        self.s3_client.delete_object(Bucket=self.bucket, Key=path)


def get_storage(config: Dict) -> StorageBackend:
    """Factory function to get appropriate storage backend"""
    storage_type = config.get("type", "local")
    
    if storage_type == "local":
        return LocalStorage(
            config.get("path", "/opt/airflow/datalake"),
            max_retries=config.get("max_retries", 3)
        )
    elif storage_type == "s3":
        bucket = config.get("path", "").replace("s3://", "").split("/")[0]
        region = config.get("credentials", {}).get("region", "us-east-1") if config.get("credentials") else "us-east-1"
        return S3Storage(bucket, region)
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")

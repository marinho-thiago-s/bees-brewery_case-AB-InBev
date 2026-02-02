"""SparkSession factory for consistent Spark configuration"""

from pyspark.sql import SparkSession
from typing import Dict, Optional


class SparkSessionFactory:
    """Factory for creating SparkSession instances"""
    
    @staticmethod
    def get_or_create(config: Dict) -> SparkSession:
        """Get or create SparkSession with configuration
        
        Note: Creates a new session each time to avoid issues with
        shared SparkContext across Airflow processes. Airflow uses
        multiprocessing which breaks Python singleton patterns.
        """
        
        # Get or create the active SparkSession
        try:
            spark = SparkSession.getActiveSession()
            if spark is not None:
                return spark
        except Exception:
            pass
        
        spark_config = config.get("spark", {})
        
        builder = SparkSession.builder \
            .master(spark_config.get("master", "local")) \
            .appName(config.get("app_name", "BeesBrewing")) \
            .config("spark.executor.memory", spark_config.get("memory", "2g")) \
            .config("spark.executor.cores", str(spark_config.get("cores", 2))) \
            .config("spark.sql.shuffle.partitions", "8") \
            .config("spark.sql.files.ignoreCorruptFiles", "true") \
            .config("spark.sql.files.ignoreMissingFiles", "true") \
            .config("spark.hadoopRDD.ignoreEmptySplits", "true") \
            .config("spark.speculation", "false") \
            .config("spark.task.maxFailures", "4") \
            .config("spark.driver.maxResultSize", "1g") \
            .config("spark.shuffle.io.retryWait", "5s") \
            .config("spark.shuffle.io.maxRetries", "5") \
            .config("spark.sql.parquet.int96AsTimestamp", "false") \
            .config("spark.sql.parquet.datetimeRebaseModeInWrite", "CORRECTED")
        
        # Apply additional configs
        additional_config = spark_config.get("additional_config", {})
        for key, value in additional_config.items():
            builder.config(key, value)
        
        return builder.getOrCreate()
    
    @staticmethod
    def stop():
        """Stop the current SparkSession"""
        try:
            spark = SparkSession.getActiveSession()
            if spark is not None:
                spark.stop()
        except Exception:
            pass  # Spark context may already be stopped

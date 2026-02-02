"""Silver Layer: Transform and clean data from Bronze"""

from pyspark.sql import functions as F
from pyspark.sql.functions import col, trim
from spark_jobs.base_job import BaseJob
from datetime import datetime


class TransformationJob(BaseJob):
    """Transform Bronze layer data to Silver layer"""
    
    def __init__(self, config: dict, storage=None, execution_date: str = None):
        """Initialize with optional execution_date from Airflow"""
        super().__init__(config, storage)
        # Use provided execution_date or current date
        self.execution_date = execution_date or datetime.now().strftime('%Y-%m-%d')
        self._log(f"Initialized with execution_date: {self.execution_date}")
    
    def execute(self) -> None:
        """Execute transformation job"""
        self._log("Starting Silver layer transformation...")
        
        try:
            # Read Bronze data with partition using execution_date
            bronze_path = f"bronze/breweries/created_at={self.execution_date}"
            df = self.storage.read(bronze_path, format="parquet")
            
            initial_count = df.count()
            self._log(f"Records read from Bronze: {initial_count}")
            
            if initial_count == 0:
                raise ValueError("Bronze data is empty!")
            
            # Transformations
            df_silver = df.select(
                col("id"),
                trim(col("name")).alias("name"),
                trim(col("brewery_type")).alias("brewery_type"),
                trim(col("state_province")).alias("state"),
                trim(col("city")).alias("city"),
                trim(col("country")).alias("country"),
                col("website_url"),
                col("phone"),
                col("ingested_at")
            ).dropDuplicates(["id"])
            
            # Validate quality
            final_count = df_silver.count()
            duplicates_removed = initial_count - final_count
            self._log(f"Records after deduplication: {final_count} (removed: {duplicates_removed})")
            
            # Check for null values in key columns
            null_count = self._validate_not_null(df_silver, ["id", "name", "state"])
            
            # Write to Silver using storage abstraction with partition
            silver_path = f"silver/breweries_cleaned/created_at={self.execution_date}"
            self.storage.write(df_silver, silver_path, format="parquet", mode="overwrite")
            
            self._log(f"✅ Transformation completed! {final_count} records written to {silver_path}")
            
        except Exception as e:
            self._log(f"❌ Transformation failed: {str(e)}", level="ERROR")
            raise


def transform(spark, input_path: str, output_path: str) -> str:
    """
    Standalone function to transform bronze data to silver layer
    
    Args:
        spark: SparkSession
        input_path: Caminho base contendo dados bronze
        output_path: Caminho base para salvar dados silver
        
    Returns:
        Caminho onde os dados foram salvos
    """
    from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType
    from pathlib import Path
    from datetime import datetime
    from os.path import exists
    import glob
    
    # Read Bronze data - tenta com partição, se não encontrar tenta sem partição
    bronze_base = f"{input_path}/bronze/breweries"
    
    # Primeiro tenta ler diretamente (para testes sem partição)
    try:
        if exists(bronze_base):
            df = spark.read.parquet(bronze_base)
        else:
            # Tenta com partição de data
            current_date = datetime.now().strftime('%Y-%m-%d')
            bronze_path = f"{bronze_base}/created_at={current_date}"
            if exists(bronze_path):
                df = spark.read.parquet(bronze_path)
            else:
                raise ValueError("Bronze data está vazio!")
    except Exception as e:
        raise ValueError(f"Bronze data está vazio! Erro: {str(e)}")
    
    initial_count = df.count()
    
    if initial_count == 0:
        raise ValueError("Bronze data está vazio!")
    
    # Transformations
    df_silver = df.select(
        col("id"),
        trim(col("name")).alias("name"),
        trim(col("brewery_type")).alias("brewery_type"),
        trim(col("state_province")).alias("state"),
        trim(col("city")).alias("city"),
        trim(col("country")).alias("country"),
        col("website_url"),
        col("phone"),
        col("ingested_at")
    ).dropDuplicates(["id"])
    
    # Write to Silver partitioned by state
    silver_path = f"{output_path}/silver/breweries"
    df_silver.write \
        .mode("overwrite") \
        .partitionBy("state") \
        .format("parquet") \
        .save(silver_path)
    
    return silver_path

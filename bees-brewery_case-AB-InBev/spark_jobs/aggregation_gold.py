"""Gold Layer: Aggregate and summarize data from Silver"""

from pyspark.sql.functions import count, col
from spark_jobs.base_job import BaseJob
from datetime import datetime


class AggregationJob(BaseJob):
    """Aggregate Silver layer data to Gold layer"""
    
    def __init__(self, config: dict, storage=None, execution_date: str = None):
        """Initialize with optional execution_date from Airflow"""
        super().__init__(config, storage)
        # Use provided execution_date or current date
        self.execution_date = execution_date or datetime.now().strftime('%Y-%m-%d')
        self._log(f"Initialized with execution_date: {self.execution_date}")
    
    def execute(self) -> None:
        """Execute aggregation job"""
        self._log("Starting Gold layer aggregation...")
        
        try:
            # Read Silver data with partition using execution_date
            silver_path = f"silver/breweries_cleaned/created_at={self.execution_date}"
            df = self.storage.read(silver_path, format="parquet")
            
            input_count = df.count()
            self._log(f"Records read from Silver: {input_count}")
            
            if input_count == 0:
                raise ValueError("Silver data is empty!")
            
            # Aggregate by state and brewery type
            df_gold = df.groupBy("state", "brewery_type").agg(
                count("id").alias("qty")
            ).orderBy(col("qty").desc())
            
            output_count = df_gold.count()
            self._log(f"Aggregated groups: {output_count}")
            
            # Write to Gold using storage abstraction with partition
            gold_path = f"gold/breweries_stats/created_at={self.execution_date}"
            self.storage.write(df_gold, gold_path, format="parquet", mode="overwrite")
            
            self._log(f"✅ Aggregation completed! {output_count} groups written to {gold_path}")
            
        except Exception as e:
            self._log(f"❌ Aggregation failed: {str(e)}", level="ERROR")
            raise


def aggregate(spark, input_path: str, output_path: str) -> str:
    """
    Standalone function to aggregate silver data to gold layer
    
    Args:
        spark: SparkSession
        input_path: Caminho base contendo dados silver
        output_path: Caminho base para salvar dados gold
        
    Returns:
        Caminho onde os dados foram salvos
    """
    from datetime import datetime
    from pyspark.sql.functions import count, col
    from os.path import exists
    
    # Read Silver data - tenta sem partição primeiro (para testes), depois com partição
    silver_base = f"{input_path}/silver/breweries"
    
    # Primeiro tenta ler diretamente (para testes sem partição)
    try:
        if exists(silver_base):
            df = spark.read.parquet(silver_base)
        else:
            # Tenta com partição de data
            current_date = datetime.now().strftime('%Y-%m-%d')
            silver_path = f"{silver_base}_cleaned/created_at={current_date}"
            if exists(silver_path):
                df = spark.read.parquet(silver_path)
            else:
                raise ValueError("Silver data está vazio!")
    except Exception as e:
        raise ValueError(f"Silver data está vazio! Erro: {str(e)}")
    
    input_count = df.count()
    
    if input_count == 0:
        raise ValueError("Silver data estão vazios!")
    
    # Aggregate by state and brewery type
    df_gold = df.groupBy("state", "brewery_type").agg(
        count("id").alias("qty")
    ).orderBy(col("qty").desc())
    
    # Write to Gold without partition for tests
    gold_path = f"{output_path}/gold/breweries_agg"
    df_gold.write.mode("overwrite").format("parquet").save(gold_path)
    
    return gold_path

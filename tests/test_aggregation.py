"""
Testes unitários para o módulo de Aggregation Gold
"""

import pytest
from pyspark.sql import SparkSession
from spark_jobs.aggregation_gold import aggregate


@pytest.fixture(scope="session")
def spark():
    """Cria uma sessão Spark para testes"""
    spark_session = SparkSession.builder \
        .appName("test-gold") \
        .master("local[1]") \
        .getOrCreate()
    yield spark_session
    spark_session.stop()


@pytest.fixture
def sample_silver_data(spark, tmp_path):
    """Cria dados de exemplo em formato Silver para testes"""
    data = [
        {"id": 1, "state": "CA", "brewery_type": "micro"},
        {"id": 2, "state": "CA", "brewery_type": "micro"},
        {"id": 3, "state": "NY", "brewery_type": "nano"},
        {"id": 4, "state": "NY", "brewery_type": "micro"},
        {"id": 5, "state": "NY", "brewery_type": "micro"},
    ]
    df = spark.createDataFrame(data)
    
    # Salva como Parquet em Silver
    silver_path = str(tmp_path / "silver" / "breweries")
    df.write.mode("overwrite").parquet(silver_path)
    
    return str(tmp_path)


def test_aggregate_gold_success(spark, sample_silver_data, tmp_path):
    """Testa agregação gold bem-sucedida"""
    input_path = sample_silver_data
    output_path = str(tmp_path / "output")
    
    # Executa agregação
    result_path = aggregate(spark, input_path, output_path)
    
    # Verifica se os dados foram salvos
    assert "gold/breweries_agg" in result_path
    df_result = spark.read.parquet(result_path)
    
    # Verifica contagem (2 estados + tipos de cervejaria)
    assert df_result.count() == 3  # CA-micro, NY-nano, NY-micro
    
    # Verifica colunas
    assert "state" in df_result.columns
    assert "brewery_type" in df_result.columns
    assert "qty" in df_result.columns


def test_aggregate_gold_sums_correctly(spark, sample_silver_data, tmp_path):
    """Testa se as agregações estão corretas"""
    input_path = sample_silver_data
    output_path = str(tmp_path / "output")
    
    aggregate(spark, input_path, output_path)
    
    gold_path = f"{output_path}/gold/breweries_agg"
    df_result = spark.read.parquet(gold_path)
    
    # Verifica totais por grupo
    results = df_result.collect()
    
    # CA-micro deve ter qty=2
    ca_micro = [r for r in results if r.state == "CA" and r.brewery_type == "micro"]
    assert len(ca_micro) == 1
    assert ca_micro[0].qty == 2
    
    # NY-micro deve ter qty=2
    ny_micro = [r for r in results if r.state == "NY" and r.brewery_type == "micro"]
    assert len(ny_micro) == 1
    assert ny_micro[0].qty == 2
    
    # NY-nano deve ter qty=1
    ny_nano = [r for r in results if r.state == "NY" and r.brewery_type == "nano"]
    assert len(ny_nano) == 1
    assert ny_nano[0].qty == 1


def test_aggregate_gold_no_nulls(spark, sample_silver_data, tmp_path):
    """Testa se não há nulos nas agregações"""
    input_path = sample_silver_data
    output_path = str(tmp_path / "output")
    
    aggregate(spark, input_path, output_path)
    
    gold_path = f"{output_path}/gold/breweries_agg"
    df_result = spark.read.parquet(gold_path)
    
    # Verifica que não há nulos
    from pyspark.sql.functions import col
    null_count = df_result.filter(
        col("state").isNull() | 
        col("brewery_type").isNull() | 
        col("qty").isNull()
    ).count()
    
    assert null_count == 0


def test_aggregate_gold_empty_silver(spark, tmp_path):
    """Testa comportamento com Silver vazio"""
    # Cria Silver vazio
    from pyspark.sql.types import StructType, StructField, StringType, IntegerType
    schema = StructType([
        StructField("id", IntegerType(), True),
        StructField("state", StringType(), True),
        StructField("brewery_type", StringType(), True)
    ])
    df_empty = spark.createDataFrame([], schema)
    
    silver_path = str(tmp_path / "silver" / "breweries")
    df_empty.write.mode("overwrite").parquet(silver_path)
    
    input_path = str(tmp_path)
    output_path = str(tmp_path / "output")
    
    # Deve lançar ValueError
    with pytest.raises(ValueError, match="estão vazios"):
        aggregate(spark, input_path, output_path)

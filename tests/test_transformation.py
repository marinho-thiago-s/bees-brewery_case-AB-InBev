"""
Testes unitários para o módulo de Transformation Silver
"""

import pytest
from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from spark_jobs.transformation_silver import transform


@pytest.fixture(scope="session")
def spark():
    """Cria uma sessão Spark para testes"""
    spark_session = SparkSession.builder \
        .appName("test-silver") \
        .master("local[1]") \
        .config("spark.sql.shuffle.partitions", "1") \
        .getOrCreate()
    yield spark_session
    spark_session.stop()


@pytest.fixture
def sample_bronze_data(spark, tmp_path):
    """Cria dados de exemplo no formato bronze para testes"""
    data = [
        {"id": 1, "name": "  JOHN BREWERY  ", "brewery_type": "micro", "state_province": "  CA  ", "country": "USA", "website_url": "http://example.com", "phone": "555-1234", "city": "San Francisco", "ingested_at": "2026-02-01T00:00:00"},
        {"id": 2, "name": "  JANE BREWERY  ", "brewery_type": "nano", "state_province": "  NY  ", "country": "USA", "website_url": "http://example.com", "phone": "555-5678", "city": "New York", "ingested_at": "2026-02-01T00:00:00"},
        {"id": 1, "name": "  JOHN BREWERY  ", "brewery_type": "micro", "state_province": "  CA  ", "country": "USA", "website_url": "http://example.com", "phone": "555-1234", "city": "San Francisco", "ingested_at": "2026-02-01T00:00:00"},  # Duplicado
    ]
    df = spark.createDataFrame(data)
    
    # Salva como PARQUET (não JSON) para simular dados bronze corretamente
    bronze_path = str(tmp_path / "bronze" / "breweries")
    df.write.mode("overwrite").parquet(bronze_path)
    
    return str(tmp_path)


def test_transform_silver_success(spark, sample_bronze_data, tmp_path):
    """Testa transformação silver bem-sucedida"""
    output_path = str(tmp_path / "silver_output")
    
    # Executa transformação
    result_path = transform(spark, sample_bronze_data, output_path)
    
    # Verifica se os dados foram salvos
    assert "silver/breweries" in result_path
    df_result = spark.read.parquet(result_path)
    
    # Verifica contagem (deve ter removido duplicata)
    assert df_result.count() == 2
    
    # Verifica colunas
    assert "id" in df_result.columns
    assert "state" in df_result.columns
    assert "brewery_type" in df_result.columns


def test_transform_silver_removes_duplicates(spark, sample_bronze_data, tmp_path):
    """Testa remoção de duplicatas"""
    output_path = str(tmp_path / "silver_output")
    
    transform(spark, sample_bronze_data, output_path)
    
    silver_path = f"{output_path}/silver/breweries"
    df_result = spark.read.parquet(silver_path)
    
    # Conta IDs únicos
    unique_ids = df_result.select("id").distinct().count()
    assert unique_ids == 2
    assert df_result.count() == 2


def test_transform_silver_trims_whitespace(spark, sample_bronze_data, tmp_path):
    """Testa limpeza de espaços em branco"""
    output_path = str(tmp_path / "silver_output")
    
    transform(spark, sample_bronze_data, output_path)
    
    silver_path = f"{output_path}/silver/breweries"
    df_result = spark.read.parquet(silver_path)
    
    # Verifica se state foi limpo
    states = df_result.select("state").distinct().collect()
    for row in states:
        # Verifica que não tem espaços em branco
        assert row.state == row.state.strip()
        assert not row.state.startswith(" ")
        assert not row.state.endswith(" ")


def test_transform_silver_partitions_by_state(spark, sample_bronze_data, tmp_path):
    """Testa particionamento por estado"""
    output_path = str(tmp_path / "silver_output")
    
    transform(spark, sample_bronze_data, output_path)
    
    silver_path = f"{output_path}/silver/breweries"
    df_result = spark.read.parquet(silver_path)
    
    # Verifica se estado está nos dados
    assert "state" in df_result.columns
    
    # Verifica estados distintos
    states = df_result.select("state").distinct().collect()
    state_values = [row.state for row in states]
    assert "CA" in state_values
    assert "NY" in state_values


def test_transform_silver_empty_input(spark, tmp_path):
    """Testa erro com entrada vazia"""
    # Cria DataFrame vazio com schema correto
    from pyspark.sql.types import StructType, StructField, StringType, IntegerType
    schema = StructType([
        StructField("id", IntegerType(), True),
        StructField("state_province", StringType(), True),
        StructField("brewery_type", StringType(), True),
        StructField("name", StringType(), True),
        StructField("city", StringType(), True),
        StructField("country", StringType(), True),
        StructField("website_url", StringType(), True),
        StructField("phone", StringType(), True),
        StructField("ingested_at", StringType(), True),
    ])
    df_empty = spark.createDataFrame([], schema)
    
    # CRIAR ESTRUTURA CORRETA: bronze/breweries
    empty_path = str(tmp_path / "bronze" / "breweries")
    df_empty.write.mode("overwrite").json(empty_path)
    
    input_path = str(tmp_path)
    output_path = str(tmp_path / "silver_output")
    
    # Deve lançar ValueError
    with pytest.raises(ValueError, match="está vazio"):
        transform(spark, input_path, output_path)

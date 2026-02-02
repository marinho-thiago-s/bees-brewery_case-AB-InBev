import argparse
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_quality_check(spark, data_path):
    """
    Executa validações de qualidade de dados na camada Gold.
    
    Validações:
    1. Completeness: Tabela Gold não está vazia
    2. Schema Validation: Colunas esperadas existem
    3. Consistency: Não há nulos nas chaves de agrupamento
    4. Business Rules: Qty é positivo
    
    Args:
        spark: SparkSession ativa
        data_path: Caminho base para dados (ex: /datalake)
    
    Raises:
        ValueError: Se alguma validação falhar
    """
    try:
        logger.info("--- Iniciando Data Quality Check (Gold Layer) ---")
        
        # Ler camada Gold
        gold_path = f"{data_path}/gold/breweries_agg"
        logger.info(f"Lendo dados de: {gold_path}")
        
        df = spark.read.parquet(gold_path)
        
        # ===== CHECK 1: Schema Validation =====
        logger.info("CHECK 1: Validando schema...")
        expected_columns = {"state", "brewery_type", "qty"}
        actual_columns = set(df.columns)
        
        missing_columns = expected_columns - actual_columns
        if missing_columns:
            raise ValueError(f"❌ SCHEMA ERROR: Colunas faltando: {missing_columns}")
        
        logger.info(f"✅ Schema válido: {actual_columns}")
        
        # ===== CHECK 2: Completeness (Volume de Dados) =====
        logger.info("CHECK 2: Validando completeness...")
        total_rows = df.count()
        logger.info(f"   Linhas encontradas na Gold: {total_rows}")
        
        if total_rows == 0:
            raise ValueError("❌ COMPLETENESS FAILURE: A tabela Gold está vazia!")
        
        logger.info(f"✅ Completeness OK: {total_rows} registros")
        
        # ===== CHECK 3: Consistency (Nulos nas chaves) =====
        logger.info("CHECK 3: Validando consistency...")
        null_check = df.filter(
            col("state").isNull() | 
            col("brewery_type").isNull() | 
            col("qty").isNull()
        ).count()
        
        if null_check > 0:
            raise ValueError(
                f"❌ CONSISTENCY FAILURE: Encontradas {null_check} linhas com valores NULOS"
            )
        
        logger.info(f"✅ Consistency OK: Sem nulos nas chaves")
        
        # ===== CHECK 4: Business Rules (Qty positivo) =====
        logger.info("CHECK 4: Validando regras de negócio...")
        negative_qty = df.filter(col("qty") <= 0).count()
        
        if negative_qty > 0:
            raise ValueError(
                f"❌ BUSINESS RULE FAILURE: Encontradas {negative_qty} linhas com qty <= 0"
            )
        
        logger.info(f"✅ Business Rules OK: Todas as qty são positivas")
        
        # ===== Summary Statistics =====
        logger.info("\n--- Data Quality Summary ---")
        logger.info(f"Total Registros: {total_rows}")
        logger.info(f"Estados Únicos: {df.select('state').distinct().count()}")
        logger.info(f"Tipos de Cervejaria: {df.select('brewery_type').distinct().count()}")
        logger.info(f"Quantidade Total de Cervejarias: {df.agg({'qty': 'sum'}).collect()[0][0]}")
        
        logger.info("\n✅ SUCESSO: Todos os testes de qualidade passaram!")
        
    except Exception as e:
        logger.error(f"\n❌ ERRO na validação de qualidade: {str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Data Quality Check - Gold Layer")
    parser.add_argument("--data_path", required=True, help="Caminho base para dados")
    args = parser.parse_args()
    
    spark = SparkSession.builder \
        .appName("BeesDataQuality") \
        .getOrCreate()
    
    run_quality_check(spark, args.data_path)
    spark.stop()

"""
DAG do Airflow para orquestração do pipeline BEES Brewery - Arquitetura Melhorada

Pipeline: API -> Bronze -> Silver -> Gold -> Quality

ARQUITETURA:
- Utiliza a nova arquitetura modular com BaseJob
- Configuração centralizada em YAML (dev.yaml / prod.yaml)
- Storage backend abstrato (suporta local, S3, GCS, Delta)
- Jobs desacoplados e testáveis
- Airflow apenas faz orquestração, não processamento
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import sys
import os
import logging

# Adiciona diretórios ao path para importar módulos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.config import Config
from core.storage import get_storage
from spark_jobs.ingestion import IngestionJob
from spark_jobs.transformation_silver import TransformationJob
from spark_jobs.aggregation_gold import AggregationJob

logger = logging.getLogger(__name__)

# Carregar configuração
config = Config.from_env()
storage = get_storage(config.to_dict().get("storage", {}))

default_args = {
    'owner': 'bees-data-engineering',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'bees_brewery_medallion',
    default_args=default_args,
    description='Pipeline Medallion: API -> Bronze -> Silver -> Gold',
    schedule_interval='@daily',
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['bees', 'medallion', 'data-engineering'],
)

# --- TASK FUNCTIONS ---

def run_ingestion(**context):
    """Execute Bronze layer ingestion"""
    logger.info("Starting ingestion job...")
    with IngestionJob(config.to_dict(), storage) as job:
        job.execute()

def run_transformation(**context):
    """Execute Silver layer transformation with Airflow context"""
    logger.info("Starting transformation job...")
    # Get execution date from Airflow context
    execution_date = context['execution_date'].strftime('%Y-%m-%d')
    logger.info(f"Using execution date: {execution_date}")
    
    with TransformationJob(config.to_dict(), storage, execution_date=execution_date) as job:
        job.execute()

def run_aggregation(**context):
    """Execute Gold layer aggregation with Airflow context"""
    logger.info("Starting aggregation job...")
    # Get execution date from Airflow context
    execution_date = context['execution_date'].strftime('%Y-%m-%d')
    logger.info(f"Using execution date: {execution_date}")
    
    with AggregationJob(config.to_dict(), storage, execution_date=execution_date) as job:
        job.execute()

# --- TASKS ---

task_start = BashOperator(
    task_id='pipeline_start',
    bash_command='echo "Starting BEES Brewery Pipeline at $(date)"',
    dag=dag,
)

task_bronze = PythonOperator(
    task_id='ingestion_bronze',
    python_callable=run_ingestion,
    dag=dag,
)

task_silver = PythonOperator(
    task_id='transformation_silver',
    python_callable=run_transformation,
    dag=dag,
)

task_gold = PythonOperator(
    task_id='aggregation_gold',
    python_callable=run_aggregation,
    dag=dag,
)

task_end = BashOperator(
    task_id='pipeline_end',
    bash_command='echo "Pipeline completed successfully at $(date)"',
    dag=dag,
)

# --- DEPENDENCIES ---
task_start >> task_bronze >> task_silver >> task_gold >> task_end

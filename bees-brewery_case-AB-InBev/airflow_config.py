"""
Configuração do Airflow para o projeto BEES Brewery Case
"""

import os
from datetime import timedelta

# Airflow Home
AIRFLOW_HOME = os.getenv("AIRFLOW_HOME", "/opt/airflow")

# Core settings
AIRFLOW__CORE__DAGS_FOLDER = os.path.join(AIRFLOW_HOME, "dags")
AIRFLOW__CORE__BASE_LOG_FOLDER = os.path.join(AIRFLOW_HOME, "logs")
AIRFLOW__CORE__LOAD_EXAMPLES = False
AIRFLOW__CORE__UNIT_TEST_MODE = False
AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION = True
AIRFLOW__CORE__MAX_ACTIVE_RUNS_PER_DAG = 1
AIRFLOW__CORE__MAX_ACTIVE_TASKS_PER_DAG = 16
AIRFLOW__CORE__DAG_FILE_PROCESSOR_TIMEOUT = 50
AIRFLOW__CORE__EXECUTE_TASKS_LOCAL_FIRST = True

# Executor settings
AIRFLOW__CORE__EXECUTOR = "CeleryExecutor"
AIRFLOW__CELERY__BROKER_URL = os.getenv(
    "AIRFLOW__CELERY__BROKER_URL",
    "redis://redis:6379/0"
)
AIRFLOW__CELERY__RESULT_BACKEND = os.getenv(
    "AIRFLOW__CELERY__RESULT_BACKEND",
    "db+postgresql://airflow:airflow@postgres:5432/airflow"
)

# Database settings
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN = os.getenv(
    "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN",
    "postgresql://airflow:airflow@postgres:5432/airflow"
)

# Email settings
AIRFLOW__SMTP__SMTP_HOST = "smtp.gmail.com"
AIRFLOW__SMTP__SMTP_PORT = 587
AIRFLOW__SMTP__SMTP_USER = os.getenv("SMTP_USER", "")
AIRFLOW__SMTP__SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
AIRFLOW__SMTP__SMTP_MAIL_FROM = os.getenv("SMTP_FROM", "airflow@example.com")

# Security
AIRFLOW__CORE__FERNET_KEY = os.getenv(
    "AIRFLOW__CORE__FERNET_KEY",
    "default-key-for-development"
)

# Logging
AIRFLOW__LOGGING__LOGGING_LEVEL = os.getenv("AIRFLOW__LOGGING__LOGGING_LEVEL", "INFO")
AIRFLOW__LOGGING__COLORED_LOG_FORMAT = \
    "[%(blue)s%(asctime)s%(reset)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"

# Performance
AIRFLOW__CORE__PARALLELISM = 32
AIRFLOW__CORE__DAG_CONCURRENCY = 16
AIRFLOW__CORE__MAX_THREADS = 2

# DAG defaults
DAG_DEFAULT_ARGS = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": True,
    "email_on_retry": False,
    "email": ["admin@example.com"],
}

# Feature flags
AIRFLOW__CORE__ENABLE_XCOM_PICKLING = True
AIRFLOW__CORE__STORE_SERIALIZED_DAGS = True
AIRFLOW__WEBSERVER__ENABLE_PROXY_FIX = True

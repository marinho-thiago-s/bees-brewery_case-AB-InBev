"""
Configuration Management System - BEES Brewery Case
====================================================

Sistema centralizado de configurações com suporte a múltiplos ambientes.
Segue o padrão Factory com validação de schema e suporte a .env files.

Uso:
    from config import get_config
    config = get_config()  # Carrega baseado em ENVIRONMENT
    
    # Acessar configurações
    api_url = config.api.url
    spark_memory = config.spark.memory
    data_path = config.paths.data
"""

import os
import json
import logging
from enum import Enum
from typing import Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass, field, asdict
from dotenv import load_dotenv
from abc import ABC, abstractmethod

# Carregar variáveis de ambiente
load_dotenv()

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Ambientes suportados"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


# ============================================================================
# DATACLASSES - Estrutura tipada de configurações
# ============================================================================

@dataclass
class PathsConfig:
    """Configurações de caminhos de arquivos e diretórios"""
    data: str = field(default_factory=lambda: os.getenv("DATA_PATH", "/data"))
    logs: str = field(default_factory=lambda: os.getenv("LOGS_PATH", "/logs"))
    temp: str = field(default_factory=lambda: os.getenv("TEMP_PATH", "/tmp"))
    airflow_home: str = field(default_factory=lambda: os.getenv("AIRFLOW_HOME", "/opt/airflow"))
    
    @property
    def bronze(self) -> str:
        return f"{self.data}/bronze"
    
    @property
    def silver(self) -> str:
        return f"{self.data}/silver"
    
    @property
    def gold(self) -> str:
        return f"{self.data}/gold"
    
    @property
    def dags(self) -> str:
        return f"{self.airflow_home}/dags"
    
    @property
    def spark_jobs(self) -> str:
        return f"{self.airflow_home}/spark_jobs"
    
    def __post_init__(self):
        """Valida e cria diretórios se necessário"""
        for path_attr in ['data', 'logs', 'temp', 'airflow_home']:
            path = getattr(self, path_attr)
            Path(path).mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ Caminhos configurados: {self.data}")


@dataclass
class SparkConfig:
    """Configurações do Apache Spark"""
    master: str = field(default_factory=lambda: os.getenv("SPARK_MASTER", "local[*]"))
    app_name: str = "BeesBrewery"
    driver_memory: str = field(default_factory=lambda: os.getenv("SPARK_DRIVER_MEMORY", "2g"))
    executor_memory: str = field(default_factory=lambda: os.getenv("SPARK_EXECUTOR_MEMORY", "2g"))
    executor_cores: str = field(default_factory=lambda: os.getenv("SPARK_EXECUTOR_CORES", "2"))
    shuffle_partitions: int = 200
    default_parallelism: int = 4
    sql_extensions: list = field(default_factory=list)
    
    def get_configs_dict(self) -> Dict[str, str]:
        """Retorna configurações Spark como dicionário para SparkSession"""
        return {
            "spark.driver.memory": self.driver_memory,
            "spark.executor.memory": self.executor_memory,
            "spark.executor.cores": self.executor_cores,
            "spark.sql.shuffle.partitions": str(self.shuffle_partitions),
            "spark.default.parallelism": str(self.default_parallelism),
        }


@dataclass
class APIConfig:
    """Configurações da API BEES"""
    url: str = field(default_factory=lambda: os.getenv("API_URL", "https://api.bees.example.com"))
    key: str = field(default_factory=lambda: os.getenv("API_KEY", ""))
    timeout: int = int(os.getenv("API_TIMEOUT", "30"))
    retries: int = int(os.getenv("API_RETRIES", "3"))
    backoff_factor: float = float(os.getenv("API_BACKOFF_FACTOR", "0.5"))
    
    def validate(self):
        """Valida configurações da API"""
        if not self.key:
            logger.warning("⚠ API_KEY não configurada. Isso pode causar falhas de autenticação.")
        return True


@dataclass
class DatabaseConfig:
    """Configurações de banco de dados"""
    # PostgreSQL (Airflow metadata)
    postgres_host: str = field(default_factory=lambda: os.getenv("POSTGRES_HOST", "localhost"))
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_user: str = field(default_factory=lambda: os.getenv("POSTGRES_USER", "airflow"))
    postgres_password: str = field(default_factory=lambda: os.getenv("POSTGRES_PASSWORD", "airflow"))
    postgres_db: str = field(default_factory=lambda: os.getenv("POSTGRES_DB", "airflow"))
    
    # Redis (Celery broker)
    redis_host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    
    @property
    def postgres_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@dataclass
class AirflowConfig:
    """Configurações do Airflow"""
    executor: str = field(default_factory=lambda: os.getenv("AIRFLOW_EXECUTOR", "LocalExecutor"))
    max_active_runs_per_dag: int = int(os.getenv("AIRFLOW_MAX_ACTIVE_RUNS", "1"))
    max_active_tasks_per_dag: int = int(os.getenv("AIRFLOW_MAX_ACTIVE_TASKS", "16"))
    parallelism: int = int(os.getenv("AIRFLOW_PARALLELISM", "32"))
    dag_concurrency: int = int(os.getenv("AIRFLOW_DAG_CONCURRENCY", "16"))
    dag_file_processor_timeout: int = 50
    enable_xcom_pickling: bool = True
    store_serialized_dags: bool = True
    load_examples: bool = False
    dags_are_paused_at_creation: bool = True
    
    # Logging
    logging_level: str = field(default_factory=lambda: os.getenv("AIRFLOW_LOGGING_LEVEL", "INFO"))


@dataclass
class EmailConfig:
    """Configurações de email para notificações"""
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "smtp.gmail.com"))
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    smtp_password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    smtp_from: str = field(default_factory=lambda: os.getenv("SMTP_FROM", "airflow@example.com"))
    recipients_on_failure: list = field(default_factory=lambda: os.getenv("FAILURE_RECIPIENTS", "admin@example.com").split(","))
    enabled: bool = field(default_factory=lambda: os.getenv("EMAIL_ENABLED", "false").lower() == "true")
    
    def validate(self):
        """Valida configurações de email"""
        if self.enabled:
            required = ['smtp_user', 'smtp_password']
            for field_name in required:
                if not getattr(self, field_name):
                    logger.warning(f"⚠ Email habilitado mas {field_name} não configurado")
        return True


@dataclass
class SecurityConfig:
    """Configurações de segurança"""
    fernet_key: str = field(default_factory=lambda: os.getenv("FERNET_KEY", "default-key-for-development"))
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", ""))
    enable_authentication: bool = field(default_factory=lambda: os.getenv("ENABLE_AUTH", "false").lower() == "true")
    
    def validate(self):
        """Valida configurações de segurança"""
        if self.fernet_key == "default-key-for-development":
            logger.warning("⚠ FERNET_KEY usando valor padrão. Configure em produção!")
        return True


@dataclass
class Config:
    """Configuração centralizada do projeto"""
    environment: Environment
    paths: PathsConfig
    spark: SparkConfig
    api: APIConfig
    database: DatabaseConfig
    airflow: AirflowConfig
    email: EmailConfig
    security: SecurityConfig
    
    # Metadados
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    version: str = "1.0.0"
    
    def validate(self):
        """Valida todas as configurações"""
        logger.info(f"Validando configurações para ambiente: {self.environment.value}")
        
        self.api.validate()
        self.email.validate()
        self.security.validate()
        
        logger.info("✓ Todas as configurações validadas com sucesso")
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte configuração para dicionário (sem valores sensíveis)"""
        config_dict = asdict(self)
        # Remover valores sensíveis
        if config_dict.get('database'):
            config_dict['database']['postgres_password'] = '***'
            config_dict['database']['redis_url'] = f"redis://{self.database.redis_host}:{self.database.redis_port}/***"
        if config_dict.get('security'):
            config_dict['security']['fernet_key'] = '***'
            config_dict['security']['secret_key'] = '***'
        if config_dict.get('api'):
            config_dict['api']['key'] = '***'
        if config_dict.get('email'):
            config_dict['email']['smtp_password'] = '***'
        return config_dict
    
    def to_json(self, pretty: bool = True) -> str:
        """Converte configuração para JSON (sem valores sensíveis)"""
        if pretty:
            return json.dumps(self.to_dict(), indent=2)
        return json.dumps(self.to_dict())


# ============================================================================
# CONFIG FACTORY
# ============================================================================

class ConfigFactory(ABC):
    """Factory abstrata para criar configurações específicas de ambiente"""
    
    @abstractmethod
    def create_config(self) -> Config:
        pass


class DevelopmentConfigFactory(ConfigFactory):
    """Factory para ambiente de desenvolvimento"""
    
    def create_config(self) -> Config:
        return Config(
            environment=Environment.DEVELOPMENT,
            paths=PathsConfig(),
            spark=SparkConfig(
                master="local[*]",
                driver_memory="2g",
                executor_memory="2g",
            ),
            api=APIConfig(),
            database=DatabaseConfig(),
            airflow=AirflowConfig(executor="LocalExecutor"),
            email=EmailConfig(enabled=False),
            security=SecurityConfig(),
            debug=True,
            log_level="DEBUG",
        )


class StagingConfigFactory(ConfigFactory):
    """Factory para ambiente de staging"""
    
    def create_config(self) -> Config:
        return Config(
            environment=Environment.STAGING,
            paths=PathsConfig(),
            spark=SparkConfig(
                master="spark://spark-master:7077",
                driver_memory="4g",
                executor_memory="4g",
                executor_cores="4",
            ),
            api=APIConfig(),
            database=DatabaseConfig(),
            airflow=AirflowConfig(executor="CeleryExecutor"),
            email=EmailConfig(enabled=True),
            security=SecurityConfig(),
            debug=False,
            log_level="INFO",
        )


class ProductionConfigFactory(ConfigFactory):
    """Factory para ambiente de produção"""
    
    def create_config(self) -> Config:
        return Config(
            environment=Environment.PRODUCTION,
            paths=PathsConfig(),
            spark=SparkConfig(
                master="spark://spark-master:7077",
                driver_memory="8g",
                executor_memory="8g",
                executor_cores="8",
            ),
            api=APIConfig(),
            database=DatabaseConfig(),
            airflow=AirflowConfig(
                executor="CeleryExecutor",
                max_active_runs_per_dag=2,
                max_active_tasks_per_dag=32,
            ),
            email=EmailConfig(enabled=True),
            security=SecurityConfig(),
            debug=False,
            log_level="WARNING",
        )


class TestingConfigFactory(ConfigFactory):
    """Factory para ambiente de testes"""
    
    def create_config(self) -> Config:
        return Config(
            environment=Environment.TESTING,
            paths=PathsConfig(
                data="/tmp/test_data",
                logs="/tmp/test_logs",
                temp="/tmp/test_temp",
            ),
            spark=SparkConfig(
                master="local[1]",
                driver_memory="512m",
                executor_memory="512m",
                shuffle_partitions=1,
            ),
            api=APIConfig(),
            database=DatabaseConfig(),
            airflow=AirflowConfig(executor="LocalExecutor"),
            email=EmailConfig(enabled=False),
            security=SecurityConfig(),
            debug=True,
            log_level="DEBUG",
        )


# ============================================================================
# SINGLETON GETTER
# ============================================================================

_config_instance: Optional[Config] = None


def get_config() -> Config:
    """
    Obtém a instância singleton de configuração.
    
    A configuração é carregada uma única vez baseada na variável ENVIRONMENT.
    Ambientes suportados: development, staging, production, testing
    
    Returns:
        Config: Instância de configuração global
    
    Raises:
        ValueError: Se ambiente não for reconhecido
    """
    global _config_instance
    
    if _config_instance is not None:
        return _config_instance
    
    environment_str = os.getenv("ENVIRONMENT", "development").lower()
    
    try:
        environment = Environment(environment_str)
    except ValueError:
        logger.error(f"Ambiente inválido: {environment_str}")
        logger.info(f"Ambientes válidos: {[e.value for e in Environment]}")
        raise ValueError(f"Ambiente inválido: {environment_str}")
    
    factories = {
        Environment.DEVELOPMENT: DevelopmentConfigFactory,
        Environment.STAGING: StagingConfigFactory,
        Environment.PRODUCTION: ProductionConfigFactory,
        Environment.TESTING: TestingConfigFactory,
    }
    
    factory_class = factories[environment]
    factory = factory_class()
    _config_instance = factory.create_config()
    _config_instance.validate()
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Configuração carregada para ambiente: {environment.value.upper()}")
    logger.info(f"{'='*80}\n")
    
    return _config_instance


def reset_config():
    """Reset da instância de configuração (útil para testes)"""
    global _config_instance
    _config_instance = None
    logger.info("Configuração resetada")


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    # Carregar configuração baseada em ENVIRONMENT
    config = get_config()
    
    print("\n" + "="*80)
    print("CONFIGURAÇÕES CARREGADAS")
    print("="*80 + "\n")
    
    print(f"Ambiente: {config.environment.value}")
    print(f"Debug: {config.debug}")
    print(f"Data Path: {config.paths.data}")
    print(f"Spark Master: {config.spark.master}")
    print(f"API URL: {config.api.url}")
    print(f"Database: {config.database.postgres_host}:{config.database.postgres_port}")
    
    print("\n" + "="*80)
    print("JSON SEGURO (sem valores sensíveis)")
    print("="*80 + "\n")
    print(config.to_json(pretty=True))

"""Configuration management system with environment support"""

from dataclasses import dataclass
from typing import Dict, Optional
import yaml
import os


@dataclass
class SparkConfig:
    """Spark configuration"""
    master: str
    memory: str
    cores: int
    additional_config: Optional[Dict[str, str]] = None


@dataclass
class StorageConfig:
    """Storage configuration"""
    type: str  # "local", "s3", "gcs", "delta"
    path: str
    credentials: Optional[Dict[str, str]] = None


@dataclass
class APIConfig:
    """API configuration"""
    url: str
    timeout: int = 30
    retry_count: int = 3


@dataclass
class Config:
    """Main configuration container"""
    spark: SparkConfig
    storage: StorageConfig
    api: APIConfig
    app_name: str = "BeesBrewing"
    environment: str = "dev"  # Add environment tracking
    
    @classmethod
    def from_env(cls, env: str = None) -> "Config":
        """
        Load configuration from environment-specific YAML file
        
        Args:
            env: Environment name (dev, staging, prod). 
                 Defaults to AIRFLOW_ENV or 'dev'
        
        Returns:
            Config object with loaded settings
        """
        if env is None:
            env = os.getenv("AIRFLOW_ENV", "dev")
        
        config_file = f"config/environments/{env}.yaml"
        
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        with open(config_file) as f:
            data = yaml.safe_load(f)
        
        config = cls(
            spark=SparkConfig(**data.get("spark", {})),
            storage=StorageConfig(**data.get("storage", {})),
            api=APIConfig(**data.get("api", {})),
            app_name=data.get("app_name", "BeesBrewing"),
            environment=env,
        )
        return config
    
    @classmethod
    def from_yaml(cls, env: str = None) -> "Config":
        """Alias para from_env - para compatibilidade com testes"""
        return cls.from_env(env)
    
    def to_dict(self) -> Dict:
        """Convert config to dictionary"""
        return {
            "spark": {
                "master": self.spark.master,
                "memory": self.spark.memory,
                "cores": self.spark.cores,
                "additional_config": self.spark.additional_config or {},
            },
            "storage": {
                "type": self.storage.type,
                "path": self.storage.path,
                "credentials": self.storage.credentials or {},
            },
            "api": {
                "url": self.api.url,
                "timeout": self.api.timeout,
                "retry_count": self.api.retry_count,
            },
            "app_name": self.app_name,
            "environment": self.environment,
        }


# Alias para compatibilidade com testes
AppConfig = Config

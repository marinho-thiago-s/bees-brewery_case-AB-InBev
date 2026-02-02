"""
Test configuration with pytest and fixtures for modular architecture
"""

import pytest
import os
import tempfile
from pyspark.sql import SparkSession
from unittest.mock import Mock
from config.config import Config, SparkConfig, StorageConfig, APIConfig
from core.storage import LocalStorage


@pytest.fixture(scope="session")
def spark_session():
    """Create a Spark session for all tests"""
    spark = SparkSession.builder \
        .appName("bees-brewery-tests") \
        .master("local[1]") \
        .config("spark.sql.shuffle.partitions", "1") \
        .config("spark.default.parallelism", "1") \
        .config("spark.driver.host", "127.0.0.1") \
        .getOrCreate()
    
    yield spark
    spark.stop()


@pytest.fixture(scope="function")
def test_storage_path():
    """Provide a temporary path for test storage"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture(scope="function")
def local_storage(test_storage_path):
    """Create a LocalStorage instance for testing"""
    return LocalStorage(test_storage_path)


@pytest.fixture(scope="function")
def test_config(test_storage_path):
    """Create a test configuration"""
    return Config(
        spark=SparkConfig(
            master="local[1]",
            memory="1g",
            cores=1,
            additional_config={"spark.sql.adaptive.enabled": "false"}
        ),
        storage=StorageConfig(
            type="local",
            path=test_storage_path
        ),
        api=APIConfig(
            url="https://api.openbrewerydb.org/v1/breweries",
            timeout=30,
            retry_count=3
        ),
        app_name="BeesBrewing-Test"
    )


@pytest.fixture(scope="function")
def mock_storage():
    """Create a mocked storage backend"""
    return Mock()


def pytest_configure(config):
    """Initial pytest configuration"""
    import logging
    logging.getLogger("py4j").setLevel(logging.ERROR)
    logging.getLogger("pyspark").setLevel(logging.ERROR)

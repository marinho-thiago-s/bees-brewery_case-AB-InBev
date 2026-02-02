"""
Unit tests for modular architecture components
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from config.config import Config, SparkConfig, StorageConfig, APIConfig
from core.storage import LocalStorage, get_storage
from spark_jobs.base_job import BaseJob
from schemas.bronze import BronzeSchema


class TestConfiguration:
    """Test configuration system"""
    
    def test_config_from_dict(self, test_config):
        """Test creating config from dictionary"""
        assert test_config.spark.master == "local[1]"
        assert test_config.storage.type == "local"
        assert test_config.api.url == "https://api.openbrewerydb.org/v1/breweries"
    
    def test_config_to_dict(self, test_config):
        """Test converting config to dictionary"""
        config_dict = test_config.to_dict()
        assert config_dict["spark"]["master"] == "local[1]"
        assert config_dict["storage"]["type"] == "local"
        assert config_dict["api"]["timeout"] == 30


class TestStorageBackend:
    """Test storage backend implementations"""
    
    def test_local_storage_write_read(self, local_storage, spark_session):
        """Test writing and reading with LocalStorage"""
        # Create test DataFrame
        data = [{"id": "1", "name": "Brewery A"}, {"id": "2", "name": "Brewery B"}]
        df = spark_session.createDataFrame(data)
        
        # Write
        local_storage.write(df, "test/breweries", format="json")
        
        # Read
        df_read = local_storage.read("test/breweries", format="json")
        
        assert df_read.count() == 2
        assert df_read.columns == ["id", "name"]
    
    def test_local_storage_exists(self, local_storage, spark_session):
        """Test checking if path exists"""
        data = [{"id": "1"}]
        df = spark_session.createDataFrame(data)
        local_storage.write(df, "test/exists", format="json")
        
        assert local_storage.exists("test/exists") is True
        assert local_storage.exists("test/nonexistent") is False
    
    def test_local_storage_delete(self, local_storage, spark_session):
        """Test deleting path"""
        data = [{"id": "1"}]
        df = spark_session.createDataFrame(data)
        local_storage.write(df, "test/delete", format="json")
        
        assert local_storage.exists("test/delete") is True
        local_storage.delete("test/delete")
        assert local_storage.exists("test/delete") is False
    
    def test_get_storage_local(self, test_storage_path):
        """Test factory function for local storage"""
        config = {"type": "local", "path": test_storage_path}
        storage = get_storage(config)
        assert isinstance(storage, LocalStorage)


class TestBaseJob:
    """Test BaseJob abstraction"""
    
    def test_base_job_execute_not_implemented(self, test_config, local_storage):
        """Test that BaseJob.execute() must be implemented"""
        with pytest.raises(TypeError):
            BaseJob(test_config.to_dict(), local_storage)
    
    def test_concrete_job_execution(self, test_config, local_storage, spark_session):
        """Test concrete job implementation"""
        
        class TestJob(BaseJob):
            def execute(self):
                self._log("Test job executing")
                data = [{"id": "1", "name": "Test"}]
                df = self.spark.createDataFrame(data)
                self.storage.write(df, "test/output", format="json")
        
        job = TestJob(test_config.to_dict(), local_storage)
        job.execute()
        
        # Verify output was written
        assert local_storage.exists("test/output")
    
    def test_base_job_schema_validation(self, test_config, local_storage, spark_session):
        """Test schema validation in BaseJob"""
        from pyspark.sql.types import StructType, StructField, StringType
        
        class ValidatingJob(BaseJob):
            def execute(self):
                # Usar o schema completo do Bronze
                schema = BronzeSchema.BREWERIES_SCHEMA
                
                data = [{
                    "id": "1",
                    "name": "Test Brewery",
                    "brewery_type": "micro",
                    "address_1": "123 Main St",
                    "address_2": None,
                    "address_3": None,
                    "city": "San Francisco",
                    "state_province": "CA",
                    "postal_code": "94102",
                    "country": "United States",
                    "county_province": None,
                    "phone": "555-1234",
                    "website_url": "https://example.com",
                    "updated_at": "2026-02-01",
                    "created_at": "2026-02-01"
                }]
                df = self.spark.createDataFrame(data, schema=schema)
                self._validate_schema(df, schema)
        
        job = ValidatingJob(test_config.to_dict(), local_storage)
        job.execute()  # Should not raise
    
    def test_base_job_row_count_validation(self, test_config, local_storage, spark_session):
        """Test row count validation"""
        
        class RowCountJob(BaseJob):
            def execute(self):
                data = [{"id": "1"}]
                df = self.spark.createDataFrame(data)
                count = self._validate_row_count(df, min_rows=1, max_rows=10)
                assert count == 1
        
        job = RowCountJob(test_config.to_dict(), local_storage)
        job.execute()


class TestSchemas:
    """Test schema definitions"""
    
    def test_bronze_schema_exists(self):
        """Test Bronze schema is defined"""
        schema = BronzeSchema.BREWERIES_SCHEMA
        assert schema is not None
        assert len(schema.fields) > 0

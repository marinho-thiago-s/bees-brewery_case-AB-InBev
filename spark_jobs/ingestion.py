"""Bronze Layer: Ingest raw data from Open Brewery DB API"""

import requests
import time
import json
from datetime import datetime
from pathlib import Path
from pyspark.sql import functions as F
from spark_jobs.base_job import BaseJob
from schemas.bronze import BronzeSchema


class IngestionJob(BaseJob):
    """Ingest raw brewery data from API to Bronze layer"""
    
    def execute(self) -> None:
        """Execute ingestion job"""
        self._log("Starting ingestion from Open Brewery DB API...")
        
        try:
            # Fetch data from API with pagination
            all_data = self._fetch_from_api()
            
            if not all_data:
                raise ValueError("No data fetched from API")
            
            # Normalize data to match schema (convert all values to strings)
            normalized_data = self._normalize_data(all_data)
            
            # Create DataFrame with explicit schema to avoid type conflicts
            df = self.spark.createDataFrame(normalized_data, schema=BronzeSchema.BREWERIES_SCHEMA)
            
            # Validate schema
            self._validate_schema(df, BronzeSchema.BREWERIES_SCHEMA)
            
            # Validate row count
            row_count = self._validate_row_count(df, min_rows=1)
            self._log(f"DataFrame created with {row_count} records")
            
            # Add ingestion metadata
            df = df.withColumn("ingested_at", F.current_timestamp())
            df = df.withColumn("ingested_date", F.current_date())
            
            # Partition by date and write
            partition_date = datetime.now().strftime('%Y-%m-%d')
            path = f"bronze/breweries/created_at={partition_date}"
            
            self.storage.write(df, path, format="parquet", mode="overwrite")
            
            self._log(f"✅ Ingestion completed! {row_count} records written to {path}")
            
        except Exception as e:
            self._log(f"❌ Ingestion failed: {str(e)}", level="ERROR")
            raise
    
    def _normalize_data(self, data: list) -> list:
        """
        Normalize raw API data to match schema
        
        Converts all values to strings and ensures all expected fields exist
        
        Args:
            data: List of raw brewery records from API
            
        Returns:
            List of normalized brewery records
        """
        schema_fields = BronzeSchema.BREWERIES_SCHEMA.fieldNames()
        normalized = []
        
        for record in data:
            normalized_record = {}
            for field in schema_fields:
                value = record.get(field)
                # Convert all values to string (None becomes None)
                normalized_record[field] = str(value) if value is not None else None
            normalized.append(normalized_record)
        
        return normalized
    
    def _fetch_from_api(self, per_page: int = 200) -> list:
        """
        Fetch all brewery data from API with pagination
        
        Args:
            per_page: Records per page (API max is 200)
            
        Returns:
            List of brewery dictionaries
        """
        api_url = self.config.get("api", {}).get("url")
        timeout = self.config.get("api", {}).get("timeout", 30)
        retry_count = self.config.get("api", {}).get("retry_count", 3)
        
        all_data = []
        page = 1
        session = requests.Session()
        
        self._log(f"Fetching from {api_url}")
        
        while True:
            try:
                self._log(f"  Page {page}...")
                
                resp = session.get(
                    api_url,
                    params={"per_page": per_page, "page": page},
                    timeout=timeout
                )
                resp.raise_for_status()
                
                data = resp.json()
                
                if not data:
                    self._log(f"Pagination complete. Total pages: {page - 1}")
                    break
                
                all_data.extend(data)
                self._log(f"  Page {page}: {len(data)} records (Total: {len(all_data)})")
                
                page += 1
                time.sleep(0.2)  # Rate limiting
                
            except requests.exceptions.RequestException as e:
                self._log(f"API error on page {page}: {str(e)}", level="ERROR")
                if page == 1 or retry_count == 0:
                    raise
                retry_count -= 1
                time.sleep(2)
        
        return all_data


def fetch_and_save_bronze(api_url: str, base_path: str, per_page: int = 200) -> str:
    """
    Standalone function to fetch data from API and save to bronze layer
    
    Args:
        api_url: URL da API de cervejarias
        base_path: Caminho base para salvar dados
        per_page: Registros por página
        
    Returns:
        Caminho onde os dados foram salvos
    """
    all_data = []
    page = 1
    session = requests.Session()
    
    while True:
        resp = session.get(
            api_url,
            params={"per_page": per_page, "page": page},
            timeout=30
        )
        resp.raise_for_status()
        
        data = resp.json()
        
        if not data:
            break
        
        all_data.extend(data)
        page += 1
        time.sleep(0.2)
    
    # Save to bronze layer with partitioning
    partition_date = datetime.now().strftime('%Y-%m-%d')
    bronze_path = Path(base_path) / "bronze" / "breweries" / f"created_at={partition_date}"
    bronze_path.mkdir(parents=True, exist_ok=True)
    
    output_file = bronze_path / "data.json"
    with open(output_file, "w") as f:
        json.dump(all_data, f)
    
    return str(bronze_path.parent.parent)

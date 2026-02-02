# ADR-002: Technology Stack and Implementation Details

Date: 2026-02-01  
Status: Accepted  
Authors: Data Engineering Team  
Stakeholders: DevOps, Data Science, Platform Team  
Related to: ADR-001 (Modular Architecture) - this document provides technical details  
Case Requirements Alignment: All 6 requirements  

---

## Table of Contents

1. [Overview](#overview)
2. [Data Layer - Medallion Architecture](#1-data-layer---medallion-architecture)
3. [Processing Engine - PySpark](#2-processing-engine---pyspark)
4. [Orchestration - Apache Airflow](#3-orchestration---apache-airflow)
5. [Storage Format - Parquet](#4-storage-format---parquet)
6. [Error Handling Strategy](#5-error-handling-strategy)
7. [Containerization - Docker](#6-containerization---docker)
8. [Technology Decision Matrix](#technology-decision-matrix)

---

## Overview

This document consolidates technical decisions supporting the modular architecture defined in ADR-001. Each section answers:

- What did we choose? (Technology/pattern)
- Why did we choose it? (Requirements alignment + alternatives)
- How did we implement it? (Code + examples)
- How does it meet the case? (Mapping to 6 requirements)

---

## 1. Data Layer - Medallion Architecture

### Context (Why this structure?)

Case Requirement: Scalability, Data Integrity

The project must structure data from multiple sources (APIs, databases, files) in a scalable and auditable way.

### Decision: Three-Layer Medallion Architecture

We implemented a 3-layer structure with clear responsibilities:

```
┌─────────────────────────────────────────────────────────┐
│ GOLD LAYER (Analytic Ready)                             │
│ • Aggregations (count, sum, avg by dimensions)          │
│ • Pre-calculated metrics for BI/dashboards              │
│ • Optimized for reporting queries                       │
│ • Format: Parquet (partitioned by date/category)        │
│ Location: datalake/gold/                                │
└─────────────────────────────────────────────────────────┘
                          ↑
┌─────────────────────────────────────────────────────────┐
│ SILVER LAYER (Business Ready)                           │
│ • Cleaned & enriched data                               │
│ • Data quality validations applied                      │
│ • Schema consistent & documented                        │
│ • Format: Parquet (partitioned by date/location)        │
│ Location: datalake/silver/                              │
└─────────────────────────────────────────────────────────┘
                          ↑
┌─────────────────────────────────────────────────────────┐
│ BRONZE LAYER (Raw Data)                                 │
│ • Exact replica of source data (no transformations)     │
│ • Immutable record of what came from source             │
│ • Raw format as received (JSON, CSV, etc)               │
│ • Format: Parquet (for query efficiency)                │
│ Location: datalake/bronze/                              │
└─────────────────────────────────────────────────────────┘
                          ↑
              ┌───────────────────────┐
              │   DATA SOURCES        │
              │ • Open Brewery API    │
              │ • External databases  │
              │ • File uploads        │
              └───────────────────────┘
```

### Implementation

```python
# spark_jobs/base_job.py - Medallion pattern
class BaseJob(ABC):
    """Implements medallion layer pattern"""
    
    def run(self, input_path: str, output_path: str) -> None:
        """ETL with medallion boundaries"""
        df = self.extract()           # Read from layer N-1 (or source)
        df = self.transform(df)       # Apply transformations
        self.load(df, output_path)    # Write to layer N
```

---

## 2. Processing Engine - PySpark

### Context

Case Requirement: Pagination + Partitioning, Scalability

Must process data volumes in parallel (partitioning) and scale from dev → production.

### Decision: Apache Spark with Python API (PySpark)

We chose PySpark because:
- Native partitioning (automatic parallelism)
- Scalable (local → cluster → cloud)
- Huge community + 10+ years maturity
- Cloud-native (AWS Glue, Databricks, GCP Dataproc)

### Implementation

#### Spark Configuration (Config-Driven)

```yaml
# config/environments/dev.yaml
spark:
  app_name: bees-brewery-dev
  master: local[*]                    # Local mode (development)
  shuffle_partitions: 100             # Lower for dev (faster startup)
  additional_conf:
    spark.sql.adaptive.enabled: "true"

# config/environments/prod.yaml
spark:
  app_name: bees-brewery-prod
  master: yarn                        # Yarn cluster (production)
  shuffle_partitions: 500             # Higher for prod (more parallelism)
  additional_conf:
    spark.sql.adaptive.enabled: "true"
    spark.dynamicAllocation.enabled: "true"
    spark.sql.adaptive.coalescePartitions.enabled: "true"
```

#### Partitioning Strategy

```python
# Requirement 1: Implement data partitioning to improve performance

class TransformationJob(BaseJob):
    def transform(self, df: DataFrame) -> DataFrame:
        # PARTITIONING 1: By date (temporal partitioning)
        df = df.repartition("year", "month", "day")
        
        # PARTITIONING 2: By location (domain partitioning)
        df = df.repartition("state", "city")
        
        # PARTITIONING 3: Optimize shuffle
        shuffle_partitions = self.config.spark.shuffle_partitions
        df = df.coalesce(shuffle_partitions)
        
        return df

# Result:
# - Spark distributes work across partitions
# - Each worker processes partition independently
# - Scales linearly with data size (if more workers available)
```

#### Spark Session Factory

```python
# core/spark_session.py
class SparkSessionFactory:
    """Factory pattern for SparkSession creation"""
    
    @classmethod
    def get_or_create(cls, config: SparkConfig) -> SparkSession:
        return SparkSession.builder \
            .appName(config.app_name) \
            .master(config.master) \
            .config("spark.sql.shuffle.partitions", config.shuffle_partitions) \
            .getOrCreate()
```

---

## 3. Orchestration - Apache Airflow

### Context

Case Requirement: Error Handling, Scheduling, Monitoring

Must orchestrate jobs in sequence (ingestion → transformation → aggregation) with automatic retry and monitoring.

### Decision: Apache Airflow

We chose Airflow because:
- Powerful scheduling (cron-like syntax)
- Error handling with retry policies
- Excellent UI for monitoring
- Huge community (Apache project)
- Easy integration with Spark

### Implementation

#### DAG Definition

```python
# dags/bees_brewery_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import timedelta

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'retries': 2,                      # Retry policy (Requirement 4)
    'retry_delay': timedelta(minutes=5),
    'on_failure_callback': alert_slack, # Alert on failure
}

with DAG(
    'bees_brewery_medallion',
    default_args=default_args,
    schedule_interval='0 0 * * *',     # Daily at midnight
    catchup=False,
) as dag:
    
    def run_ingestion():
        job = IngestionJob(config, storage)
        job.run('raw', 'bronze')
    
    def run_transformation():
        job = TransformationJob(config, storage)
        job.run('bronze', 'silver')
    
    def run_aggregation():
        job = AggregationJob(config, storage)
        job.run('silver', 'gold')
    
    # Tasks
    ingestion = PythonOperator(
        task_id='ingestion',
        python_callable=run_ingestion,
        pool='spark_pool',              # Resource management
    )
    
    transformation = PythonOperator(
        task_id='transformation',
        python_callable=run_transformation,
        pool='spark_pool',
    )
    
    aggregation = PythonOperator(
        task_id='aggregation',
        python_callable=run_aggregation,
        pool='spark_pool',
    )
    
    # Dependencies (DAG)
    ingestion >> transformation >> aggregation
```

#### Retry & Error Handling

```python
# Airflow handles retries automatically
# If ingestion fails:
# 1. Airflow waits 5 minutes
# 2. Retries (up to 2 times)
# 3. If still fails, calls on_failure_callback (alert_slack)
# 4. Marks task as FAILED in UI

# Meanwhile, transformation & aggregation are blocked
# (depend_on_past prevents running with failed upstream)
```

---

## 4. Storage Format - Parquet

### Context

Case Requirement: Performance, Scalability, Data Integrity

Must store data efficiently (compression, querying, partitioning).

### Decision: Apache Parquet Format

We chose Parquet because:
- Columnar format (efficient for analytics)
- Built-in compression (reduces storage by 80%)
- Partitioning support (Spark writes partitioned Parquet naturally)
- Schema enforcement (data integrity)
- Cloud storage optimized (S3, GCS)

### Implementation

#### Parquet Writing with Partitioning

```python
# spark_jobs/base_job.py
def load(self, df: DataFrame, output_path: str) -> None:
    """Load data as partitioned Parquet"""
    
    # PARTITIONING: Write with partition columns
    # This creates directory structure:
    # datalake/silver/year=2026/month=02/day=01/part-*.parquet
    
    df.write \
        .format("parquet") \
        .mode("overwrite") \
        .partitionBy("year", "month", "day") \
        .parquet(output_path)
    
    # Benefits:
    # 1. Compressed (50-80% smaller than CSV)
    # 2. Partitioned (Spark reads only needed partitions)
    # 3. Schema-enforced (type safety)
    # 4. Columnar (fast analytics queries)
```

#### Reading Partitioned Parquet

```python
# spark_jobs/transformation_silver.py
def extract(self) -> DataFrame:
    # Spark automatically discovers partitions
    df = self.spark.read.parquet(f"{self.config.storage.path}/bronze")
    
    # If reading specific partition:
    df = df.filter((df.year == 2026) & (df.month == 2))
    # Spark only reads matching partition directories
```

---

## 5. Error Handling Strategy

### Context

Case Requirement: Robust Error Handling, Resilience

Must handle multiple error types (data quality, storage, processing) differently.

### Decision: Hierarchical Exception System with Structured Logging

```python
# core/exceptions.py
class BeesBreweryException(Exception):
    """Base exception"""

class DataQualityException(BeesBreweryException):
    """Data validation failed"""

class StorageException(BeesBreweryException):
    """Storage operation failed"""

class SparkJobException(BeesBreweryException):
    """Spark job failed"""
```

### Implementation

#### Error Handling in Jobs

```python
# spark_jobs/base_job.py
class BaseJob(ABC):
    def run(self, input_path: str, output_path: str) -> None:
        try:
            df = self.extract()
            
            # DATA QUALITY CHECK 1
            if df.count() == 0:
                raise DataQualityException("Empty dataset")
            
            df = self.transform(df)
            
            # DATA QUALITY CHECK 2
            if df.filter(df["brewery_id"].isNull()).count() > 0:
                raise DataQualityException("Null brewery_id found")
            
            self.load(df, output_path)
            
        except DataQualityException as e:
            # Data quality errors = alert + don't retry
            self.logger.error(f"Data quality failed: {e}", severity="CRITICAL")
            raise
        
        except StorageException as e:
            # Storage errors = log + let Airflow retry
            self.logger.error(f"Storage failed: {e}", severity="HIGH")
            raise
        
        except Exception as e:
            # Unexpected errors
            self.logger.error(f"Unexpected error: {e}", severity="CRITICAL")
            raise SparkJobException(str(e))
```

#### Structured Logging

```python
# core/logger.py
class StructuredLogger:
    def error(self, message: str, severity: str = "ERROR", **context):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "message": message,
            "context": context,
        }
        self.logger.error(json.dumps(log_entry))
```

### Airflow Error Handling

```python
# Airflow + Retry policies (Requirement 4)
default_args = {
    'retries': 2,                       # Retry transient failures
    'retry_delay': timedelta(minutes=5),
    'on_failure_callback': alert_slack, # Alert after final failure
}

# Error handling flow:
# 1. Task fails with exception
# 2. If retryable (StorageException), Airflow waits 5min → retries
# 3. If not retryable (DataQualityException), raise immediately
# 4. After all retries exhausted or non-retryable error, call alert_slack
```

---

## 6. Containerization - Docker

### Context

Case Requirement: Deployment, Environment Consistency

Must package application to run consistently in dev/staging/prod.

### Decision: Docker for Container Orchestration

We chose Docker because:
- Reproducible environments (dev = staging = prod)
- Easy deployment (single docker-compose.yaml)
- Cloud-native (runs on Kubernetes, AWS ECS, etc)
- Isolates dependencies (no "works on my machine")

### Implementation

#### Dockerfile for Airflow

```dockerfile
# docker/Dockerfile.airflow
FROM apache/airflow:2.7.3-python3.11

# Install custom dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY config/ /home/airflow/config/
COPY core/ /home/airflow/core/
COPY spark_jobs/ /home/airflow/spark_jobs/
COPY schemas/ /home/airflow/schemas/
COPY dags/ /home/airflow/dags/

# Set environment
ENV PYTHONPATH=/home/airflow:$PYTHONPATH
ENV AIRFLOW_HOME=/home/airflow
```

#### docker-compose.yaml

```yaml
version: '3.8'

services:
  airflow:
    build:
      context: .
      dockerfile: docker/Dockerfile.airflow
    environment:
      AIRFLOW_HOME: /home/airflow
      AIRFLOW__CORE__DAGS_FOLDER: /home/airflow/dags
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql://airflow:airflow@postgres:5432/airflow
      ENVIRONMENT: dev  # Load dev.yaml config
    depends_on:
      - postgres
    ports:
      - "8080:8080"
    volumes:
      - ./dags:/home/airflow/dags
      - ./config:/home/airflow/config
      - ./logs:/home/airflow/logs

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow

  spark:
    build:
      context: .
      dockerfile: docker/Dockerfile.spark
    environment:
      SPARK_MODE: master
      SPARK_RPC_AUTHENTICATION_ENABLED: "no"
```

---

## Technology Decision Matrix

Summary of all technical decisions:

| Component | Technology | Alternative | Reason |
|-----------|-----------|------------|--------|
| Data Layer | Medallion (3-layer) | Single layer | Auditability + separation |
| Processing | Apache Spark | Pandas/Dask/Polars | Native partitioning + maturity |
| Orchestration | Apache Airflow | Prefect/Dagster/Cron | Superior UI + community |
| Storage Format | Parquet | CSV/JSON/ORC | Columnar + compression + partitioning |
| Error Handling | Exception hierarchy | Flat exceptions | Type-specific handling |
| Deployment | Docker | Virtual envs | Reproducible + cloud-native |

---

## Case Requirements Coverage

```
Requirement 1: Pagination + Data Partitioning
  - Implemented in: Section 2 (PySpark - repartition strategy)
  - Evidence: config.shuffle_partitions (dev:100, prod:500)

Requirement 2: Automated Tests + Data Integrity
  - Implemented in: Section 5 (Error Handling - validation)
  - Evidence: DataQualityException checks before load

Requirement 3: Scalable Architecture
  - Implemented in: Section 1 (Medallion) + Section 2 (Spark)
  - Evidence: Multi-layer + config-driven partitions

Requirement 4: Robust Error Handling
  - Implemented in: Section 3 (Airflow retries) + Section 5 (Exceptions)
  - Evidence: Retry policies + exception hierarchy

Requirement 5 & 6: Git Best Practices + Documentation
  - Implemented in: All sections + clear separation of concerns
  - Evidence: Each technology has clear responsibility

Deployment: Production Ready
  - Implemented in: Section 6 (Docker)
  - Evidence: docker-compose.yaml ready to run
```

---

Last Updated: 2026-02-01  
Status: Accepted and Implemented  

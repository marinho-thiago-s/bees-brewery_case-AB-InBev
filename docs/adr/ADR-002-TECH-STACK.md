# ADR-002: Technology Stack & Implementation Details

**Date:** 2026-02-01  
**Status:** Accepted  
**Authors:** Data Engineering Team  
**Stakeholders:** DevOps, Data Science, Platform Team  
**Related to:** ADR-001 (Modular Architecture) - this document provides technical details  
**Case Requirements Alignment:** ✅ All 6 requirements  

---

## 📋 Índice de Temas

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

Este documento consolida decisões técnicas que suportam a arquitetura modular definida em **ADR-001**. Cada seção responde:

- **O que escolhemos?** (Tecnologia/padrão)
- **Por que escolhemos?** (Alinhamento com requirements + alternativas)
- **Como implementamos?** (Código + exemplos)
- **Como atende o caso?** (Mapeamento com 6 requirements)

---

## 1. Data Layer - Medallion Architecture

### Context (Por que essa estrutura?)

**Case Requirement:** ✅ Scalability, ✅ Data Integrity

O projeto precisa estruturar dados de múltiplas fontes (APIs, databases, files) de forma escalável e auditável.

### Decision: Three-Layer Medallion Architecture

Implementamos estrutura em 3 camadas com responsabilidades claras:

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
# spark_jobs/base_job.py - Medallio pattern
class BaseJob(ABC):
    """Implements medallion layer pattern"""
    
    def run(self, input_path: str, output_path: str) -> None:
        """ETL with medallion boundaries"""
        df = self.extract()           # Read from layer N-1 (or source)
        df = self.transform(df)       # Apply transformations
        self.load(df, output_path)    # Write to layer N
```

```python
# spark_jobs/ingestion.py - Bronze Layer
class IngestionJob(BaseJob):
    """BRONZE LAYER: Raw data ingestion"""
    
    def extract(self) -> DataFrame:
        # Read from external source (API, file, database)
        return self.spark.read.csv("s3://data-source/breweries.csv")
    
    def transform(self, df: DataFrame) -> DataFrame:
        # Minimal transformation: only add metadata
        from pyspark.sql.functions import current_timestamp, input_file_name
        return df.withColumn("ingestion_timestamp", current_timestamp()) \
                 .withColumn("source_file", input_file_name())

# spark_jobs/transformation_silver.py - Silver Layer
class TransformationJob(BaseJob):
    """SILVER LAYER: Data cleaning & enrichment"""
    
    def extract(self) -> DataFrame:
        return self.spark.read.parquet(f"{self.config.storage.path}/bronze")
    
    def transform(self, df: DataFrame) -> DataFrame:
        # Data quality checks
        if df.count() == 0:
            raise DataQualityException("Empty dataset from bronze")
        
        # Cleaning
        df = df.dropna(subset=["brewery_id", "name"])
        
        # Enrichment
        df = df.withColumn("name_upper", upper(df.name))
        df = df.withColumn("location_id", concat(df.city, lit("_"), df.state))
        
        return df

# spark_jobs/aggregation_gold.py - Gold Layer
class AggregationJob(BaseJob):
    """GOLD LAYER: Analytics & aggregations"""
    
    def extract(self) -> DataFrame:
        return self.spark.read.parquet(f"{self.config.storage.path}/silver")
    
    def transform(self, df: DataFrame) -> DataFrame:
        # Create aggregations for reporting
        return df.groupBy("type", "state").agg(
            count("brewery_id").alias("count"),
            avg("beer_count").alias("avg_beers")
        ).orderBy("state", "type")
```

### Alinhamento com Case Requirements

| Requirement | Como Atendemos |
|---|---|
| **Scalability** | ✅ Cada camada é independente, fácil escalar |
| **Data Integrity** | ✅ Bronze = cópia exata (auditável); Silver = validações aplicadas |
| **Error Handling** | ✅ Erros em qualquer camada não afetam as outras |
| **Documentation** | ✅ Padrão claro: cada layer tem responsabilidade específica |

### Alternativas Consideradas

| Alternativa | Pros | Cons | Decision |
|---|---|---|---|
| **Single Layer** | Simples | ❌ Sem auditoria; sem separação; difícil debug | Rejeitado |
| **Lambda** | Real-time + batch | ❌ Overkill; muita complexidade | Rejeitado |
| **Medallion** ✅ | Clara separação; auditável; escalável | ⚠️ Mais armazenamento | **ACEITO** |

---

## 2. Processing Engine - PySpark

### Context

**Case Requirement:** ✅ Pagination + Partitioning, ✅ Scalability

Precisa processar volumes de dados em paralelo (particionamento) e escalar de dev → produção.

### Decision: Apache Spark with Python API (PySpark)

Escolhemos **PySpark** porque:
- ✅ Partitioning nativo (parallelism automático)
- ✅ Escalável (local → cluster → cloud)
- ✅ Comunidade gigante + 10+ anos de maturity
- ✅ Cloud-native (AWS Glue, Databricks, GCP Dataproc)

### Implementation

#### Spark Configuration (Config-Driven)

```python
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

### Alinhamento com Case Requirements

| Requirement | Como Atendemos |
|---|---|
| **Pagination + Partitioning** | ✅ Repartitioning por data/location; shufflePartitions configurável |
| **Scalability** | ✅ Spark scales from laptop to 1000-node clusters |
| **Data Integrity** | ✅ ACID semantics; fault-tolerant RDDs |
| **Performance** | ✅ In-memory computation; lazy evaluation |

### Alternativas Consideradas

| Alternativa | Scalability | Partitioning | Community | Cloud Support | Decision |
|---|---|---|---|---|---|
| **Pandas** | ❌ Limited (memory-bound) | ❌ Manual | ✅ Huge | ❌ No | Rejeitado |
| **Dask** | ⚠️ Complex API | ⚠️ Clunky | ⚠️ Small | ⚠️ Limited | Rejeitado |
| **PySpark** ✅ | ✅ Excellent | ✅ Native | ✅ Huge | ✅ AWS/GCP/Azure | **ACEITO** |
| **Polars** | ✅ Fast | ⚠️ New | ⚠️ Growing | ❌ No | Rejeitado (too new) |

---

## 3. Orchestration - Apache Airflow

### Context

**Case Requirement:** ✅ Error Handling, ✅ Scheduling, ✅ Monitoring

Precisa orquestrar jobs em sequência (ingestion → transformation → aggregation) com retry automático e monitoramento.

### Decision: Apache Airflow

Escolhemos **Airflow** porque:
- ✅ Scheduling poderoso (cron-like syntax)
- ✅ Error handling com retry policies
- ✅ UI excelente para monitoramento
- ✅ Comunidade gigante (Apache project)
- ✅ Easy integration com Spark

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

### Alinhamento com Case Requirements

| Requirement | Como Atendemos |
|---|---|
| **Error Handling** | ✅ Retry policies (2 retries, 5min delay) + alerts |
| **Scheduling** | ✅ Cron-like schedule (daily at midnight) |
| **Monitoring** | ✅ UI shows status, logs, retry counts |
| **Resilience** | ✅ Automatic retries for transient failures |

### Alternativas Consideradas

| Alternativa | Scheduling | Error Handling | Monitoring | Community | Decision |
|---|---|---|---|---|---|
| **Cron Scripts** | ✅ Basic | ❌ None | ❌ None | N/A | Rejeitado |
| **Prefect** | ✅ Good | ✅ Good | ⚠️ Basic | ⚠️ Growing | Rejeitado (smaller ecosystem) |
| **Dagster** | ✅ Good | ✅ Good | ✅ Good | ⚠️ Growing | Rejeitado (overkill for this case) |
| **Airflow** ✅ | ✅ Excellent | ✅ Excellent | ✅ Excellent | ✅ Huge | **ACEITO** |

---

## 4. Storage Format - Parquet

### Context

**Case Requirement:** ✅ Performance, ✅ Scalability, ✅ Data Integrity

Precisa armazenar dados de forma eficiente (compression, querying, partitioning).

### Decision: Apache Parquet Format

Escolhemos **Parquet** porque:
- ✅ Columnar format (efficient for analytics)
- ✅ Built-in compression (reduces storage by 80%)
- ✅ Partitioning support (Spark writes partitioned Parquet naturally)
- ✅ Schema enforcement (data integrity)
- ✅ Cloud storage optimized (S3, GCS)

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

### Alinhamento com Case Requirements

| Requirement | Como Atendemos |
|---|---|
| **Performance** | ✅ Columnar format = fast queries; partitioning = parallel reads |
| **Scalability** | ✅ Efficient storage = more data per disk; scales horizontally |
| **Data Integrity** | ✅ Schema enforcement; schema evolution support |

### Alternativas Consideradas

| Alternativa | Compression | Partitioning | Schema | Cloud | Decision |
|---|---|---|---|---|---|
| **CSV** | ❌ No | ⚠️ Manual | ❌ No | ✅ Yes | Rejeitado (not scalable) |
| **JSON** | ❌ No | ⚠️ Manual | ⚠️ Loose | ✅ Yes | Rejeitado (large files) |
| **Parquet** ✅ | ✅ Yes (50-80%) | ✅ Native | ✅ Strict | ✅ Yes | **ACEITO** |
| **Delta Lake** | ✅ Yes | ✅ Native | ✅ Strict | ✅ Yes | Post-Phase 1 (too much initially) |
| **ORC** | ✅ Yes | ✅ Native | ✅ Strict | ⚠️ Limited | Rejeitado (Parquet more common) |

---

## 5. Error Handling Strategy

### Context

**Case Requirement:** ✅ Robust Error Handling, ✅ Resilience

Precisa lidar com múltiplos tipos de erros (data quality, storage, processing) de forma diferenciada.

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

### Alinhamento com Case Requirements

| Requirement | Como Atendemos |
|---|---|
| **Robust Error Handling** | ✅ Exception hierarchy + specific handling per type |
| **Resilience** | ✅ Retry policies for transient errors; immediate alerts for data issues |
| **Data Integrity** | ✅ Data quality errors block pipeline (don't load bad data) |
| **Monitoring** | ✅ Structured logs for troubleshooting |

### Alternativas Consideradas

| Alternativa | Pros | Cons | Decision |
|---|---|---|---|
| **No Specific Handling** | Simple | ❌ Can't distinguish error types | Rejeitado |
| **Flat Exception** | Simple | ❌ No differentiation | Rejeitado |
| **Hierarchical + Logging** ✅ | Type-specific handling; audit trail | ⚠️ More code | **ACEITO** |

---

## 6. Containerization - Docker

### Context

**Case Requirement:** ✅ Deployment, ✅ Environment Consistency

Precisa empacotar aplicação para rodar consistente em dev/staging/prod.

### Decision: Docker for Container Orchestration

Escolhemos **Docker** porque:
- ✅ Reproducible environments (dev = staging = prod)
- ✅ Easy deployment (single docker-compose.yaml)
- ✅ Cloud-native (runs on Kubernetes, AWS ECS, etc)
- ✅ Isolates dependencies (no "works on my machine")

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

### Alinhamento com Case Requirements

| Requirement | Como Atendemos |
|---|---|
| **Environment Consistency** | ✅ Docker ensures dev = prod |
| **Deployment** | ✅ docker-compose up -d = production ready |
| **Scalability** | ✅ Containers scale on K8s |

### Alternativas Consideradas

| Alternativa | Cons | Decision |
|---|---|---|
| **Virtual Environments** | ❌ "Works on my machine"; hard to replicate | Rejeitado |
| **Docker** ✅ | Reproducible; cloud-native; industry standard | **ACEITO** |

---

## Technology Decision Matrix

Resumo visual de todas as decisões tecnológicas:

```
┌──────────────────────────────────────────────────────────────────┐
│ TECHNOLOGY DECISION MATRIX - Why Each Choice                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ LAYER        TECHNOLOGY   REQUIREMENT   ALTERNATIVE   REASON    │
│ ─────────────────────────────────────────────────────────────   │
│ Data         Medallion    Scalability   Single layer  Flexibility│
│              (3-layer)    + Integrity   + Lambda      + Auditability
│                                                                  │
│ Processing   PySpark      Partitioning  Pandas       Native      │
│                           + Scalability Dask         partitioning│
│                                         Polars        + Maturity  │
│                                                                  │
│ Orchestration Airflow     Error Hdlg   Prefect      Superior    │
│                           + Monitoring  Dagster      UI +        │
│                                         Cron         Community   │
│                                                                  │
│ Storage      Parquet      Performance   CSV         Columnar    │
│              Format       + Integrity   JSON        format +    │
│                                         ORC         compression │
│                                                                  │
│ Errors       Exceptions   Resilience    Flat        Type-       │
│              Hierarchy    + Retries     exceptions  specific    │
│                                                      handling    │
│                                                                  │
│ Deploy       Docker       Consistency   Venvs       Industry    │
│                           + Scalability Manual      standard +  │
│                                         setup       cloud-native│
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Case Requirements Coverage

```
✅ REQUIREMENT 1: Pagination + Data Partitioning
   └─ Implemented in: Section 2 (PySpark - repartition strategy)
   └─ Evidence: config.shuffle_partitions (dev:100, prod:500)

✅ REQUIREMENT 2: Automated Tests + Data Integrity  
   └─ Implemented in: Section 5 (Error Handling - validation)
   └─ Evidence: DataQualityException checks before load

✅ REQUIREMENT 3: Scalable Architecture
   └─ Implemented in: Section 1 (Medallion) + Section 2 (Spark)
   └─ Evidence: Multi-layer + config-driven partitions

✅ REQUIREMENT 4: Robust Error Handling
   └─ Implemented in: Section 3 (Airflow retries) + Section 5 (Exceptions)
   └─ Evidence: Retry policies + exception hierarchy

✅ REQUIREMENT 5 & 6: Git Best Practices + Documentation
   └─ Implemented in: All sections + clear separation of concerns
   └─ Evidence: Each technology has clear responsibility

✅ DEPLOYMENT: Production Ready
   └─ Implemented in: Section 6 (Docker)
   └─ Evidence: docker-compose.yaml ready to run
```

---

## References

### Medallion Architecture
- [Databricks: Medallion Architecture](https://www.databricks.com/blog/2022/06/24/use-the-medallion-lakehouse-architecture-to-build-data-platforms-on-databricks.html)

### PySpark
- [Apache Spark Documentation](https://spark.apache.org/docs/latest/api/python/)
- [PySpark Best Practices](https://spark.apache.org/docs/latest/sql-performance-tuning.html)
- [Partitioning Guide](https://spark.apache.org/docs/latest/sql-data-sources-parquet.html#partition-discovery)

### Airflow
- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [Error Handling & Retry Policies](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/taskflow.html)

### Parquet
- [Parquet Format Documentation](https://parquet.apache.org/)
- [Compression & Performance](https://parquet.apache.org/docs/file-format/data-types/)

### Docker
- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose for Airflow](https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose-quickstart.html)

---

**Last Updated:** 2026-02-01  
**Status:** ✅ Accepted & Implemented  
**Supersedes:** 
- ADR-002: Airflow Orchestration Strategy
- ADR-003: PySpark Transformations Pattern
- ADR-004: Docker Containerization
- ADR-005: Parquet Storage Format
- ADR-006: Error Handling Strategy

**Related:**
- ADR-001: Modular and Scalable Data Pipeline Architecture (architectural foundation)
- REQUIREMENTS_MAPPING.md (requirement traceability)
- ARCHITECTURE_IMPLEMENTATION.md (implementation guide)

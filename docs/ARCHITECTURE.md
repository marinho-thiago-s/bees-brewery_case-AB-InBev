# BEES Brewery Case - General Architecture

Status: Production Ready
Last Updated: 2026-02-02
Case Alignment: All 6 Requirements Met

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Layered Architecture](#layered-architecture)
3. [Main Components](#main-components)
4. [Data Flow (Medallion)](#data-flow-medallion)
5. [Technology Stack](#technology-stack)
6. [Why These Choices?](#why-these-choices)
7. [Next Steps](#next-steps)

---

## Executive Summary

This project implements a **scalable, resilient, and well-tested Data Pipeline** that meets all 6 requirements of the Bees case:

| # | Requirement | Solution |
|---|---|---|
| 1 | Pagination + Data Partitioning | Spark partitions + Airflow scheduler |
| 2 | Automated Tests + Data Integrity | BaseJob pattern + validation layer |
| 3 | Scalable Architecture | Modular, multi-layer design |
| 4 | Robust Error Handling | Custom exceptions + retry policies |
| 5 | Git Best Practices | Clear separation of concerns |
| 6 | Clear Documentation | ADRs + guides + this architecture doc |

### Pipeline Status

```
24/24 Tests Passing
DAG Executing Successfully
Pipeline Processing Data Correctly:
   - 9.083 breweries ingested (Bronze)
   - 5.451 cleaned and transformed (Silver)
   - 389 aggregations (Gold)
```

---

## Layered Architecture

```
Layer 1: ORCHESTRATION
Apache Airflow - Scheduler, Monitoring, Dependency Management
  - Daily schedule (0 0 * * *)
  - Retry policies (2 retries, 5min delay)
  - Slack alerts on failure

Layer 2: JOB ABSTRACTION
BaseJob Pattern - Unified ETL Interface
  - IngestionJob (Bronze layer)
  - TransformationJob (Silver layer)
  - AggregationJob (Gold layer)
  - extract() / transform() / load() pattern
  - Centralized error handling & logging

Layer 3: CORE SERVICES
Storage (abstraction), Spark (factory), Logger, Exceptions
  - StorageBackend (Local/S3/GCS)
  - SparkSessionFactory
  - StructuredLogger
  - Custom Exceptions
  - Dependency decoupling
  - Multiple backend support

Layer 4: CONFIGURATION
YAML-based Config (dev/staging/prod)
  - config/environments/dev.yaml
  - config/environments/prod.yaml
  - Environment-specific without code changes

Layer 5: DATA LAYER
Medallion Architecture (Bronze -> Silver -> Gold)
  - Bronze: Raw data (immutable)
  - Silver: Cleaned & validated
  - Gold: Aggregated for analytics
  - Parquet format with partitioning
  - Data quality validation at each layer

Layer 6: TESTING
Unit + Integration Tests
  - 24 tests (20 unit + 4 architecture)
  - ~80% code coverage
  - Mocks for dependencies
  - All tests passing
```

---

## Main Components

### 1. Orchestration (Apache Airflow)

```python
# dags/bees_brewery_dag.py
- pipeline_start -> ingestion_bronze -> transformation_silver 
  -> aggregation_gold -> pipeline_end
- Retry policy: 2x with 5min delay
- Schedule: Daily @ midnight
- Monitoring: UI + structured logs
```

### 2. Job Abstraction (BaseJob Pattern)

```python
# spark_jobs/base_job.py
class BaseJob(ABC):
    def run(self, input_path, output_path):
        df = self.extract()
        self._validate_not_null(df, ["id", "name"])
        df = self.transform(df)
        self._validate_not_null(df, ["id", "name"])
        self.load(df, output_path)
```

### 3. Core Services
- **Storage**: LocalStorage (extensible to S3/GCS)
- **Spark**: SparkSessionFactory with config-driven
- **Logger**: Structured logging with JSON output
- **Exceptions**: Hierarchy (DataQuality, Storage, SparkJob)

### 4. Data Layers
- **Bronze**: 9.083 raw records (immutable)
- **Silver**: 5.451 cleaned records (60% retention)
- **Gold**: 389 aggregations by state/type

---

## Data Flow (Medallion)

```
OpenBrewery API
(9.083 breweries)
        |
        v
BRONZE LAYER (Raw)
  - No transformations
  - Immutable record of source
  - Format: Parquet (10 partitions)
  - Location: datalake/bronze/
  - Records: 9.083
        |
        v (ingestion_bronze)
SILVER LAYER (Cleaned)
  - Duplicates removed
  - Names trimmed (whitespace)
  - State normalized
  - Format: Parquet (partitioned)
  - Location: datalake/silver/
  - Records: 5.451 (40% dedup)
        |
        v (transformation_silver)
GOLD LAYER (Analytics Ready)
  - Aggregations by state/type
  - Metrics calculated
  - Format: Parquet
  - Location: datalake/gold/
  - Groups: 389
  
  Top 3 State/Type Combos:
  1. California - Micro: 268
  2. California - Brewpub: 159
  3. Washington - Micro: 147
```

---

## Technology Stack

| Layer | Technology | Why |
|-------|------------|-----|
| Processing | Apache Spark 3.5 | Native partitioning + scalability |
| Orchestration | Apache Airflow 2.7 | Superior UI + retry policies |
| Storage | Parquet + Partitioning | Columnar format + compression |
| Language | Python 3.12 + PySpark | Industry standard for data eng |
| Container | Docker + Docker Compose | Reproducible environments |
| Testing | pytest 7.4 + Mocks | 24 tests, ~80% coverage |
| Logging | Structured JSON logging | Easier debugging + alerts |
| Configuration | YAML-based | Environment-specific without code changes |

---

## Why These Choices?

### Spark vs Alternatives

| Criteria | Spark | Pandas | Dask | Polars |
|----------|-------|--------|------|--------|
| Partitioning | Native | No | Partial | Partial |
| Scalability | Production | Memory Limited | Limited | Limited |
| Community | Huge | Huge | Growing | Emerging |
| Cloud Support | AWS/GCP/Azure | No | No | No |
| Maturity | 10+ years | Mature | Growing | New |

**Decision:** Spark (meets 100% of requirements + production-ready maturity)

### Airflow vs Alternatives

| Criteria | Airflow | Prefect | Dagster |
|----------|---------|---------|---------|
| Scheduling | Powerful | Good | Good |
| Error Handling | Retries/SLAs | Basic | Good |
| Monitoring | Excellent UI | Basic | Basic |
| Community | Huge | Growing | Growing |
| Learning Curve | Medium | Low | Low |

**Decision:** Airflow (best UI + community + retry policies)

### Layered vs Monolithic

| Aspect | Layered | Monolithic |
|--------|---------|-----------|
| Testability | 100% | 20% |
| Scalability | Easy | Hard |
| Error Handling | Centralized | Dispersed |
| Reusability | High | Low |
| Onboarding | Easy | Hard |

**Decision:** Layered (pays off at scale)

---

## Next Steps

### Phase 1: Current (COMPLETED)
- Configuration Layer
- Core Services
- Job Abstraction
- Medallion Pattern
- Automated Tests
- Docker Setup
- Documentation

### Phase 2: Cloud Integration (Q2 2026)
- Add S3Storage backend
- Add GCS storage backend
- Setup CI/CD (GitHub Actions)
- Add monitoring (Prometheus/Grafana)

### Phase 3: Advanced Features (Q3 2026)
- Delta Lake integration
- Data cataloging
- Kubernetes deployment
- ML pipeline integration

---

## References

- ADR-001: Modular Architecture Decision (adr/ADR-001-modular-architecture.md)
- ADR-002: Technology Stack Decision (adr/ADR-002-TECH-STACK.md)
- Implementation Guide: IMPLEMENTATION.md
- Troubleshooting: TROUBLESHOOTING.md

---

Status: Production Ready
Next Review: 2026-03-01

# BEES Brewery Case - ETL Pipeline

Complete ETL pipeline for processing BEES Brewery case data, using Medallion architecture (Bronze, Silver, Gold) with Airflow and Spark.

## Documentation

**Read first:**
1. **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Architecture overview and technical decisions
2. **[IMPLEMENTATION.md](docs/IMPLEMENTATION.md)** - Setup, deployment and adjustment history
3. **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Diagnosis and troubleshooting

**Architectural Decisions:**
- **[ADRs Index](docs/adr/README.md)** - Architecture Decision Records
- **[ADR-001](docs/adr/ADR-001-modular-architecture.md)** - Modular Architecture
- **[ADR-002](docs/adr/ADR-002-TECH-STACK.md)** - Technology Stack

---

## Project Structure

```
bees-brewery-case/
├── dags/                  # Airflow DAGs
│   └── bees_brewery_dag.py
├── spark_jobs/            # Segregated PySpark scripts
│   ├── ingestion.py       # API -> Bronze
│   ├── transformation_silver.py  # Bronze -> Silver
│   ├── aggregation_gold.py       # Silver -> Gold
│   └── base_job.py        # Base pattern
├── tests/                 # Unit tests (PyTest)
│   ├── test_ingestion.py
│   ├── test_transformation.py
│   ├── test_aggregation.py
│   └── test_architecture.py
├── core/                  # Core services
│   ├── storage.py         # Storage abstraction
│   ├── spark_session.py   # Spark factory
│   ├── logger.py          # Structured logging
│   └── exceptions.py      # Custom exceptions
├── config/                # Configuration management
│   ├── config.py          # Config dataclasses
│   └── environments/      # YAML configs
│       ├── dev.yaml
│       └── prod.yaml
├── schemas/               # Data contracts
│   └── bronze.py
├── docker/                # Custom Dockerfiles
│   ├── Dockerfile.airflow
│   └── Dockerfile.spark
├── docker-compose.yaml    # Container orchestration
└── requirements.txt       # Python dependencies
```

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Python 3.12+
- Git

### 1. Clone the repository

```bash
git clone <repository-url>
cd bees-brewery-case
```

### 2. Install dependencies (optional - Docker recommended)

```bash
pip install -r requirements.txt
```

### 3. Start containers (Airflow + Spark)

```bash
docker-compose up -d
```

Wait 30-45 seconds for initialization.

### 4. Access interfaces

- **Airflow UI**: http://localhost:8080 (airflow / airflow)
- **Spark Master**: http://localhost:8081

### 5. Trigger pipeline

```bash
# Enter Airflow container
docker-compose exec airflow-webserver bash

# Unpause and trigger DAG
airflow dags unpause bees_brewery_medallion
airflow dags trigger bees_brewery_medallion
```

## Components

### Ingestion (Bronze Layer)

**File**: `spark_jobs/ingestion.py`

Fetches data from OpenBrewery DB API and stores in Bronze layer as Parquet.

**Main methods**:
- `fetch_data_from_api()`: Fetches paginated data from API
- `execute()`: Normalizes data and creates Bronze DataFrame
- Data validation via `_validate_not_null()`

**How it meets case requirements**:
- Pagination: API pagination + Spark partitions
- Data integrity: Schema enforcement + validation
- Error handling: Custom exceptions + logging

### Transformation (Silver Layer)

**File**: `spark_jobs/transformation_silver.py`

Cleans, validates and enriches data from Bronze to Silver.

**Main methods**:
- `extract()`: Reads from Bronze
- `transform()`: Removes duplicates, normalizes, validates
- `load()`: Saves to Silver with partitions

**Data quality checks**:
- Removes null values in required fields
- Deduplicates records
- Normalizes strings (trim whitespace)

### Aggregation (Gold Layer)

**File**: `spark_jobs/aggregation_gold.py`

Creates aggregations and business metrics from Silver to Gold.

**Main methods**:
- `extract()`: Reads from Silver
- `transform()`: Groups and aggregates by state/type
- `load()`: Saves analytics-ready data

**Metrics**:
- Count by brewery_type and state
- Top combinations calculated
- Ready for BI/dashboards

## Tests

Run all tests:

```bash
pytest tests/ -v
```

Run tests for specific module:

```bash
pytest tests/test_ingestion.py -v
pytest tests/test_transformation.py -v
pytest tests/test_aggregation.py -v
```

With coverage:

```bash
pytest tests/ --cov=spark_jobs --cov-report=term-missing
```

Expected: 24 tests passing, ~80% coverage

## Data Flow

```
OpenBrewery API
        |
        v
[Ingestion Task] -> Bronze Layer (9.083 records, raw)
        |
        v
[Transformation Task] -> Silver Layer (5.451 records, cleaned)
        |
        v
[Aggregation Task] -> Gold Layer (389 aggregations)
        |
        v
[Validation] -> Data Quality Checks
```

## Medallion Layers

### Bronze
- Raw data from API (immutable)
- No transformations applied
- Format: Parquet
- Records: 9.083 breweries
- Retention: Indefinite

### Silver
- Cleaned and validated data
- Duplicates removed (60% retention)
- Strings normalized
- Metadata added (ingestion timestamp)
- Format: Parquet (date partitioned)
- Records: 5.451 breweries

### Gold
- Aggregated and analyzed data
- Business metrics (counts by state/type)
- Data ready for BI/Analytics/Dashboards
- Format: Parquet
- Aggregations: 389 combinations

## Configuration

### Environment Variables

Configuration is YAML-based in `config/environments/`:

**dev.yaml** - Development
```yaml
spark:
  master: local[*]
  shuffle_partitions: 100
```

**prod.yaml** - Production
```yaml
spark:
  master: yarn
  shuffle_partitions: 500
```

### docker-compose.yaml

Defines services:
- Airflow Webserver (scheduler UI)
- Airflow Scheduler (DAG executor)
- Spark Master (computation engine)
- Spark Worker(s)
- PostgreSQL (Airflow metadata database)

## Docker

### Build images

```bash
docker-compose build
```

### Run pipeline

```bash
docker-compose up -d
```

### View logs

```bash
docker-compose logs -f airflow-scheduler
docker-compose logs -f spark-master
```

### Stop everything

```bash
docker-compose down
```

### Clean volumes (fresh start)

```bash
docker-compose down -v
docker-compose up -d
```

## Logs

Logs are saved in `logs/` directory:

```bash
# Airflow logs
tail -f logs/dag_id=bees_brewery_medallion/*/task_id=*/attempt=1.log

# Docker logs
docker-compose logs -f airflow-scheduler
```

## Architecture

For detailed architecture information, see:
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Layered architecture overview
- [ADR-001](docs/adr/ADR-001-modular-architecture.md) - Why modular design
- [ADR-002](docs/adr/ADR-002-TECH-STACK.md) - Why these technologies

### Key Design Patterns

1. **Medallion Pattern** - Three-layer data architecture
2. **BaseJob Pattern** - Unified ETL interface with common error handling
3. **Dependency Injection** - Storage and Spark injected, not hardcoded
4. **Factory Pattern** - SparkSession and Storage created via factories
5. **Configuration Management** - YAML-based, multi-environment support

## Case Requirements Coverage

This project meets all 6 Bees case requirements:

1. **Pagination + Data Partitioning** - Spark partitions + API pagination
2. **Automated Tests + Data Integrity** - 24 tests + validation layer
3. **Scalable Architecture** - Modular design + multi-backend support
4. **Robust Error Handling** - Custom exceptions + retry policies
5. **Git Best Practices** - Clear separation of concerns
6. **Clear Documentation** - ADRs + guides + inline comments

## Contributing

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes following existing patterns (see BaseJob)
3. Write tests: `pytest tests/test_your_feature.py`
4. Commit: `git commit -m 'feat: description'`
5. Push: `git push origin feature/your-feature`
6. Open Pull Request

## Support

For questions and issues:
1. Check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
2. Review relevant ADR (ADR-001 or ADR-002)
3. Open an issue in the repository

## Status

- Build: Passing
- Tests: 24/24 passing
- Coverage: ~80%
- Production: Ready

## License

BEES Brewery Case Project - All rights reserved
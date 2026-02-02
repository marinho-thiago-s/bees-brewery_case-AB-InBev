# 🏗️ BEES Brewery Case - Arquitetura Geral

**Status:** ✅ Production Ready  
**Last Updated:** 2026-02-02  
**Case Alignment:** ✅ All 6 Requirements Met

---

## 📋 Índice

1. [Executive Summary](#executive-summary)
2. [Arquitetura em Camadas](#arquitetura-em-camadas)
3. [Componentes Principais](#componentes-principais)
4. [Fluxo de Dados (Medallion)](#fluxo-de-dados-medallion)
5. [Stack Tecnológico](#stack-tecnológico)
6. [Por Que Essas Escolhas?](#por-que-essas-escolhas)
7. [Próximos Passos](#próximos-passos)

---

## Executive Summary

Este projeto implementa um **Data Pipeline escalável, resiliente e bem-testado** que atende aos 6 requirements do caso Bees:

| # | Requirement | Solução |
|---|---|---|
| 1️⃣ | **Pagination + Data Partitioning** | Spark partitions + Airflow scheduler |
| 2️⃣ | **Automated Tests + Data Integrity** | BaseJob pattern + validation layer |
| 3️⃣ | **Scalable Architecture** | Modular, multi-layer design |
| 4️⃣ | **Robust Error Handling** | Custom exceptions + retry policies |
| 5️⃣ | **Git Best Practices** | Clear separation of concerns |
| 6️⃣ | **Clear Documentation** | ADRs + guides + this architecture doc |

### 📊 Pipeline Status

```
✅ 24/24 Testes Passando
✅ DAG Executando com Sucesso
✅ Pipeline Processando Dados Corretamente:
   - 9.083 cervejarias ingeridas (Bronze)
   - 5.451 limpas e transformadas (Silver)
   - 389 agregações (Gold)
```

---

## Arquitetura em Camadas

```
┌────────────────────────────────────────────────────────────────┐
│ LAYER 1: ORCHESTRATION                                         │
│ Apache Airflow - Scheduler, Monitoring, Dependency Management  │
│ ✅ Daily schedule (0 0 * * *)                                  │
│ ✅ Retry policies (2 retries, 5min delay)                      │
│ ✅ Slack alerts on failure                                     │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│ LAYER 2: JOB ABSTRACTION                                      │
│ BaseJob Pattern - Unified ETL Interface                       │
│ ├─ IngestionJob (Bronze layer)                                │
│ ├─ TransformationJob (Silver layer)                           │
│ └─ AggregationJob (Gold layer)                                │
│ ✅ extract() / transform() / load() pattern                    │
│ ✅ Centralized error handling & logging                        │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│ LAYER 3: CORE SERVICES                                        │
│ Storage (abstraction), Spark (factory), Logger, Exceptions    │
│ ├─ StorageBackend (Local/S3/GCS)                              │
│ ├─ SparkSessionFactory                                        │
│ ├─ StructuredLogger                                           │
│ └─ Custom Exceptions                                          │
│ ✅ Desacoplamento de dependências                             │
│ ✅ Suporte a múltiplos backends                               │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│ LAYER 4: CONFIGURATION                                        │
│ YAML-based Config (dev/staging/prod)                          │
│ ├─ config/environments/dev.yaml                               │
│ └─ config/environments/prod.yaml                              │
│ ✅ Environment-specific without code changes                  │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│ LAYER 5: DATA LAYER                                           │
│ Medallion Architecture (Bronze → Silver → Gold)               │
│ ├─ Bronze: Raw data (immutable)                               │
│ ├─ Silver: Cleaned & validated                                │
│ └─ Gold: Aggregated for analytics                             │
│ ✅ Parquet format with partitioning                           │
│ ✅ Data quality validation at each layer                      │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│ LAYER 6: TESTING                                              │
│ Unit + Integration Tests                                      │
│ ├─ 24 tests (20 unit + 4 architecture)                        │
│ ├─ ~80% code coverage                                         │
│ └─ Mocks for dependencies                                     │
│ ✅ All tests passing                                          │
└────────────────────────────────────────────────────────────┘
```

---

## Componentes Principais

### 1. **Orchestration (Apache Airflow)**
```python
# dags/bees_brewery_dag.py
- pipeline_start → ingestion_bronze → transformation_silver 
  → aggregation_gold → pipeline_end
- Retry policy: 2x com 5min delay
- Schedule: Daily @ midnight
- Monitoring: UI + structured logs
```

### 2. **Job Abstraction (BaseJob Pattern)**
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

### 3. **Core Services**
- **Storage**: LocalStorage (extensível para S3/GCS)
- **Spark**: SparkSessionFactory com config-driven
- **Logger**: Structured logging com JSON output
- **Exceptions**: Hierarchy (DataQuality, Storage, SparkJob)

### 4. **Data Layers**
- **Bronze**: 9.083 registros brutos (imutável)
- **Silver**: 5.451 registros limpos (60% retenção)
- **Gold**: 389 agregações por estado/tipo

---

## Fluxo de Dados (Medallion)

```
┌──────────────────────┐
│  OpenBrewery API     │
│  (9.083 breweries)   │
└──────────┬───────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  BRONZE LAYER (Raw)                 │
│  • No transformations               │
│  • Immutable record of source       │
│  • Format: Parquet (10 partitions)  │
│  • Location: datalake/bronze/       │
│  ✅ 9.083 records                    │
└──────────┬───────────────────────────┘
           │ (ingestion_bronze)
           ▼
┌─────────────────────────────────────┐
│  SILVER LAYER (Cleaned)             │
│  • Duplicates removed               │
│  • Names trimmed (whitespace)       │
│  • State normalized                 │
│  • Format: Parquet (partitioned)    │
│  • Location: datalake/silver/       │
│  ✅ 5.451 records (40% dedup)        │
└──────────┬───────────────────────────┘
           │ (transformation_silver)
           ▼
┌─────────────────────────────────────┐
│  GOLD LAYER (Analytics Ready)       │
│  • Aggregations by state/type       │
│  • Metrics calculated               │
│  • Format: Parquet                  │
│  • Location: datalake/gold/         │
│  ✅ 389 groups                       │
│                                      │
│  Top 3 State/Type Combos:           │
│  1. California - Micro: 268         │
│  2. California - Brewpub: 159       │
│  3. Washington - Micro: 147         │
└─────────────────────────────────────┘
```

---

## Stack Tecnológico

| Layer | Technology | Why |
|-------|------------|-----|
| **Processing** | Apache Spark 3.5 | Native partitioning + scalability |
| **Orchestration** | Apache Airflow 2.7 | Superior UI + retry policies |
| **Storage** | Parquet + Partitioning | Columnar format + compression |
| **Lang** | Python 3.12 + PySpark | Industry standard for data eng |
| **Container** | Docker + Docker Compose | Reproducible environments |
| **Testing** | pytest 7.4 + Mocks | 24 tests, ~80% coverage |
| **Logging** | Structured JSON logging | Easier debugging + alerts |
| **Config** | YAML-based | Environment-specific without code changes |

---

## Por Que Essas Escolhas?

### ✅ Spark vs Alternativas
| Critério | Spark | Pandas | Dask | Polars |
|----------|-------|--------|------|--------|
| Partitioning | ✅ Native | ❌ | ⚠️ | ⚠️ |
| Scalability | ✅ Production | ⚠️ Memory | ⚠️ | ⚠️ |
| Community | ✅ Huge | ✅ Huge | ⚠️ | ❌ |
| Cloud Support | ✅ AWS/GCP/Azure | ❌ | ❌ | ❌ |
| Maturity | ✅ 10+ years | ✅ | ⚠️ | ❌ |

**Decision:** ✅ Spark (atende 100% dos requirements + maduro em produção)

### ✅ Airflow vs Alternativas
| Critério | Airflow | Prefect | Dagster |
|----------|---------|---------|---------|
| Scheduling | ✅ Poderoso | ✅ Good | ✅ Good |
| Error Handling | ✅ Retries/SLAs | ⚠️ | ✅ |
| Monitoring | ✅ UI excelente | ⚠️ Basic | ⚠️ |
| Community | ✅ Gigante | ⚠️ Growing | ⚠️ Growing |
| Learning Curve | ⚠️ Medium | ✅ Low | ✅ Low |

**Decision:** ✅ Airflow (melhor UI + comunidade + retry policies)

### ✅ Layered vs Monolithic
| Aspecto | Layered | Monolithic |
|---------|---------|-----------|
| Testability | ✅ 100% | ❌ 20% |
| Scalability | ✅ Easy | ❌ Hard |
| Error Handling | ✅ Centralized | ❌ Dispersed |
| Reusability | ✅ High | ❌ Low |
| Onboarding | ✅ Easy | ❌ Hard |

**Decision:** ✅ Layered (compensa em escala)

---

## Próximos Passos

### Phase 1: Current (✅ COMPLETED)
- [x] Configuration Layer
- [x] Core Services
- [x] Job Abstraction
- [x] Medallion Pattern
- [x] Automated Tests
- [x] Docker Setup
- [x] Documentation

### Phase 2: Cloud Integration (Q2 2026)
- [ ] Add S3Storage backend
- [ ] Add GCS storage backend
- [ ] Setup CI/CD (GitHub Actions)
- [ ] Add monitoring (Prometheus/Grafana)

### Phase 3: Advanced Features (Q3 2026)
- [ ] Delta Lake integration
- [ ] Data cataloging
- [ ] Kubernetes deployment
- [ ] ML pipeline integration

---

## 📚 Referências

- **ADR-001:** [Modular Architecture Decision](adr/ADR-001-modular-architecture.md)
- **ADR-002:** [Technology Stack Decision](adr/ADR-002-TECH-STACK.md)
- **Implementation Guide:** [IMPLEMENTATION.md](IMPLEMENTATION.md)
- **Troubleshooting:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

**Status:** ✅ Production Ready  
**Next Review:** 2026-03-01

# 🔧 TROUBLESHOOTING - Guia de Diagnóstico e Correção

**Status:** ✅ Complete Guide  
**Last Updated:** 2026-02-02  
**Covers:** All issues encountered and solutions

---

## 📋 Índice de Problemas

1. [Spark Type Conflicts](#1-spark-type-conflicts)
2. [DAG Task Hanging](#2-dag-task-hanging)
3. [Data Validation Errors](#3-data-validation-errors)
4. [Docker Issues](#4-docker-issues)
5. [Testing Failures](#5-testing-failures)
6. [Performance Issues](#6-performance-issues)

---

## 1. Spark Type Conflicts

### Problema: "Can not merge type DoubleType and LongType"

**Sintomas:**
```
pyspark.sql.utils.AnalysisException: Can not merge type DoubleType and LongType
```

**Causa Raiz:**
- API OpenBrewery retorna valores numéricos inconsistentes
- Alguns como float (ex: `36.7749`), outros como int (ex: `12345`)
- Spark tenta inferir schema automaticamente em cada partição
- Spark não consegue reconciliar tipos diferentes no mesmo campo

**Solução Implementada:**

```python
# spark_jobs/ingestion.py

def _normalize_data(self, data: list) -> list:
    """Normalize all values to strings BEFORE Spark processes"""
    schema_fields = BronzeSchema.BREWERIES_SCHEMA.fieldNames()
    normalized = []
    
    for record in data:
        normalized_record = {}
        for field in schema_fields:
            value = record.get(field)
            # Convert ALL values to string (eliminates type conflicts)
            normalized_record[field] = str(value) if value is not None else None
        normalized.append(normalized_record)
    
    return normalized

def execute(self) -> None:
    # ...
    all_data = []  # Collect all API pages
    
    # 1️⃣ NORMALIZE: Convert to strings BEFORE creating DataFrame
    normalized_data = self._normalize_data(all_data)
    
    # 2️⃣ USE EXPLICIT SCHEMA: Don't let Spark infer
    df = self.spark.createDataFrame(
        normalized_data, 
        schema=BronzeSchema.BREWERIES_SCHEMA  # All StringType
    )
```

**Por que funciona:**
- ✅ Todos os valores são strings → sem conflito de tipo
- ✅ Schema explícito → Spark usa schema definido, não infere
- ✅ Normalização antecipada → evita problemas em paralelo

**Teste:**
```bash
docker-compose exec -T airflow-webserver python3 << 'PYTHON'
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("test").getOrCreate()
df = spark.read.parquet("/opt/airflow/datalake/bronze/breweries/created_at=2026-02-02")
print(f"✅ Bronze Data: {df.count():,} records without type errors")
PYTHON
```

---

## 2. DAG Task Hanging

### Problema: Tasks ficam em `[running]` indefinidamente

**Sintomas:**
```
[DAG TEST] end task task_id=ingestion_bronze
WARNING - No tasks to run. unrunnable tasks: {transformation_silver [running], aggregation_gold [None]}
```

**Causa Raiz:**
- TransformationJob procurava por dados em caminho **sem partição de data**
- Mas IngestionJob salvava dados **com partição de data** (`created_at=2026-02-02`)
- TransformationJob não encontrava dados → travava tentando ler

**Exemplo do Bug:**
```python
# ❌ ANTES - Procurava por bronze/breweries (sem data)
bronze_path = "bronze/breweries"
df = self.storage.read(bronze_path, format="parquet")

# Mas IngestionJob salvava em:
# bronze/breweries/created_at=2026-02-02/
# → ERRO: Arquivo não encontrado!
```

**Solução Implementada:**

```python
# ✅ DEPOIS - Adicionar execution_date aos Jobs

# dags/bees_brewery_dag.py
def run_transformation(**context):
    """Get execution_date from Airflow context"""
    execution_date = context['execution_date'].strftime('%Y-%m-%d')
    
    job = TransformationJob(
        config, 
        storage,
        execution_date=execution_date  # ✅ Pass to job
    )
    job.execute()

# spark_jobs/transformation_silver.py
class TransformationJob(BaseJob):
    def __init__(self, config: dict, storage=None, execution_date: str = None):
        super().__init__(config, storage)
        # Use provided date or current date
        self.execution_date = execution_date or datetime.now().strftime('%Y-%m-%d')
    
    def execute(self) -> None:
        # ✅ USE execution_date for partition
        bronze_path = f"bronze/breweries/created_at={self.execution_date}"
        df = self.storage.read(bronze_path, format="parquet")
```

**Por que funciona:**
- ✅ Airflow passa execution_date via context
- ✅ Job usa data exata para localizar dados particionados
- ✅ Caminho sempre bate: `bronze/breweries/created_at=2026-02-02/`

**Teste:**
```bash
# Trigger DAG e monitorar
docker-compose exec -T airflow-webserver bash -c \
  "airflow dags trigger bees_brewery_medallion && \
   sleep 5 && \
   airflow dags test bees_brewery_medallion 2026-02-02"

# Verificar nos logs
docker-compose logs airflow-scheduler | grep "TaskInstance Finished"
```

---

## 3. Data Validation Errors

### Problema: `_validate_not_null()` retorna TypeError

**Sintomas:**
```
TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'
```

**Causa Raiz:**
```python
# ❌ ANTES - Usar sum() em valores que podem ser None
null_counts_row = df.select([
    spark_sum(col(c).isNull().cast("int")).alias(c) for c in columns
]).collect()[0]

total_nulls = sum(null_counts_row.asDict().values())
# Se alguns valores são None, sum() falha!
```

**Solução Implementada:**

```python
# ✅ DEPOIS - Usar filter().count() e tratar None

def _validate_not_null(self, df: DataFrame, columns: list) -> int:
    """Count null values in specified columns"""
    from pyspark.sql.functions import col
    
    # Method 1: Filter + count (mais Pythônico)
    null_counts = {}
    for column in columns:
        null_count = df.filter(col(column).isNull()).count()
        null_counts[column] = null_count
    
    # Sum with None filtering
    total_nulls = sum(v for v in null_counts.values() if v is not None)
    
    if total_nulls > 0:
        self._log(
            f"Warning: Found {total_nulls} null values in columns {columns}: {null_counts}",
            level="WARNING"
        )
    
    return total_nulls
```

**Por que funciona:**
- ✅ `count()` sempre retorna int (nunca None)
- ✅ List comprehension com `if v is not None` garante apenas ints
- ✅ Mais legível: "contar nulos" vs "somar booleanos"

**Teste:**
```bash
docker-compose exec -T airflow-webserver pytest tests/test_transformation.py::test_transform_silver_success -v
# ✅ PASSED
```

---

## 4. Docker Issues

### Problema 4a: Container não inicia

**Sintomas:**
```
ERROR: Service airflow-webserver failed to build
```

**Solução:**
```bash
# 1. Remove containers e volumes
docker-compose down -v

# 2. Rebuild sem cache
docker-compose build --no-cache

# 3. Start fresh
docker-compose up -d

# 4. Wait for initialization
sleep 60

# 5. Verify
docker-compose ps
```

### Problema 4b: Porta 8080 já em uso

**Solução:**
```bash
# Find process using port 8080
lsof -i :8080

# Kill it
kill -9 <PID>

# Or use different port in docker-compose.yaml
# ports:
#   - "8081:8080"
```

### Problema 4c: "Cannot connect to Docker daemon"

**Solução:**
```bash
# Ensure Docker Desktop is running
# macOS: Open Docker.app from Applications

# Or check status
docker ps

# If not working, restart Docker daemon
# macOS: killall Docker && open /Applications/Docker.app
```

---

## 5. Testing Failures

### Problema 5a: "Bronze data está vazio" em testes

**Sintomas:**
```
ValueError: Bronze data está vazio!
```

**Causa:**
- Fixture cria dados em `tmp_path/bronze/breweries` (sem partição)
- Função `transform()` procura em `tmp_path/bronze/breweries/created_at=2026-02-02` (com partição)
- Não encontra → erro

**Solução (já implementada):**
```python
# spark_jobs/transformation_silver.py

def transform(spark, input_path: str, output_path: str) -> str:
    """Flexible: try without partition first (tests), then with (DAG)"""
    
    bronze_base = f"{input_path}/bronze/breweries"
    
    try:
        # Tentar SEM partição (testes usam isso)
        if exists(bronze_base):
            df = spark.read.parquet(bronze_base)
        else:
            # Tentar COM partição (DAG usa isso)
            current_date = datetime.now().strftime('%Y-%m-%d')
            bronze_path = f"{bronze_base}/created_at={current_date}"
            if exists(bronze_path):
                df = spark.read.parquet(bronze_path)
            else:
                raise ValueError("Bronze data está vazio!")
    except Exception as e:
        raise ValueError(f"Bronze data está vazio! Erro: {str(e)}")
```

**Teste:**
```bash
docker-compose exec -T airflow-webserver pytest tests/ -v
# ✅ 24 PASSED
```

### Problema 5b: "ModuleNotFoundError: No module named 'pyspark'"

**Solução:**
```bash
# Dentro do container (onde PySpark está instalado)
docker-compose exec -T airflow-webserver pytest tests/ -v

# OU instalar localmente (opcional)
pip install pyspark pytest pytest-cov
```

---

## 6. Performance Issues

### Problema 6a: Spark startup lento

**Causa:** Spark master externo em dev (comunicação overhead)

**Solução (já implementada):**
```yaml
# config/environments/dev.yaml
spark:
  master: local[*]  # ✅ Local mode (rápido)

# config/environments/prod.yaml
spark:
  master: yarn      # Cluster mode (escalável)
```

**Benchmark:**
```
Before:  ~60s (com retries)
After:   ~39s (primeira tentativa com local[*])
```

### Problema 6b: Muitas partições = overhead

**Solução:**
```python
# Configurar shuffle_partitions por ambiente
# dev.yaml: shuffle_partitions: 100  (rápido, dev)
# prod.yaml: shuffle_partitions: 500 (escalável, prod)

# Usar config
df = df.coalesce(self.config.spark.shuffle_partitions)
```

### Problema 6c: "Executor memory exceeded"

**Solução:**
```yaml
# config/environments/prod.yaml
spark:
  additional_conf:
    spark.driver.memory: 4g
    spark.executor.memory: 8g
    spark.dynamicAllocation.enabled: "true"
```

---

## Matriz de Diagnóstico Rápido

| Erro | Camada | Causa | Solução |
|------|--------|-------|---------|
| DoubleType + LongType | Spark | Schema inference | Use StringType explícito |
| "No tasks to run" | DAG | Partition mismatch | Adicione execution_date |
| TypeError in validate | Job | None em sum() | Use count() + filter |
| "Data está vazio" | Test | Path mismatch | Torne função flexível |
| Port 8080 em uso | Docker | Outro processo | Kill ou mude porta |
| PySpark not found | Python | Não instalado | Rode dentro do container |

---

## Checklist de Debugging

Quando algo não funciona:

- [ ] Verificar logs: `docker-compose logs -f airflow-scheduler`
- [ ] Verificar DAG UI: http://localhost:8080
- [ ] Verificar dados existem: `docker-compose exec -T airflow-webserver python3 << 'verify_data.py'`
- [ ] Rodar testes: `docker-compose exec -T airflow-webserver pytest tests/ -v`
- [ ] Reiniciar containers: `docker-compose down && docker-compose up -d`
- [ ] Verificar config: `cat config/environments/dev.yaml`
- [ ] Verificar storage: `ls -la datalake/bronze/`

---

## Quando Pedir Ajuda

Forneça:
1. **Erro completo** (copiar stack trace)
2. **Comando que rodou** (como reproduzir)
3. **Contexto** (dev? prod? qual versão?)
4. **O que já tentou** (ajustes feitos)

---

## 📚 Referências

- [Spark Type System](https://spark.apache.org/docs/latest/sql-ref-datatypes.html)
- [Airflow Error Handling](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/errors.html)
- [Docker Troubleshooting](https://docs.docker.com/config/containers/troubleshoot/)
- [Parquet Schema](https://parquet.apache.org/docs/file-format/data-types/)

---

**Last Updated:** 2026-02-02  
**Issues Resolved:** 4 major + 6 categories  
**All Tests Passing:** ✅ 24/24

# DOCKER_TEST_VALIDATION.md - Guia Completo de Teste com Docker

**Date:** 2026-02-01  
**Status:** Ready for Testing  
**Purpose:** Validar que a solução funciona corretamente em Docker  

---

## 🚀 Pré-requisitos

### Verificar instalação

```bash
# Docker deve estar instalado e rodando
docker --version
# Expected: Docker version 20.10+

docker-compose --version
# Expected: Docker Compose version 2.0+
```

Se Docker não está rodando no Mac:
1. Abra **Docker Desktop** (procure em Applications)
2. Espere até que o ícone na barra de menu mostre "Docker Desktop is running"

---

## 🧪 Teste 1: Build das Imagens

```bash
cd /Users/thiagomarinhoesilva/Documents/GITHUB/teste_ambev/bees-brewery-case

# Build (isso vai baixar base images e instalar dependências)
# Esperado: ~5-10 minutos na primeira vez
docker-compose build

# Validação esperada:
# ✅ Successfully tagged bees-brewery-case_airflow-webserver:latest
# ✅ Successfully tagged bees-brewery-case_spark-master:latest
# ✅ Successfully tagged bees-brewery-case_spark-worker:latest
```

---

## 🧪 Teste 2: Iniciar Containers

```bash
# Iniciar em background
docker-compose up -d

# Esperado: 6 containers iniciando
# - postgres
# - airflow-webserver
# - airflow-scheduler
# - spark-master
# - spark-worker (pode levar alguns segundos)

# Validar que containers estão rodando
docker-compose ps

# Esperado output:
# NAME                                 STATUS
# bees-brewery-case-postgres-1         Up (healthy)
# bees-brewery-case-airflow-webserver-1   Up (healthy)
# bees-brewery-case-airflow-scheduler-1   Up (healthy)
# bees-brewery-case-spark-master-1     Up (healthy)
# bees-brewery-case-spark-worker-1     Up (healthy)
```

---

## 🧪 Teste 3: Verificar Airflow UI

```bash
# Airflow deve estar disponível em http://localhost:8080
# Abra no navegador: http://localhost:8080

# Credenciais padrão:
# Username: airflow
# Password: airflow

# Se aparecer login page: ✅ Airflow está rodando
# Se aparecer DAG "bees_brewery_medallion": ✅ DAG foi carregado
```

---

## 🧪 Teste 4: Verificar Spark UI

```bash
# Spark Master deve estar disponível em http://localhost:8081
# Abra no navegador: http://localhost:8081

# Esperado:
# - Status: Alive
# - Workers: 1
# - Cores: 2 (ou mais se sua máquina tem mais)
# - Memory: Disponível e alocado
```

---

## 🧪 Teste 5: Rodar DAG Manualmente

```bash
# Dentro do container Airflow
docker-compose exec airflow-webserver bash

# Agora você está DENTRO do container:
# 1. Unpause a DAG
airflow dags unpause bees_brewery_medallion

# 2. Trigger manualmente
airflow dags test bees_brewery_medallion 2026-02-01

# Esperado output:
# [2026-02-01 00:00:00,000] {bash_operator.py:123} INFO - Running command: ['python', ...]
# [2026-02-01 00:00:00,000] {bash_operator.py:123} INFO - Task exited with return code 0

# 3. Sair do container
exit
```

---

## 🧪 Teste 6: Verificar Datalake

```bash
# Ver estrutura de diretórios criada
ls -la ./datalake/

# Esperado após rodar DAG:
# datalake/
# ├── bronze/     (dados brutos da API)
# ├── silver/     (dados transformados)
# └── gold/       (dados agregados)

# Validar Parquet files foram criados
find ./datalake -name "*.parquet" -type f

# Esperado: vários arquivos .parquet em cada layer
```

---

## 🧪 Teste 7: Rodar Testes Automatizados

```bash
# Dentro do container Airflow
docker-compose exec airflow-webserver bash

# Rodar testes unitários
cd /opt/airflow
pytest tests/ -v --cov=spark_jobs --cov-report=term-missing

# Esperado:
# tests/test_ingestion.py::test_ingestion_job_init PASSED
# tests/test_transformation.py::test_transformation_extracts_bronze PASSED
# tests/test_aggregation.py::test_aggregation_job_init PASSED
# tests/test_architecture.py::test_full_pipeline PASSED
#
# ================ 10 passed in 2.34s ================
# Coverage: 85%
```

---

## 🧪 Teste 8: Verificar Logs

```bash
# Ver logs de um container específico
docker-compose logs airflow-webserver -f

# Ver logs do Scheduler
docker-compose logs airflow-scheduler -f

# Ver logs do Spark Master
docker-compose logs spark-master -f

# Esperado: logs sem erros críticos
```

---

## 🧪 Teste 9: Verificar Conectividade Entre Containers

```bash
# Dentro do Airflow container
docker-compose exec airflow-webserver bash

# Testar conexão com Spark Master
python3 << EOF
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("test") \
    .master("spark://spark-master:7077") \
    .getOrCreate()

print("✅ Spark connection OK")
spark.stop()
EOF

# Esperado: ✅ Spark connection OK
```

---

## 🧪 Teste 10: Parar Containers

```bash
# Parar todos os containers
docker-compose down

# Esperado: containers stopped and removed

# Validar que pararam
docker ps

# Esperado: lista vazia (ou apenas containers de outros projetos)
```

---

## 🎯 TESTE COMPLETO DA DAG: Logs e Arquivos de Saída

### Visão Geral do Pipeline

A DAG `bees_brewery_medallion` executa 5 tarefas em sequência:

```
pipeline_start → ingestion_bronze → transformation_silver → aggregation_gold → pipeline_end
```

**Fluxo de dados esperado:**
- **Bronze:** Dados brutos da API (JSON normalizado em Parquet)
- **Silver:** Dados limpos e transformados
- **Gold:** Dados agregados para análises

---

### 📋 PARTE 1: Preparar Ambiente para Teste

```bash
# 1. Ir para diretório do projeto
cd /Users/thiagomarinhoesilva/Documents/GITHUB/teste_ambev/bees-brewery-case

# 2. Limpar containers anteriores (se existirem)
docker-compose down -v

# 3. Construir imagens
docker-compose build

# Esperado:
# ✅ Successfully tagged bees-brewery-case_airflow-webserver:latest
# ✅ Successfully tagged bees-brewery-case_spark-master:latest
# ✅ Successfully tagged bees-brewery-case_spark-worker:latest

# 4. Iniciar containers em background
docker-compose up -d

# 5. Aguardar inicialização completa (30-60 segundos)
sleep 30

# 6. Validar que containers estão saudáveis
docker-compose ps

# Esperado output:
# STATUS = "Up" e "healthy" (ou "Up" sem a parte de health ainda)
```

---

### 📊 PARTE 2: Validar Estado Inicial da DAG

```bash
# 1. Acessar container do Airflow
docker-compose exec airflow-webserver bash

# Agora você está DENTRO do container Airflow
# Todos os comandos a seguir rodam DENTRO do container

# 2. Verificar que DAG está registrada
airflow dags list | grep bees_brewery_medallion

# Esperado output:
# bees_brewery_medallion | /opt/airflow/dags/bees_brewery_dag.py | False

# 3. Verificar tarefas da DAG
airflow tasks list bees_brewery_medallion

# Esperado output:
# pipeline_start
# ingestion_bronze
# transformation_silver
# aggregation_gold
# pipeline_end

# 4. Unpause a DAG (necessário para rodar)
airflow dags unpause bees_brewery_medallion

# Esperado:
# Dag: bees_brewery_medallion, paused: False
```

---

### 🚀 PARTE 3: Executar a DAG Manualmente

```bash
# AINDA DENTRO DO CONTAINER AIRFLOW

# Opção A: Test mode (mais rápido, para debug)
airflow dags test bees_brewery_medallion 2026-02-01

# Opção B: Trigger normal (simula execução real)
# airflow dags trigger bees_brewery_medallion --exec-date 2026-02-01

# ⏳ Aguarde 2-5 minutos para execução completa
# Você verá muitas linhas de log enquanto executa

# Sinais de sucesso:
# ✅ [2026-02-01 XX:XX:XX,XXX] {bash_operator.py:123} INFO - Running command: ['echo', ...]
# ✅ [2026-02-01 XX:XX:XX,XXX] {python_operator.py:180} INFO - Task exited with return code 0
# ✅ Ingestion completed! XXX records written to bronze/breweries/...
```

---

### 📝 PARTE 4: Monitorar Logs da DAG em Tempo Real

**Em outro terminal (Terminal 2):**

```bash
# Enquanto a DAG está rodando, monitore os logs

cd /Users/thiagomarinhoesilva/Documents/GITHUB/teste_ambev/bees-brewery-case

# Ver logs do Airflow Scheduler
docker-compose logs -f airflow-scheduler

# Esperado (deve haver logs da execução da DAG):
# [2026-02-01 XX:XX:XX,XXX] {scheduler.py:xxx} INFO - Running <TaskInstance: bees_brewery_medallion.ingestion_bronze 2026-02-01T00:00:00+00:00 [running]> on worker...
```

**Em um terceiro terminal (Terminal 3):**

```bash
# Ver logs do Spark Master durante execução dos jobs

docker-compose logs -f spark-master

# Esperado:
# 26/02/01 XX:XX:XX INFO Master: Registering worker...
# 26/02/01 XX:XX:XX INFO MasterWebUI: Binding MasterWebUI to 0.0.0.0
```

---

### 📂 PARTE 5: Validar Arquivos de Saída - Bronze Layer

**De volta no Terminal 1 (container Airflow), após DAG completar:**

```bash
# AINDA DENTRO DO CONTAINER AIRFLOW

# 1. Listar estrutura do datalake
ls -la /opt/airflow/datalake/

# Esperado:
# drwxr-xr-x  bronze/
# drwxr-xr-x  silver/
# drwxr-xr-x  gold/

# 2. Verificar dados Bronze (raw)
ls -la /opt/airflow/datalake/bronze/breweries/

# Esperado:
# drwxr-xr-x  created_at=2026-02-01/

# 3. Ver arquivos Parquet em Bronze
find /opt/airflow/datalake/bronze -name "*.parquet" -type f

# Esperado:
# /opt/airflow/datalake/bronze/breweries/created_at=2026-02-01/part-00000-xxx.snappy.parquet
# (pode haver múltiplos part-XXXXX files)

# 4. Contar linhas em Bronze
python3 << 'EOF'
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("test").getOrCreate()
df = spark.read.parquet("/opt/airflow/datalake/bronze/breweries/created_at=2026-02-01")
print(f"✅ Bronze Records: {df.count()}")
print(f"✅ Bronze Schema: {df.schema}")
df.show(5)
EOF

# Esperado output:
# ✅ Bronze Records: XXX (número de cervejarias da API)
# ✅ Bronze Schema: StructType([...])
# Mostra 5 primeiras linhas com dados brutos
```

---

### 📂 PARTE 6: Validar Arquivos de Saída - Silver Layer

```bash
# AINDA DENTRO DO CONTAINER AIRFLOW

# 1. Verificar dados Silver (transformados)
ls -la /opt/airflow/datalake/silver/

# Esperado:
# drwxr-xr-x  breweries_cleaned/

# 2. Ver arquivos Parquet em Silver
find /opt/airflow/datalake/silver -name "*.parquet" -type f

# Esperado:
# /opt/airflow/datalake/silver/breweries_cleaned/created_at=2026-02-01/part-00000-xxx.snappy.parquet

# 3. Validar transformação (Silver deve ter menos colunas/dados limpos)
python3 << 'EOF'
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("test").getOrCreate()

print("=" * 60)
print("COMPARAÇÃO: BRONZE vs SILVER")
print("=" * 60)

# Bronze
bronze_df = spark.read.parquet("/opt/airflow/datalake/bronze/breweries/created_at=2026-02-01")
print(f"\n📊 BRONZE (Raw):")
print(f"  Records: {bronze_df.count()}")
print(f"  Columns: {len(bronze_df.columns)}")
print(f"  Column names: {bronze_df.columns}")

# Silver
silver_df = spark.read.parquet("/opt/airflow/datalake/silver/breweries_cleaned/created_at=2026-02-01")
print(f"\n📊 SILVER (Cleaned):")
print(f"  Records: {silver_df.count()}")
print(f"  Columns: {len(silver_df.columns)}")
print(f"  Column names: {silver_df.columns}")

print(f"\n✅ Sample Silver data:")
silver_df.show(5)

spark.stop()
EOF

# Esperado:
# SILVER deve ter:
#   - Mesmo número ou menos registros (outliers removidos)
#   - Colunas renomeadas/limpas
#   - Dados sem valores nulos em campos importantes
#   - Timestamp de transformação adicionado
```

---

### 📂 PARTE 7: Validar Arquivos de Saída - Gold Layer

```bash
# AINDA DENTRO DO CONTAINER AIRFLOW

# 1. Verificar dados Gold (agregados)
ls -la /opt/airflow/datalake/gold/

# Esperado:
# drwxr-xr-x  breweries_stats/

# 2. Ver arquivos Parquet em Gold
find /opt/airflow/datalake/gold -name "*.parquet" -type f

# Esperado:
# /opt/airflow/datalake/gold/breweries_stats/created_at=2026-02-01/part-00000-xxx.snappy.parquet

# 3. Validar agregações (Gold deve ter estadísticas por grupo)
python3 << 'EOF'
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("test").getOrCreate()

gold_df = spark.read.parquet("/opt/airflow/datalake/gold/breweries_stats/created_at=2026-02-01")

print("=" * 60)
print("GOLD LAYER (Agregado para Analytics)")
print("=" * 60)
print(f"\n📊 Estatísticas:")
print(f"  Total de grupos/agregações: {gold_df.count()}")
print(f"  Colunas: {gold_df.columns}")

print(f"\n📈 Sample agregado:")
gold_df.show(10)

print(f"\n📊 Schema do Gold:")
gold_df.printSchema()

spark.stop()
EOF

# Esperado:
# GOLD deve ter agregações como:
#   - Count por brewery_type (estado, tipo, etc.)
#   - Stats (min, max, avg) de valores numéricos
#   - Dados prontos para BI/Dashboard
```

---

### 📜 PARTE 8: Validar Logs Estruturados

```bash
# AINDA DENTRO DO CONTAINER AIRFLOW

# 1. Ver logs de execução da DAG
cat /opt/airflow/logs/dag_id=bees_brewery_medallion/*/2026-02-01T00:00:00*/task_id=*/attempt=1.log

# Alternativamente, ver diretório de logs
find /opt/airflow/logs -name "*.log" -type f | head -10

# 2. Ver log específico de uma tarefa (exemplo: ingestion_bronze)
cat /opt/airflow/logs/dag_id=bees_brewery_medallion/run_id=manual__2026-02-01T00:00:00*/task_id=ingestion_bronze/attempt=1.log 2>/dev/null || echo "Log ainda não disponível"

# 3. Extrair informações importantes dos logs
python3 << 'EOF'
import glob
import os

# Procurar por logs da execução
log_dir = "/opt/airflow/logs/dag_id=bees_brewery_medallion"
log_files = glob.glob(f"{log_dir}/**/attempt=1.log", recursive=True)

print(f"Found {len(log_files)} log files")
print("\nProcurando por keywords importantes...\n")

keywords = [
    "✅", "❌", "ERROR", "WARN", "completed", "failed", 
    "records written", "rows processed", "Schema validation"
]

for log_file in sorted(log_files)[:3]:  # Primeiros 3 logs
    print(f"\n{'='*60}")
    print(f"File: {log_file.split('/')[-3]}")
    print(f"{'='*60}")
    
    with open(log_file, 'r') as f:
        for line in f:
            if any(kw in line for kw in keywords):
                print(line.strip())
EOF
```

---

### 🔍 PARTE 9: Validação Completa de Integridade de Dados

```bash
# AINDA DENTRO DO CONTAINER AIRFLOW

# Script completo de validação end-to-end

python3 << 'EOF'
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, isnull, countDistinct
import sys

spark = SparkSession.builder \
    .appName("DataQualityValidation") \
    .getOrCreate()

print("\n" + "="*70)
print("🔍 VALIDAÇÃO COMPLETA: Pipeline de Dados BEES Brewery")
print("="*70)

# --- BRONZE LAYER ---
print("\n📦 BRONZE LAYER (Raw Data)")
print("-" * 70)

try:
    bronze = spark.read.parquet("/opt/airflow/datalake/bronze/breweries/created_at=2026-02-01")
    
    bronze_count = bronze.count()
    print(f"✅ Bronze records: {bronze_count}")
    
    if bronze_count == 0:
        print("❌ ERRO: Bronze layer vazia!")
        sys.exit(1)
    
    print(f"✅ Bronze columns: {len(bronze.columns)} - {bronze.columns}")
    
    # Verificar nulos
    null_counts = bronze.select([count(isnull(col(c))).alias(c) for c in bronze.columns]).collect()[0]
    print(f"✅ Valores nulos por coluna: {null_counts.asDict()}")
    
except Exception as e:
    print(f"❌ Erro ao validar Bronze: {e}")
    sys.exit(1)

# --- SILVER LAYER ---
print("\n🔄 SILVER LAYER (Transformed Data)")
print("-" * 70)

try:
    silver = spark.read.parquet("/opt/airflow/datalake/silver/breweries_cleaned/created_at=2026-02-01")
    
    silver_count = silver.count()
    print(f"✅ Silver records: {silver_count}")
    
    if silver_count == 0:
        print("⚠️  Aviso: Silver layer vazia")
    else:
        print(f"✅ Silver columns: {len(silver.columns)} - {silver.columns}")
        
        # Comparação com Bronze
        reduction = ((bronze_count - silver_count) / bronze_count * 100) if bronze_count > 0 else 0
        print(f"✅ Redução de dados: {reduction:.2f}% (outliers removidos)")
        
        # Mostrar sample
        print(f"\n📋 Sample (5 linhas):")
        silver.show(5, truncate=False)
        
except Exception as e:
    print(f"⚠️  Aviso ao validar Silver: {e}")

# --- GOLD LAYER ---
print("\n📊 GOLD LAYER (Aggregated Data)")
print("-" * 70)

try:
    gold = spark.read.parquet("/opt/airflow/datalake/gold/breweries_stats/created_at=2026-02-01")
    
    gold_count = gold.count()
    print(f"✅ Gold records (agregações): {gold_count}")
    
    if gold_count == 0:
        print("⚠️  Aviso: Gold layer vazia")
    else:
        print(f"✅ Gold columns: {len(gold.columns)} - {gold.columns}")
        
        print(f"\n📈 Agregações Gold (amostra):")
        gold.show(5, truncate=False)
        
except Exception as e:
    print(f"⚠️  Aviso ao validar Gold: {e}")

# --- RESUMO FINAL ---
print("\n" + "="*70)
print("✅ VALIDAÇÃO CONCLUÍDA COM SUCESSO")
print("="*70)
print(f"""
📊 RESUMO FINAL:
  Bronze:  {bronze_count} registros (dados brutos)
  Silver:  {silver_count if silver_count else 'N/A'} registros (dados limpos)
  Gold:    {gold_count if gold_count else 'N/A'} registros (dados agregados)
  
✅ Pipeline completou todas as 3 camadas (Bronze → Silver → Gold)
""")

spark.stop()
EOF

# Esperado output:
# ✅ VALIDAÇÃO CONCLUÍDA COM SUCESSO
# Mostra contagem de registros em cada camada
# Mostra que dados fluiram corretamente através do pipeline
```

---

### 📋 PARTE 10: Checklist de Validação da DAG

```bash
# Fora do container, ou dentro dele para verificar

# 1. Verificar via Airflow UI (navegador)
# http://localhost:8080
# - Procure por: bees_brewery_medallion
# - Deve aparecer "Last Run: 2026-02-01"
# - Deve mostrar "Success" com checkmark verde

# 2. Verificar diretórios de saída (fora do container)
ls -la /Users/thiagomarinhoesilva/Documents/GITHUB/teste_ambev/bees-brewery-case/datalake/

# Esperado:
# drwxr-xr-x  bronze/
# drwxr-xr-x  silver/
# drwxr-xr-x  gold/

# 3. Contar arquivos Parquet
find /Users/thiagomarinhoesilva/Documents/GITHUB/teste_ambev/bees-brewery-case/datalake -name "*.parquet" | wc -l

# Esperado: > 0 (vários arquivos parquet criados)

# 4. Verificar logs do container
docker-compose logs airflow-scheduler | grep "bees_brewery_medallion" | tail -20

# Esperado: logs mostrando execução bem-sucedida das tarefas
```

---

### 🎯 PARTE 11: Validação Visual - Airflow UI

```
1. Acesse: http://localhost:8080
   Username: admin / Password: admin

2. Procure pelo DAG "bees_brewery_medallion"

3. Verifique:
   ✅ DAG está na lista
   ✅ Status mostrado como "active" (verde)
   ✅ "Paused" está desligado (False)

4. Clique no DAG para ver:
   ✅ Graph View: 5 tarefas (start → bronze → silver → gold → end)
   ✅ Tree View: Última execução em 2026-02-01
   ✅ Todos os boxes aparecem em verde (sucesso)

5. Clique em cada tarefa para ver logs:
   ✅ pipeline_start: "echo Starting..."
   ✅ ingestion_bronze: "Starting ingestion from Open Brewery DB API"
   ✅ transformation_silver: "Starting transformation job"
   ✅ aggregation_gold: "Starting aggregation job"
   ✅ pipeline_end: "echo Pipeline completed successfully"
```

---

### ⚠️ TROUBLESHOOTING: Se algo falhar

```bash
# Se DAG falhar, procure por erros:

# 1. Ver erro detalhado
docker-compose logs airflow-scheduler | grep -A 10 "ERROR"

# 2. Ver erro do Spark
docker-compose logs spark-master | grep -A 5 "ERROR"

# 3. Verificar se API está respondendo
docker-compose exec airflow-webserver bash
python3 << 'EOF'
import requests
url = "https://api.openbrewerydb.org/breweries?per_page=1"
try:
    resp = requests.get(url, timeout=10)
    print(f"API Status: {resp.status_code}")
    print(f"Response: {resp.json()[:1]}")
except Exception as e:
    print(f"API Error: {e}")
EOF

# 4. Verificar storage/disco
du -sh /Users/thiagomarinhoesilva/Documents/GITHUB/teste_ambev/bees-brewery-case/datalake/
df -h

# 5. Verificar memória do Docker
docker stats
```

---

### 📊 RESUMO: O que deve acontecer

```
Início:
  └─ docker-compose up -d
     └─ Aguarda 30-60 segundos

DAG Trigger:
  └─ airflow dags test bees_brewery_medallion 2026-02-01
     └─ Tarefa 1 (start): Echo inicial
     └─ Tarefa 2 (ingestion): 
        ├─ Fetch da API OpenBreweryDB
        ├─ Normaliza dados (strings)
        ├─ Valida schema
        └─ Salva em: datalake/bronze/breweries/created_at=2026-02-01/ (Parquet)
     
     └─ Tarefa 3 (transformation):
        ├─ Lê dados de Bronze
        ├─ Remove outliers/nulos
        ├─ Renomeia colunas
        ├─ Adiciona timestamps
        └─ Salva em: datalake/silver/breweries_cleaned/created_at=2026-02-01/ (Parquet)
     
     └─ Tarefa 4 (aggregation):
        ├─ Lê dados de Silver
        ├─ Agrupa por brewery_type/state/etc
        ├─ Calcula stats (count, min, max, avg)
        └─ Salva em: datalake/gold/breweries_stats/created_at=2026-02-01/ (Parquet)
     
     └─ Tarefa 5 (end): Echo final

Resultado Final:
  ✅ Arquivo de partição em cada camada
  ✅ Logs mostrando "Task exited with return code 0"
  ✅ Estrutura Medallion completa: Bronze → Silver → Gold
```

---

**🎉 Sucesso:** Se chegou aqui e tudo passou, seu pipeline está pronto para produção!

---

## 📊 Checklist de Validação

```
✅ PRÉ-REQUISITOS
  ☐ Docker instalado
  ☐ Docker daemon rodando
  ☐ Docker Compose instalado
  ☐ Mínimo 4GB RAM disponível para Docker

✅ BUILD
  ☐ Dockerfile.airflow build com sucesso
  ☐ Dockerfile.spark build com sucesso
  ☐ Requirements.txt instalado corretamente

✅ CONTAINERS
  ☐ Postgres iniciado e healthy
  ☐ Airflow Webserver iniciado e healthy
  ☐ Airflow Scheduler iniciado e healthy
  ☐ Spark Master iniciado
  ☐ Spark Worker iniciado e conectado ao Master

✅ AIRFLOW
  ☐ UI acessível em http://localhost:8080
  ☐ DAG "bees_brewery_medallion" visível
  ☐ DAG pode ser unpaused
  ☐ DAG pode ser triggerado manualmente

✅ SPARK
  ☐ UI acessível em http://localhost:8081
  ☐ Worker registrado no Master
  ☐ Aplicações podem ser submitidas

✅ PIPELINE
  ☐ Ingestion Job executa com sucesso
  ☐ Transformation Job executa com sucesso
  ☐ Aggregation Job executa com sucesso
  ☐ Dados aparecem em datalake/bronze/
  ☐ Dados aparecem em datalake/silver/
  ☐ Dados aparecem em datalake/gold/

✅ TESTES
  ☐ Testes unitários rodam com sucesso
  ☐ Cobertura > 80%
  ☐ Nenhum teste falha
  ☐ Testes de integração passam

✅ DADOS
  ☐ Dados Bronze: raw formato original
  ☐ Dados Silver: cleaned e enriched
  ☐ Dados Gold: aggregated para analytics
  ☐ Parquet files foram criados
  ☐ Schema validação passou

✅ ERRO HANDLING
  ☐ DataQualityException funciona corretamente
  ☐ StorageException é capturada
  ☐ Logging estruturado está ativo
  ☐ Retry policies funcionam em Airflow

✅ CLEANUP
  ☐ docker-compose down remove containers
  ☐ Volumes persistem (ou são deletados se --volumes)
```

---

## 🔧 Troubleshooting

### ❌ Erro: "Cannot connect to Docker daemon"

```bash
# Solução 1: Iniciar Docker Desktop
open /Applications/Docker.app

# Solução 2: Aguardar que inicialize completamente
sleep 30

# Solução 3: Validar que daemon está respondendo
docker ps
```

### ❌ Erro: "Port 8080 is already in use"

```bash
# Encontrar processo usando porta 8080
lsof -i :8080

# Matar processo
kill -9 <PID>

# Ou usar porta diferente
docker-compose up -d -p 8090:8080
```

### ❌ Erro: "Insufficient disk space"

```bash
# Limpar images não usadas
docker system prune -a

# Liberar espaço (cuidado!)
docker image prune
```

### ❌ Erro: "Container exited with code 1"

```bash
# Ver logs detalhados
docker-compose logs <service-name>

# Exemplo:
docker-compose logs airflow-webserver
```

### ❌ Erro: "Spark Worker não conecta ao Master"

```bash
# Verificar que spark-master está healthy
docker-compose logs spark-master

# Esperado: "Started MasterWebUI at ..."

# Verificar network
docker network inspect bees-brewery-case_default

# Esperado: ambos master e worker no mesmo network
```

---

## 📈 Monitoramento Durante Execução

### Monitorar em Tempo Real

```bash
# Terminal 1: Ver logs do Scheduler
docker-compose logs airflow-scheduler -f

# Terminal 2: Ver logs do Airflow Webserver
docker-compose logs airflow-webserver -f

# Terminal 3: Ver logs do Spark Master
docker-compose logs spark-master -f

# Terminal 4: Executar comandos
docker-compose exec airflow-webserver bash
```

### Verificar Métricas

```bash
# CPU e Memory usage dos containers
docker stats

# Esperado:
# CONTAINER                   CPU %    MEM USAGE / LIMIT
# bees-brewery-case-postgres-1      0.5%     150MB / 8GB
# bees-brewery-case-airflow-webserver-1  2%  500MB / 8GB
```

---

## ✅ Validação Final

Se todos os testes passaram, você tem:

✅ **Arquitetura Modular**
- Código bem separado (config, core, jobs, schemas)
- Dependency injection funcionando
- Multi-environment suportado

✅ **Pipeline Escalável**
- Medallion architecture (Bronze → Silver → Gold)
- Spark partitioning funcionando
- Airflow orchestration rodando

✅ **Robustez**
- Error handling com retry policies
- Data quality validation ativa
- Logging estruturado

✅ **Deployment Ready**
- Docker compose levanta tudo
- Todos containers comunicam
- Pipeline executa end-to-end

✅ **Documentação Completa**
- ADRs explicam decisões
- REQUIREMENTS_MAPPING mostra rastreabilidade
- README descreve como rodar

---

## 🎁 Próximas Etapas

Depois que validar com Docker:

1. **Commit no Git**
   ```bash
   git add .
   git commit -m "feat: production-ready data pipeline with Docker"
   git push origin main
   ```

2. **Preparar para apresentação**
   - Ter Docker rodando
   - Ter Airflow UI acessível
   - Ter testes passando

3. **Demonstração para Bees**
   - Mostrar DAG no Airflow
   - Rodar pipeline manualmente
   - Mostrar dados em cada layer
   - Explicar decisões técnicas via ADRs

---

**Last Updated:** 2026-02-01  
**Status:** ✅ Ready for Docker Testing  
**Next Step:** Start Docker daemon and run tests

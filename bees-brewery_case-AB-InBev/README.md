# BEES Brewery Case - ETL Pipeline

Pipeline de ETL completo para processamento de dados do caso BEES Brewery, utilizando arquitetura Medallion (Bronze, Silver, Gold) com Airflow e Spark.

## 📚 Documentação

**Leia primeiro:**
1. 📘 **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Visão geral da arquitetura + decisões técnicas
2. 📗 **[IMPLEMENTATION.md](docs/IMPLEMENTATION.md)** - Setup, deployment e histórico de ajustes
3. 📕 **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Diagnóstico e solução de problemas

**Decisões Arquiteturais:**
- 📋 **[ADRs Index](docs/adr/README.md)** - Architecture Decision Records
- 📌 **[ADR-001](docs/adr/ADR-001-modular-architecture.md)** - Arquitetura Modular
- 📌 **[ADR-002](docs/adr/ADR-002-TECH-STACK.md)** - Stack Tecnológico

---

## 📋 Estrutura do Projeto

```
bees-brewery-case/
├── dags/                  # DAGs do Airflow
│   └── bees_brewery_dag.py
├── spark_jobs/            # Scripts PySpark segregados
│   ├── ingestion.py       # API -> Bronze
│   ├── transformation.py  # Bronze -> Silver
│   └── aggregation.py     # Silver -> Gold
├── tests/                 # Testes unitários (PyTest)
│   ├── test_ingestion.py
│   ├── test_transformation.py
│   └── test_aggregation.py
├── docker/                # Dockerfiles customizados
│   └── Dockerfile.spark
├── docker-compose.yaml    # Orquestração de containers
└── requirements.txt       # Dependências Python
```

## 🚀 Quick Start

### Pré-requisitos

- Docker e Docker Compose instalados
- Python 3.9+
- Git

### 1. Clonar o repositório

```bash
git clone <repository-url>
cd bees-brewery-case
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Iniciar containers (Airflow + Spark)

```bash
docker-compose up -d
```

### 4. Acessar interfaces

- **Airflow UI**: http://localhost:8080
- **Spark Master**: http://localhost:8080

## 📚 Componentes

### Ingestion (Bronze Layer)

**Arquivo**: `spark_jobs/ingestion.py`

Responsável por extrair dados da API BEES e armazenar na camada Bronze em formato parquet.

**Principais métodos**:
- `fetch_data_from_api()`: Busca dados da API
- `create_bronze_dataframe()`: Cria DataFrame a partir dos dados
- `save_to_bronze()`: Salva dados em formato parquet
- `ingest()`: Executa pipeline completo

**Exemplo de uso**:
```python
from pyspark.sql import SparkSession
from spark_jobs.ingestion import BeesIngestion

spark = SparkSession.builder.appName("Ingestion").getOrCreate()
ingestion = BeesIngestion(spark, "https://api.example.com", api_key="key")
ingestion.ingest("customers", "customers", "/data")
```

### Transformation (Silver Layer)

**Arquivo**: `spark_jobs/transformation.py`

Responsável por limpeza, validação e transformação de dados de Bronze para Silver.

**Principais métodos**:
- `clean_data()`: Remove duplicatas e normaliza strings
- `validate_data()`: Valida colunas obrigatórias e nulos
- `enrich_data()`: Adiciona metadados (timestamp, ID único)
- `save_to_silver()`: Salva dados em Silver
- `transform()`: Executa pipeline completo

**Exemplo de uso**:
```python
from spark_jobs.transformation import BeesTransformation

transformation = BeesTransformation(spark)
df = transformation.transform(
    "/data/bronze/customers",
    "customers",
    "/data",
    required_columns=["id", "name", "email"]
)
```

### Aggregation (Gold Layer)

**Arquivo**: `spark_jobs/aggregation.py`

Responsável por agregações, análises e métricas de negócio em Gold.

**Principais métodos**:
- `aggregate_by_group()`: Agrupa e aplica funções de agregação
- `apply_filters()`: Filtra dados
- `sort_data()`: Ordena dados
- `calculate_metrics()`: Calcula métricas customizadas
- `save_to_gold()`: Salva dados em Gold
- `aggregate()`: Executa pipeline completo

**Exemplo de uso**:
```python
from spark_jobs.aggregation import BeesAggregation

aggregation = BeesAggregation(spark)
df = aggregation.aggregate(
    "/data/silver/sales",
    "sales_summary",
    "/data",
    group_by_cols=["category"],
    agg_specs={"amount": "sum", "quantity": "avg"},
    sort_columns=[("amount", "desc")]
)
```

## 🧪 Testes

Executar todos os testes:

```bash
pytest tests/ -v
```

Executar testes de um módulo específico:

```bash
pytest tests/test_ingestion.py -v
pytest tests/test_transformation.py -v
pytest tests/test_aggregation.py -v
```

Com cobertura:

```bash
pytest tests/ --cov=spark_jobs --cov-report=html
```

## 🔄 Fluxo de Dados

```
API BEES
   ↓
[Ingestion Task] → Bronze Layer (Parquet)
   ↓
[Transformation Task] → Silver Layer (Parquet)
   ↓
[Aggregation Task] → Gold Layer (Parquet)
   ↓
[Validation Task] → Data Quality Checks
```

## 📊 Camadas Medallion

### Bronze
- Dados brutos da API
- Sem transformações
- Formato: Parquet
- Retenção: Indefinida

### Silver
- Dados limpos e validados
- Duplicatas removidas
- Strings normalizadas
- Metadados adicionados
- Formato: Parquet

### Gold
- Dados agregados e analisados
- Métricas de negócio
- Dados prontos para BI/Analytics
- Formato: Parquet

## ⚙️ Configuração

### Variáveis de Ambiente

Criar arquivo `.env` na raiz do projeto:

```env
# API
API_URL=https://api.example.com
API_KEY=your-api-key

# Spark
SPARK_MASTER=spark://localhost:7077
SPARK_MEMORY=2g

# Data paths
DATA_PATH=/data

# Airflow
AIRFLOW_HOME=/opt/airflow
```

### docker-compose.yaml

Configurar services:
- Airflow Webserver
- Airflow Scheduler
- Spark Master
- Spark Worker(s)
- PostgreSQL (Airflow metadata)

## 🐳 Docker

### Build customizado da imagem Spark

```bash
docker build -f docker/Dockerfile.spark -t bees-spark:latest .
```

### Executar job Spark diretamente

```bash
docker exec -it bees-spark-master spark-submit \
  --class org.apache.spark.examples.SparkPi \
  /opt/spark/examples/jars/spark-examples_2.12-3.5.0.jar \
  100
```

## 📝 Logs

Logs são salvos em `/logs`:

```bash
tail -f logs/spark_jobs.log
tail -f logs/airflow_scheduler.log
```

## 🤝 Contribuindo

1. Criar branch feature: `git checkout -b feature/sua-feature`
2. Commit changes: `git commit -am 'Adiciona nova feature'`
3. Push to branch: `git push origin feature/sua-feature`
4. Abrir Pull Request

## 📞 Suporte

Para dúvidas e issues, abrir uma issue no repositório.

## 📄 Licença

Projeto BEES Brewery Case - Todos os direitos reservados.

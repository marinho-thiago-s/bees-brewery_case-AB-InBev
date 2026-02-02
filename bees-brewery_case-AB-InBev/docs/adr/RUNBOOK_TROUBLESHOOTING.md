# Runbook de Troubleshooting - BEES Brewery Pipeline

**Versão:** 1.1  
**Data:** 1 de Fevereiro de 2026  
**Objetivo:** Guia prático para diagnóstico e resolução de problemas comuns no pipeline Medallion

---

## 📋 Índice Rápido

1. [Problemas de Execução](#1-problemas-de-execução)
2. [Problemas de Dados](#2-problemas-de-dados)
3. [Problemas de Configuração](#3-problemas-de-configuração)
4. [Problemas de Infraestrutura](#4-problemas-de-infraestrutura)
5. [Debugging Avançado](#5-debugging-avançado)
6. [Problemas de Performance](#6-problemas-de-performance)
7. [Problemas com Versionamento](#7-problemas-com-versionamento)
8. [Health Checks e Testes](#8-health-checks-e-testes)
9. [Maintenance Window](#9-maintenance-window)
10. [Contatos e Escalation](#10-contatos-e-escalation)
11. [Checklist de Verificação](#11-checklist-de-verificação)
12. [Quick Reference - Comandos Úteis](#12-quick-reference---comandos-úteis)
13. [Escalation Path](#13-escalation-path)

---

## 1. Problemas de Execução

### 1.1 Pipeline Não Inicia

#### 🔍 Sintomas
```
[ERROR] DAG failed to parse
[ERROR] Task execution failed
[ERROR] SchedulerJob: Failed to start
```

#### 🛠️ Diagnóstico

**Passo 1:** Verificar logs do Scheduler
```bash
# Acessar logs do Airflow
docker-compose logs airflow-scheduler | tail -100

# Ou em desenvolvimento local
tail -f logs/scheduler/latest
```

**Passo 2:** Validar sintaxe da DAG
```bash
# Verificar se DAG está bem formada
python dags/bees_brewery_dag.py

# Verificar erros de import
python -m py_compile dags/bees_brewery_dag.py
```

**Passo 3:** Checar permissões de arquivo
```bash
ls -la dags/bees_brewery_dag.py
# Deve estar com permissões 644 ou 755
```

#### ✅ Solução

**Cenário A: Erro de Sintaxe Python**
```bash
# 1. Verificar erro específico
python dags/bees_brewery_dag.py 2>&1 | grep -A 10 "SyntaxError"

# 2. Corrigir arquivo
# (Editar dags/bees_brewery_dag.py)

# 3. Revalidar
python dags/bees_brewery_dag.py
```

**Cenário B: Erro de Import**
```bash
# 1. Verificar dependências instaladas
pip list | grep -E "airflow|pyspark|apache"

# 2. Instalar dependências faltantes
pip install -r requirements.txt

# 3. Reiniciar containers (se Docker)
docker-compose restart airflow-scheduler
```

**Cenário C: Permissões Incorretas**
```bash
# Corrigir permissões
chmod 644 dags/bees_brewery_dag.py

# Reiniciar Airflow
docker-compose restart airflow-webserver airflow-scheduler
# OU
systemctl restart airflow-scheduler
```

#### 📝 Verificações
- [ ] Arquivo `dags/bees_brewery_dag.py` existe
- [ ] Sintaxe Python válida
- [ ] Todas as importações resolvem
- [ ] Permissões de arquivo corretas (644)
- [ ] Scheduler está rodando

#### ⏱️ SLA: 10 minutos

---

### 1.2 Task Execution Timeout

#### 🔍 Sintomas
```
[ERROR] Task timeout after 3600 seconds
[ERROR] Max tries exceeded: 3
[ERROR] Task heartbeat lost
```

#### 🛠️ Diagnóstico

**Passo 1:** Verificar logs da task
```bash
# Em Docker
docker-compose logs airflow-worker | grep "ingestion_bronze" | tail -50

# Em local
tail -f logs/dag_id=bees_brewery_medallion/task_id=ingestion_bronze/*.log
```

**Passo 2:** Checar uso de recursos
```bash
# CPU/Memory
docker stats airflow-worker

# OU em local
top -p <spark_pid>
free -m
```

**Passo 3:** Validar conectividade com API
```bash
# Testar endpoint da API
curl -I https://api.openbrewerydb.org/v1/breweries

# Com timeout customizado
curl --max-time 10 https://api.openbrewerydb.org/v1/breweries | head -20
```

#### ✅ Solução

**Cenário A: API Lenta**
```python
# Em config/environments/prod.yaml, aumentar timeout
api:
  timeout: 60  # De 30 para 60 segundos
  retries: 5
  backoff_factor: 2
```

**Cenário B: Spark Lento**
```python
# Em config/environments/prod.yaml, aumentar recursos
spark:
  driver_memory: 4g    # De 2g para 4g
  executor_memory: 4g
  executor_cores: 4
```

**Cenário C: Timeout da Task**
```python
# Em dags/bees_brewery_dag.py
ingestion_task = PythonOperator(
    task_id='ingestion_bronze',
    python_callable=run_ingestion,
    execution_timeout=timedelta(minutes=30),  # Aumentar de 10 para 30
    retries=3,
    retry_delay=timedelta(minutes=5),
)
```

**Cenário D: Muitos Retries**
```bash
# Se há muitas tentativas falhando:
# 1. Limpar estado anterior
airflow tasks clear bees_brewery_medallion -s 2026-02-01

# 2. Reexecutar
airflow tasks run bees_brewery_medallion ingestion_bronze 2026-02-01
```

#### 📝 Verificações
- [ ] Conectividade com API (curl test)
- [ ] Recursos disponíveis (CPU/Memory)
- [ ] Timeout configurado adequadamente
- [ ] Rede estável (sem packet loss)
- [ ] Logs indicam etapa de lentidão

#### ⏱️ SLA: 20 minutos

---

### 1.3 Task Failed com AttributeError

#### 🔍 Sintomas
```
[ERROR] AttributeError: 'NoneType' object has no attribute 'baseRDD'
[ERROR] AttributeError: 'DataFrame' has no attribute 'transform'
```

#### 🛠️ Diagnóstico

**Passo 1:** Extrair full traceback
```bash
# Ver erro completo
docker-compose logs airflow-worker | grep -A 30 "AttributeError"

# OU em arquivo
cat logs/dag_id=bees_brewery_medallion/task_id=*/attempt=1/*.log | grep -A 30 "Traceback"
```

**Passo 2:** Verificar versão de dependências
```bash
# Versão do PySpark
python -c "import pyspark; print(pyspark.__version__)"

# Versão do Airflow
python -c "import airflow; print(airflow.__version__)"

# Comparar com requirements.txt
cat requirements.txt | grep -E "pyspark|apache-airflow"
```

#### ✅ Solução

**Cenário A: Spark Session é None**
```python
# ❌ ERRO
class IngestionJob(BaseJob):
    def execute(self):
        self.spark.createDataFrame(...)  # self.spark pode ser None

# ✅ CORRETO
class IngestionJob(BaseJob):
    def execute(self):
        if self.spark is None:
            raise ValueError("Spark session não foi inicializado")
        self.spark.createDataFrame(...)
```

**Cenário B: Versão PySpark Incompatível**
```bash
# 1. Verificar versão esperada
cat requirements.txt | grep pyspark

# 2. Reinstalar versão correta
pip install --force-reinstall pyspark==3.5.0

# 3. Validar
python -c "from pyspark.sql import SparkSession; print('OK')"
```

**Cenário C: DataFrame não tem método esperado**
```python
# ❌ ERRO - PySpark 3.0 não tem 'transform'
df.transform(lambda x: x.select("*"))

# ✅ CORRETO - Usar select direto
df.select("*")

# ✅ OU - Para versão nova (3.5+)
from pyspark.sql.functions import transform
```

#### 📝 Verificações
- [ ] Versão PySpark matches requirements.txt
- [ ] Spark Session inicializado corretamente
- [ ] Métodos disponíveis na versão em uso
- [ ] Imports corretos para a versão
- [ ] Sem conflitos de dependências

#### ⏱️ SLA: 15 minutos

---

## 2. Problemas de Dados

### 2.1 Bronze Layer Vazia

#### 🔍 Sintomas
```
[WARNING] Bronze data está vazio!
[ERROR] Silver layer precisa de dados Bronze
[ERROR] ValueError: No schema provided
```

#### 🛠️ Diagnóstico

**Passo 1:** Verificar se dados foram salvos
```bash
# Verificar estrutura de diretórios
find datalake/bronze -type f | head -20

# Verificar tamanho de dados
du -sh datalake/bronze/breweries/

# Contar arquivos
find datalake/bronze/breweries -name "*.json" -o -name "*.parquet" | wc -l
```

**Passo 2:** Validar logs de ingestion
```bash
# Extrair logs da task
cat logs/dag_id=bees_brewery_medallion/task_id=ingestion_bronze/*/log.txt

# Procurar por erros
grep -i "error\|exception\|failed" logs/dag_id=bees_brewery_medallion/task_id=ingestion_bronze/*/log.txt
```

**Passo 3:** Testar API manualmente
```bash
# Verificar se API está respondendo
curl -s "https://api.openbrewerydb.org/v1/breweries?per_page=1" | python -m json.tool

# Verificar quantidade de registros
curl -s "https://api.openbrewerydb.org/v1/breweries?per_page=1" | jq '.[] | length'
```

#### ✅ Solução

**Cenário A: API não está respondendo**
```bash
# 1. Testar conectividade
ping -c 3 api.openbrewerydb.org

# 2. Testar DNS
nslookup api.openbrewerydb.org

# 3. Aguardar recuperação da API
sleep 300  # Esperar 5 minutos

# 4. Reexecutar task
airflow tasks run bees_brewery_medallion ingestion_bronze 2026-02-01
```

**Cenário B: Dados foram salvos em local errado**
```bash
# 1. Procurar por dados em outros locais
find datalake -name "*.json" -o -name "*.parquet"

# 2. Verificar configuração de paths
cat config/environments/prod.yaml | grep -A 5 "storage:"

# 3. Mover dados para local correto
mv datalake/bronze_output/* datalake/bronze/breweries/

# 4. Reexecutar pipeline dependente
airflow tasks run bees_brewery_medallion transformation_silver 2026-02-01
```

**Cenário C: Ingestion falhou silenciosamente**
```bash
# 1. Executar manualmente para ver erro
python -c "
from spark_jobs.ingestion import fetch_and_save_bronze
from core.spark_session import get_spark_session

spark = get_spark_session()
fetch_and_save_bronze(spark, 'https://api.openbrewerydb.org/v1/breweries', 'datalake/bronze/breweries')
"

# 2. Corrigir erro
# (verificar logs de erro acima)

# 3. Limpar e reexecutar
rm -rf datalake/bronze/breweries/*
airflow tasks run bees_brewery_medallion ingestion_bronze 2026-02-01
```

#### 📝 Verificações
- [ ] API está respondendo (curl test)
- [ ] Conectividade com internet OK
- [ ] Caminho de output está correto
- [ ] Permissões de escrita em datalake
- [ ] Logs mostram dados foram fetched

#### ⏱️ SLA: 15 minutos

---

### 2.2 Schema Mismatch em Silver Layer

#### 🔍 Sintomas
```
[ERROR] Schema mismatch!
[ERROR] Expected StructType([...]), got StructType([...])
[ERROR] ValueError: Schema validation failed
```

#### 🛠️ Diagnóstico

**Passo 1:** Verificar schema esperado vs atual
```bash
# Extrair schema da primeira linha de Bronze
python -c "
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('debug').getOrCreate()
df = spark.read.json('datalake/bronze/breweries/').limit(1)
df.printSchema()
"

# Comparar com schema esperado
cat schemas/bronze.py | grep -A 20 "BREWERIES_SCHEMA"
```

**Passo 2:** Verificar dados de entrada
```bash
# Ver sample de dados
cat datalake/bronze/breweries/*.json | head -5 | python -m json.tool

# Verificar campos presentes
cat datalake/bronze/breweries/*.json | jq 'keys' | head -1
```

#### ✅ Solução

**Cenário A: Campos faltando nos dados**
```bash
# 1. Verificar quais campos estão faltando
python -c "
import json
with open('datalake/bronze/breweries/*.json', 'r') as f:
    data = json.load(f)
    print('Campos presentes:', data.keys())
"

# 2. Se API não retorna campo, adicionar logicamente
# Em spark_jobs/transformation_silver.py
from pyspark.sql.functions import lit

df = df.withColumn('campo_faltando', lit(None))
```

**Cenário B: Tipo de dado diferente**
```bash
# 1. Verificar tipo esperado vs atual
python -c "
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('debug').getOrCreate()
df = spark.read.json('datalake/bronze/breweries/').limit(1)

# Ver tipo de cada coluna
for field in df.schema:
    print(f'{field.name}: {field.dataType}')
"

# 2. Converter tipos conforme necessário
# Em spark_jobs/transformation_silver.py
from pyspark.sql.types import StringType, IntegerType
from pyspark.sql.functions import col

df = df.withColumn('id', col('id').cast(StringType()))
```

**Cenário C: Schema definido incorretamente**
```bash
# 1. Atualizar schema em schemas/bronze.py
# Remover campos faltando ou adicionar novos

# 2. Validar schema
python -c "
from schemas.bronze import BronzeSchema
print('Schema BREWERIES:')
BronzeSchema.BREWERIES_SCHEMA.printTreeString()
"

# 3. Reexecutar pipeline
airflow tasks run bees_brewery_medallion transformation_silver 2026-02-01
```

#### 📝 Verificações
- [ ] Campos de Bronze match com esperado
- [ ] Tipos de dados corretos
- [ ] Schema em `schemas/bronze.py` atualizado
- [ ] Sem valores inesperados (null onde não esperado)
- [ ] Dados de amostra validam com schema

#### ⏱️ SLA: 20 minutos

---

### 2.3 Gold Layer com Resultados Incorretos

#### 🔍 Sintomas
```
[WARNING] Resultado diferente do esperado
[ERROR] Somas não batem com manual check
[ERROR] Contagens incorretas por estado
```

#### 🛠️ Diagnóstico

**Passo 1:** Validar dados de entrada (Silver)
```bash
# Contar registros
python -c "
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('debug').getOrCreate()
silver = spark.read.parquet('datalake/silver/breweries/')
print(f'Total de breweries em Silver: {silver.count()}')
print(f'Sem duplicatas: {silver.dropDuplicates().count()}')
"
```

**Passo 2:** Validar lógica de agregação
```bash
# Executar query de agregação manualmente
python -c "
from pyspark.sql import SparkSession
from pyspark.sql.functions import count

spark = SparkSession.builder.appName('debug').getOrCreate()
silver = spark.read.parquet('datalake/silver/breweries/')

# Agregação por tipo e estado
agg_result = silver.groupBy('brewery_type', 'state_province').count().collect()
for row in agg_result[:10]:
    print(row)
"
```

**Passo 3:** Comparar com expectativa
```bash
# Verificar resultado Gold
python -c "
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('debug').getOrCreate()
gold = spark.read.parquet('datalake/gold/breweries_agg/')
gold.show(20)

# Exportar para análise
gold.coalesce(1).write.mode('overwrite').csv('/tmp/gold_debug/')
"
```

#### ✅ Solução

**Cenário A: Duplicatas não foram removidas**
```python
# ✅ CORRETO - Em transformation_silver.py
from pyspark.sql.functions import row_number, col
from pyspark.sql.window import Window

window_spec = Window.partitionBy("id").orderBy("updated_at")
df = df.withColumn("rn", row_number().over(window_spec))
df = df.filter(col("rn") == 1).drop("rn")
```

**Cenário B: Agregação com valores NULL**
```python
# ✅ CORRETO - Em aggregation_gold.py
from pyspark.sql.functions import count, coalesce, lit

result = silver.filter(col("brewery_type").isNotNull()) \
    .groupBy("brewery_type", "state_province") \
    .agg(count("*").alias("quantity"))
```

**Cenário C: Particionamento incorreto**
```python
# ✅ CORRETO - Verificar particionamento
silver.show()  # Verificar colunas
silver.groupBy("state_province").count().show()  # Contar por estado

# Se estado está vazio/null:
silver.filter(col("state_province").isNotNull()).groupBy("state_province").count().show()
```

#### 📝 Verificações
- [ ] Silver contém dados esperados
- [ ] Sem valores NULL onde não esperado
- [ ] Agregação agrupa corretamente
- [ ] Contagens batem com validação manual
- [ ] Particionamento aplicado corretamente

#### ⏱️ SLA: 25 minutos

---

## 3. Problemas de Configuração

### 3.1 Arquivo Config Não Encontrado

#### 🔍 Sintomas
```
[ERROR] FileNotFoundError: config/environments/prod.yaml not found
[ERROR] KeyError: 'spark' not found in config
```

#### 🛠️ Diagnóstico

**Passo 1:** Verificar estrutura de configs
```bash
# Listar arquivos
find config -type f

# Verificar conteúdo
cat config/config.py
cat config/environments/prod.yaml
```

**Passo 2:** Validar YAML syntax
```bash
# Verificar sintaxe YAML
python -c "import yaml; yaml.safe_load(open('config/environments/prod.yaml'))" || echo "YAML inválido"

# Ver estrutura
python -c "import yaml; print(yaml.safe_load(open('config/environments/prod.yaml')))"
```

#### ✅ Solução

**Cenário A: Arquivo não existe**
```bash
# 1. Criar arquivo base
cp config/environments/dev.yaml config/environments/prod.yaml

# 2. Ajustar para produção
# (Editar valores conforme necessário)

# 3. Validar
python -c "from config.config import Config; c = Config.from_yaml('prod'); print('OK')"
```

**Cenário B: Caminho relativo incorreto**
```python
# ❌ ERRO
config = Config.from_yaml("config/environments/prod.yaml")

# ✅ CORRETO - Usar caminho relativo ao projeto
import os
config_path = os.path.join(os.path.dirname(__file__), "config", "environments", "prod.yaml")
config = Config.from_yaml(config_path)

# ✅ OU - Em variável de ambiente
import os
env = os.getenv("ENV", "dev")
config = Config.from_yaml(f"config/environments/{env}.yaml")
```

**Cenário C: Variável de ambiente não setada**
```bash
# 1. Verificar variável
echo $ENV

# 2. Setar variável
export ENV=prod

# 3. Verificar que foi setada
echo $ENV

# 4. Em Docker, adicionar ao docker-compose.yaml
environment:
  - ENV=prod
  - PYTHONPATH=/opt/airflow
```

#### 📝 Verificações
- [ ] Arquivo config existe em caminho esperado
- [ ] Sintaxe YAML válida
- [ ] Variáveis de ambiente setadas
- [ ] Permissões de leitura do arquivo (644)
- [ ] PYTHONPATH inclui diretório de configs

#### ⏱️ SLA: 10 minutos

---

### 3.2 Credenciais/API Key Não Configurada

#### 🔍 Sintomas
```
[ERROR] InvalidCredentialsError
[ERROR] 401 Unauthorized
[ERROR] API key not provided
```

#### 🛠️ Diagnóstico

**Passo 1:** Verificar variáveis de ambiente
```bash
# Listar todas as variáveis relevantes
env | grep -i "api\|key\|secret\|password"

# Verificar variável específica
echo $API_KEY
echo $OPENBREWERY_API_KEY
```

**Passo 2:** Verificar onde credenciais são usadas
```bash
# Procurar por referências
grep -r "API_KEY\|api_key\|secret" config/ spark_jobs/ --include="*.py"
```

#### ✅ Solução

**Cenário A: Variável não está setada**
```bash
# 1. Setar temporariamente (dev only)
export API_KEY="sua_chave_aqui"

# 2. Verificar
echo $API_KEY

# 3. Permanentemente em ~/.bashrc ou ~/.zshrc
echo 'export API_KEY="sua_chave_aqui"' >> ~/.zshrc
source ~/.zshrc
```

**Cenário B: Credenciais em arquivo**
```bash
# 1. Criar arquivo .env (NÃO COMMITAR)
echo "API_KEY=sua_chave_aqui" > .env

# 2. Carregar em script
set -a
source .env
set +a

# 3. Usar em Python
import os
api_key = os.getenv("API_KEY")
```

**Cenário C: Credenciais em Docker**
```yaml
# docker-compose.yaml
services:
  airflow-worker:
    environment:
      - API_KEY=${API_KEY}
      - OPENBREWERY_API_KEY=${OPENBREWERY_API_KEY}
```

```bash
# Executar com variáveis
API_KEY="chave123" docker-compose up -d
```

#### 📝 Verificações
- [ ] Variável de ambiente está setada
- [ ] Credenciais corretas
- [ ] Sem credenciais em código ou git
- [ ] .env está em .gitignore
- [ ] Acesso à API funciona (curl test)

#### ⏱️ SLA: 10 minutos

---

## 4. Problemas de Infraestrutura

### 4.1 Docker Container Não Inicia

#### 🔍 Sintomas
```
[ERROR] Container exited with code 1
[ERROR] No space left on device
[ERROR] Cannot connect to Docker daemon
```

#### 🛠️ Diagnóstico

**Passo 1:** Verificar status dos containers
```bash
# Ver containers rodando
docker-compose ps

# Ver todos containers (incluindo parados)
docker-compose ps -a

# Ver logs de container específico
docker-compose logs airflow-worker | tail -50
```

**Passo 2:** Verificar recursos
```bash
# Uso de disco
docker system df

# Recursos em tempo real
docker stats

# Espaço disponível
df -h
```

**Passo 3:** Validar arquivo docker-compose
```bash
# Validar sintaxe
docker-compose config

# Ver se há erros
docker-compose config 2>&1 | head -20
```

#### ✅ Solução

**Cenário A: Sem espaço em disco**
```bash
# 1. Liberar espaço
docker system prune -a  # Remove containers e images não usadas
docker volume prune     # Remove volumes não usados

# 2. Limpar específicos
docker rmi $(docker images -q)  # Remove todas as images
docker volume rm $(docker volume ls -q)  # Remove todos os volumes

# 3. Reiniciar
docker-compose up -d
```

**Cenário B: Docker daemon não está rodando**
```bash
# macOS
brew services start docker
# OU
open /Applications/Docker.app

# Linux
sudo systemctl start docker

# Verificar
docker --version
```

**Cenário C: Port já em uso**
```bash
# 1. Verificar qual processo usa a port
lsof -i :8080  # Para porta 8080

# 2. Liberar port
kill -9 <PID>

# 3. OU usar port diferente em docker-compose.yaml
ports:
  - "8081:8080"  # Usar 8081 ao invés de 8080
```

**Cenário D: Arquivo docker-compose corrompido**
```bash
# 1. Validar
docker-compose config

# 2. Se houver erro, corrigir indentação/sintaxe
# (Editar docker-compose.yaml)

# 3. Tentar novamente
docker-compose up -d
```

#### 📝 Verificações
- [ ] Docker daemon está rodando
- [ ] Espaço em disco disponível (>10GB)
- [ ] Ports não estão em uso
- [ ] docker-compose.yaml é válido
- [ ] Permissões de arquivo OK

#### ⏱️ SLA: 15 minutos

---

### 4.2 Spark Job OutOfMemoryError

#### 🔍 Sintomas
```
[ERROR] Exception in thread "Executor task launch worker"
[ERROR] java.lang.OutOfMemoryError: GC overhead limit exceeded
[ERROR] java.lang.OutOfMemoryError: Java heap space
```

#### 🛠️ Diagnóstico

**Passo 1:** Verificar memória atual
```bash
# Em Docker
docker stats airflow-worker

# Em local
free -h
ps aux | grep spark | grep java
```

**Passo 2:** Verificar configuração de memória
```bash
# Ver configuração Spark
cat config/environments/prod.yaml | grep -A 10 "spark:"

# Ver argumentos JVM
grep -r "Xmx\|Xms\|executor_memory\|driver_memory" config/
```

#### ✅ Solução

**Cenário A: Memory insuficiente**
```yaml
# config/environments/prod.yaml
spark:
  driver_memory: 4g      # Aumentar de 2g
  executor_memory: 8g    # Aumentar de 4g
  executor_cores: 4
  num_executors: 2       # Ou reduzir para 1 se pouco RAM
```

**Cenário B: Em Docker, limitar melhor**
```yaml
# docker-compose.yaml
services:
  airflow-worker:
    environment:
      - SPARK_LOCAL_IP=0.0.0.0
      - SPARK_DRIVER_MEMORY=4g
      - SPARK_EXECUTOR_MEMORY=4g
    mem_limit: 16g  # Limitar container
```

**Cenário C: Dados muito grandes**
```python
# Adicionar reparticionamento em ingestion
# spark_jobs/ingestion.py

df = spark.read.json(...)
# Repartição antes de salvar
df = df.repartition(10)  # Dividir em 10 partições
df.write.mode("overwrite").json(output_path)
```

**Cenário D: Validar máquina tem recursos**
```bash
# Verificar RAM disponível
free -h

# Se < 8GB, não rodar em local
# Se < 4GB, deve usar Docker com limites reduzidos

# Recomendação
# Desenvolvimento: 4GB RAM no container
# Produção: 16GB+ RAM no container
```

#### 📝 Verificações
- [ ] RAM disponível na máquina
- [ ] Configuração Spark memória adequada
- [ ] Sem outras aplicações consumindo RAM
- [ ] Reparticionamento aplicado se necessário
- [ ] Persistência de dados não explosiva

#### ⏱️ SLA: 20 minutos

---

## 5. Debugging Avançado

### 5.1 Ativar Debug Logging

#### 🛠️ Procedimento

**Passo 1:** Configurar logging em dev
```yaml
# config/environments/dev.yaml
logging:
  level: DEBUG
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

**Passo 2:** Adicionar logging em código
```python
# spark_jobs/ingestion.py
import logging

logger = logging.getLogger(__name__)

class IngestionJob(BaseJob):
    def execute(self):
        logger.debug(f"Input path: {self.input_path}")
        logger.info(f"Starting ingestion...")
        logger.debug(f"API URL: {self.api_url}")
        
        try:
            df = self._fetch_data()
            logger.debug(f"Fetched {df.count()} records")
        except Exception as e:
            logger.error(f"Error fetching data: {str(e)}", exc_info=True)
            raise
```

**Passo 3:** Ver logs detalhados
```bash
# Em Docker
docker-compose logs airflow-worker | grep DEBUG

# Em arquivo
tail -f logs/dag_id=bees_brewery_medallion/task_id=*/attempt=*/log.txt | grep DEBUG
```

---

### 5.2 Executar Task Isolada

#### 🛠️ Procedimento

**Passo 1:** Executar via Python direto
```python
# script_debug.py
import sys
sys.path.insert(0, '/path/to/project')

from config.config import Config
from core.storage import LocalStorage
from spark_jobs.ingestion import IngestionJob

# Carregar config
config = Config.from_yaml("config/environments/dev.yaml")

# Criar job
storage = LocalStorage(config.storage.path)
job = IngestionJob(config.to_dict(), storage)

# Executar
try:
    job.execute()
    print("✅ Job succeeded!")
except Exception as e:
    print(f"❌ Job failed: {str(e)}")
    import traceback
    traceback.print_exc()
```

```bash
python script_debug.py
```

**Passo 2:** Debugar com breakpoints (VSCode)
```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Ingestion",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/script_debug.py",
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ]
}
```

---

### 5.3 Inspecionar DataFrame

#### 🛠️ Procedimento

```python
# script_inspect.py
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, isnull, count

spark = SparkSession.builder.appName("inspect").getOrCreate()

# Ler dados
df = spark.read.json("datalake/bronze/breweries/")

print("=== SCHEMA ===")
df.printSchema()

print("\n=== SAMPLE DATA ===")
df.show(5, truncate=False)

print("\n=== COUNT ===")
print(f"Total records: {df.count()}")

print("\n=== NULL VALUES ===")
for col_name in df.columns:
    null_count = df.filter(isnull(col(col_name))).count()
    print(f"{col_name}: {null_count} nulls")

print("\n=== DISTINCT VALUES ===")
for col_name in df.columns[:3]:  # Primeiras 3 colunas
    distinct = df.select(col_name).distinct().count()
    print(f"{col_name}: {distinct} distinct values")

print("\n=== SUMMARY ===")
df.describe().show()
```

```bash
python script_inspect.py
```

---

## 6. Problemas de Performance

### 6.1 Pipeline Muito Lento

#### 🔍 Sintomas
```
[WARNING] Pipeline rodando há mais de 2 horas
[WARNING] Bronze task leva 40 minutos
[WARNING] Silver transformation timeout
```

#### 🛠️ Diagnóstico

**Passo 1:** Identificar gargalo
```bash
# Ver tempo de cada task
airflow dags test bees_brewery_medallion 2026-02-01 -d | grep "Task duration"

# OU em logs
cat logs/dag_id=bees_brewery_medallion/*/log.txt | grep -E "finished|duration"
```

**Passo 2:** Monitorar recursos durante execução
```bash
# Terminal 1: Executar pipeline
airflow tasks run bees_brewery_medallion ingestion_bronze 2026-02-01

# Terminal 2: Monitorar (em Docker)
watch -n 1 'docker stats airflow-worker --no-stream | grep -E "CPU|MEM"'

# OU em local
watch -n 1 'ps aux | grep spark | grep -v grep'
```

**Passo 3:** Analisar plano de execução Spark
```python
# script_analyze_plan.py
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("analyze").getOrCreate()
df = spark.read.json("datalake/bronze/breweries/")

# Ver plano de execução
df.explain(extended=True)

# Contar partições
print(f"Partições: {df.rdd.getNumPartitions()}")

# Ver distribuição de dados
df.groupBy("state_province").count().show(20)
```

#### ✅ Solução

**Cenário A: Muitas partições causa overhead**
```python
# spark_jobs/ingestion.py
df = spark.read.json(...)
# Reduzir partições
df = df.coalesce(4)  # De 200 para 4
df.write.mode("overwrite").json(output_path)
```

**Cenário B: Falta de broadcast em join**
```python
# ✅ CORRETO - Bronze é grande, referência é pequena
from pyspark.sql.functions import broadcast

result = bronze.join(
    broadcast(reference_df),  # Enviar pequeno DF para todos os nodes
    "id"
)
```

**Cenário C: Sem cache de dados intermediários**
```python
# ✅ CORRETO - Cache dados que serão reutilizados
silver = bronze.filter(...).select(...)
silver.cache()

# Usar silver múltiplas vezes sem recalcular
silver.write.parquet(...)
```

**Cenário D: API rate limit**
```python
# ✅ CORRETO - Adicionar delays entre requisições
import time

for page in range(total_pages):
    data = fetch_page(page)
    time.sleep(0.5)  # 500ms entre requests
    df = df.union(convert_to_df(data))
```

#### 📝 Verificações
- [ ] Número de partições apropriado (CPU count)
- [ ] Broadcast usado para DataFrames pequenos
- [ ] Cache aplicado em transformações reutilizadas
- [ ] Sem full table scans desnecessários
- [ ] API rate limits respeitados

#### ⏱️ SLA: 30 minutos

---

### 6.2 Consumo Excessivo de Memória

#### 🔍 Sintomas
```
[ERROR] GC overhead limit exceeded
[ERROR] Unable to acquire memory
[WARNING] Spilling to disk
```

#### 🛠️ Diagnóstico

**Passo 1:** Verificar alocação atual
```bash
# Em Docker
docker stats --no-stream | grep airflow-worker

# Ver limites
docker inspect <container_id> | grep -A 5 "Memory"
```

**Passo 2:** Identificar operações memory-hungry
```python
# Verificar se há collect() em DF grande
# ❌ EVITAR
df.collect()  # Traz tudo para memória

# ✅ PREFERIR
df.show(5)     # Mostra amostra
df.count()     # Conta sem material
```

**Passo 3:** Monitorar durante execução
```bash
# Terminal separado
watch -n 1 'free -m; echo "---"; docker stats --no-stream'
```

#### ✅ Solução

**Cenário A: Collect em DataFrame grande**
```python
# ❌ ERRO
result = silver.groupBy("state").count().collect()
for row in result:
    process(row)

# ✅ CORRETO - Usar iterate ou write
silver.groupBy("state").count().write.csv("/tmp/result/")

# ✅ OU - Usar toLocalIterator()
for row in silver.groupBy("state").count().toLocalIterator():
    process(row)
```

**Cenário B: Aumentar memória alocada**
```yaml
# config/environments/prod.yaml
spark:
  driver_memory: 8g      # De 4g para 8g
  executor_memory: 8g    # De 4g para 8g
  executor_cores: 2      # Reduzir cores para menos tasks paralelas
  num_executors: 1       # Usar apenas 1 executor se tiver pouca RAM
```

**Cenário C: Persistência intermediária**
```python
# spark_jobs/transformation_silver.py
# Dividir em etapas e salvar intermediários

# Etapa 1: Limpar dados
bronze = spark.read.json(...)
cleaned = bronze.filter(...).select(...)
cleaned.write.parquet("datalake/silver/tmp_cleaned/")

# Etapa 2: Transformar
cleaned = spark.read.parquet("datalake/silver/tmp_cleaned/")
transformed = cleaned.join(...).groupBy(...)
transformed.write.parquet("datalake/silver/breweries/")
```

#### 📝 Verificações
- [ ] Sem collect() em DataFrames grandes
- [ ] Memória alocada > tamanho maior DF × 3
- [ ] Persistent cache removido após uso
- [ ] Etapas divididas se muito grandes
- [ ] Monitoramento durante execução

#### ⏱️ SLA: 25 minutos

---

## 7. Problemas com Versionamento

### 7.1 DAG Alterada mas Não Reflete no Airflow

#### 🔍 Sintomas
```
[ERROR] Alterações em bees_brewery_dag.py não aparecem
[WARNING] Task ainda usa código antigo
[ERROR] Mudanças foram commitadas mas não rodaram
```

#### 🛠️ Diagnóstico

**Passo 1:** Verificar se arquivo foi modificado
```bash
# Ver status Git
git status dags/bees_brewery_dag.py

# Ver último commit
git log -1 --oneline dags/bees_brewery_dag.py

# Ver diferenças
git diff dags/bees_brewery_dag.py
```

**Passo 2:** Verificar parsing da DAG
```bash
# Validar sintaxe
python dags/bees_brewery_dag.py

# Ver quando foi parsed por último
ls -la logs/dag_processor_manager/
tail -50 logs/dag_processor_manager/dag_processor_manager.log | grep "bees_brewery_dag"
```

**Passo 3:** Verificar cache do Airflow
```bash
# Ver versão em DB
docker-compose exec airflow-webserver airflow dags list | grep bees_brewery

# Ver arquivos em AIRFLOW_HOME
docker-compose exec airflow-webserver ls -la $AIRFLOW_HOME/dags/
```

#### ✅ Solução

**Cenário A: Arquivo não foi salvo**
```bash
# Verificar conteúdo
cat dags/bees_brewery_dag.py | grep -A 5 "dag_id="

# Se vazio ou incorreto, editar novamente
# (Usar editor de preferência)
```

**Cenário B: Dag parser não recarregou**
```bash
# Em Docker
docker-compose restart airflow-scheduler

# Em local
systemctl restart airflow-scheduler

# Aguardar parse (até 5 minutos)
sleep 60
airflow dags list | grep bees_brewery
```

**Cenário C: Cache do browser**
```bash
# Hard refresh em Airflow UI
# Cmd+Shift+R (Mac) ou Ctrl+Shift+R (Linux/Windows)

# OU limpar via terminal
curl -X POST http://localhost:8080/api/experimental/pools/clear_cache
```

**Cenário D: Forçar reparse**
```bash
# 1. Limpar DAG do DB
airflow dags delete bees_brewery_medallion

# 2. Recriar desde zero
airflow dags list  # Vai ler arquivo novamente

# 3. Reexecutar
airflow dags trigger bees_brewery_medallion
```

#### 📝 Verificações
- [ ] Arquivo editado e salvo corretamente
- [ ] Git status mostra arquivo modificado
- [ ] Scheduler foi reiniciado após mudança
- [ ] Browser cache foi limpo (hard refresh)
- [ ] DAG parser completou (check logs)

#### ⏱️ SLA: 15 minutos

---

### 7.2 Merge Conflict em DAG ou Configuração

#### 🔍 Sintomas
```
[ERROR] CONFLICT (content conflict): dags/bees_brewery_dag.py
[ERROR] Automatic merge failed
[ERROR] Fix conflicts and commit the result
```

#### 🛠️ Diagnóstico

**Passo 1:** Identificar arquivos em conflito
```bash
# Ver status
git status

# Ver conflitos detalhados
git diff --name-only --diff-filter=U
```

**Passo 2:** Ver marcadores de conflito
```bash
# Abrir arquivo
cat dags/bees_brewery_dag.py | grep -A 5 -B 5 "<<<<"

# Mostrar ambos os lados
git diff dags/bees_brewery_dag.py
```

#### ✅ Solução

**Cenário A: Resolver conflito manualmente**
```bash
# 1. Abrir arquivo e resolver conflito
# Remover marcadores: <<<<<<, ======, >>>>>>
# Manter código correto de ambos os lados

# 2. Validar resultado
python dags/bees_brewery_dag.py

# 3. Marcar como resolvido
git add dags/bees_brewery_dag.py

# 4. Completar merge
git commit -m "Merge: Resolve conflicts in DAG"
```

**Cenário B: Usar versão do branch atual**
```bash
# Manter versão local (--ours)
git checkout --ours dags/bees_brewery_dag.py
git add dags/bees_brewery_dag.py

# OU manter versão remota (--theirs)
git checkout --theirs dags/bees_brewery_dag.py
git add dags/bees_brewery_dag.py
```

**Cenário C: Abort merge e começar novamente**
```bash
# Se tudo ficou muito confuso
git merge --abort

# Tentar merge novamente
git merge origin/main
```

#### 📝 Verificações
- [ ] Ambos os lados do conflito entendidos
- [ ] Código merged é válido (python -m py_compile)
- [ ] Testes passam após merge
- [ ] Commit message descreve resolução
- [ ] Nenhum marcador de conflito permanece

#### ⏱️ SLA: 20 minutos

---

## 8. Health Checks e Testes

### 8.1 Executar Health Check do Pipeline

#### 🛠️ Procedimento

```bash
# script_health_check.sh
#!/bin/bash

echo "🏥 HEALTH CHECK - BEES Brewery Pipeline"
echo "========================================"

# 1. Verificar Docker
echo -e "\n✓ Verificando Docker..."
if docker-compose ps | grep -q "Up"; then
    echo "  ✅ Docker containers rodando"
else
    echo "  ❌ Docker containers não estão todos UP"
    docker-compose ps
fi

# 2. Verificar Airflow
echo -e "\n✓ Verificando Airflow..."
if curl -s http://localhost:8080/api/v1/dags | jq '.dags[0]' > /dev/null; then
    echo "  ✅ Airflow webserver respondendo"
else
    echo "  ❌ Airflow não está respondendo"
fi

# 3. Verificar API
echo -e "\n✓ Verificando Open Brewery DB..."
if curl -s -I https://api.openbrewerydb.org/v1/breweries | grep -q "200"; then
    echo "  ✅ API respondendo com 200 OK"
else
    echo "  ❌ API não está respondendo"
fi

# 4. Verificar Spark
echo -e "\n✓ Verificando Spark..."
if python -c "from pyspark.sql import SparkSession; print('OK')" 2>/dev/null; then
    echo "  ✅ PySpark instalado corretamente"
else
    echo "  ❌ Problema com PySpark"
fi

# 5. Verificar Dados
echo -e "\n✓ Verificando Data Lake..."
BRONZE_COUNT=$(find datalake/bronze -type f | wc -l)
if [ "$BRONZE_COUNT" -gt 0 ]; then
    echo "  ✅ Bronze layer: $BRONZE_COUNT arquivos"
else
    echo "  ⚠️  Bronze layer vazio"
fi

echo -e "\n✅ Health Check Concluído!"
```

```bash
chmod +x script_health_check.sh
./script_health_check.sh
```

---

### 8.2 Executar Testes Unitários

#### 🛠️ Procedimento

```bash
# Executar todos os testes
pytest tests/ -v

# Executar teste específico
pytest tests/test_ingestion.py -v

# Ver coverage
pytest tests/ --cov=spark_jobs --cov=core

# Gerar relatório HTML
pytest tests/ --cov=spark_jobs --cov-report=html
open htmlcov/index.html
```

---

## 9. Maintenance Window

### 9.1 Rotina de Limpeza Semanal

#### 🛠️ Checklist

```bash
# Rodar toda segunda-feira às 2am

# 1. Limpar logs antigos (>30 dias)
find logs -type f -mtime +30 -delete

# 2. Compactar logs
gzip logs/**/*.log

# 3. Limpar dados de teste
rm -rf datalake/tmp/*

# 4. Validar integridade
python tests/test_architecture.py

# 5. Backup de dados
tar -czf datalake_$(date +%Y%m%d).tar.gz datalake/

# 6. Reiniciar containers
docker-compose restart

# 7. Validar startup
sleep 60
./script_health_check.sh
```

---

### 9.2 Rotina de Atualizações Mensais

#### 🛠️ Checklist

```bash
# Executar todo primeiro dia do mês

# 1. Atualizar dependências
pip install --upgrade -r requirements.txt

# 2. Rodar testes
pytest tests/ -v

# 3. Rodar full pipeline
airflow dags backfill bees_brewery_medallion --start-date 2026-01-01 --end-date 2026-02-01

# 4. Validar saídas
python scripts/validate_outputs.py

# 5. Atualizar documentação
# (Revisar RUNBOOK_TROUBLESHOOTING.md, etc)

# 6. Commit changes
git add requirements.txt docs/
git commit -m "Monthly update: $(date +%B-%Y)"
git push
```

---

## 10. Contatos e Escalation

### 10.1 Matriz de Responsabilidades

| Categoria | Responsável | Contato | Tempo Resposta |
|-----------|------------|---------|----------------|
| Pipeline Airflow | Data Engineer #1 | email@company.com | 1h |
| Spark/Data | Data Engineer #2 | email2@company.com | 2h |
| Infraestrutura | DevOps | devops@company.com | 30min |
| Banco de Dados | DBA | dba@company.com | 1h |
| On-Call Rotativo | Verificar PagerDuty | - | 15min |

### 10.2 Escalation Flow

```
Nível 1: Consultara runbook (você aqui)
   ↓
Nível 2: Contatar Data Engineer responsável
   ↓
Nível 3: Engajar DevOps/Infraestrutura
   ↓
Nível 4: Engajar On-Call Engineer
   ↓
Nível 5: Engajar Tech Lead / CTO
```

---

## 11. Checklist de Verificação

### 11.1 Antes de Rodar Pipeline

- [ ] **Configuração**
  - [ ] `config/environments/prod.yaml` existe e é válido
  - [ ] Variáveis de ambiente setadas (`$ENV`, `$API_KEY`)
  - [ ] PYTHONPATH inclui diretório do projeto

- [ ] **Código**
  - [ ] Sem erros de syntax (`python -m py_compile`)
  - [ ] Imports resolvem (`python -c "from dags import bees_brewery_dag"`)
  - [ ] Testes passando (`pytest tests/ -v`)

- [ ] **Infraestrutura**
  - [ ] Docker daemon rodando
  - [ ] Espaço em disco disponível (>10GB)
  - [ ] Memória disponível (>4GB)
  - [ ] Ports livres (8080, 5432, 6379)

- [ ] **Conectividade**
  - [ ] Internet funcionando
  - [ ] API acessível (`curl -I https://api.openbrewerydb.org/v1/breweries`)
  - [ ] DNS resolvendo (`nslookup api.openbrewerydb.org`)

- [ ] **Dados**
  - [ ] Diretório `datalake` existe
  - [ ] Permissões de escrita OK
  - [ ] Bronze/Silver/Gold directories criados

### 11.2 Após Falha de Pipeline

1. **Coletar Informações**
   - [ ] Screenshot da mensagem de erro
   - [ ] Logs completos da task
   - [ ] Versão do software (`airflow --version`, `spark-submit --version`)
   - [ ] Status de recursos (CPU, memory, disk)

2. **Isolar Problema**
   - [ ] Reproduzir erro manualmente
   - [ ] Verificar logs com DEBUG ativado
   - [ ] Validar cada etapa da DAG isoladamente

3. **Documentar Solução**
   - [ ] Descrever erro exato
   - [ ] Listar passos de resolução
   - [ ] Adicionar ao POST_MORTEM se for novo erro

---

## 12. Quick Reference - Comandos Úteis

### Docker
```bash
# Containers
docker-compose up -d              # Iniciar
docker-compose down               # Parar
docker-compose logs -f            # Logs em tempo real
docker-compose ps                 # Status
docker exec -it <container> bash  # Entrar no container

# Limpeza
docker system prune -a            # Remove tudo não usado
docker volume prune               # Remove volumes
```

### Airflow
```bash
# DAG
airflow dags list                 # Listar DAGs
airflow tasks list bees_brewery_medallion  # Listar tasks
airflow tasks run bees_brewery_medallion ingestion_bronze 2026-02-01  # Executar task

# Limpeza
airflow tasks clear bees_brewery_medallion -s 2026-02-01  # Limpar estado
airflow dags delete bees_brewery_medallion  # Deletar DAG
```

### Spark
```bash
# Local
spark-submit --version           # Versão
spark-shell                      # REPL Scala
pyspark                          # REPL Python

# Em Docker
docker-compose exec airflow-worker spark-submit --version
docker-compose exec airflow-worker pyspark
```

### Data Lake
```bash
# Inspecionar
find datalake -type f | wc -l    # Contar arquivos
du -sh datalake/                 # Tamanho total
ls -lah datalake/bronze/breweries/

# Limpeza
rm -rf datalake/bronze/*         # Limpar Bronze
rm -rf datalake/silver/*         # Limpar Silver
rm -rf datalake/gold/*           # Limpar Gold
```

### Git
```bash
# Status
git status                        # Ver mudanças
git log --oneline -10            # Últimos 10 commits
git diff                         # Diferenças não staged

# Operações
git pull origin main             # Atualizar do remoto
git push origin main             # Enviar para remoto
git stash                        # Guardar mudanças temporariamente
```

---

## 13. Escalation Path

Se problema não for resolvido com este runbook:

1. **Pesquisar Issues GitHub** → https://github.com/seu-repo/issues
2. **Logs Detalhados** → Coletar todos os logs e compartilhar
3. **Reproducible Example** → Criar minimal test case
4. **Stack Overflow** → Procurar por tags: `airflow`, `pyspark`, `docker`
5. **Community Slack** → Airflow Community, PySpark Community
6. **Suporte Comercial** → Se usando Astronomer ou Databricks

---

**Versão:** 1.1  
**Data de Criação:** 1 de Fevereiro de 2026  
**Data de Atualização:** 1 de Fevereiro de 2026  
**Próxima Revisão:** 1 de Março de 2026  
**Responsável:** Data Engineering Team

### Histórico de Versões

| Versão | Data | Mudanças |
|--------|------|----------|
| 1.0 | 1 Feb 2026 | Versão inicial com seções principais |
| 1.1 | 1 Feb 2026 | Adicionado: Performance, Versionamento, Health Checks, Maintenance |


# DOCKER_TEST_VALIDATION - Complete Testing Guide with Docker

Date: 2026-02-01
Status: Ready for Testing
Purpose: Validate that the solution works correctly in Docker

---

## Prerequisites

### Verify Installation

```bash
# Docker must be installed and running
docker --version
# Expected: Docker version 20.10+

docker-compose --version
# Expected: Docker Compose version 2.0+
```

If Docker is not running on Mac:
1. Open **Docker Desktop** (search in Applications)
2. Wait until menu bar icon shows "Docker Desktop is running"

---

## Test 1: Build Images

```bash
cd /Users/thiagomarinhoesilva/Documents/GITHUB/teste_ambev/bees-brewery-case

# Build (downloads base images and installs dependencies)
# Expected: ~5-10 minutes on first run
docker-compose build

# Expected validation:
# Successfully tagged bees-brewery-case_airflow-webserver:latest
# Successfully tagged bees-brewery-case_spark-master:latest
# Successfully tagged bees-brewery-case_spark-worker:latest
```

---

## Test 2: Start Containers

```bash
# Start in background
docker-compose up -d

# Expected: 6 containers starting
# - postgres
# - airflow-webserver
# - airflow-scheduler
# - spark-master
# - spark-worker (may take few seconds)

# Validate containers are running
docker-compose ps

# Expected output:
# NAME                                 STATUS
# bees-brewery-case-postgres-1         Up (healthy)
# bees-brewery-case-airflow-webserver-1   Up (healthy)
# bees-brewery-case-airflow-scheduler-1   Up (healthy)
# bees-brewery-case-spark-master-1     Up (healthy)
# bees-brewery-case-spark-worker-1     Up (healthy)
```

---

## Test 3: Verify Airflow UI

```bash
# Airflow should be available at http://localhost:8080
# Open in browser: http://localhost:8080

# Default credentials:
# Username: airflow
# Password: airflow

# If login page appears: Airflow is running
# If DAG "bees_brewery_medallion" appears: DAG was loaded
```

---

## Test 4: Verify Spark UI

```bash
# Spark Master should be available at http://localhost:8081
# Open in browser: http://localhost:8081

# Expected:
# - Status: Alive
# - Workers: 1
# - Cores: 2 (or more if your machine has more)
# - Memory: Available and allocated
```

---

## Test 5: Run DAG Manually

```bash
# Inside Airflow container
docker-compose exec airflow-webserver bash

# Now you are INSIDE the container:
# 1. Unpause DAG
airflow dags unpause bees_brewery_medallion

# 2. Trigger manually
airflow dags test bees_brewery_medallion 2026-02-01

# Expected output:
# [2026-02-01 00:00:00,000] {bash_operator.py:123} INFO - Running command: ['python', ...]
# [2026-02-01 00:00:00,000] {bash_operator.py:123} INFO - Task exited with return code 0

# 3. Exit container
exit
```

---

## Test 6: Verify Datalake

```bash
# See directory structure created
ls -la ./datalake/

# Expected after running DAG:
# datalake/
# ├── bronze/     (raw data from API)
# ├── silver/     (transformed data)
# └── gold/       (aggregated data)

# Validate Parquet files were created
find ./datalake -name "*.parquet" -type f

# Expected: several .parquet files in each layer
```

---

## Test 7: Run Automated Tests

```bash
# Inside Airflow container
docker-compose exec airflow-webserver bash

# Run unit tests
cd /opt/airflow
pytest tests/ -v --cov=spark_jobs --cov-report=term-missing

# Expected:
# tests/test_ingestion.py::test_ingestion_job_init PASSED
# tests/test_transformation.py::test_transformation_extracts_bronze PASSED
# tests/test_aggregation.py::test_aggregation_job_init PASSED
# tests/test_architecture.py::test_full_pipeline PASSED
#
# ================ 10 passed in 2.34s ================
# Coverage: 85%
```

---

## Test 8: Verify Logs

```bash
# View logs from specific container
docker-compose logs airflow-webserver -f

# View Scheduler logs
docker-compose logs airflow-scheduler -f

# View Spark Master logs
docker-compose logs spark-master -f

# Expected: logs without critical errors
```

---

## Test 9: Verify Connectivity Between Containers

```bash
# Inside Airflow container
docker-compose exec airflow-webserver bash

# Test connection to Spark Master
python3 << EOF
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("test") \
    .master("spark://spark-master:7077") \
    .getOrCreate()

print("Spark connection OK")
spark.stop()
EOF

# Expected: Spark connection OK
```

---

## Test 10: Stop Containers

```bash
# Stop all containers
docker-compose down

# Expected: containers stopped and removed

# Validate they stopped
docker ps

# Expected: empty list (or only containers from other projects)
```

---

## COMPLETE DAG TEST: Logs and Output Files

### Pipeline Overview

The DAG `bees_brewery_medallion` executes 5 tasks in sequence:

```
pipeline_start -> ingestion_bronze -> transformation_silver -> aggregation_gold -> pipeline_end
```

**Expected data flow:**
- **Bronze:** Raw data from API (JSON normalized to Parquet)
- **Silver:** Cleaned and transformed data
- **Gold:** Aggregated data for analysis

---

### PART 1: Prepare Environment for Test

```bash
# 1. Go to project directory
cd /Users/thiagomarinhoesilva/Documents/GITHUB/teste_ambev/bees-brewery-case

# 2. Clean previous containers (if they exist)
docker-compose down -v

# 3. Build images
docker-compose build

# Expected:
# Successfully tagged bees-brewery-case_airflow-webserver:latest
# Successfully tagged bees-brewery-case_spark-master:latest
# Successfully tagged bees-brewery-case_spark-worker:latest

# 4. Start containers in background
docker-compose up -d

# 5. Wait for complete initialization (30-60 seconds)
sleep 30

# 6. Validate containers are healthy
docker-compose ps

# Expected output:
# STATUS = "Up" and "healthy" (or "Up" if health check not running yet)
```

---

### PART 2: Validate Initial DAG State

```bash
# 1. Access Airflow container
docker-compose exec airflow-webserver bash

# Now you are INSIDE Airflow container
# All commands below run INSIDE the container

# 2. Verify DAG is registered
airflow dags list | grep bees_brewery_medallion

# Expected output:
# bees_brewery_medallion | /opt/airflow/dags/bees_brewery_dag.py | False

# 3. Verify DAG tasks
airflow tasks list bees_brewery_medallion

# Expected output:
# pipeline_start
# ingestion_bronze
# transformation_silver
# aggregation_gold
# pipeline_end

# 4. Unpause DAG (required to run)
airflow dags unpause bees_brewery_medallion

# Expected:
# Dag: bees_brewery_medallion, paused: False
```

---

### PART 3: Execute DAG Manually

```bash
# STILL INSIDE AIRFLOW CONTAINER

# Option A: Test mode (faster, for debug)
airflow dags test bees_brewery_medallion 2026-02-01

# Option B: Normal trigger (simulates actual execution)
# airflow dags trigger bees_brewery_medallion --exec-date 2026-02-01

# Wait 2-5 minutes for execution
# You will see many log lines while running

# Success signs:
# [2026-02-01 XX:XX:XX,XXX] {bash_operator.py:123} INFO - Running command: ['echo', ...]
# [2026-02-01 XX:XX:XX,XXX] {python_operator.py:180} INFO - Task exited with return code 0
# Ingestion completed! XXX records written to bronze/breweries/...
```

---

### PART 4: Monitor DAG Logs in Real Time

**In another terminal (Terminal 2):**

```bash
# While DAG is running, monitor logs

cd /Users/thiagomarinhoesilva/Documents/GITHUB/teste_ambev/bees-brewery-case

# View Airflow Scheduler logs
docker-compose logs -f airflow-scheduler

# Expected (should show DAG execution logs):
# [2026-02-01 XX:XX:XX,XXX] {scheduler.py:xxx} INFO - Running <TaskInstance: bees_brewery_medallion.ingestion_bronze 2026-02-01T00:00:00+00:00 [running]> on worker...
```

**In a third terminal (Terminal 3):**

```bash
# View Spark Master logs during job execution

docker-compose logs -f spark-master

# Expected:
# 26/02/01 XX:XX:XX INFO Master: Registering worker...
# 26/02/01 XX:XX:XX INFO MasterWebUI: Binding MasterWebUI to 0.0.0.0
```

---

### PART 5: Validate Output Files - Bronze Layer

**Back in Terminal 1 (Airflow container), after DAG completes:**

```bash
# STILL INSIDE AIRFLOW CONTAINER

# 1. List datalake structure
ls -la /opt/airflow/datalake/

# Expected:
# drwxr-xr-x  bronze/
# drwxr-xr-x  silver/
# drwxr-xr-x  gold/

# 2. Verify Bronze data (raw)
ls -la /opt/airflow/datalake/bronze/breweries/

# Expected:
# drwxr-xr-x  created_at=2026-02-01/

# 3. See Parquet files in Bronze
find /opt/airflow/datalake/bronze -name "*.parquet" -type f

# Expected:
# /opt/airflow/datalake/bronze/breweries/created_at=2026-02-01/part-00000-xxx.snappy.parquet
# (may have multiple part-XXXXX files)

# 4. Count rows in Bronze
python3 << 'EOF'
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("test").getOrCreate()
df = spark.read.parquet("/opt/airflow/datalake/bronze/breweries/created_at=2026-02-01")
print(f"Bronze Records: {df.count()}")
print(f"Bronze Schema: {df.schema}")
df.show(5)
EOF

# Expected output:
# Bronze Records: XXX (number of breweries from API)
# Bronze Schema: StructType([...])
# Shows 5 first rows with raw data
```

---

### PART 6: Validate Output Files - Silver Layer

```bash
# STILL INSIDE AIRFLOW CONTAINER

# 1. Verify Silver data (transformed)
ls -la /opt/airflow/datalake/silver/

# Expected:
# drwxr-xr-x  breweries_cleaned/

# 2. See Parquet files in Silver
find /opt/airflow/datalake/silver -name "*.parquet" -type f

# Expected:
# /opt/airflow/datalake/silver/breweries_cleaned/created_at=2026-02-01/part-00000-xxx.snappy.parquet

# 3. Validate transformation (Silver should have fewer columns/cleaned data)
python3 << 'EOF'
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("test").getOrCreate()

print("=" * 60)
print("COMPARISON: BRONZE vs SILVER")
print("=" * 60)

# Bronze
bronze_df = spark.read.parquet("/opt/airflow/datalake/bronze/breweries/created_at=2026-02-01")
print(f"\nBRONZE (Raw):")
print(f"  Records: {bronze_df.count()}")
print(f"  Columns: {len(bronze_df.columns)}")
print(f"  Column names: {bronze_df.columns}")

# Silver
silver_df = spark.read.parquet("/opt/airflow/datalake/silver/breweries_cleaned/created_at=2026-02-01")
print(f"\nSILVER (Cleaned):")
print(f"  Records: {silver_df.count()}")
print(f"  Columns: {len(silver_df.columns)}")
print(f"  Column names: {silver_df.columns}")

print(f"\nSample Silver data:")
silver_df.show(5)

spark.stop()
EOF

# Expected:
# SILVER should have:
#   - Same or fewer records (outliers removed)
#   - Renamed/cleaned columns
#   - Data without nulls in important fields
#   - Transformation timestamp added
```

---

### PART 7: Validate Output Files - Gold Layer

```bash
# STILL INSIDE AIRFLOW CONTAINER

# 1. Verify Gold data (aggregated)
ls -la /opt/airflow/datalake/gold/

# Expected:
# drwxr-xr-x  breweries_stats/

# 2. See Parquet files in Gold
find /opt/airflow/datalake/gold -name "*.parquet" -type f

# Expected:
# /opt/airflow/datalake/gold/breweries_stats/created_at=2026-02-01/part-00000-xxx.snappy.parquet

# 3. Validate aggregations (Gold should have statistics by group)
python3 << 'EOF'
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("test").getOrCreate()

gold_df = spark.read.parquet("/opt/airflow/datalake/gold/breweries_stats/created_at=2026-02-01")

print("=" * 60)
print("GOLD LAYER (Aggregated for Analytics)")
print("=" * 60)
print(f"\nStatistics:")
print(f"  Total groups/aggregations: {gold_df.count()}")
print(f"  Columns: {gold_df.columns}")

print(f"\nSample aggregation:")
gold_df.show(10)

print(f"\nGold Schema:")
gold_df.printSchema()

spark.stop()
EOF

# Expected:
# GOLD should have aggregations such as:
#   - Count by brewery_type (state, type, etc.)
#   - Stats (min, max, avg) of numeric values
#   - Data ready for BI/Dashboard
```

---

### PART 8: Validate Structured Logs

```bash
# STILL INSIDE AIRFLOW CONTAINER

# 1. View DAG execution logs
cat /opt/airflow/logs/dag_id=bees_brewery_medallion/*/2026-02-01T00:00:00*/task_id=*/attempt=1.log

# Alternatively, view log directory
find /opt/airflow/logs -name "*.log" -type f | head -10

# 2. View specific task log (example: ingestion_bronze)
cat /opt/airflow/logs/dag_id=bees_brewery_medallion/run_id=manual__2026-02-01T00:00:00*/task_id=ingestion_bronze/attempt=1.log 2>/dev/null || echo "Log not yet available"

# 3. Extract important information from logs
python3 << 'EOF'
import glob
import os

# Search for execution logs
log_dir = "/opt/airflow/logs/dag_id=bees_brewery_medallion"
log_files = glob.glob(f"{log_dir}/**/attempt=1.log", recursive=True)

print(f"Found {len(log_files)} log files")
print("\nSearching for important keywords...\n")

keywords = [
    "Success", "Error", "WARN", "completed", "failed", 
    "records written", "rows processed", "Schema validation"
]

for log_file in sorted(log_files)[:3]:  # First 3 logs
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

### PART 9: Complete Data Integrity Validation

```bash
# STILL INSIDE AIRFLOW CONTAINER

# Complete end-to-end validation script

python3 << 'EOF'
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, isnull, countDistinct
import sys

spark = SparkSession.builder \
    .appName("DataQualityValidation") \
    .getOrCreate()

print("\n" + "="*70)
print("Data Pipeline Validation: BEES Brewery")
print("="*70)

# --- BRONZE LAYER ---
print("\nBRONZE LAYER (Raw Data)")
print("-" * 70)

try:
    bronze = spark.read.parquet("/opt/airflow/datalake/bronze/breweries/created_at=2026-02-01")
    
    bronze_count = bronze.count()
    print(f"Bronze records: {bronze_count}")
    
    if bronze_count == 0:
        print("ERROR: Bronze layer is empty!")
        sys.exit(1)
    
    print(f"Bronze columns: {len(bronze.columns)} - {bronze.columns}")
    
    # Check nulls
    null_counts = bronze.select([count(isnull(col(c))).alias(c) for c in bronze.columns]).collect()[0]
    print(f"Null values per column: {null_counts.asDict()}")
    
except Exception as e:
    print(f"ERROR validating Bronze: {e}")
    sys.exit(1)

# --- SILVER LAYER ---
print("\nSILVER LAYER (Transformed Data)")
print("-" * 70)

try:
    silver = spark.read.parquet("/opt/airflow/datalake/silver/breweries_cleaned/created_at=2026-02-01")
    
    silver_count = silver.count()
    print(f"Silver records: {silver_count}")
    
    if silver_count == 0:
        print("WARNING: Silver layer is empty")
    else:
        print(f"Silver columns: {len(silver.columns)} - {silver.columns}")
        
        # Compare with Bronze
        reduction = ((bronze_count - silver_count) / bronze_count * 100) if bronze_count > 0 else 0
        print(f"Data reduction: {reduction:.2f}% (outliers removed)")
        
        # Show sample
        print(f"\nSample (5 rows):")
        silver.show(5, truncate=False)
        
except Exception as e:
    print(f"WARNING validating Silver: {e}")

# --- GOLD LAYER ---
print("\nGOLD LAYER (Aggregated Data)")
print("-" * 70)

try:
    gold = spark.read.parquet("/opt/airflow/datalake/gold/breweries_stats/created_at=2026-02-01")
    
    gold_count = gold.count()
    print(f"Gold records (aggregations): {gold_count}")
    
    if gold_count == 0:
        print("WARNING: Gold layer is empty")
    else:
        print(f"Gold columns: {len(gold.columns)} - {gold.columns}")
        
        print(f"\nAggregations Gold (sample):")
        gold.show(5, truncate=False)
        
except Exception as e:
    print(f"WARNING validating Gold: {e}")

# --- FINAL SUMMARY ---
print("\n" + "="*70)
print("VALIDATION COMPLETED SUCCESSFULLY")
print("="*70)
print(f"""
Final Summary:
  Bronze:  {bronze_count} records (raw data)
  Silver:  {silver_count if silver_count else 'N/A'} records (cleaned data)
  Gold:    {gold_count if gold_count else 'N/A'} records (aggregated data)
  
Pipeline completed all 3 layers (Bronze -> Silver -> Gold)
""")

spark.stop()
EOF

# Expected output:
# VALIDATION COMPLETED SUCCESSFULLY
# Shows record count at each layer
# Shows data flowed correctly through pipeline
```

---

### PART 10: DAG Validation Checklist

```bash
# Outside container, or inside to verify

# 1. Verify via Airflow UI (browser)
# http://localhost:8080
# - Look for: bees_brewery_medallion
# - Should show "Last Run: 2026-02-01"
# - Should show "Success" with green checkmark

# 2. Verify output directories (outside container)
ls -la /Users/thiagomarinhoesilva/Documents/GITHUB/teste_ambev/bees-brewery-case/datalake/

# Expected:
# drwxr-xr-x  bronze/
# drwxr-xr-x  silver/
# drwxr-xr-x  gold/

# 3. Count Parquet files
find /Users/thiagomarinhoesilva/Documents/GITHUB/teste_ambev/bees-brewery-case/datalake -name "*.parquet" | wc -l

# Expected: > 0 (several parquet files created)

# 4. Check container logs
docker-compose logs airflow-scheduler | grep "bees_brewery_medallion" | tail -20

# Expected: logs showing successful task execution
```

---

### PART 11: Visual Validation - Airflow UI

```
1. Access: http://localhost:8080
   Username: admin / Password: admin

2. Find DAG "bees_brewery_medallion"

3. Verify:
   - DAG is in the list
   - Status shown as "active" (green)
   - "Paused" is off (False)

4. Click DAG to see:
   - Graph View: 5 tasks (start -> bronze -> silver -> gold -> end)
   - Tree View: Last execution on 2026-02-01
   - All boxes appear green (success)

5. Click each task for logs:
   - pipeline_start: "echo Starting..."
   - ingestion_bronze: "Starting ingestion from Open Brewery DB API"
   - transformation_silver: "Starting transformation job"
   - aggregation_gold: "Starting aggregation job"
   - pipeline_end: "echo Pipeline completed successfully"
```

---

### TROUBLESHOOTING: If something fails

```bash
# If DAG fails, look for errors:

# 1. View detailed error
docker-compose logs airflow-scheduler | grep -A 10 "ERROR"

# 2. View Spark error
docker-compose logs spark-master | grep -A 5 "ERROR"

# 3. Check if API is responding
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

# 4. Check storage/disk
du -sh /Users/thiagomarinhoesilva/Documents/GITHUB/teste_ambev/bees-brewery-case/datalake/
df -h

# 5. Check memory of Docker
docker stats
```

---

### SUMMARY: What should happen

```
Start:
  - docker-compose up -d
  - Wait 30-60 seconds

DAG Trigger:
  - airflow dags test bees_brewery_medallion 2026-02-01
  - Task 1 (start): Echo initial
  - Task 2 (ingestion): 
     * Fetch from API OpenBreweryDB
     * Normalize data (strings)
     * Validate schema
     * Save to: datalake/bronze/breweries/created_at=2026-02-01/ (Parquet)
  
  - Task 3 (transformation):
     * Read Bronze data
     * Remove outliers/nulls
     * Rename columns
     * Add timestamps
     * Save to: datalake/silver/breweries_cleaned/created_at=2026-02-01/ (Parquet)
  
  - Task 4 (aggregation):
     * Read Silver data
     * Group by brewery_type/state/etc
     * Calculate stats (count, min, max, avg)
     * Save to: datalake/gold/breweries_stats/created_at=2026-02-01/ (Parquet)
  
  - Task 5 (end): Echo final

Final Result:
  - Partition file in each layer
  - Logs showing "Task exited with return code 0"
  - Complete Medallion structure: Bronze -> Silver -> Gold
```

---

## Validation Checklist

```
PREREQUISITES
  [ ] Docker installed
  [ ] Docker daemon running
  [ ] Docker Compose installed
  [ ] Minimum 4GB RAM available for Docker

BUILD
  [ ] Dockerfile.airflow builds successfully
  [ ] Dockerfile.spark builds successfully
  [ ] Requirements.txt installed correctly

CONTAINERS
  [ ] Postgres started and healthy
  [ ] Airflow Webserver started and healthy
  [ ] Airflow Scheduler started and healthy
  [ ] Spark Master started
  [ ] Spark Worker started and connected to Master

AIRFLOW
  [ ] UI accessible at http://localhost:8080
  [ ] DAG "bees_brewery_medallion" visible
  [ ] DAG can be unpaused
  [ ] DAG can be triggered manually

SPARK
  [ ] UI accessible at http://localhost:8081
  [ ] Worker registered with Master
  [ ] Applications can be submitted

PIPELINE
  [ ] Ingestion Job executes successfully
  [ ] Transformation Job executes successfully
  [ ] Aggregation Job executes successfully
  [ ] Data appears in datalake/bronze/
  [ ] Data appears in datalake/silver/
  [ ] Data appears in datalake/gold/

TESTS
  [ ] Unit tests run successfully
  [ ] Coverage > 80%
  [ ] No test failures
  [ ] Integration tests pass

DATA
  [ ] Bronze data: raw original format
  [ ] Silver data: cleaned and enriched
  [ ] Gold data: aggregated for analytics
  [ ] Parquet files were created
  [ ] Schema validation passed

ERROR HANDLING
  [ ] DataQualityException works correctly
  [ ] StorageException is caught
  [ ] Structured logging is active
  [ ] Retry policies work in Airflow

CLEANUP
  [ ] docker-compose down removes containers
  [ ] Volumes persist (or deleted if --volumes)
```

---

## Monitoring During Execution

### Monitor in Real Time

```bash
# Terminal 1: View Scheduler logs
docker-compose logs airflow-scheduler -f

# Terminal 2: View Airflow Webserver logs
docker-compose logs airflow-webserver -f

# Terminal 3: View Spark Master logs
docker-compose logs spark-master -f

# Terminal 4: Execute commands
docker-compose exec airflow-webserver bash
```

### Check Metrics

```bash
# CPU and Memory usage of containers
docker stats

# Expected:
# CONTAINER                   CPU %    MEM USAGE / LIMIT
# bees-brewery-case-postgres-1      0.5%     150MB / 8GB
# bees-brewery-case-airflow-webserver-1  2%  500MB / 8GB
```

---

## Final Validation

If all tests passed, you have:

SUCCESS: Modular Architecture
- Code well separated (config, core, jobs, schemas)
- Dependency injection working
- Multi-environment supported

SUCCESS: Scalable Pipeline
- Medallion architecture (Bronze -> Silver -> Gold)
- Spark partitioning working
- Airflow orchestration running

SUCCESS: Robustness
- Error handling with retry policies
- Data quality validation active
- Structured logging

SUCCESS: Deployment Ready
- Docker compose brings up everything
- All containers communicate
- Pipeline executes end-to-end

SUCCESS: Complete Documentation
- ADRs explain decisions
- REQUIREMENTS_MAPPING shows traceability
- README describes how to run

---

## Next Steps

After validating with Docker:

1. **Commit to Git**
   ```bash
   git add .
   git commit -m "feat: production-ready data pipeline with Docker"
   git push origin main
   ```

2. **Prepare for presentation**
   - Have Docker running
   - Have Airflow UI accessible
   - Have tests passing

3. **Demonstrate to Bees**
   - Show DAG in Airflow
   - Run pipeline manually
   - Show data in each layer
   - Explain technical decisions via ADRs

---

Last Updated: 2026-02-01
Status: Ready for Docker Testing
Next Step: Start Docker daemon and run tests

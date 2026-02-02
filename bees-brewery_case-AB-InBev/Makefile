.PHONY: help setup install test test-cov lint format clean docker-build docker-up docker-down logs

help:
	@echo "=================================="
	@echo "BEES Brewery Case - Makefile"
	@echo "=================================="
	@echo ""
	@echo "Comandos disponíveis:"
	@echo ""
	@echo "  make setup          - Setup inicial do projeto"
	@echo "  make install        - Instala dependências Python"
	@echo "  make test           - Executa testes unitários"
	@echo "  make test-cov       - Executa testes com cobertura"
	@echo "  make lint           - Verifica código com pylint/flake8"
	@echo "  make format         - Formata código com black"
	@echo "  make clean          - Limpa arquivos temporários"
	@echo ""
	@echo "Docker:"
	@echo ""
	@echo "  make docker-build   - Build imagens Docker"
	@echo "  make docker-up      - Inicia containers"
	@echo "  make docker-down    - Para containers"
	@echo "  make logs           - Mostra logs dos containers"
	@echo ""

setup:
	@echo "Executando setup inicial..."
	@bash setup.sh

install:
	@echo "Instalando dependências..."
	pip install --upgrade pip
	pip install -r requirements.txt

test:
	@echo "Executando testes..."
	pytest tests/ -v

test-cov:
	@echo "Executando testes com cobertura..."
	pytest tests/ -v --cov=spark_jobs --cov-report=html --cov-report=term-missing
	@echo "Relatório gerado em: htmlcov/index.html"

lint:
	@echo "Verificando código..."
	pylint spark_jobs/ tests/ dags/ || true
	flake8 spark_jobs/ tests/ dags/ || true

format:
	@echo "Formatando código..."
	black spark_jobs/ tests/ dags/

clean:
	@echo "Limpando arquivos temporários..."
	find . -type d -name __pycache__ -exec rm -rf {} + || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + || true
	find . -type d -name ".coverage" -exec rm -rf {} + || true
	find . -type d -name "htmlcov" -exec rm -rf {} + || true
	@echo "✓ Limpeza concluída"

docker-build:
	@echo "Building imagens Docker..."
	docker-compose build

docker-up:
	@echo "Iniciando containers..."
	docker-compose up -d
	@echo "✓ Containers iniciados"
	@echo "  Airflow: http://localhost:8080"
	@echo "  Spark Master: http://localhost:8081"

docker-down:
	@echo "Parando containers..."
	docker-compose down
	@echo "✓ Containers parados"

docker-clean:
	@echo "Removendo volumes..."
	docker-compose down -v
	@echo "✓ Volumes removidos"

logs:
	@echo "Mostrando logs (Ctrl+C para sair)..."
	docker-compose logs -f

logs-airflow:
	docker-compose logs -f airflow-webserver

logs-spark:
	docker-compose logs -f spark-master

status:
	@echo "Status dos containers:"
	docker-compose ps

airflow-init:
	@echo "Inicializando Airflow..."
	docker-compose exec -it airflow-webserver airflow db init
	docker-compose exec -it airflow-webserver airflow users create \
		--username airflow \
		--firstname Airflow \
		--lastname Admin \
		--role Admin \
		--email admin@example.com \
		--password airflow

spark-shell:
	@echo "Conectando ao Spark Shell..."
	docker-compose exec spark-master spark-shell

bash-spark:
	docker-compose exec spark-master bash

bash-airflow:
	docker-compose exec airflow-webserver bash

.DEFAULT_GOAL := help

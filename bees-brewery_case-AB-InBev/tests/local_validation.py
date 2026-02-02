#!/usr/bin/env python3
"""
LOCAL_VALIDATION_TESTS.py - Testes locais sem Docker Daemon

Valida toda a arquitetura e código sem precisar de Docker rodando.
Pode ser executado com: python tests/local_validation.py
"""

import sys
import os
from pathlib import Path
from typing import List, Tuple
import importlib.util

# Cores para output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


class LocalValidator:
    """Valida arquitetura sem Docker daemon"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.passed = 0
        self.failed = 0
        self.tests_run = []
    
    def log_test(self, name: str, passed: bool, message: str = ""):
        """Log resultado de teste"""
        status = f"{GREEN}✅ PASS{RESET}" if passed else f"{RED}❌ FAIL{RESET}"
        print(f"{status} | {name}")
        if message:
            print(f"        {message}")
        
        self.tests_run.append((name, passed, message))
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    # ============================================================================
    # TESTE 1: Validar Estrutura de Diretórios
    # ============================================================================
    
    def test_directory_structure(self):
        """Valida que todos diretórios essenciais existem"""
        print(f"\n{BOLD}{BLUE}[TESTE 1] Validar Estrutura de Diretórios{RESET}")
        
        required_dirs = [
            "config",
            "config/environments",
            "core",
            "spark_jobs",
            "schemas",
            "dags",
            "tests",
            "docs",
            "docs/adr",
            "docker",
            "datalake",
        ]
        
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            exists = dir_path.exists() and dir_path.is_dir()
            self.log_test(
                f"Diretório: {dir_name}",
                exists,
                f"Path: {dir_path}"
            )
    
    # ============================================================================
    # TESTE 2: Validar Arquivos de Configuração
    # ============================================================================
    
    def test_configuration_files(self):
        """Valida arquivos de configuração YAML"""
        print(f"\n{BOLD}{BLUE}[TESTE 2] Validar Arquivos de Configuração{RESET}")
        
        required_files = [
            "config/config.py",
            "config/environments/dev.yaml",
            "config/environments/prod.yaml",
            "core/storage.py",
            "core/spark_session.py",
            "core/logger.py",
            "schemas/bronze.py",
            "dags/bees_brewery_dag.py",
            "requirements.txt",
            "docker-compose.yaml",
        ]
        
        for file_name in required_files:
            file_path = self.project_root / file_name
            exists = file_path.exists() and file_path.is_file()
            self.log_test(
                f"Arquivo: {file_name}",
                exists,
                f"Path: {file_path}"
            )
    
    # ============================================================================
    # TESTE 3: Validar Imports Python
    # ============================================================================
    
    def test_python_imports(self):
        """Valida que imports principais funcionam"""
        print(f"\n{BOLD}{BLUE}[TESTE 3] Validar Imports Python{RESET}")
        
        # Adicionar projeto ao path
        sys.path.insert(0, str(self.project_root))
        
        imports_to_test = [
            ("config.config", "AppConfig"),
            ("core.storage", "StorageBackend"),
            ("core.logger", "StructuredLogger"),
            ("core.spark_session", "SparkSessionFactory"),
            ("spark_jobs.base_job", "BaseJob"),
            ("spark_jobs.ingestion", "IngestionJob"),
            ("spark_jobs.transformation_silver", "TransformationJob"),
            ("spark_jobs.aggregation_gold", "AggregationJob"),
            ("schemas.bronze", "BRONZE_SCHEMA"),
        ]
        
        for module_name, class_name in imports_to_test:
            try:
                module = importlib.import_module(module_name)
                has_class = hasattr(module, class_name)
                self.log_test(
                    f"Import: {module_name}.{class_name}",
                    has_class,
                    f"Classe encontrada: {class_name}"
                )
            except ImportError as e:
                self.log_test(
                    f"Import: {module_name}.{class_name}",
                    False,
                    f"Erro: {str(e)}"
                )
    
    # ============================================================================
    # TESTE 4: Validar Configuração YAML
    # ============================================================================
    
    def test_yaml_configuration(self):
        """Valida que YAML config carrega corretamente"""
        print(f"\n{BOLD}{BLUE}[TESTE 4] Validar Configuração YAML{RESET}")
        
        sys.path.insert(0, str(self.project_root))
        
        try:
            from config.config import AppConfig
            
            # Testar dev config
            try:
                dev_config = AppConfig.from_yaml("dev")
                self.log_test(
                    "Config: dev.yaml carrega",
                    dev_config.environment == "dev",
                    f"Environment: {dev_config.environment}"
                )
            except Exception as e:
                self.log_test("Config: dev.yaml carrega", False, str(e))
            
            # Testar prod config
            try:
                prod_config = AppConfig.from_yaml("prod")
                self.log_test(
                    "Config: prod.yaml carrega",
                    prod_config.environment == "prod",
                    f"Environment: {prod_config.environment}"
                )
            except Exception as e:
                self.log_test("Config: prod.yaml carrega", False, str(e))
        
        except ImportError as e:
            self.log_test("Import AppConfig", False, str(e))
    
    # ============================================================================
    # TESTE 5: Validar Storage Abstraction
    # ============================================================================
    
    def test_storage_abstraction(self):
        """Valida que Storage abstraction está bem implementada"""
        print(f"\n{BOLD}{BLUE}[TESTE 5] Validar Storage Abstraction{RESET}")
        
        sys.path.insert(0, str(self.project_root))
        
        try:
            from core.storage import StorageBackend, LocalStorage
            from abc import ABC
            
            # Testar que StorageBackend é abstrato
            is_abstract = issubclass(StorageBackend, ABC)
            self.log_test(
                "StorageBackend é abstrato",
                is_abstract,
                "Corretamente usa ABC (Abstract Base Class)"
            )
            
            # Testar que LocalStorage implementa StorageBackend
            is_subclass = issubclass(LocalStorage, StorageBackend)
            self.log_test(
                "LocalStorage herda de StorageBackend",
                is_subclass,
                "Corretamente implementa interface"
            )
            
            # Testar métodos obrigatórios
            required_methods = ['read', 'write', 'exists', 'delete']
            for method in required_methods:
                has_method = hasattr(LocalStorage, method)
                self.log_test(
                    f"LocalStorage.{method} existe",
                    has_method,
                    f"Método: {method}"
                )
        
        except Exception as e:
            self.log_test("Storage abstraction", False, str(e))
    
    # ============================================================================
    # TESTE 6: Validar Job Abstraction
    # ============================================================================
    
    def test_job_abstraction(self):
        """Valida que Job abstraction está bem implementada"""
        print(f"\n{BOLD}{BLUE}[TESTE 6] Validar Job Abstraction{RESET}")
        
        sys.path.insert(0, str(self.project_root))
        
        try:
            from spark_jobs.base_job import BaseJob
            from spark_jobs.ingestion import IngestionJob
            from abc import ABC
            
            # Testar que BaseJob é abstrato
            is_abstract = issubclass(BaseJob, ABC)
            self.log_test(
                "BaseJob é abstrato",
                is_abstract,
                "Corretamente usa ABC"
            )
            
            # Testar que IngestionJob herda de BaseJob
            is_subclass = issubclass(IngestionJob, BaseJob)
            self.log_test(
                "IngestionJob herda de BaseJob",
                is_subclass,
                "Corretamente implementa padrão"
            )
            
            # Testar métodos obrigatórios (execute é o método abstrato em BaseJob)
            required_methods = ['execute', '__init__', '_validate_schema']
            for method in required_methods:
                has_method = hasattr(BaseJob, method)
                self.log_test(
                    f"BaseJob.{method} existe",
                    has_method,
                    f"Método: {method}"
                )
        
        except Exception as e:
            self.log_test("Job abstraction", False, str(e))
    
    # ============================================================================
    # TESTE 7: Validar Exception Hierarchy
    # ============================================================================
    
    def test_exception_hierarchy(self):
        """Valida que exception hierarchy está bem implementada"""
        print(f"\n{BOLD}{BLUE}[TESTE 7] Validar Exception Hierarchy{RESET}")
        
        sys.path.insert(0, str(self.project_root))
        
        try:
            from core.exceptions import (
                BeesBreweryException,
                DataQualityException,
                StorageException,
                SparkJobException
            )
            
            # Testar hierarquia
            exceptions_to_test = [
                (DataQualityException, BeesBreweryException),
                (StorageException, BeesBreweryException),
                (SparkJobException, BeesBreweryException),
            ]
            
            for exc_class, parent_class in exceptions_to_test:
                is_subclass = issubclass(exc_class, parent_class)
                self.log_test(
                    f"{exc_class.__name__} herda de {parent_class.__name__}",
                    is_subclass,
                    "Hierarquia correta"
                )
        
        except Exception as e:
            self.log_test("Exception hierarchy", False, str(e))
    
    # ============================================================================
    # TESTE 8: Validar Schemas
    # ============================================================================
    
    def test_schemas(self):
        """Valida que schemas estão bem definidos"""
        print(f"\n{BOLD}{BLUE}[TESTE 8] Validar Schemas{RESET}")
        
        sys.path.insert(0, str(self.project_root))
        
        try:
            from schemas.bronze import BRONZE_SCHEMA
            
            # Testar que schema existe
            has_schema = BRONZE_SCHEMA is not None
            self.log_test(
                "BRONZE_SCHEMA definido",
                has_schema,
                "Schema para bronze layer"
            )
            
            # Testar que schema tem campos
            has_fields = hasattr(BRONZE_SCHEMA, 'fields') and len(BRONZE_SCHEMA.fields) > 0
            self.log_test(
                "BRONZE_SCHEMA tem campos",
                has_fields,
                f"Campos: {len(BRONZE_SCHEMA.fields)}"
            )
        
        except Exception as e:
            self.log_test("Schemas", False, str(e))
    
    # ============================================================================
    # TESTE 9: Validar Documentação
    # ============================================================================
    
    def test_documentation(self):
        """Valida que documentação essencial existe"""
        print(f"\n{BOLD}{BLUE}[TESTE 9] Validar Documentação{RESET}")
        
        docs_to_check = [
            "docs/adr/README.md",
            "docs/adr/ADR-001-modular-architecture.md",
            "docs/adr/ADR-002-TECH-STACK.md",
            "docs/ARCHITECTURE_IMPLEMENTATION.md",
            "docs/REQUIREMENTS_MAPPING.md",
            "docs/DOCKER_DAEMON_EXPLAINED.md",
            "README.md",
        ]
        
        for doc in docs_to_check:
            doc_path = self.project_root / doc
            exists = doc_path.exists() and doc_path.is_file()
            self.log_test(
                f"Doc: {doc}",
                exists,
                f"Path: {doc_path}"
            )
    
    # ============================================================================
    # TESTE 10: Validar Type Hints
    # ============================================================================
    
    def test_type_hints(self):
        """Valida que código tem type hints"""
        print(f"\n{BOLD}{BLUE}[TESTE 10] Validar Type Hints{RESET}")
        
        sys.path.insert(0, str(self.project_root))
        
        try:
            from spark_jobs.base_job import BaseJob
            import inspect
            
            # Verificar que métodos têm type hints
            methods_to_check = ['execute', '__init__', '_validate_schema']
            
            for method_name in methods_to_check:
                if hasattr(BaseJob, method_name):
                    method = getattr(BaseJob, method_name)
                    sig = inspect.signature(method)
                    
                    # Contar annotations
                    annotations_count = sum(
                        1 for param in sig.parameters.values()
                        if param.annotation != inspect.Parameter.empty
                    )
                    
                    has_hints = annotations_count > 0 or sig.return_annotation != inspect.Signature.empty
                    self.log_test(
                        f"BaseJob.{method_name} tem type hints",
                        has_hints,
                        f"Annotations: {annotations_count}"
                    )
                else:
                    self.log_test(
                        f"BaseJob.{method_name} existe",
                        False,
                        f"Método não encontrado"
                    )
        
        except Exception as e:
            self.log_test("Type hints", False, str(e))
    
    # ============================================================================
    # TESTE 11: Validar Requirements
    # ============================================================================
    
    def test_requirements(self):
        """Valida que requirements.txt tem dependências essenciais"""
        print(f"\n{BOLD}{BLUE}[TESTE 11] Validar Requirements{RESET}")
        
        req_file = self.project_root / "requirements.txt"
        
        if not req_file.exists():
            self.log_test("requirements.txt existe", False, "Arquivo não encontrado")
            return
        
        with open(req_file) as f:
            requirements = f.read().lower()
        
        essential_packages = [
            ("pyspark", "Apache Spark"),
            ("apache-airflow", "Apache Airflow"),
            ("pyyaml", "YAML support"),
            ("pytest", "Testing framework"),
            ("pandas", "Data manipulation"),
        ]
        
        for package, description in essential_packages:
            has_package = package in requirements
            self.log_test(
                f"Dependency: {package}",
                has_package,
                description
            )
    
    # ============================================================================
    # TESTE 12: Validar Docker Files
    # ============================================================================
    
    def test_docker_files(self):
        """Valida que Docker files estão bem definidos"""
        print(f"\n{BOLD}{BLUE}[TESTE 12] Validar Docker Files{RESET}")
        
        docker_files = [
            "docker/Dockerfile.airflow",
            "docker/Dockerfile.spark",
            "docker-compose.yaml",
        ]
        
        for docker_file in docker_files:
            file_path = self.project_root / docker_file
            exists = file_path.exists() and file_path.is_file()
            self.log_test(
                f"Docker: {docker_file}",
                exists,
                f"Path: {file_path}"
            )
            
            # Para Dockerfiles, validar que tem FROM
            if exists and "Dockerfile" in docker_file:
                with open(file_path) as f:
                    content = f.read()
                    has_from = "FROM" in content
                    self.log_test(
                        f"  └─ {docker_file} tem FROM",
                        has_from,
                        "Base image definido"
                    )
    
    # ============================================================================
    # EXECUTAR TODOS OS TESTES
    # ============================================================================
    
    def run_all_tests(self):
        """Executa todos os testes"""
        print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
        print(f"{BOLD}{BLUE}LOCAL VALIDATION TESTS - Sem Docker Daemon{RESET}")
        print(f"{BOLD}{BLUE}{'='*70}{RESET}")
        
        # Executar testes
        self.test_directory_structure()
        self.test_configuration_files()
        self.test_python_imports()
        self.test_yaml_configuration()
        self.test_storage_abstraction()
        self.test_job_abstraction()
        self.test_exception_hierarchy()
        self.test_schemas()
        self.test_documentation()
        self.test_type_hints()
        self.test_requirements()
        self.test_docker_files()
        
        # Resumo final
        self.print_summary()
    
    def print_summary(self):
        """Imprime resumo dos testes"""
        total = self.passed + self.failed
        percentage = (self.passed / total * 100) if total > 0 else 0
        
        print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
        print(f"{BOLD}{BLUE}RESUMO DOS TESTES{RESET}")
        print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")
        
        print(f"Total: {total}")
        print(f"{GREEN}✅ Passou: {self.passed}{RESET}")
        print(f"{RED}❌ Falhou: {self.failed}{RESET}")
        print(f"Sucesso: {percentage:.1f}%\n")
        
        if self.failed == 0:
            print(f"{GREEN}{BOLD}🎉 TODOS OS TESTES PASSARAM!{RESET}")
            print(f"{GREEN}Sua arquitetura está pronta para Docker.{RESET}\n")
            print("Próximos passos:")
            print("1. Abrir Docker Desktop: open /Applications/Docker.app")
            print("2. Aguardar 30 segundos para o daemon iniciar")
            print("3. Executar: docker-compose up -d")
            print("4. Acessar Airflow em http://localhost:8080")
        else:
            print(f"{RED}{BOLD}⚠️ {self.failed} testes falharam!{RESET}")
            print(f"{RED}Verifique os erros acima.{RESET}\n")
        
        print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")


if __name__ == "__main__":
    validator = LocalValidator()
    validator.run_all_tests()
    
    # Exit com código apropriado
    sys.exit(0 if validator.failed == 0 else 1)

"""
Testes unitários para o módulo de Ingestion
"""

import pytest
import json
import os
from unittest.mock import Mock, patch
from spark_jobs.ingestion import fetch_and_save_bronze


@patch('spark_jobs.ingestion.requests.Session.get')
def test_fetch_and_save_bronze_success(mock_get, tmp_path):
    """Testa ingestão bem-sucedida de dados da API"""
    # Mock de resposta da API - PRIMEIRO retorna dados, DEPOIS retorna vazio para parar
    mock_response_with_data = Mock()
    mock_response_with_data.json.return_value = [
        {"id": 1, "name": "Brewery 1", "state": "CA"},
        {"id": 2, "name": "Brewery 2", "state": "NY"}
    ]
    
    mock_response_empty = Mock()
    mock_response_empty.json.return_value = []
    
    # Configurar side_effect para retornar dados na primeira chamada, vazio na segunda
    mock_get.side_effect = [mock_response_with_data, mock_response_empty]
    
    # Executa função
    fetch_and_save_bronze("https://api.example.com/breweries", str(tmp_path))
    
    # Verifica se arquivo foi criado
    bronze_dir = tmp_path / "bronze" / "breweries"
    assert bronze_dir.exists()
    
    # Verifica conteúdo do arquivo
    json_files = list(bronze_dir.glob("*/data.json"))
    assert len(json_files) > 0
    
    with open(json_files[0], "r") as f:
        data = json.load(f)
    assert len(data) == 2
    assert data[0]["id"] == 1


@patch('spark_jobs.ingestion.requests.Session.get')
def test_fetch_and_save_bronze_pagination(mock_get, tmp_path):
    """Testa paginação na ingestão"""
    # Mock de duas páginas com dados + uma página vazia para parar
    mock_response_page1 = Mock()
    mock_response_page1.json.return_value = [
        {"id": 1, "name": "Brewery 1"},
        {"id": 2, "name": "Brewery 2"}
    ]
    
    mock_response_page2 = Mock()
    mock_response_page2.json.return_value = [
        {"id": 3, "name": "Brewery 3"}
    ]
    
    mock_response_empty = Mock()
    mock_response_empty.json.return_value = []
    
    # IMPORTANTE: Configurar para 3 chamadas (2 com dados + 1 vazia para parar)
    mock_get.side_effect = [mock_response_page1, mock_response_page2, mock_response_empty]
    
    # Executa função
    fetch_and_save_bronze("https://api.example.com/breweries", str(tmp_path))
    
    # Verifica se todos os dados foram salvos
    # Buscar em todo o diretório recursivamente
    import glob
    json_files = glob.glob(str(tmp_path / "**" / "data.json"), recursive=True)
    assert len(json_files) > 0, f"Nenhum arquivo encontrado em {tmp_path}"
    
    with open(json_files[0], "r") as f:
        data = json.load(f)
    assert len(data) == 3  # 2 + 1


@patch('spark_jobs.ingestion.requests.Session.get')
def test_fetch_and_save_bronze_api_error(mock_get, tmp_path):
    """Testa erro na chamada da API"""
    import requests
    mock_get.side_effect = requests.exceptions.RequestException("API Error")
    
    with pytest.raises(requests.exceptions.RequestException):
        fetch_and_save_bronze("https://api.example.com/breweries", str(tmp_path))


@patch('spark_jobs.ingestion.requests.Session.get')
def test_fetch_and_save_bronze_creates_partitioned_path(mock_get, tmp_path):
    """Testa se o caminho é particionado por data"""
    mock_response_with_data = Mock()
    mock_response_with_data.json.return_value = [{"id": 1, "name": "Test Brewery"}]
    
    mock_response_empty = Mock()
    mock_response_empty.json.return_value = []
    
    mock_get.side_effect = [mock_response_with_data, mock_response_empty]
    
    fetch_and_save_bronze("https://api.example.com/breweries", str(tmp_path))
    
    # Verifica se o caminho contém created_at partition
    bronze_dir = tmp_path / "bronze" / "breweries"
    subdirs = list(bronze_dir.iterdir())
    
    assert len(subdirs) > 0
    assert any("created_at=" in str(d) for d in subdirs)

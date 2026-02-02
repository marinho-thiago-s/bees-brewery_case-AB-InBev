#!/bin/bash

# Script de inicialização do projeto BEES Brewery Case
# Este script configura o ambiente e inicia os containers

set -e

echo "=========================================="
echo "BEES Brewery Case - Setup Inicial"
echo "=========================================="

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Verificar se Docker está instalado
echo -e "\n${YELLOW}Verificando Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo "Docker não está instalado. Por favor, instale Docker e tente novamente."
    exit 1
fi
echo -e "${GREEN}✓ Docker encontrado${NC}"

# 2. Verificar se Docker Compose está instalado
echo -e "\n${YELLOW}Verificando Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose não está instalado. Por favor, instale Docker Compose e tente novamente."
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose encontrado${NC}"

# 3. Criar arquivo .env se não existir
echo -e "\n${YELLOW}Configurando variáveis de ambiente...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Arquivo .env criado (baseado em .env.example)${NC}"
else
    echo -e "${GREEN}✓ Arquivo .env já existe${NC}"
fi

# 4. Criar diretórios necessários
echo -e "\n${YELLOW}Criando diretórios...${NC}"
mkdir -p data/bronze data/silver data/gold logs
echo -e "${GREEN}✓ Diretórios criados${NC}"

# 5. Instalar dependências Python
echo -e "\n${YELLOW}Instalando dependências Python...${NC}"
if command -v python3 &> /dev/null; then
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Dependências instaladas${NC}"
fi

# 6. Build das imagens Docker
echo -e "\n${YELLOW}Building imagens Docker...${NC}"
docker-compose build
echo -e "${GREEN}✓ Imagens Docker buildadas${NC}"

# 7. Iniciar containers
echo -e "\n${YELLOW}Iniciando containers...${NC}"
docker-compose up -d
echo -e "${GREEN}✓ Containers iniciados${NC}"

# 8. Aguardar inicialização
echo -e "\n${YELLOW}Aguardando inicialização dos serviços...${NC}"
sleep 10

# 9. Exibir status
echo -e "\n${GREEN}=========================================="
echo "Setup concluído com sucesso!"
echo "==========================================${NC}"

echo -e "\n${YELLOW}Serviços disponíveis:${NC}"
echo "  • Airflow UI: http://localhost:8080"
echo "  • Spark Master: http://localhost:8081"
echo "  • PostgreSQL: localhost:5432"
echo "  • Redis: localhost:6379"

echo -e "\n${YELLOW}Próximos passos:${NC}"
echo "  1. Acessar Airflow: http://localhost:8080"
echo "  2. Usuário padrão: airflow"
echo "  3. Senha padrão: airflow"
echo "  4. Ativar DAG: bees_brewery_etl_pipeline"

echo -e "\n${YELLOW}Comandos úteis:${NC}"
echo "  • Ver logs: docker-compose logs -f"
echo "  • Parar containers: docker-compose down"
echo "  • Remover volumes: docker-compose down -v"
echo "  • Executar testes: pytest tests/ -v"

echo ""

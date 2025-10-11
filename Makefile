# Makefile para AI Influencer Backend

.PHONY: help install dev build up down logs restart clean test

help:
	@echo "AI Influencer Backend - Comandos disponibles:"
	@echo ""
	@echo "  make install    - Instalar dependencias localmente"
	@echo "  make dev        - Ejecutar en modo desarrollo (local)"
	@echo "  make build      - Construir imagen Docker"
	@echo "  make up         - Iniciar contenedores Docker"
	@echo "  make down       - Detener contenedores Docker"
	@echo "  make logs       - Ver logs de los contenedores"
	@echo "  make restart    - Reiniciar contenedores"
	@echo "  make clean      - Limpiar archivos temporales"
	@echo "  make test       - Ejecutar tests (si existen)"
	@echo ""

install:
	pip install -r requirements.txt

dev:
	python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Aplicación iniciada en http://localhost:8000"
	@echo "Documentación en http://localhost:8000/docs"

down:
	docker-compose down

logs:
	docker-compose logs -f

restart:
	docker-compose restart

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

test:
	pytest -v


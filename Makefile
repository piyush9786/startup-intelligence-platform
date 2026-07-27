SHELL := /bin/bash

.PHONY: help build up down logs ps migrate migrations superuser seed test lint shell reset

help:
	@echo "make build       Build containers"
	@echo "make up          Start the full development stack"
	@echo "make down        Stop the stack"
	@echo "make logs        Follow application logs"
	@echo "make migrations  Create Django migrations"
	@echo "make migrate     Apply Django migrations"
	@echo "make superuser   Create an admin user"
	@echo "make seed        Add starter authoritative sources"
	@echo "make test        Run backend and frontend tests"
	@echo "make lint        Run Python lint checks"
	@echo "make shell       Open a Django shell"
	@echo "make reset       Delete containers and local data volumes"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f backend worker frontend

ps:
	docker compose ps

migrations:
	docker compose run --rm backend python manage.py makemigrations

migrate:
	docker compose run --rm backend python manage.py migrate

superuser:
	docker compose exec backend python manage.py createsuperuser

seed:
	docker compose exec backend python manage.py seed_sources

test:
	docker compose run --rm backend pytest
	docker compose run --rm frontend npm test
	docker compose run --rm frontend npm run build

lint:
	docker compose run --rm backend ruff check .

shell:
	docker compose exec backend python manage.py shell

reset:
	docker compose down -v --remove-orphans

GPU_COMPOSE := docker compose -f docker-compose.yml -f docker-compose.gpu.yml

.PHONY: up-gpu down-gpu gpu-check ollama-test llm-logs

up-gpu:
	$(GPU_COMPOSE) up -d --build

down-gpu:
	$(GPU_COMPOSE) down

gpu-check:
	nvidia-smi
	$(GPU_COMPOSE) exec ollama ollama ps

ollama-test:
	$(GPU_COMPOSE) exec ollama \
		ollama run qwen3:4b "Reply with exactly: MODEL_OK"

llm-logs:
	$(GPU_COMPOSE) logs -f ollama backend worker

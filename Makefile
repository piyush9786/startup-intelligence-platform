SHELL := /bin/bash

GPU_COMPOSE := docker compose -f docker-compose.yml -f docker-compose.gpu.yml

.PHONY: help build up up-gpu down down-gpu logs ps migrate migrations \
	superuser seed catalogs doctor create-admin test lint shell reset \
	laptop-setup laptop-setup-gpu laptop-doctor laptop-doctor-gpu

help:
	@echo "make laptop-setup      One-command CPU laptop setup"
	@echo "make laptop-setup-gpu  One-command NVIDIA GPU laptop setup"
	@echo "make up                Start the existing CPU stack"
	@echo "make up-gpu            Start with NVIDIA GPU for Ollama"
	@echo "make down              Stop the CPU stack"
	@echo "make down-gpu          Stop the GPU stack"
	@echo "make doctor            Check services and required catalogs"
	@echo "make create-admin      Create/update a local admin account"
	@echo "make catalogs          Re-import all bundled catalogs"
	@echo "make test              Run backend and frontend checks"
	@echo "make reset             Delete containers and local volumes"

laptop-setup:
	./scripts/laptop_setup.sh

laptop-setup-gpu:
	./scripts/laptop_setup.sh --gpu

laptop-doctor:
	./scripts/laptop_doctor.sh

laptop-doctor-gpu:
	./scripts/laptop_doctor.sh --gpu

build:
	docker compose build

up:
	docker compose up -d

up-gpu:
	$(GPU_COMPOSE) up -d --build

down:
	docker compose down --remove-orphans

down-gpu:
	$(GPU_COMPOSE) down --remove-orphans

logs:
	./scripts/laptop_logs.sh

ps:
	docker compose ps

migrations:
	docker compose run --rm backend python manage.py makemigrations

migrate:
	docker compose run --rm backend python manage.py migrate

superuser:
	docker compose exec backend python manage.py createsuperuser

create-admin:
	./scripts/create_local_admin.sh

seed: catalogs

catalogs:
	docker compose exec backend python manage.py bootstrap_catalogs
	docker compose exec backend python manage.py platform_doctor --strict

doctor:
	./scripts/laptop_doctor.sh

test:
	docker compose run --rm backend pytest
	docker compose run --rm backend ruff check .
	docker compose run --rm frontend npm test
	docker compose run --rm frontend npm run lint
	docker compose run --rm frontend npm run build

lint:
	docker compose run --rm backend ruff check .
	docker compose run --rm frontend npm run lint

shell:
	docker compose exec backend python manage.py shell

reset:
	./scripts/laptop_reset.sh --yes

ollama-test:
	$(GPU_COMPOSE) exec ollama \
		ollama run qwen3:4b "Reply with exactly: MODEL_OK"

llm-logs:
	$(GPU_COMPOSE) logs -f ollama backend worker

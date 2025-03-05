.PHONY: help setup dev test lint format migrate build-image push-image deploy clean install-deps

# Variables
PROJECT_NAME = voice_agent
DOCKER_IMAGE_NAME = voice-agent
DOCKER_REGISTRY ?= your-registry
VERSION ?= latest

# Colors
COLOR_RESET = \033[0m
COLOR_INFO = \033[32m
COLOR_WARN = \033[33m

help: ## Show this help
	@echo "$(COLOR_INFO)Voice Agent Makefile$(COLOR_RESET)"
	@echo "$(COLOR_INFO)------------------$(COLOR_RESET)"
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(COLOR_INFO)%-20s$(COLOR_RESET) %s\n", $$1, $$2}'

setup: ## Setup development environment
	@echo "$(COLOR_INFO)Setting up development environment...$(COLOR_RESET)"
	cp .env.example .env
	mkdir -p prompts
	@echo "$(COLOR_INFO)Creating prompt templates...$(COLOR_RESET)"
	cp -r ./app/templates/* ./prompts/ || true
	@echo "$(COLOR_INFO)Setup complete. Please update .env with your API keys.$(COLOR_RESET)"

install-deps: ## Install Python dependencies
	@echo "$(COLOR_INFO)Installing Python dependencies...$(COLOR_RESET)"
	pip install -r requirements.txt
	@echo "$(COLOR_INFO)Dependencies installed.$(COLOR_RESET)"

dev: ## Run development server
	@echo "$(COLOR_INFO)Starting development server...$(COLOR_RESET)"
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-docker: ## Run development environment using Docker
	@echo "$(COLOR_INFO)Starting Docker development environment...$(COLOR_RESET)"
	docker-compose up --build

test: ## Run tests
	@echo "$(COLOR_INFO)Running tests...$(COLOR_RESET)"
	pytest -v tests/

test-cov: ## Run tests with coverage
	@echo "$(COLOR_INFO)Running tests with coverage...$(COLOR_RESET)"
	pytest --cov=app tests/ --cov-report=term --cov-report=html
	@echo "$(COLOR_INFO)Coverage report generated in htmlcov/$(COLOR_RESET)"

lint: ## Run linters
	@echo "$(COLOR_INFO)Running linters...$(COLOR_RESET)"
	flake8 app tests
	mypy app

format: ## Format code
	@echo "$(COLOR_INFO)Formatting code...$(COLOR_RESET)"
	black app tests
	isort app tests

migrate: ## Run database migrations
	@echo "$(COLOR_INFO)Running database migrations...$(COLOR_RESET)"
	alembic upgrade head

migrate-create: ## Create a new migration
	@echo "$(COLOR_INFO)Creating a new migration...$(COLOR_RESET)"
	alembic revision --autogenerate -m "$(message)"

build-image: ## Build Docker image
	@echo "$(COLOR_INFO)Building Docker image...$(COLOR_RESET)"
	docker build -t $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME):$(VERSION) .

push-image: ## Push Docker image to registry
	@echo "$(COLOR_INFO)Pushing Docker image to registry...$(COLOR_RESET)"
	docker push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME):$(VERSION)

deploy: ## Deploy the application
	@echo "$(COLOR_INFO)Deploying the application...$(COLOR_RESET)"
	bash deploy/scripts/deploy.sh

clean: ## Clean up temporary files
	@echo "$(COLOR_INFO)Cleaning up...$(COLOR_RESET)"
	rm -rf __pycache__ .pytest_cache htmlcov .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Database management
db-psql: ## Connect to PostgreSQL database
	@echo "$(COLOR_INFO)Connecting to PostgreSQL...$(COLOR_RESET)"
	docker-compose exec db psql -U postgres -d voice_agent

db-create: ## Create database
	@echo "$(COLOR_INFO)Creating database...$(COLOR_RESET)"
	docker-compose exec db psql -U postgres -c "CREATE DATABASE voice_agent;"

db-drop: ## Drop database
	@echo "$(COLOR_WARN)WARNING: This will drop the database!$(COLOR_RESET)"
	@read -p "Are you sure? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker-compose exec db psql -U postgres -c "DROP DATABASE IF EXISTS voice_agent;"; \
		echo "$(COLOR_INFO)Database dropped.$(COLOR_RESET)"; \
	else \
		echo "$(COLOR_INFO)Aborted.$(COLOR_RESET)"; \
	fi

# N8N management
n8n-import: ## Import N8N workflows
	@echo "$(COLOR_INFO)Importing N8N workflows...$(COLOR_RESET)"
	bash deploy/scripts/import_n8n_workflows.sh
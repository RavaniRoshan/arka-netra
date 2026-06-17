.PHONY: help test lint typecheck build docker-run docker-down

help:
	@echo "Available commands:"
	@echo "  make test     - Run tests"
	@echo "  make lint     - Lint Python code with ruff"
	@echo "  make typecheck - Type check with mypy"
	@echo "  make build    - Build Docker image"
	@echo "  make docker-run - Run Docker containers"
	@echo "  make docker-down - Stop Docker containers"

# Run tests
test:
	python -m pytest tests/ -q

# Lint Python code
lint:
	ruff check src/ tests/

# Type check
typecheck:
	mypy src/

# Build Docker image
build:
	docker build -t project-solaris:latest .

# Run Docker containers
docker-run:
	docker-compose up --build -d

# Stop Docker containers
docker-down:
	docker-compose down

# Quick development setup
dev-setup:
	pip install -e .[dev]
	docker-compose up --build -d
	sleep 30
	@echo "API available at http://localhost:8000"
	@echo "Dashboard available at http://localhost:8501"

# Clean up
docker-clean:
	docker system prune -f
	rm -rf data/raw/* models/* reports/*
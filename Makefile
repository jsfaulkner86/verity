.PHONY: install dev test lint format typecheck run docker-build docker-run clean

install:
	pip install -e .

dev:
	pip install -e ".[dev,langsmith]"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=verity --cov-report=html

lint:
	ruff check verity/ tests/

format:
	black verity/ tests/
	ruff check --fix verity/ tests/

typecheck:
	mypy verity/

run:
	uvicorn verity.api.main:app --host 0.0.0.0 --port 8080 --reload

docker-build:
	docker build -t verity:latest .

docker-run:
	docker compose up

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov dist build *.egg-info

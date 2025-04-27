#! /bin/bash

# check lint
echo "----------- Checking lint..."
poetry run ruff format src/ tests/

# check format
echo "----------- Checking format..."
poetry run ruff check --fix src/ tests/

# check type hints
echo "----------- Checking type hints..."
poetry run mypy src/

# run tests
echo "----------- Running tests..."
poetry run pytest

# check coverage
echo "----------- Checking coverage..."
poetry run pytest --cov=src/marketplace_aggregator --cov-report=term-missing

echo "----------- Done!"
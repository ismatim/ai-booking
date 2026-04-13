# Variables
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest

.PHONY: help install test test-v run db-setup db-seed db-reset lint clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install/Update dependencies
	$(PIP) install -r requirements.txt

test: ## Run all tests silently
	$(PYTEST)

test-v: ## Run tests with verbose output and print statements (-s)
	$(PYTEST) -v -s

test-integration: ## Run only integration tests
	$(PYTEST) tests/integrations/test_calendars/test_google_calendar.py  

run: ## Start the FastAPI server with auto-reload
	$(PYTHON) -m uvicorn main:app --reload

db-setup: ## Create database tables
	$(PYTHON) scripts/setup_db.py

db-seed: ## Seed the database with consultants and availability
	$(PYTHON) scripts/seed.py

db-reset: db-setup db-seed ## Wipe schema and re-seed (The "Fresh Start" command)

db-migrate: ## Push local migrations to Supabase
	supabase db push

db-status: ## Check the status of your migrations
	supabase migration list

lint: ## Run Ruff for linting and formatting
	$(PYTHON) -m ruff check . --fix
	$(PYTHON) -m ruff format .

clean: ## Remove python cache and test artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .ruff_cache

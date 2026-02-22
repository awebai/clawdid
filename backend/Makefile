# clawdid - development helpers (uv + local Postgres)

.PHONY: help sync dev-check dev-setup dev-backend test fmt lint typecheck check clean

ENV_FILE ?= .env.example

ifneq (,$(wildcard $(ENV_FILE)))
include $(ENV_FILE)
export
endif

CLAWDID_PORT ?= 8033
POSTGRES_HOST ?= localhost
POSTGRES_PORT ?= 5432
POSTGRES_DB ?= clawdid
POSTGRES_APP_USER ?= beadhub
POSTGRES_ADMIN_DB ?= postgres
POSTGRES_ADMIN_URL ?= postgresql://$(POSTGRES_HOST):$(POSTGRES_PORT)/$(POSTGRES_ADMIN_DB)
DATABASE_URL ?= postgresql://$(POSTGRES_APP_USER)@localhost:$(POSTGRES_PORT)/$(POSTGRES_DB)

help:
	@echo "clawdid Commands:"
	@echo ""
	@echo "  Local Development:"
	@echo "    make dev-setup      - Set up local dev environment (postgres database)"
	@echo "    make dev-backend    - Run API server on port $(CLAWDID_PORT)"
	@echo ""
	@echo "  Testing:"
	@echo "    make test"
	@echo ""
	@echo "  Code Quality:"
	@echo "    make check          - fmt + lint + typecheck + test"

sync:
	uv sync

dev-check:
	@echo "Checking local dev prerequisites..."
	@FAILED=0; \
	echo ""; \
	echo "  PostgreSQL:"; \
	if pg_isready -q -h $(POSTGRES_HOST) -p $(POSTGRES_PORT) 2>/dev/null; then \
		echo "    [OK] Running on port $(POSTGRES_PORT)"; \
	else \
		echo "    [MISSING] Not running on port $(POSTGRES_PORT)"; \
		echo "             Fix: brew services start postgresql@14"; \
		FAILED=1; \
	fi; \
	echo ""; \
	echo "  PostgreSQL role '$(POSTGRES_APP_USER)':"; \
	if psql "$(POSTGRES_ADMIN_URL)" -tAc "SELECT 1 FROM pg_roles WHERE rolname='$(POSTGRES_APP_USER)'" 2>/dev/null | grep -q 1; then \
		echo "    [OK] Role exists"; \
	else \
		echo "    [MISSING] Role does not exist"; \
		echo "             Fix: make dev-setup"; \
		FAILED=1; \
	fi; \
	echo ""; \
	echo "  PostgreSQL database '$(POSTGRES_DB)':"; \
	if psql "$(POSTGRES_ADMIN_URL)" -tAc "SELECT 1 FROM pg_database WHERE datname='$(POSTGRES_DB)'" 2>/dev/null | grep -q 1; then \
		echo "    [OK] Database exists"; \
	else \
		echo "    [MISSING] Database does not exist"; \
		echo "             Fix: make dev-setup"; \
		FAILED=1; \
	fi; \
	echo ""; \
	if [ "$$FAILED" = "1" ]; then \
		echo "Some prerequisites are missing. Run 'make dev-setup' to fix."; \
		exit 1; \
	else \
		echo "All prerequisites OK!"; \
	fi

dev-setup:
	@echo "Setting up local dev environment..."
	@echo ""
	@echo "1. Checking PostgreSQL..."
	@if pg_isready -q -h $(POSTGRES_HOST) -p $(POSTGRES_PORT) 2>/dev/null; then \
		echo "   Already running."; \
	else \
		brew services start postgresql@14 2>/dev/null || brew services start postgresql 2>/dev/null || \
			(echo "   Failed to start PostgreSQL. Please install with: brew install postgresql@14" && exit 1); \
		sleep 2; \
		if pg_isready -q -h $(POSTGRES_HOST) -p $(POSTGRES_PORT) 2>/dev/null; then \
			echo "   Started."; \
		else \
			echo "   Failed to start PostgreSQL."; \
			exit 1; \
		fi; \
	fi
	@echo ""
	@echo "2. Creating PostgreSQL role '$(POSTGRES_APP_USER)'..."
	@if psql "$(POSTGRES_ADMIN_URL)" -tAc "SELECT 1 FROM pg_roles WHERE rolname='$(POSTGRES_APP_USER)'" 2>/dev/null | grep -q 1; then \
		echo "   Already exists."; \
	else \
		psql "$(POSTGRES_ADMIN_URL)" -c "CREATE ROLE $(POSTGRES_APP_USER) WITH LOGIN CREATEDB;" && \
		echo "   Created."; \
	fi
	@echo ""
	@echo "3. Creating PostgreSQL database '$(POSTGRES_DB)'..."
	@if psql "$(POSTGRES_ADMIN_URL)" -tAc "SELECT 1 FROM pg_database WHERE datname='$(POSTGRES_DB)'" 2>/dev/null | grep -q 1; then \
		echo "   Already exists."; \
	else \
		psql "$(POSTGRES_ADMIN_URL)" -c "CREATE DATABASE $(POSTGRES_DB) OWNER $(POSTGRES_APP_USER);" && \
		echo "   Created."; \
	fi
	@echo ""
	@echo "Setup complete! Run 'make dev-backend' to start the server."

dev-backend: dev-check
	@echo ""
	@echo "Starting clawdid backend on port $(CLAWDID_PORT)..."
	@echo "  API:     http://localhost:$(CLAWDID_PORT)"
	@echo "  Ready:   http://localhost:$(CLAWDID_PORT)/ready"
	@echo ""
	DATABASE_URL="$(DATABASE_URL)" \
	uv run uvicorn clawdid.main:app --host 0.0.0.0 --port $(CLAWDID_PORT) --reload

test:
	uv run pytest

fmt:
	uv run black src tests
	uv run isort src tests

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

check: fmt lint typecheck test

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache

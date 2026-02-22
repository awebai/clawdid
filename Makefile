# ABOUTME: Development commands for clawdid
# ABOUTME: Run `make help` to see available targets

.PHONY: help dev dev-backend dev-frontend dev-site dev-stop status api-smoke quality-gates \
        test lint lint-types format check frontend-install frontend-build site-build \
        dev-db-up dev-db-down dev-db-reset \
        docker-validate local-container local-container-down

# Default env file (can be overridden)
ENV_FILE ?= .env.dev

# Load env file if it exists
ifneq (,$(wildcard $(ENV_FILE)))
include $(ENV_FILE)
export
endif

# Defaults — ports chosen to avoid conflicts with sibling projects:
#   beadhub        5173/8000
#   beadhub-cloud  5174/8001
#   aweb           8023
#   aweb-cloud     5180/8008
#   claweb         5177/8005
CLAWDID_PORT ?= 18111
VITE_PORT ?= 18113
SITE_PORT ?= 18114
DEV_POSTGRES_PORT ?= 15489
LOCAL_POSTGRES_PORT ?= 15490
LOCAL_API_PORT ?= 18112

POSTGRES_HOST ?= 127.0.0.1
POSTGRES_DB ?= clawdid_dev
POSTGRES_APP_USER ?= clawdid

DATABASE_URL ?= postgresql://$(POSTGRES_APP_USER)@$(POSTGRES_HOST):$(DEV_POSTGRES_PORT)/$(POSTGRES_DB)

DEV_DB_COMPOSE ?= docker-compose.dev-db.yml
LOCAL_ENV_FILE ?= .env.local-container
LOCAL_COMPOSE ?= docker-compose.local-container.yml
LOCAL_IMAGE ?= clawdid-local
RELEASE_PLATFORM ?= linux/amd64

help:
	@echo "clawdid Development Commands"
	@echo ""
	@echo "Development:"
	@echo "  make dev-db-up         Start local Postgres container (port $(DEV_POSTGRES_PORT))"
	@echo "  make dev              Start backend + SPA together"
	@echo "  make dev-backend       Start backend server (port $(CLAWDID_PORT))"
	@echo "  make dev-frontend      Start SPA dev server (port $(VITE_PORT))"
	@echo "  make dev-site          Start Hugo marketing site (port $(SITE_PORT))"
	@echo "  make dev-stop          Stop dev server (kill ports)"
	@echo "  make status            Show status"
	@echo "  make api-smoke         Quick reachability checks"
	@echo ""
	@echo "Code Quality:"
	@echo "  make test              Run tests"
	@echo "  make lint              Run ruff"
	@echo "  make lint-types        Run mypy"
	@echo "  make format            Format code"
	@echo "  make check             Format + lint + typecheck + test"
	@echo "  make frontend-build    Build SPA bundle"
	@echo "  make site-build        Build marketing site"
	@echo ""
	@echo "Local Container Stack (release image + local Postgres):"
	@echo "  make docker-validate   Validate docker-compose files"
	@echo "  make local-container   Build image and run stack (api $(LOCAL_API_PORT), pg $(LOCAL_POSTGRES_PORT))"
	@echo "  make local-container-down Stop stack"
	@echo ""
	@echo "Ports:"
	@echo "  clawdid dev backend:          $(CLAWDID_PORT)"
	@echo "  clawdid spa dev server:       $(VITE_PORT)"
	@echo "  clawdid site dev server:      $(SITE_PORT)"
	@echo "  clawdid dev postgres:         $(DEV_POSTGRES_PORT)"
	@echo "  clawdid local-container api:  $(LOCAL_API_PORT)"
	@echo "  clawdid local-container pg:   $(LOCAL_POSTGRES_PORT)"

dev:
	@echo "Starting backend on http://127.0.0.1:$(CLAWDID_PORT) and SPA on http://localhost:$(VITE_PORT)"
	@echo "  Press Ctrl-C to stop both."
	@trap 'kill 0' EXIT; \
		( cd backend && DATABASE_URL="$(DATABASE_URL)" uv run uvicorn clawdid.main:app --reload --port $(CLAWDID_PORT) ) & \
		( cd frontend && pnpm install && VITE_PORT=$(VITE_PORT) pnpm run dev -- --port $(VITE_PORT) ) & \
		wait

dev-db-up:
	@echo "Starting dev Postgres on localhost:$(DEV_POSTGRES_PORT) (DB=$(POSTGRES_DB), user=$(POSTGRES_APP_USER))..."
	DEV_POSTGRES_PORT="$(DEV_POSTGRES_PORT)" POSTGRES_DB="$(POSTGRES_DB)" POSTGRES_APP_USER="$(POSTGRES_APP_USER)" \
		docker compose -p clawdid-dev-db -f "$(DEV_DB_COMPOSE)" up -d postgres
	@echo "Ready when pg_isready succeeds:"
	@echo "  pg_isready -h $(POSTGRES_HOST) -p $(DEV_POSTGRES_PORT)"

dev-db-down:
	@echo "Stopping dev Postgres..."
	DEV_POSTGRES_PORT="$(DEV_POSTGRES_PORT)" POSTGRES_DB="$(POSTGRES_DB)" POSTGRES_APP_USER="$(POSTGRES_APP_USER)" \
		docker compose -p clawdid-dev-db -f "$(DEV_DB_COMPOSE)" down

dev-db-reset:
	@echo "Resetting dev database $(POSTGRES_DB) on port $(DEV_POSTGRES_PORT)..."
	@set -eu; \
		psql "postgresql://$(POSTGRES_APP_USER)@$(POSTGRES_HOST):$(DEV_POSTGRES_PORT)/postgres" -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS \\\"$(POSTGRES_DB)\\\";"; \
		psql "postgresql://$(POSTGRES_APP_USER)@$(POSTGRES_HOST):$(DEV_POSTGRES_PORT)/postgres" -v ON_ERROR_STOP=1 -c "CREATE DATABASE \\\"$(POSTGRES_DB)\\\" OWNER \\\"$(POSTGRES_APP_USER)\\\";"

dev-backend:
	@echo "Starting backend on http://127.0.0.1:$(CLAWDID_PORT)"
	@echo "  Health: http://127.0.0.1:$(CLAWDID_PORT)/health"
	@echo "  Ready:  http://127.0.0.1:$(CLAWDID_PORT)/ready"
	@echo "  DB:     $(DATABASE_URL)"
	cd backend && DATABASE_URL="$(DATABASE_URL)" uv run uvicorn clawdid.main:app --reload --port $(CLAWDID_PORT)

frontend-install:
	cd frontend && pnpm install

dev-frontend:
	@echo "Starting SPA on http://localhost:$(VITE_PORT)"
	cd frontend && pnpm install && VITE_PORT=$(VITE_PORT) pnpm run dev -- --port $(VITE_PORT)

dev-site:
	@echo "Starting marketing site on http://localhost:$(SITE_PORT)"
	cd site && pnpm install && hugo server --port $(SITE_PORT) --bind 127.0.0.1

dev-stop:
	-@lsof -ti :$(CLAWDID_PORT) | xargs kill 2>/dev/null || true
	-@lsof -ti :$(LOCAL_API_PORT) | xargs kill 2>/dev/null || true
	-@lsof -ti :$(VITE_PORT) | xargs kill 2>/dev/null || true
	-@lsof -ti :$(SITE_PORT) | xargs kill 2>/dev/null || true
	@echo "Stopped dev servers (if running)."

status:
	@echo "=== Dev DB (docker) ==="
	@DEV_POSTGRES_PORT="$(DEV_POSTGRES_PORT)" POSTGRES_DB="$(POSTGRES_DB)" POSTGRES_APP_USER="$(POSTGRES_APP_USER)" \
		docker compose -p clawdid-dev-db -f "$(DEV_DB_COMPOSE)" ps 2>/dev/null || echo "  (not running)"
	@echo ""
	@echo "=== Local container stack ==="
	@ENV_FILE="$(LOCAL_ENV_FILE)" LOCAL_IMAGE="$(LOCAL_IMAGE):latest" docker compose --env-file "$(LOCAL_ENV_FILE)" -f "$(LOCAL_COMPOSE)" ps 2>/dev/null || echo "  (not running)"
	@echo ""
	@echo "Backend dev ($(CLAWDID_PORT)):"
	@curl -fsS http://127.0.0.1:$(CLAWDID_PORT)/health 2>/dev/null || echo "  Not running"

api-smoke:
	@set -eu; \
		base="http://127.0.0.1:$(CLAWDID_PORT)"; \
		echo "[1/2] $$base/health"; \
		curl -fsS "$$base/health" >/dev/null; \
		echo "PASS: /health reachable"; \
		echo "[2/2] $$base/ready"; \
		curl -fsS "$$base/ready" >/dev/null; \
		echo "PASS: /ready reachable"

quality-gates: check

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check src tests

lint-types:
	cd backend && uv run mypy src

format:
	cd backend && uv run black src tests
	cd backend && uv run isort src tests

check:
	cd backend && make check

frontend-build:
	cd frontend && pnpm install && pnpm run build

site-build:
	cd site && hugo --minify

docker-validate:
	DEV_POSTGRES_PORT=15489 POSTGRES_DB=clawdid_dev POSTGRES_APP_USER=clawdid docker compose -f "$(DEV_DB_COMPOSE)" config >/dev/null
	ENV_FILE=.env.local-container.example LOCAL_IMAGE="$(LOCAL_IMAGE):latest" docker compose --env-file .env.local-container.example -f "$(LOCAL_COMPOSE)" config >/dev/null
	@echo "Validated $(DEV_DB_COMPOSE) and $(LOCAL_COMPOSE)"

local-container:
	@test -f "$(LOCAL_ENV_FILE)" || (echo "Missing $(LOCAL_ENV_FILE). Use .env.local-container.example as the template." && exit 1)
	@echo "Building local release image $(LOCAL_IMAGE):latest for $(RELEASE_PLATFORM)..."
	docker build --platform "$(RELEASE_PLATFORM)" -f Dockerfile.release -t "$(LOCAL_IMAGE):latest" .
	@echo "Starting local stack (postgres + api)..."
	ENV_FILE="$(LOCAL_ENV_FILE)" LOCAL_IMAGE="$(LOCAL_IMAGE):latest" docker compose --env-file "$(LOCAL_ENV_FILE)" -f "$(LOCAL_COMPOSE)" up -d
	@echo "Try:"
	@echo "  curl -fsS http://127.0.0.1:$$(rg -n '^CLAWDID_API_PORT=' -S \"$(LOCAL_ENV_FILE)\" | sed -E 's/.*=//')/health | jq ."

local-container-down:
	@echo "Stopping local stack..."
	@set -eu; \
		env_file="$(LOCAL_ENV_FILE)"; \
		if [ ! -f "$$env_file" ]; then env_file=".env.local-container.example"; fi; \
		ENV_FILE="$$env_file" LOCAL_IMAGE="$(LOCAL_IMAGE):latest" docker compose --env-file "$$env_file" -f "$(LOCAL_COMPOSE)" down

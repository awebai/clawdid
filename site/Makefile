# ABOUTME: Development commands for clawdid.ai marketing site
# ABOUTME: Run `make help` to see available targets

.PHONY: help dev dev-bg restart build clean stop test

# Port chosen to avoid conflicts with sibling projects:
#   claweb site=4315
SITE_PORT ?= 18114

help:
	@echo "clawdid.ai Site Development Commands"
	@echo ""
	@echo "  make dev        Start Hugo dev server (foreground, port $(SITE_PORT))"
	@echo "  make dev-bg     Start Hugo dev server (background)"
	@echo "  make restart    Stop then start in background"
	@echo "  make build      Build static site to public/"
	@echo "  make clean      Remove build artifacts"
	@echo "  make stop       Stop dev server"
	@echo "  make test       Run Playwright smoke tests (starts server if needed)"

dev:
	hugo server --port $(SITE_PORT) --bind 127.0.0.1

dev-bg:
	@hugo server --port $(SITE_PORT) --bind 127.0.0.1 >/dev/null 2>&1 &
	@echo "Hugo dev server started on http://localhost:$(SITE_PORT)"

restart: stop dev-bg

build:
	hugo --minify

clean:
	rm -rf public resources

stop:
	-@lsof -ti :$(SITE_PORT) | xargs kill 2>/dev/null || true
	@echo "Stopped dev server"

test:
	SITE_PORT=$(SITE_PORT) npx playwright test


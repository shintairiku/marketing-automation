# =============================================================================
# Development Makefile
# =============================================================================
# Usage:
#   make dev              - Start all (Supabase auto-skip if running + Backend + Frontend)
#   make dev STRIPE=1     - Same + Stripe webhook listener
#   make frontend         - Start Frontend only
#   make backend          - Start Backend only
#   make supabase         - Start local Supabase
#   make stripe           - Start Stripe webhook listener
#   make stop             - Stop Supabase containers
#   make lint             - Run lint checks (frontend + backend)
#   make build            - Run frontend production build
#   make check            - Run lint + build (pre-push verification)
# =============================================================================

# Options (e.g. make dev STRIPE=1)
STRIPE ?= 0

# Colors for log prefixes
C_FRONT  := \033[36m
C_BACK   := \033[33m
C_STRIPE := \033[35m
C_INFO   := \033[32m
C_RESET  := \033[0m

# Directories
ROOT_DIR   := $(shell pwd)
FRONT_DIR  := $(ROOT_DIR)/frontend
BACK_DIR   := $(ROOT_DIR)/backend

# Commands
FRONT_CMD  := cd $(FRONT_DIR) && bun run dev
BACK_CMD   := cd $(BACK_DIR) && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8080
STRIPE_CMD := stripe listen --forward-to localhost:3000/api/subscription/webhook

# Supabase port (from supabase/config.toml)
SUPABASE_API_PORT := 15421

.PHONY: dev frontend backend supabase stripe stop lint build check fix help

# ---------------------------------------------------------------------------
# Main targets
# ---------------------------------------------------------------------------

## Start development environment
dev:
	@# --- Supabase: auto-start if not running ---
	@if ss -tln | grep -q ':$(SUPABASE_API_PORT) ' 2>/dev/null; then \
		printf '$(C_INFO)[supabase]$(C_RESET) Already running. Skipping.\n'; \
	else \
		printf '$(C_INFO)[supabase]$(C_RESET) Starting...\n'; \
		npx supabase start; \
		printf '$(C_INFO)[supabase]$(C_RESET) Ready. Studio: http://localhost:15423\n'; \
	fi
	@echo "================================================"
	@echo "  Frontend : http://localhost:3000"
	@echo "  Backend  : http://localhost:8080"
	@echo "  Supabase : http://localhost:15423 (Studio)"
	@if [ "$(STRIPE)" = "1" ]; then echo "  Stripe   : webhook listener active"; fi
	@echo "  Ctrl+C to stop all services"
	@echo "================================================"
	@trap 'kill 0; exit 0' INT TERM; \
	( $(BACK_CMD)  2>&1 | sed -u "s/^/$$(printf '$(C_BACK)[backend]$(C_RESET)  ')/" ) & \
	if [ "$(STRIPE)" = "1" ]; then \
		( $(STRIPE_CMD) 2>&1 | sed -u "s/^/$$(printf '$(C_STRIPE)[stripe]$(C_RESET)   ')/" ) & \
	fi; \
	( $(FRONT_CMD) 2>&1 | sed -u "s/^/$$(printf '$(C_FRONT)[frontend]$(C_RESET) ')/" ) & \
	wait

## Start Frontend dev server only
frontend:
	@cd $(FRONT_DIR) && bun run dev

## Start Backend dev server only
backend:
	@cd $(BACK_DIR) && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8080

## Start local Supabase (Docker containers)
supabase:
	@if ss -tln | grep -q ':$(SUPABASE_API_PORT) ' 2>/dev/null; then \
		printf '$(C_INFO)[supabase]$(C_RESET) Already running. Skipping.\n'; \
	else \
		echo "Starting Supabase..."; \
		npx supabase start; \
		echo "Supabase is ready. Studio: http://localhost:15423"; \
	fi

## Start Stripe webhook listener
stripe:
	@$(STRIPE_CMD)

## Stop Supabase containers
stop:
	@echo "Stopping Supabase..."
	@npx supabase stop
	@echo "Supabase stopped."

# ---------------------------------------------------------------------------
# Quality checks
# ---------------------------------------------------------------------------

## Run lint checks (frontend ESLint + backend ruff)
lint:
	@echo "=== Backend: ruff check ==="
	@cd $(BACK_DIR) && uv run ruff check app
	@echo ""
	@echo "=== Backend: ruff format --check ==="
	@cd $(BACK_DIR) && uv run ruff format --check app || true
	@echo ""
	@echo "=== Frontend: ESLint ==="
	@cd $(FRONT_DIR) && bun run lint

## Run frontend production build
build:
	@cd $(FRONT_DIR) && bun run build

## Pre-push check: lint + build
check: lint build
	@echo ""
	@echo "All checks passed."

## Auto-fix: ruff format + lint fix
fix:
	@echo "=== Backend: ruff format ==="
	@cd $(BACK_DIR) && uv run ruff format app
	@echo ""
	@echo "=== Backend: ruff fix ==="
	@cd $(BACK_DIR) && uv run ruff check --fix app

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

## Show this help
help:
	@echo "Available targets:"
	@echo ""
	@echo "  Development:"
	@echo "    make dev              Start all (Supabase + Backend + Frontend)"
	@echo "    make dev STRIPE=1     Same + Stripe webhook listener"
	@echo "    make frontend         Start Frontend only"
	@echo "    make backend          Start Backend only"
	@echo "    make supabase         Start local Supabase (auto-skips if running)"
	@echo "    make stripe           Start Stripe webhook listener"
	@echo "    make stop             Stop Supabase containers"
	@echo ""
	@echo "  Quality:"
	@echo "    make lint             Run ruff check/format + ESLint"
	@echo "    make build            Run frontend production build"
	@echo "    make check            Run lint + build (pre-push)"
	@echo "    make fix              Auto-fix: ruff format + ruff --fix"

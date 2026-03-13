SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help install install-client install-server dev dev-client dev-server build build-client build-server lint lint-frontend format format-frontend

help:
	@echo "Available targets:"
	@echo "  make install           # Install client/server dependencies"
	@echo "  make dev               # Run client and server dev servers together"
	@echo "  make dev-client      # Run Next.js dev server"
	@echo "  make dev-server       # Run FastAPI dev server"
	@echo "  make build             # Build client and run server import check"
	@echo "  make lint              # Run client lint"
	@echo "  make format            # Run client formatter"

install: install-client install-server

install-client:
	cd client && pnpm install

install-server:
	cd server && uv sync

dev:
	@set -euo pipefail; \
	trap 'kill -TERM -$$$$ 2>/dev/null || true' EXIT INT TERM; \
	(cd server && uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload) & \
	(cd client && pnpm dev) & \
	wait

dev-client:
	cd client && pnpm dev

dev-server:
	cd server && uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

build: build-client build-server

build-client:
	cd client && pnpm build

build-server:
	cd server && uv run python -c "import src.main"

lint: lint-client

lint-frontend:
	cd client && pnpm lint

format: format-client

format-frontend:
	cd client && pnpm format

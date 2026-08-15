SHELL := /bin/bash

.PHONY: help stop reset-redis gateway auth-api file-api grpc-auth sec-worker img-worker log-worker docker-up

.DEFAULT_GOAL := help

help:
	@printf "System Management:\n"
	@printf "  make stop         Stop local uvicorn/workers and docker compose\n"
	@printf "  make reset-redis  Compatibility target used by VS Code tasks\n"
	@printf "\nIndividual Services:\n"
	@printf "  make gateway      Run the main API Gateway\n"
	@printf "  make auth-api     Run the Auth Service API (Port 8001)\n"
	@printf "  make file-api     Run the File API Service (Port 8002)\n"
	@printf "  make grpc-auth    Run the Auth gRPC Server\n"
	@printf "  make sec-worker   Run the Security Scanner Worker\n"
	@printf "  make img-worker   Run the Image Processor Worker\n"
	@printf "  make log-worker   Run the Logging Service Worker\n"
	@printf "  make docker-up    Start backend infrastructure\n"

# --- System Management ---

stop:
	@pkill -f "[u]vicorn" || true
	@pkill -f "[u]v run python" || true
	@docker compose down --remove-orphans 2>/dev/null || true
	@printf "Stopped local task processes and compose services.\n"

reset-redis:
	@printf "No Redis service is defined in docker-compose.yml, so there is nothing to reset.\n"

# --- Individual Services ---

gateway:
	uv run uvicorn gateway.main:app --reload

auth-api:
	uv run uvicorn auth_service.main:app --reload --port 8001

file-api:
	uv run uvicorn api.main:app --reload --port 8002

grpc-auth:
	uv run python -m auth_service.grpc.grpc_server

sec-worker:
	uv run python -m security_scanner.worker

img-worker:
	uv run python -m image_processor.worker

log-worker:
	uv run python -m logger_service.worker

docker-up:
	docker compose up
# Malware Scanning Pipeline

A production-ready, event-driven distributed system to process file uploads asynchronously. This monorepo demonstrates a high-performance, decoupled architecture that separates ingestion, security scanning, and auditing into containerized microservices.

## Overview

The system uses an API-first, headless approach. Incoming uploads are accepted quickly by the API gateway and heavy work (e.g. malware scanning) is handed off to asynchronous workers via RabbitMQ so user requests are never blocked.

Core components

- **API Gateway:** FastAPI (Python) — secure, async HTTP API for upload ingestion and job orchestration.
- **Message Broker:** RabbitMQ — Topic exchange for routing jobs and events with at-least-once delivery semantics.
- **Security Worker:** ClamAV (via clamd) — memory-to-memory malware scanning pipeline (no local disk I/O).
- **Storage:** MinIO — S3-compatible object storage for streaming file transfers.
- **Database:** PostgreSQL (SQLAlchemy + asyncpg) — state-machine driven job records and centralized audit logs.
- **Logger Service:** Lightweight microservice that subscribes to `system.events` and persists a forensic audit trail (e.g. Supabase/Postgres).

## High-Level Flow

1. Client uploads a file to the API.
2. FastAPI calculates a SHA-256 hash for deduplication and streams the file bytes to MinIO.
3. API creates a DB record with `status = pending` and publishes a job message to RabbitMQ.
4. API immediately returns `202 Accepted` to the client.
5. Worker consumes the job, streams the file from MinIO directly into the ClamAV daemon socket, updates the DB state, and emits lifecycle events to `system.events`.
6. Logger service captures events and writes an immutable audit trail.

## Key Technical Decisions

- **Adapter Pattern for Storage:** Storage is pluggable — swap MinIO with AWS S3 or Azure Blob Storage by replacing the adapter only.
- **Memory-to-Memory Streaming:** Files flow from object storage to the scanner over network sockets to avoid server-side disk I/O and reduce I/O latency.
- **SHA-256 Deduplication:** Content-addressed dedup prevents redundant work and provides deterministic identifiers for artifacts.
- **Database Portability:** SQLAlchemy + `asyncpg` keeps DB access vendor-agnostic while retaining Postgres features.
- **Topic Exchange Routing:** Topic exchange on RabbitMQ enables fine-grained routing of events and simple extension points for new workers.

## Folder Layout (Monorepo)

```
/malware-scanning-pipeline
├── api/                  # FastAPI Gateway
├── worker/               # ClamAV Scanner
├── logger/               # Audit/Event Service
├── shared/               # Shared logic (Models, Database, Storage Adapters)
├── database/migrations/  # Alembic SQL versions
├── docker-compose.yml    # Infrastructure orchestration
└── pyproject.toml        # Root workspace configuration
```

## Resume-Ready Highlights

- **Cloud Automation:** CI/CD via GitHub Actions to build and publish Docker images and deploy ephemeral stacks.
- **IaC for Local Development:** `docker compose` brings up RabbitMQ, MinIO, PostgreSQL, and ClamAV for reproducible local testing.
- **Migration Management:** Alembic manages schema changes and provides a reversible migration history.
- **Traceability:** A `job_id` travels across API, broker, and worker to enable end-to-end tracing of file processing.

## Local Development

1. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Launch infra (RabbitMQ, MinIO, Postgres, ClamAV)

```bash
docker compose up -d
```

3. Apply database migrations

```bash
alembic upgrade head
```

4. Run services

```bash
# From the api/ folder
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Run a worker (example)
python -m worker.scanner

# Run logger service
python -m logger.service
```

## Configuration

Configuration is driven by environment variables for 12-factor compatibility. Example variables:

- `DATABASE_URL` — Postgres connection URL
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` — MinIO credentials
- `RABBITMQ_URL` — AMQP connection string
- `CLAMD_HOST`, `CLAMD_PORT` — ClamAV daemon socket/location

## Operational Notes

- Worker design favors streaming to minimize memory footprint — files are processed as streams rather than loading entire payloads into memory.
- Message processing is idempotent where possible; lifecycle transitions are validated in the database to protect against duplicate deliveries.
- All meaningful state transitions are emitted to the `system.events` exchange for observability and audit.

## CI / CD

- Use GitHub Actions to build, test, and publish Docker images.
- Provision ephemeral cloud environments for integration testing and then tear them down to avoid lingering resources.

## Contributing

Contributions are welcome. Please open issues or PRs describing the change and include tests for the modified components.

## License

This repository contains example/demo code. Add your preferred license file if you intend to reuse it in production.

---

Updated: a concise production-ready README for the malware scanning pipeline.

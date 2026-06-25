# FiloJ

An event-driven distributed system to process file uploads asynchronously. This monorepo demonstrates a high-performance, decoupled architecture that separates ingestion, security scanning, image processing, and auditing into containerized microservices.

## Overview

The system uses an API-first, headless approach. Incoming uploads are accepted quickly by the API gateway and heavy work (e.g. malware scanning, image processing) is handed off to asynchronous workers via RabbitMQ so user requests are never blocked.

### Core Components

- **API Gateway:** FastAPI (Python) — secure, async HTTP API for upload ingestion and job orchestration.
- **Message Broker:** RabbitMQ — Topic exchange for routing jobs and events with at-least-once delivery semantics.
- **Security Scanner Worker:** ClamAV (via clamd) — memory-to-memory malware scanning pipeline (no local disk I/O).
- **Image Processor Worker:** PIL/piexif — extracts image metadata, handles EXIF orientation, processes images asynchronously.
- **Logger Service:** Lightweight microservice that subscribes to `system.events` and persists a forensic audit trail to PostgreSQL.
- **Storage:** MinIO — S3-compatible object storage for streaming file transfers.
- **Database:** PostgreSQL (SQLAlchemy + asyncpg) — state-machine driven job records, file metadata, and centralized audit logs.
- **Shared Library:** Unified configuration, database models, broker communication, storage adapters, and logging across all services.

## High-Level Flow

1. Client uploads a file to the API (`/file/upload`).
2. FastAPI calculates a SHA-256 hash for deduplication and streams the file bytes to MinIO.
3. API validates file type and creates DB records (`Job`, `FileMetaData`) with `status = pending`.
4. API publishes job messages to RabbitMQ topic exchange (`system.events`).
5. API immediately returns `202 Accepted` to the client.
6. **Security Scanner Worker** consumes jobs, streams file from MinIO directly into the ClamAV daemon socket, updates DB state, and emits scan events.
7. **Image Processor Worker** (if image) extracts metadata (EXIF), handles image rotation based on orientation, and updates file metadata.
8. **Logger Service** subscribes to `system.events` with pattern `event.#` and persists an immutable audit trail of all lifecycle events.
9. All services emit events to `system.events` for complete traceability.

## Key Technical Decisions

- **Adapter Pattern for Storage:** Storage is pluggable via `S3StorageAdapter` — swap MinIO with AWS S3 or Azure Blob Storage without changing worker code.
- **Memory-to-Memory Streaming:** Files flow directly from MinIO to ClamAV over network sockets; image bytes streamed to PIL — zero local disk I/O on workers.
- **SHA-256 Content Deduplication:** Prevents redundant scanning and processing; provides deterministic artifact identifiers.
- **Topic Exchange Routing:** RabbitMQ topic exchange (`system.events`) with pattern-based subscriptions (`event.#`) enables fine-grained event routing and simple extension for new workers.
- **Async/Await Throughout:** FastAPI, asyncpg, aio_pika, PIL Image operations — entire pipeline is async for high concurrency.
- **Database Portability:** SQLAlchemy ORM + asyncpg keeps DB access vendor-agnostic while preserving Postgres-native features (JSONB for result_data).
- **Monorepo with Workspace Members:** Python workspace (via uv) keeps all services in one repo with shared dependencies and unified configuration.
- **Centralized Audit Trail:** All lifecycle events published to message broker; logger service persists immutable records for compliance and debugging.

## Folder Layout (Monorepo)

```
dunno-what/
├── api/                           # FastAPI Gateway (upload ingestion & orchestration)
│   ├── main.py                    # API endpoints (/health, /file/upload)
│   └── utils.py                   # File type validation helpers
├── security_scanner/              # ClamAV Security Scanner Worker
│   ├── worker.py                  # Job consumer, ClamAV integration
│   └── clamav.py                  # ClamAV daemon client
├── image_processor/               # Image Processing Worker
│   └── worker.py                  # Image metadata extraction, EXIF rotation
├── logger_service/                # Audit Logger Service
│   └── worker.py                  # Event consumer, audit trail persistence
├── shared/                        # Shared library (workspace member)
│   └── src/shared/
│       ├── models.py              # SQLAlchemy models (Job, FileMetaData, AuditLog)
│       ├── database.py            # AsyncSession, engine setup
│       ├── broker.py              # RabbitMQ BrokerClient
│       ├── storage.py             # S3StorageAdapter (MinIO)
│       ├── logger.py              # Centralized logging
│       └── config.py              # Environment config & constants
├── database/
│   └── migrations/                # Alembic SQL versions
├── clamav/
│   └── clamd.conf                 # ClamAV daemon configuration
├── docker-compose.yml             # Infrastructure orchestration
├── alembic.ini                    # Alembic migration config
├── pyproject.toml                 # Root workspace (uv workspace members)
└── README.md                      # This file
```

## Local Development

### 1. Setup Python Environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

Using **uv** (recommended) or pip:

```bash
# With uv (fast workspace resolver)
uv sync

# Or with pip
pip install -e ./shared -e ./api -e ./security_scanner -e ./image_processor -e ./logger_service
```

### 3. Launch Infrastructure (RabbitMQ, MinIO, PostgreSQL, ClamAV)

```bash
docker compose up -d
```

Verify services are healthy:
```bash
docker compose ps
```

**Service Endpoints:**
- RabbitMQ Management: `http://localhost:15672` (guest/guest)
- MinIO Console: `http://localhost:9001` (admin/password123)
- ClamAV: `localhost:3310`
- PostgreSQL: `localhost:5432`

### 4. Apply Database Migrations

```bash
alembic upgrade head
```

### 5. Run Services (in separate terminals)

**API Gateway:**
```bash
cd api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Security Scanner Worker:**
```bash
cd security_scanner
python -m worker
```

**Image Processor Worker:**
```bash
cd image_processor
python -m worker
```

**Logger Service:**
```bash
cd logger_service
python -m worker
```

### 6. Test Upload

```bash
curl -X POST http://localhost:8000/file/upload \
  -F "uploaded_file=@/path/to/test.jpg"
```

Expected response: `202 Accepted` with job details.

## Configuration

All configuration is driven by environment variables for 12-factor compatibility. See `shared/src/shared/config.py` for defaults.

### Core Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/filoj` |
| `DATABASE_SCHEMA` | PostgreSQL schema name | `public` |
| `MINIO_ENDPOINT` | MinIO server URL | `http://localhost:9000` |
| `MINIO_ACCESS_KEY` | MinIO access key | `admin` |
| `MINIO_SECRET_KEY` | MinIO secret key | `password123` |
| `RABBITMQ_URL` | RabbitMQ AMQP connection | `amqp://guest:guest@localhost/` |
| `CLAMD_HOST` | ClamAV daemon host | `localhost` |
| `CLAMD_PORT` | ClamAV daemon port | `3310` |
| `ALLOWED_FILES` | Comma-separated allowed file extensions | `jpg,jpeg,png,pdf,docx` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Local Development `.env` Example

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/filoj
DATABASE_SCHEMA=public
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=password123
RABBITMQ_URL=amqp://guest:guest@localhost/
CLAMD_HOST=localhost
CLAMD_PORT=3310
ALLOWED_FILES=jpg,jpeg,png,gif,pdf,docx,txt
LOG_LEVEL=DEBUG
```

Load environment variables before running services:
```bash
set -a && source .env && set +a
```

## Operational Notes

- **Worker Design:** Favors streaming to minimize memory footprint — files are processed as streams rather than loading entire payloads into memory.
- **Idempotency:** Message processing is idempotent where possible; lifecycle transitions are validated in the database to protect against duplicate deliveries.
- **Event Observability:** All meaningful state transitions are emitted to the `system.events` exchange for observability, traceability, and audit.
- **Job Status Machine:** Job transitions follow a strict state machine: `pending` → `scanning` → `processing` → `completed|failed|quarantined`.
- **Retry Logic:** Workers implement exponential backoff and max delivery count to handle transient failures gracefully.

## Highlights

- **Microservices Architecture:** Decoupled, independently deployable services communicate via async message queue.
- **Cloud-Native Design:** Container-first deployment with Docker Compose for local dev and scalable to Kubernetes.
- **Production Patterns:** Circuit breakers, graceful degradation, audit logging, and comprehensive error handling.
- **Database Migrations:** Alembic manages schema evolution with versioned, reversible migrations.
- **End-to-End Tracing:** Job IDs propagate across API, broker, and workers for complete request traceability.
- **Storage Abstraction:** Pluggable storage adapters enable multi-cloud deployments (MinIO, AWS S3, Azure Blob).

## Contributing

Contributions are welcome. Please open issues or PRs describing changes and include tests for modified components.

## License

This repository contains example code. Add your preferred license file if you intend to reuse it in production.

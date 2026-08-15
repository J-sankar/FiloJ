# FiloJ

An event-driven distributed system to process file uploads asynchronously. This monorepo demonstrates a high-performance, decoupled architecture that separates ingestion, security scanning, image processing, and auditing into containerized microservices.

## Architecture

The current main branch contains these active pieces:

- `gateway/` — public HTTP gateway that routes requests to internal services
- `auth_service/` — developer auth, refresh/logout, API-key management, and webhook configuration
- `api/` — file upload service and job submission flow
- `security_scanner/` — ClamAV-backed malware scanning worker
- `image_processor/` — image processing worker
- `logger_service/` — event/audit logging worker
- `dispatcher/` — orchestration/dispatch logic
- `shared/` — shared config, logging, database, messaging, and utilities

## Service layout and responsibilities

### Gateway

The gateway runs at `http://localhost:8000` by default and proxies requests like:

- `/auth/...` → auth service
- `/file/...` → file processing service

The gateway also validates developer identity or API-key context and forwards auth headers.

### Auth service

When you call the auth service directly on port `8001`, the routes are under `/api/auth` and `/api/key`, and the webhook routes live at `/api/webhook`.

Direct-service routes include:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `POST /api/key`
- `GET /api/webhook`
- `POST /api/webhook`
- `DELETE /api/webhook`

Through the gateway on port `8000`, the same routes are exposed as:

- `POST /auth/api/auth/register`
- `POST /auth/api/auth/login`
- `POST /auth/api/auth/refresh`
- `POST /auth/api/auth/logout`
- `POST /auth/api/key`
- `GET /auth/api/webhook`
- `POST /auth/api/webhook`
- `DELETE /auth/api/webhook`

Developer headers are expected in the auth flow, including:

- `X-Developer-ID` for direct internal requests to the auth service
- `Authorization: Bearer <token>` for gateway-mediated requests

### File service

The file API service is the upload-facing service.

Direct-service routes include:

- `GET /health`
- `POST /file/upload`

Through the gateway, the same service is reached as:

- `GET /file/health`
- `POST /file/file/upload`

Upload flow in the current code:

1. Validates filename and MIME type
2. Computes a SHA-256 hash for deduplication
3. Stores the file in MinIO-backed storage
4. Creates a DB record in the shared model layer
5. Publishes a scan task to RabbitMQ
6. Emits an `event.api.file_uploaded` audit event

## Current local startup commands

The repo includes a `Makefile` with the active service commands used by this branch:

```bash
make gateway
make auth-api
make file-api
make grpc-auth
make sec-worker
make img-worker
make log-worker
make docker-up
make stop
```

### Direct service commands

```bash
uv run uvicorn gateway.main:app --reload
uv run uvicorn auth_service.main:app --reload --port 8001
uv run uvicorn api.main:app --reload --port 8002
uv run python -m auth_service.grpc.grpc_server
uv run python -m security_scanner.worker
uv run python -m image_processor.worker
uv run python -m logger_service.worker
```

## Infrastructure

The application expects the following services to be running locally for development:

- RabbitMQ
- MinIO
- ClamAV

The root `docker-compose.yml` currently starts:

```bash
docker compose up
```

Service endpoints from the current Compose file:

- RabbitMQ: `amqp://guest:guest@localhost:5672`
- RabbitMQ management: `http://localhost:15672`
- MinIO: `http://localhost:9000`
- MinIO console: `http://localhost:9001`
- ClamAV: `localhost:3310`

## Python workspace setup

The root project uses a uv workspace. Install dependencies with:

```bash
uv sync
```

The workspace members are defined in `pyproject.toml` and include:

- `api`
- `security_scanner`
- `logger_service`
- `image_processor`
- `shared`
- `auth_service`
- `dispatcher`
- `gateway`

## Environment variables

The app reads settings from environment variables and `.env` files.

Key settings currently used by the gateway and auth service include:

```bash
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
FILE_SERVICE_URL=http://localhost:8002
AUTH_SERVICE_URL=http://localhost:8001
REDIS_HOST=localhost
REDIS_PORT=6379
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/your_db
INTERNAL_GATEWAY_SECRET=your-internal-secret
```

The shared database layer also uses `DATABASE_URL` for async SQLAlchemy connections.

## Example login flow

Register or log in directly against the auth service:

```bash
curl -X POST "http://localhost:8001/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "your-password"
  }'
```

Through the gateway, use the proxied route instead:

```bash
curl -X POST "http://localhost:8000/auth/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "your-password"
  }'
```

The response includes:

- `access_token`
- `developer_id`
- `name`
- `plan`

## Example webhook deletion

Directly against the auth service, delete the webhook with the developer id header:

```bash
curl -X DELETE "http://localhost:8001/api/webhook" \
  -H "X-Developer-ID: 11111111-2222-3333-4444-555555666666"
```

Through the gateway, use the gateway path and pass the bearer token instead:

```bash
curl -X DELETE "http://localhost:8000/auth/api/webhook" \
  -H "Authorization: Bearer <access_token>"
```

## Notes

- This main branch is a monorepo rather than a single app.
- The gateway is the main front door for external traffic.
- The auth and file services are separate FastAPI apps with independent entry points.
- Messaging and file processing are event-driven and rely on the shared broker and storage abstractions.

## Repository structure

```text
dunno-what/
├── api/
├── auth_service/
├── database/
├── dispatcher/
├── gateway/
├── image_processor/
├── logger_service/
├── security_scanner/
├── shared/
├── clamav/
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── alembic.ini
├── pyproject.toml
├── README.md

```



from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from gateway.routers.proxy import proxy_request
from shared.logger import get_logger
from contextlib import asynccontextmanager
import time
import httpx


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = httpx.AsyncClient(
        limits=httpx.Limits(max_keepalive_connections=50, max_connections=100)
    )

    app.state.http_client = client

    yield

    await app.state.http_client.aclose()


app = FastAPI(title="API Gateway", lifespan=lifespan)


@app.middleware("http")
async def log_request(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} | {duration}ms"
    )
    return response


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.api_route(
    "/{service}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
)
async def gateway(service: str, path: str, request: Request):
    return await proxy_request(
        service,
        path,
        request,
        request.headers.get("x-developer-id"),
        request.headers.get("x-developer-plan"),
    )


@app.exception_handler(Exception)
async def gloabl_exception_handler(request: Request, exc: Exception):
    logger.error(f"UNHANDLED ERROR: {str(exc).lower()}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal Gateway Error"})

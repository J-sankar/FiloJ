from fastapi import FastAPI,Request,status
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from auth_service.routes.auth import router
from auth_service.routes.api_keys import router as api_router
from shared.logger import get_logger
from shared.database import  engine, Base
from contextlib import asynccontextmanager


logger = get_logger(__name__)



@asynccontextmanager
async def lifespan(app: FastAPI):

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("DB setup complete")
    yield
    await engine.dispose()
    logger.info("Shutting down")
app = FastAPI(title="Auth Service",lifespan=lifespan)
app.include_router(router, prefix="/api/auth")
app.include_router(api_router, prefix="/api/key")

app.get("/health")
def health():
    return {"status":"healthy"}



@app.exception_handler(HTTPException)
async def http_exception_handler(request:Request, exc:HTTPException):
    logger.warning(f"ERROR: {str(exc).lower()}",exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={"details": exc.detail}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred."}
    )

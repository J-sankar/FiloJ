import hashlib
from contextlib import asynccontextmanager
from typing import Annotated

import uuid
import anyio
from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.exceptions import HTTPException
from shared.broker import BrokerClient
from shared.database import AsyncSession, Base, engine, get_session
from shared.logger import get_logger
from shared.models import FileMetaData, Job
from shared.storage import S3StorageAdapter
from sqlalchemy import select

from api.dependencies import DeveloperHeaders, get_developer
from api.utils import allowed_file_type, get_file_type, validate_mime

logger = get_logger(__name__)
storage = S3StorageAdapter()
broker = BrokerClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await storage.setup_buckets()
    await broker.connect()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("DB setup complete")
    yield
    await engine.dispose()
    await broker.close()
    logger.info("Shutting down")


app = FastAPI(title="FiloJ", lifespan=lifespan)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


async def iterator(filename: str):
    async with await anyio.open_file(filename, "rb") as f:
        while chunk := await f.read(1024 * 1024):
            yield chunk


@app.post("/file/upload")
async def upload_file(
    developer: Annotated[DeveloperHeaders, Depends(get_developer)],
    uploaded_file: Annotated[UploadFile, File(...)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    
    filename = uploaded_file.filename
    
    filetype = get_file_type(filename)

    if not allowed_file_type(filename):
        logger.warning(f"Invalid file type , file : {filename} | {filetype}")
        raise HTTPException(status_code=400, detail="File type is invalid")
    if not  await validate_mime(uploaded_file):
        raise HTTPException(400,"File type mismatch — file content does not match extension")
    
    try:
        m = hashlib.sha256()
        chunk_size = 1024 * 1024
        while chunk := await uploaded_file.read(chunk_size):
            m.update(chunk)
        file_hash = m.hexdigest()
        file_key = f"{file_hash}{filetype}"
        job_res = await db.execute(
            select(Job)
            .join(Job.file)
            .where(FileMetaData.upload_id == file_hash,FileMetaData.developer_id==developer.developer_id)
            .order_by(Job.updated_at.desc())
        )
        existing_job = job_res.scalars().first()
        if existing_job:
            if existing_job.status in (
                "scanning",
                "processing",
                "completed",
                "pending",
                "clean"
            ):
                logger.info("File hash exists in db")
                return {
                    "message": "File already exists",
                    "job_id": str(existing_job.id),
                    "status": existing_job.status,
                }
        await uploaded_file.seek(0)
        file_stream = uploaded_file.file
        await storage.upload_file(file_key, file_stream,bucket=storage.upload_bucket)
        logger.info(f"File Uploaded to Storage | {filename}")
        async with db.begin_nested():
    
    
            file_metadata = FileMetaData(
                type=filetype,
                name=filename,
                upload_id=file_hash,
                storage_location=file_key,

                developer_id     = developer.developer_id,
            )   
 
            new_job = Job(
                file=file_metadata  
            )
            
            db.add(file_metadata)
            db.add(new_job)
        await db.commit()
        job_payload = {"job_id": str(new_job.id), "file_hash": file_key,"developer_id":developer.developer_id}
        await broker.publish(
            exchange_name="work.tasks",
            routing_key=f"task{filetype}.scan",
            payload=job_payload,
        )
        new_log = {
            "job_id": str(new_job.id),
            "routing_key": f"task{filetype}.scan",
            "service": "api",
            "action": "file scheduled for scanning",
        }
        await broker.publish("system.events", routing_key="event.api.file_uploaded", payload=new_log,headers=None)
        logger.info(
            f"Scan job scheduled | job: {str(new_job.id)[:8]} | file: {filename}"
        )
        return {
            "message": "File uploaded and scheduled for processing",
            "job_id": str(new_job.id),
            "upload_id": file_key,
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"ERROR: {str(e).lower()}")
        raise HTTPException(status_code=500, detail="Internal Server Error")




# async def get_presigned_url(
#         developer: Annotated[DeveloperHeaders, Depends(get_developer)],
#         db: Annotated[AsyncSession, Depends(get_session)],
#         job_id: str 
# ):
#     developer_id = developer.developer_id
#     try:
#         job_res = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
#         job = job_res.scalar_one_or_none()
#         if not job:
#             return HTTPException(status_code=401, detail="Job not found")
#         if job.
    
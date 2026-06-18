from clamd import  BufferTooLongError,ConnectionError
from shared.logger import get_logger
from shared.broker import BrokerClient
from shared.storage import S3StorageAdapter
from security_scanner.clamav import ClamAVClient
from shared.database import AsyncSesssionLocal
from shared.models import (Job)
from sqlalchemy import select
from aio_pika.abc import AbstractIncomingMessage
import json
import uuid
import asyncio
from contextlib import asynccontextmanager
import tempfile as temp
worker_id = str(uuid.uuid4())

logger = get_logger(__name__)
s3 = S3StorageAdapter()



@asynccontextmanager
async def job_transaction(job_id: str):
    """Centralises job status update on failure"""
    async with AsyncSesssionLocal() as db:
        try:
            yield db
        except ConnectionError as e:
            job = await db.get(Job, uuid.UUID(job_id))
            if job:
                job.status = "queued_for_retry"
                job.result_data = {"error": "clamav connection dropped, retrying"}
                await db.commit()
            raise e
        except Exception as e:
            job = await db.get(Job, uuid.UUID(job_id))
            if job:
                job.status = "failed"
                job.result_data = {"error": str(e).lower()}
                await db.commit()
            raise e


async def scan_file(message: AbstractIncomingMessage,broker:BrokerClient, cd: ClamAVClient):
    async with message.process(requeue=True):
        try:

            data_decoded = message.body.decode("utf-8")
            data = json.loads(data_decoded)
            job_id = data.get("job_id", None)
            file_key = data.get("file_hash", None)
            async with job_transaction(job_id) as db:
                logger.info(f"Job:{job_id[:8]} | Obtained")
                job_res = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
                job = job_res.scalar_one_or_none()
                if not job:
                    logger.error(f"Job not found: {job_id[:8]}")
                    return
                job.status = "scanning"
                await db.commit()
                audit_log = {"job_id": job_id, "service": "scanner_worker", "routing_key":"event.scanner.scan_start","action":"security scan started"}
                await broker.publish("system.events", "event.scanner.scan_start",payload=audit_log)
                logger.info(f"Job:{job_id[:8]} | Scan started")
                with temp.SpooledTemporaryFile(max_size=50*1024*1024) as spoolfile: 
                    async for chunk in  s3.get_file_stream(file_key=file_key):
                        spoolfile.write(chunk)
                    spoolfile.seek(0)

                    scan_res = await cd.scan(spoolfile)
                    status_tuple = scan_res.get("stream", ('ERROR', None))
                    final_stat = "clean" if status_tuple[0] == 'OK' else "infected"
                    logger.debug(f"Obtained result: job_id {job_id[:8]} | status : {final_stat} ")
                    audit_log = {"job_id": job_id, "service": "scanner_worker", "routing_key":"event.scanner.scan_success","action":f"security scan completed: status - {final_stat} "}
                    await broker.publish("system.events", "event.scanner.scan_success",payload=audit_log)
                    if final_stat == "infected":
                        await s3.move_to_quarantine(file_key)
                    job.result_data = scan_res
                    job.status = final_stat
                    await db.commit()
                        
        except ConnectionError :
            audit_log = {"job_id": job_id, "service": "scanner_worker", "routing_key":"event.scanner.scan_fail","action":"queued_for_retry"}
            await broker.publish("system.events", "event.scanner.scan_fail",payload=audit_log)
            logger.error("ClamAV unreachable — stopping worker")
            raise SystemExit(1)
        except BufferTooLongError :
            audit_log = {"job_id": job_id, "service": "scanner_worker", "routing_key":"event.scanner.scan_fail","action":"security scan failed, buffer too long"}
            await broker.publish("system.events", "event.scanner.scan_fail",payload=audit_log)

            logger.error(f"File too large | job: {job_id[:8]}")
            return 
            
        except Exception as e:
            logger.exception(f"Failed to process message: {str(e).lower()}")
            delivery_count = message.headers.get("x-delivery-count",0)
            if delivery_count == 3:
                audit_log = {"job_id": job_id, "service": "scanner_worker", "routing_key":"event.scanner.scan_fail","action":"moved to dlx exchange"}
            else:
                audit_log = {"job_id": job_id, "service": "scanner_worker", "routing_key":"event.scanner.scan_fail","action":f"ERROR: {str(e).lower()[:20]}, retyring"}
            await broker.publish("system.events", "event.scanner.scan_fail",payload=audit_log)
            raise e


async def scan_worker():
    
        try:
            broker = BrokerClient()
            await broker.connect()
            queue = await broker.get_configured_queue("work.tasks", "task.*.scan", "scanner-queue")
            logger.info(f"Worker:{str(worker_id)[:8]} | Waiting for scan jobs")
            cd = ClamAVClient()
            await cd.connect()
            async with queue.iterator() as iterator:
                message:AbstractIncomingMessage
                async for message in iterator:
                    await scan_file(message, broker, cd)
        except SystemExit:
            raise
        except Exception as e:
            logger.error(str(e).lower())
            return
if __name__ == "__main__":
    asyncio.run(scan_worker())           


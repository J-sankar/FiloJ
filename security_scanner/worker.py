from clamd import BufferTooLongError, ConnectionError
from shared.logger import get_logger
from shared.broker import BrokerClient
from shared.storage import S3StorageAdapter
from security_scanner.clamav import ClamAVClient
from shared.database import AsyncSesssionLocal
from shared.models import Job, FileMetaData
from shared.config import ALLOWED_FILES
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


MAX_DELIVERY_COUNT = 3


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
            raise
        except Exception as e:
            job = await db.get(Job, uuid.UUID(job_id))
            if job:
                job.status = "failed"
                job.result_data = {"error": str(e).lower()}
                await db.commit()
            raise


async def _publish_audit(
    broker: BrokerClient, job_id: str, routing_key: str, action: str
) -> None:
    """Thin wrapper so audit-log dicts aren't duplicated everywhere."""
    await broker.publish(
        "system.events",
        routing_key,
        payload={
            "job_id": job_id,
            "service": "scanner_worker",
            "routing_key": routing_key,
            "action": action,
        },
    )


async def scan_file(
    message: AbstractIncomingMessage, broker: BrokerClient, cd: ClamAVClient
):
    async with message.process(requeue=True):
        try:
            data_decoded = message.body.decode("utf-8")
            data = json.loads(data_decoded)
            job_id: str = data["job_id"]
            file_key: str = data["file_hash"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Malformed message, discarding: {e}")
            await message.nack(requeue=False)
            return
        try:
            async with job_transaction(job_id) as db:
                logger.info(f"Job:{job_id[:8]} | Obtained")
                job_res = await db.execute(
                    select(Job).where(Job.id == uuid.UUID(job_id))
                )
                job = job_res.scalar_one_or_none()
                if not job:
                    logger.error(f"Job not found: {job_id[:8]}")
                    return
                job.status = "scanning"
                await db.commit()
                filemetadata_res = await db.execute(
                    select(FileMetaData).where(
                        FileMetaData.storage_location == file_key
                    )
                )
                filemetadata = filemetadata_res.scalar_one_or_none()
                if not filemetadata:
                    raise ValueError(f"FileMetaData not found for key: {file_key}")
                await _publish_audit(
                    broker, job_id, "event.scanner.scan_start", "security scan started"
                )
                logger.info(f"Job:{job_id[:8]} | Scan started")
                with temp.SpooledTemporaryFile(max_size=50 * 1024 * 1024) as spoolfile:
                    loop = asyncio.get_running_loop()
                    async for chunk in s3.get_file_stream(file_key=file_key):
                        await loop.run_in_executor(None, spoolfile.write, chunk)
                    await loop.run_in_executor(None, spoolfile.seek, 0)

                    scan_res = await cd.scan(spoolfile)
                    status_tuple = scan_res.get("stream", ("ERROR", None))
                    final_stat = "clean" if status_tuple[0] == "OK" else "infected"
                    logger.debug(
                        f"Obtained result: job_id {job_id[:8]} | status : {final_stat} "
                    )
                    await _publish_audit(
                        broker,
                        job_id,
                        "event.scanner.scan_success",
                        f"security scan completed: status - {final_stat}",
                    )
                    if final_stat == "infected":
                        await s3.move_to_quarantine(file_key)
                        filemetadata.bucket = "quarantine"
                        await db.commit()
                        return
                    job.result_data = scan_res
                    job.status = final_stat
                    await db.commit()
                    if ALLOWED_FILES.get(filemetadata.type, None) == "image":
                        await broker.publish(
                            "work.tasks", "task.image.process", data_decoded
                        )
                        await _publish_audit(
                            broker,
                            job_id,
                            "event.scanner.image_queued",  # Fix: was wrongly reusing scan_success key
                            "image submitted to processing",
                        )
                        logger.info(f"Job:{job_id[:8]} | Image scheduled for processing")

        except ConnectionError:
            await _publish_audit(
                broker, job_id, "event.scanner.scan_fail", "queued_for_retry"
            )
            logger.error("ClamAV unreachable — stopping worker")
            raise SystemExit(1)
        except BufferTooLongError:
            await _publish_audit(
                broker,
                job_id,
                "event.scanner.scan_fail",
                "scan failed: buffer too long",
            )

            logger.error(f"File too large | job: {job_id[:8]}")
            await message.nack(requeue=False)

        except Exception as e:
            logger.exception(f"Failed to process message: {str(e).lower()}")
            delivery_count = message.headers.get("x-delivery-count", 0)
            if (
                delivery_count >= MAX_DELIVERY_COUNT
            ):  # Fix: was == 3 (misses counts > 3)
                action = "moved to dlx exchange"
            else:
                action = f"error: {str(e)[:50]}, retrying (attempt {delivery_count + 1}/{MAX_DELIVERY_COUNT})"
            await _publish_audit(broker, job_id, "event.scanner.scan_fail", action)
            raise 


async def scan_worker():
    broker: BrokerClient | None = None
    cd: ClamAVClient | None = None
    try:
        broker = BrokerClient()
        await broker.connect()
        cd = ClamAVClient()
        await cd.connect()
        queue = await broker.get_configured_queue(
            "work.tasks", "task.*.scan", "scanner-queue"
        )
        logger.info(f"Worker:{str(worker_id)[:8]} | Waiting for scan jobs")
        async with queue.iterator() as iterator:
            message: AbstractIncomingMessage
            async for message in iterator:
                await scan_file(message, broker, cd)
    except SystemExit:
        raise
    except Exception as e:
        logger.error(str(e).lower())
    finally:
        if cd is not None:
            await cd.disconnect()
        if broker is not None:
            await broker.close()


if __name__ == "__main__":
    asyncio.run(scan_worker())

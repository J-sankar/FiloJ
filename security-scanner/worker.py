import clamd
from shared.logger import get_logger
from shared.broker import BrokerClient
from shared.storage import S3StorageAdapter
from shared.database import AsyncSesssionLocal
from shared.models import (Job, AuditLog)
from sqlalchemy import select
from aio_pika.abc import AbstractIncomingMessage
import json
import uuid
import asyncio
import tempfile as temp
worker_id = str(uuid.uuid4())

logger = get_logger(__name__)
s3 = S3StorageAdapter()

cd = clamd.ClamdNetworkSocket(host='localhost', port=3310)

async def scan_file(message: AbstractIncomingMessage):
    async with message.process():
        try:

            data_decoded = message.body.decode("utf-8")
            data = json.loads(data_decoded)
            job_id = data.get("job_id", None)
            file_key = data.get("file_hash", None)
            async with AsyncSesssionLocal() as db:
                job_res = await db.execute(select(Job).where(Job.id == uuid.uuid4(job_id)))
                job = job_res.scalar_one_or_none()
                if not job:
                    logger.error(f"Job not found: {job_id[:8]}")
                    return
                job.status = "scanning"
                db.add(job)
                await db.commit()
                with temp.SpooledTemporaryFile(max_size=50*1024*1024) as spoolfile: 
                    async for chunk in  s3.get_file_stream(file_key=file_key):
                        spoolfile.write(chunk)
                    spoolfile.seek(0)

                    scan_res = await asyncio.to_thread(cd.instream, spoolfile)
                    status_tuple = scan_res.get("stream", ('ERROR', None))
                    final_stat = "clean" if status_tuple[0] == 'OK' else "infected"
                    logger.info(f"Obtained result: job_id {job_id[:8]} | status : {final_stat} ")
                    if final_stat == "clean":

                        await s3.move_to_quarantine(file_key)

                        


        except Exception as e:
            logger.exception(f"Failed to process message: {e}")
            raise e


async def scan_worker():
    
        try:
            broker = BrokerClient()
            await broker.connect()
            queue = await broker.get_configured_queue("work.tasks", "task.*.scan", "scanner-queue")
            logger.info(f"Worker:{str(worker_id)[:8]} | Waiting for scan jobs")
            async with queue.iterator() as iterator:
                message:AbstractIncomingMessage
                async for message in iterator:
                    await scan_file(message)
        except Exception as e:
            logger.error(str(e).lower())
            return
if __name__ == "__main__":
    asyncio.run(scan_worker())           


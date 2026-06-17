import clamd
from shared.logger import get_logger
from shared.broker import BrokerClient
from shared.database import AsyncSesssionLocal
from shared.models import (Job, AuditLog)
from aio_pika.abc import AbstractIncomingMessage,AbstractProcessContext
import json
import uuid
import asyncio
worker_id = str(uuid.uuid4())

logger = get_logger(__name__)

async def scan_file(message: AbstractIncomingMessage):
    async with message.process():
        data_decoded = message.body.decode("utf-8")
        data = json.loads(data_decoded)
        logger.info(f"Obtained job: {data.get('job_id')[:8]} | file_hash : {data.get('file_hash')[:8]}")
        


async def scan_worker():
    async with AsyncSesssionLocal() as db:
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


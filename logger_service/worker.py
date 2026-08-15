from shared.database import AsyncSesssionLocal
from shared.models import AuditLog
from shared.logger import get_logger
from shared.broker import BrokerClient
from aio_pika.abc import AbstractIncomingMessage, AbstractQueue
import asyncio
import json
import uuid

logger = get_logger(__name__)

async def process_batch(batch_messages:list[AbstractIncomingMessage], batch_data:list[AuditLog]):
        try:
            async with AsyncSesssionLocal() as db:
                    db.add_all(batch_data)
                    await db.commit()
                    logger.info("Pushed batch todb")
                   
                    
                    for msg in batch_messages:
                        await msg.ack()

        except Exception as e:
            logger.exception(f"Failed to process message: {str(e).lower()}")
            for msg in batch_messages:
                await msg.nack(requeue=True)



async def audit_logger():
    broker: BrokerClient | None = None
    batch_data: list = []
    batch_messages : list = []
    try:
        broker = BrokerClient()
        await broker.connect(prefetch_count=5)
        queue: AbstractQueue = await broker.get_configured_queue(
            "system.events", "event.#", "logger_queue"
        )
        async with queue.iterator() as iterator:

            message: AbstractIncomingMessage
            async for message in iterator:
                try:
                    data_decoded = message.body.decode('utf-8')
                    data = json.loads(data_decoded)
                    logger.debug(data)
                    if isinstance(data, dict):
                        data = [data]
                        
                    for log_entry in data:
                        log_entry["job_id"] = uuid.UUID(log_entry["job_id"])
                        batch_data.append(AuditLog(**log_entry))
                        batch_messages.append(message)

                    if len(batch_data) >= 5:
                        await process_batch(batch_messages,batch_data)
                        batch_data.clear()
                        batch_messages.clear()
                except (UnicodeDecodeError, json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Malformed message, discarding: {e}")
                    await message.nack(requeue=False)
        
    except Exception as e:
        logger.error(f"ERROR: {str(e).lower()}")
    finally:
        if batch_data:
            logger.info("Shutdown detected, flushing remaining batch...")
            await process_batch(batch_messages, batch_data)
            batch_messages.clear()
            batch_data.clear()
        if broker and broker.connection:
            await broker.close()


if __name__ == "__main__":
    asyncio.run(audit_logger())
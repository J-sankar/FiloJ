from redis.asyncio import Redis
from aio_pika.abc import AbstractIncomingMessage, AbstractQueue
from shared.broker import BrokerClient
from shared.logger import get_logger
from shared.redis.client import RedisClient
from dispatcher.grpc_clients.auth_client import AuthGrpcClient
from dispatcher.orchestrator.processor import process_webhook
from dispatcher.orchestrator.dispatch_context import DispatchContext
from dispatcher.orchestrator.webhook_config import WebhookConfigResolver
import httpx
import asyncio

logger = get_logger(__name__)


async def _publish_audit(
    broker: BrokerClient, job_id: str, routing_key: str, action: str
) -> None:
    """Thin wrapper so audit-log dicts aren't duplicated everywhere."""
    await broker.publish(
        "system.events",
        routing_key,
        payload={
            "job_id": job_id,
            "service": "image_processor",
            "routing_key": routing_key,
            "action": action,
        },
    )


async def start_worker():
    broker: BrokerClient | None = None
    redis: Redis | None = None
    auth_grpc_client: AuthGrpcClient | None = None
    try:
        broker = BrokerClient()
        await broker.connect()
        redis_client = RedisClient()
        redis = redis_client.client
        auth_grpc_client = AuthGrpcClient()
        config_resolver = WebhookConfigResolver(redis,auth_grpc_client)
        queue: AbstractQueue = await broker.get_configured_queue(
            "webhook.retry", "event.job.*", "webhook_dipatcher"
        )
        async with httpx.AsyncClient() as http_client:
            ctx = DispatchContext(broker,http_client,config_resolver)
            async with queue.iterator() as iterator:
                message: AbstractIncomingMessage
                async for message in iterator:
                    
                    await process_webhook(message,ctx)
    except (KeyboardInterrupt):
        logger.warning("Shutting down...")
    except Exception as e:
        logger.error(f"ERROR | {str(e).lower()}")
    finally:
        if broker.connection:
            await broker.close()
        if redis_client.client:
            await redis_client.close()
        if auth_grpc_client:
            await auth_grpc_client.close()


if __name__ == "__main__":
    asyncio.run(start_worker())

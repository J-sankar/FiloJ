from redis.asyncio import Redis
from dispatcher.cache.webhook_repo import WebhookRepo
from dispatcher.grpc_clients.auth_client import AuthGrpcClient
from shared.logger import get_logger
# import asyncio

logger = get_logger(__name__)

class WebhookConfigResolver:
    def __init__(self,redis:Redis,auth_grpc_client: AuthGrpcClient):
        self.redis = redis
        self.auth_grpc_client = auth_grpc_client
        

    async def get_webhook_config(self,developer_id:str)->tuple[str,str]:
        logger.info(f"Obtaining webhook details for developer: {developer_id[:8]}")
        webhook_repo = WebhookRepo(self.redis)
        webhook_config = await webhook_repo.get_cache_data(developer_id)
        if not webhook_config:
            logger.info(f"Developer:{developer_id[:8]} | Cache Miss. Checking Auth Service..")
            response = await self.auth_grpc_client.look_up_webhook_config(developer_id)
            config = {
                "webhook_url" :response.webhook_url,
                "webhook_secret" : response.webhook_secret
            }
            await webhook_repo.cache_webhook_config(developer_id,metadata=config)
            return await self.get_webhook_config(developer_id)
        logger.info(f"Developer: {developer_id[:8]}| Cache hit. Webhook configurations found")
        logger.debug(f"{webhook_config}")
        return (webhook_config.get("webhook_url",None), webhook_config.get("webhook_secret",None))


# async def main(developer_id:str):
#     redis = Redis(host="localhost", port=6379,decode_responses=True)
#     auth_grpc_client = AuthGrpcClient()
#     webhook_url,webhook_secret = await get_webhook_config(developer_id,redis,auth_grpc_client)
#     logger.debug(f"url: {webhook_url}, secet: {webhook_secret}")


# if __name__ == "__main__":
#     asyncio.run(main("031c4d73-238b-4562-80c6-19c0513fa689"))
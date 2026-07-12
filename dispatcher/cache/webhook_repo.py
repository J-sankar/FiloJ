from redis.asyncio import Redis
from shared.redis.cache_keys import (web_hook_config_key)
from datetime import datetime, timezone



def current_window() -> str:
    """Returns the current hourly window identifier, e.g. '2026-07-04T15'."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")
                                               
class WebhookRepo:
    def __init__(self,redis:Redis ):
        self.redis = redis

   


    
    async def cache_webhook_config(self, developer_id:str,metadata:dict,ttl:int=600):
        key = web_hook_config_key(developer_id)
        try:
            await self.redis.hset(key,mapping=metadata)
            await self.redis.expire(key,ttl)
        except Exception :
            raise 


    
    async def get_cache_data(self, developer_id:str):
        key = web_hook_config_key(developer_id)
        try:
            return await self.redis.hgetall(key)
        except Exception :
            raise 

    



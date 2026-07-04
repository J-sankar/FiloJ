from redis.asyncio import Redis
from redis.commands.core import AsyncScript
from shared.redis.cache_keys import (api_key_meta_key,api_key_usage_key)

RATE_LIMIT_SCRIPT = """
    local status = redis.call('HGET',KEYS[1], 'status')
    if status == false then return {-2, 0} end
    if status == 'revoked'then return {-1,0}end
    local limit = tonumber(redis.call('HGET', KEYS[1], 'request_per_hour'))
    local count = redis.call('INCR', KEYS[2])
    if count == 1 then redis.call('EXPIRE', KEYS[2], ARGV[1]) end 
    if count > limit return {0, count} end
    return {1,count}

"""


class ApiKeyRepo:
    def __init__(self,redis:Redis ):
        self.redis = redis
        self.RATE_LIMIT_SCRIPT:AsyncScript = redis.register_script(RATE_LIMIT_SCRIPT)

    async def check_and_increment(self,api_key:str,ttl:int = 3700) -> tuple[int,int] :
        try:
            result = await self.RATE_LIMIT_SCRIPT(script=self.RATE_LIMIT_SCRIPT,
                                           keys= [api_key_meta_key(api_key), api_key_usage_key(api_key),
                                                  ],
                                                  args=[ttl])
            return result[0], result[1]
        except Exception :
            raise 


    
    async def cache_metadata(self, api_key:str,metadata:dict,ttl:int=300):
        key = api_key_meta_key(api_key)
        try:
            await self.redis.hset(key,mapping=metadata)
            await self.redis.expire(key,ttl)
        except Exception :
            raise 


    
    async def get_cache_data(self, api_key:str):
        key = api_key_meta_key(api_key)
        try:
            return await self.redis.hgetall(key)
        except Exception :
            raise 

    



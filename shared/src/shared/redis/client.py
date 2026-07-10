import redis.asyncio as redis
from shared.logger import get_logger


logger = get_logger(__name__)



class RedisClient:
    def __init__(self, host: str, port: int, db: int = 0, password: str | None = None, max_connections: int = 50):
        self._pool = redis.ConnectionPool(
            host=host, port=port, db=db, password=password,
            decode_responses=True, max_connections=max_connections,
            socket_timeout=5, socket_connect_timeout=5, retry_on_timeout=True,
        )
        self.client = redis.Redis(connection_pool=self._pool)

    async def ping(self) -> bool:
        try:
            await self.client.ping()
            logger.info("Redis: Connected")
        except redis.RedisError as e:
            logger.error(f"Redis connection failed: {e}")
            raise e
        


    async def close(self):
        await self.client.aclose()
        await self._pool.aclose()
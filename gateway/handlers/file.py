from fastapi import Request,HTTPException,status

from gateway.handlers.base import ServiceHandler

from gateway.core.security import extract_bearer_headers,hash_key
from gateway.cache.api_key_repo import ApiKeyRepo
from shared.logger import get_logger

logger =get_logger(__name__)


class FileServiceHandler(ServiceHandler):
    def should_handle(self, path: str) -> bool:
        return True

    async def get_context(self, request: Request) -> tuple[str, str]:
        api_key = extract_bearer_headers(request)
        key_hash = hash_key(api_key)
        api_key_repo = ApiKeyRepo(redis=request.app.state.redis)

        result, count = await api_key_repo.check_and_increment(api_key=key_hash)
        if result == -2 :
                logger.info("Cache Miss: checking with auth service")
                response = await request.app.state.grpc_auth_client.look_up_api_key(key_hash)
                metadata = {
                    "status": response.status,  # could be "active" or "revoked" — cache either way
                    "developer_id": response.developer_id,
                    "api_key_id": response.api_key_id,
                    "plan": response.plan,
                    "requests_per_hour": response.requests_per_hour,
                    "max_file_size_bytes": response.max_file_size_bytes,
                    "storage_quota_bytes": response.storage_quota_bytes,
                }
                await api_key_repo.cache_metadata(key_hash, metadata)
                await self.get_context(request)
        if result == -1 :
                logger.warning("Api key inactive/revoked")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Api key inactive/revoked")
        if result == 0:
                logger.error("Rate Limit exceeded")
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="You have hit your plan limits, please retry later, or upgrade to a higher plan if using free plan")

        logger.info(f"Cache hit | result: {result}, request count: {count} in current window")
        cache_data = await api_key_repo.get_cache_data(key_hash)
        return cache_data.get("developer_id", None), cache_data.get("plan", None)
        
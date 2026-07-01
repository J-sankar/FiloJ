from shared.database import AsyncSession
from shared.logger import get_logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from auth_service.utils.auth import hash_api_key
from auth_service.models.auth import ApiKey
from auth_service.core.exceptions import InactiveApiKeyError,InactiveDeveloperError,InvalidApiKeyError

logger = get_logger(__name__)



async def validate_api_key(api_key:str,db:AsyncSession) :
    key_hash = hash_api_key(api_key)
    try:
        res = await db.execute(
                    select(ApiKey)
                    .options(selectinload(ApiKey.developer))
                    .where(ApiKey.key_hash == key_hash)
                )
        api_key = res.scalar_one_or_none()
        if not api_key:
            logger.warning("key not found")
            raise InvalidApiKeyError("Api key not found. Please check with the environment")
        if not api_key.is_active:
            logger.warning("Revoked/Access denied")
            raise InactiveApiKeyError("Revoked/Access Denied")
        developer = api_key.developer
        if not developer.is_active:
            raise InactiveDeveloperError("Developer inactive/revoked")
        return developer
    
    except Exception :
        raise 
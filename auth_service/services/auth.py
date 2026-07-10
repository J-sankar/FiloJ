from shared.database import AsyncSession
from shared.logger import get_logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from auth_service.models.auth import ApiKey,Developer
from auth_service.core.exceptions import InactiveDeveloperError,InvalidApiKeyError

logger = get_logger(__name__)



async def get_api_key_developer(key_hash:str,db:AsyncSession)-> tuple[Developer,str] :

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
        developer = api_key.developer
        if not developer.is_active:
            raise InactiveDeveloperError("Developer inactive/revoked")
        status = "active" if api_key.is_active else "revoked"
        return (developer,status)
    
    except Exception :
        raise 
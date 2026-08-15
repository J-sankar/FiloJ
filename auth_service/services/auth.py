from shared.database import AsyncSession
from shared.logger import get_logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from auth_service.models.auth import ApiKey,Developer
from auth_service.core.exceptions import InactiveDeveloperError,InvalidApiKeyError,DeveloperNotFoundError,WebhookConfigNotFoundError
import uuid
logger = get_logger(__name__)



async def get_api_key_developer(key_hash:str,db:AsyncSession)-> tuple[str,str] :

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

async def get_webhook_config(developer_id:str | uuid.UUID,db:AsyncSession)->tuple[str,str] :
    try :
        res = await db.execute(select(Developer).where(developer_id == Developer.id))
        developer = res.scalar_one_or_none()
        if not developer:
            logger.warning("Developer details not found")
            raise DeveloperNotFoundError("Developer not found")
        if not developer.is_active:
            raise InactiveDeveloperError("Developer inactive/revoked")
        webhook_url , webhook_secret = developer.webhook_url, developer.webhook_secret
        if not webhook_url or not webhook_secret:
            logger.warning("Webhook details not configured")
            raise WebhookConfigNotFoundError("Webhook details not configured, please do it in the dashboard")
        return webhook_url,webhook_secret
    except Exception :
        raise



async def create_webhook_config(developer_id:str|uuid.UUID,webhook_url:str,webhook_secret:str,db:AsyncSession) -> tuple[str,str] | None :
    try:
        developer_res = await db.execute(select(Developer).where(Developer.id ==  developer_id))
        developer = developer_res.scalar_one_or_none()
        if not developer:
            raise DeveloperNotFoundError(f"Developer {str(developer_id)[:8]} not found")
        developer.webhook_url = str(webhook_url)
        developer.webhook_secret = webhook_secret
        await db.commit()
        logger.info(f"Developer : {str(developer_id)[:8]} | webhook configured:")
        return developer.webhook_url,developer.webhook_secret
    except Exception:
        await db.rollback()
        raise

async def delete_webhook_config(
    developer_id: str | uuid.UUID,
    db: AsyncSession,
) -> None:
    developer_res = await db.execute(
        select(Developer).where(Developer.id == developer_id)
    )
    developer = developer_res.scalar_one_or_none()

    if developer is None:
        raise DeveloperNotFoundError(f"Developer {developer_id} not found")

    try:
        developer.webhook_url = None
        developer.webhook_secret = None
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception(f"Failed to delete webhook config for developer {str(developer_id)[:8]}")
        raise

    logger.info(f"Developer : {str(developer_id)[:8]} | webhook config deleted")



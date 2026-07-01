from fastapi.exceptions import HTTPException
from auth_service.schemas.api_key import (ApiKeyCreate,ApiKeyCreateResponse)
from auth_service.utils.auth import get_current_developer
from fastapi import APIRouter,Depends
from shared.database import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shared.logger import get_logger
from auth_service.models.auth import ApiKey
import secrets
import uuid
import hashlib


logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["apikey"])

@router.post("", response_model=ApiKeyCreateResponse)
async def create_apikey(
    body: ApiKeyCreate,x_developer_id : uuid.UUID = Depends(get_current_developer), db:AsyncSession = Depends(get_session)
) -> ApiKeyCreateResponse:
    key_name = body.name
    key_res = await db.execute(select(ApiKey).where(ApiKey.name == key_name, ApiKey.developer_id == x_developer_id))
    existing_key = key_res.scalar_one_or_none()

    if existing_key:
        logger.debug(existing_key.key_hash)
        raise HTTPException(403, "Api key already exists in this name")
    
    new_secret= secrets.token_urlsafe(32)
    env_tag = key_name.lower().replace(" ", "_")[:10]
    plain_key = f"FiloJ_{env_tag}_{new_secret}"
    logger.debug(plain_key)
    key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
    display_prefix = f"{env_tag}{'*'*18}"
    new_api_key = ApiKey(name = key_name, developer_id = x_developer_id,display_prefix=display_prefix,key_hash=key_hash )
    db.add(new_api_key)
    await db.commit()
    logger.info("Api key created")
    return ApiKeyCreateResponse(raw_key=plain_key)
    
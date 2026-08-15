import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from shared.database import get_session
from shared.logger import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.schemas.webhook import (
    WebhookConfigResponse,
    WebhookCreationRequest,
    WebhookCreationResponse,
    WebhookConfigDeletionRequest,
    WebhookConfigDeletionResponse

)
from auth_service.services.auth import create_webhook_config, get_webhook_config,delete_webhook_config as delete_config
from auth_service.utils.auth import get_current_developer

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["webhook"])


@router.post("", response_model=WebhookCreationResponse)
async def set_webhook_config(
    body: WebhookCreationRequest,
    x_developer_id: Annotated[uuid.UUID, Depends(get_current_developer)],
    db: Annotated[AsyncSession , Depends(get_session)],
):
    new_secret = secrets.token_urlsafe(32)
    env_tag = str(x_developer_id)[:8].lower().strip()
    plain_secret = f"Filo-J_{env_tag}_{new_secret}"
    webhook_url, webhook_secret = await create_webhook_config(
        x_developer_id, body.webhook_url, plain_secret, db
    )
    return WebhookCreationResponse(
        webhook_url=webhook_url, webhook_secret=webhook_secret
    )


@router.get("", response_model=WebhookConfigResponse)
async def obtain_webhook_config(
    body: WebhookCreationRequest,
    x_developer_id: Annotated[uuid.UUID, Depends(get_current_developer)],
    db: Annotated[AsyncSession,Depends(get_session)],
):
    webhook_url, webhook_secret = await get_webhook_config(x_developer_id, db)
    secure_secret = webhook_secret[:5].strip() + ("*") * 10
    return WebhookConfigResponse(webhook_url=webhook_url, webhook_secret=secure_secret)



@router.delete("",response_model=WebhookConfigDeletionResponse)
async def delete_webhook_config(
    x_developer_id: Annotated[uuid.UUID, Depends(get_current_developer)],
    db: Annotated[AsyncSession,Depends(get_session)],
):

        webhook_url, webhook_secret = await get_webhook_config(x_developer_id, db)
        if webhook_url is None:
            logger.warning("No webhook config found for developer %s", x_developer_id)
            raise HTTPException(status_code=404, detail="No webhook configuration found")

        await delete_config(developer_id=x_developer_id,db=db)
        logger.info("Successfully deleted webhook configurations")
        return WebhookConfigDeletionResponse()
        

    
    
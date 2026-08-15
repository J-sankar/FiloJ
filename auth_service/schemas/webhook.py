from pydantic import BaseModel, AnyHttpUrl

class WebhookCreationRequest(BaseModel):
    """Request Schema for webhook creation"""
    webhook_url: AnyHttpUrl

    

class WebhookCreationResponse(BaseModel):
    webhook_url: AnyHttpUrl
    webhook_secret: str
    message: str = "Copy the secret right now, this secret will not be displayed again"


class WebhookConfigResponse(BaseModel):
    """Response Schema for Webhook Configurations"""
    webhook_url: str
    webhook_secret: str



class WebhookConfigDeletionResponse(BaseModel):
    """Response schema for deleting Webhook for the developer"""
    success:bool = True
    message:str = "Successfully deleted webhook configuration"

class WebhookConfigDeletionRequest(BaseModel):
    """Response schema for deleting Webhook for the developer"""
    webhook_url:AnyHttpUrl  
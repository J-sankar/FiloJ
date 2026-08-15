from pydantic import BaseModel,ConfigDict
from datetime import datetime


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyCreateResponse(BaseModel):
    raw_key: str
    message:str = "Please copy the API Key to a secure place. This will not be displayed again"


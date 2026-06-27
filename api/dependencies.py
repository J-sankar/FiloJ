# auth_service/utils/dependencies.py
from fastapi import Request, HTTPException
import uuid
import os

env = os.getenv("ENV")
class DeveloperHeaders:
    def __init__(self, developer_id: str, plan: str):
        self.developer_id = developer_id
        self.plan         = plan

async def get_developer(request: Request) -> DeveloperHeaders:
    developer_id = request.headers.get("X-Developer-Id")
    plan         = request.headers.get("X-Developer-Plan")
    
    if env == "development":
        return  DeveloperHeaders(developer_id= uuid.uuid4(), plan= "BASIC")
    if not developer_id:
        raise HTTPException(401, "Unauthorized — missing developer id")
    if not plan:
        raise HTTPException(401, "Unauthorized — missing plan")

    # validate developer_id is a valid UUID
    try:
        uuid.UUID(developer_id)
    except ValueError:
        
        raise HTTPException(401, "Invalid developer id")

    return DeveloperHeaders(
        developer_id = developer_id,
        plan         = plan
    ) 
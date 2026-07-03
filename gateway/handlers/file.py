from fastapi import Request

from gateway.core.security import verify_api_key
from gateway.handlers.base import ServiceHandler


class FileServiceHandler(ServiceHandler):
    def should_handle(self, path: str) -> bool:
        return True

    async def get_context(self, request: Request) -> tuple[str, str]:
        response = await verify_api_key(request)
        return response.developer_id, response.plan
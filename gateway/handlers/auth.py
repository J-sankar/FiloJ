from fastapi import Request

from gateway.core.security import decode_token
from gateway.handlers.base import ServiceHandler


class AuthServiceHandler(ServiceHandler):
    def should_handle(self, path: str) -> bool:
        return path == "api/key"

    async def get_context(self, request: Request) -> tuple[str, str]:
        token = decode_token(request)
        return token.get("sub", ""), token.get("plan", "")
from fastapi import Request

from gateway.core.security import decode_token,extract_bearer_headers
from gateway.handlers.base import ServiceHandler


class AuthServiceHandler(ServiceHandler):
    def should_handle(self, path: str) -> bool:
        return path == "api/key"

    async def get_context(self, request: Request) -> tuple[str, str]:
        bearer_token = extract_bearer_headers(request)
        token = decode_token(bearer_token)
        return token.get("sub", ""), token.get("plan", "")
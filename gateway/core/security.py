from gateway.grpc_clients.auth_client import AuthGrpcClient
from fastapi import HTTPException, Request
from jose import JWTError, jwt

from gateway.core.config import settings
from shared.logger import get_logger

logger  = get_logger(__name__)


grpc_auth_client = AuthGrpcClient()

def decode_token(request:Request) :
    headers = request.headers
    auth_headers = headers.get("Authorization")
    if not auth_headers:
        logger.warning("No auth headers found")
        raise HTTPException(401,"No auth headers")
    parts = auth_headers.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(401, "Invalid Authorization header format")
    bearer_token = parts[1]
    try:
        token = jwt.decode(
            bearer_token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        logger.info("Token decoded")
        return token
    except JWTError as e:
        logger.error(f"ERROR while decoding token: {str(e).lower()}")
        raise HTTPException(401, "Invalid or expired token")




async def verify_api_key(request:Request):
    headers = request.headers
    auth_headers = headers.get("Authorization")
    if not auth_headers:
        logger.warning("No auth headers found")
        raise HTTPException(401,"No auth headers")
    parts = auth_headers.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(401, "Invalid Authorization header format")
    api_key = parts[1]
    if not api_key:
        raise HTTPException(401, "Api Key Missing")
    response = await grpc_auth_client.validate_key(api_key)

    return response 
   

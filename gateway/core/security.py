from fastapi import HTTPException, Request
from jose import JWTError, jwt

from gateway.core.config import settings
from shared.logger import get_logger
import hashlib
logger  = get_logger(__name__)





def extract_bearer_headers(request: Request) -> str :
    headers = request.headers
    auth_headers = headers.get("Authorization")
    if not auth_headers:
        logger.warning("No auth headers found")
        raise HTTPException(401,"No auth headers")
    parts = auth_headers.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(401, "Invalid Authorization header format")
    bearer_token = parts[1]
    return bearer_token

def decode_token(bearer_token:str) :
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





def hash_key(api_key:str)->str:
    return hashlib.sha256(api_key.encode()).hexdigest()
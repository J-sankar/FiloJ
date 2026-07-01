# auth_service/utils/auth.py
import os
import secrets
from datetime import datetime,timezone, timedelta
from fastapi import HTTPException, Request, Response,Header,status
from jose import JWTError, jwt
from passlib.context import CryptContext
import uuid
import hashlib

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET          = os.getenv("JWT_SECRET")
JWT_ALGORITHM       = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRY_MINUTES  = int(os.getenv("JWT_EXPIRY_MINUTES", 60))
REFRESH_EXPIRY_DAYS = int(os.getenv("REFRESH_EXPIRY_DAYS", 30))
IS_PROD             = os.getenv("ENV") == "production"
INTERNAL_SECRET     = os.getenv("INTERNAL_GATEWAY_SECRET")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(developer_id: str, plan: str) -> str:
    payload = {
        "sub":  developer_id,
        "plan": plan,
        "exp":  datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRY_MINUTES)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def set_refresh_cookie(response: Response, token: str):
    response.set_cookie(
        key      = "refresh_token",
        value    = token,
        httponly = True,
        secure   = IS_PROD,
        samesite = "lax",
        max_age  = 60 * 60 * 24 * REFRESH_EXPIRY_DAYS
    )

def clear_refresh_cookie(response: Response):
    response.delete_cookie(
        key      = "refresh_token",
        httponly = True,
        secure   = IS_PROD,
        samesite = "lax"
    )


def verify_internal_request(request: Request):
    secret = request.headers.get("X-Internal-Secret")
    if secret != INTERNAL_SECRET:
        raise HTTPException(403, "Direct access not allowed")
    


async def get_current_developer(
    # FastAPI automatically converts "X-User-ID" to a variable name, 
    # but using 'alias' ensures exact matching
    x_developer_id: str | None = Header(default=None, alias="X-Developer-ID")
) -> uuid.UUID:
    """
    Extracts the authenticated user's ID from the NGINX gateway header.
    """
    if not x_developer_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Missing User ID header. Are you bypassing the gateway?"
        )
    
    try:
        # Convert the string header back into a Python UUID object for your database
        return uuid.UUID(x_developer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid Developer ID format"
        )
    


def hash_api_key(api_key:str)->str:
    """Function to hash api key"""
    return hashlib.sha256(api_key.strip().encode()).hexdigest()
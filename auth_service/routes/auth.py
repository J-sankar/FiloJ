from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

from shared.database import get_session
from shared.logger import get_logger
from auth_service.models.auth import Developer, RefreshToken
from auth_service.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    MessageResponse,
)
from auth_service.utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    generate_refresh_token,
    decode_access_token,
    set_refresh_cookie,
    clear_refresh_cookie,
    REFRESH_EXPIRY_DAYS,
)

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["auth"])


# --- helper ---
async def issue_tokens(
    developer: Developer, db: AsyncSession, response: Response
) -> AuthResponse:

    try:
        access_token = create_access_token(str(developer.id), developer.plan)

        raw_refresh = generate_refresh_token()

        refresh = RefreshToken(
            token=raw_refresh,
            developer_id=developer.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_EXPIRY_DAYS),
        )
        db.add(refresh)
        await db.commit()

        set_refresh_cookie(response, raw_refresh)

        logger.info(f"Tokens issued for developer: {developer.email}")

        return AuthResponse(
            access_token=access_token,
            developer_id=str(developer.id),
            name=developer.name,
            plan=developer.plan,
        )
    except Exception:
        await db.rollback()
        raise


@router.post("/register", response_model=AuthResponse)
async def register(
    body: RegisterRequest, response: Response, db: AsyncSession = Depends(get_session)
):
    
    result = await db.execute(select(Developer).where(Developer.email == body.email))
    if result.scalar_one_or_none():
        logger.warning(f"Email already registered: {body.email}")
        raise HTTPException(400, "Email already registered")

    developer = Developer(
        name=body.name, email=body.email, password=hash_password(body.password)
    )
    db.add(developer)
    await db.flush()
    await db.refresh(developer)

    logger.info(f"New developer registered: {developer.email}")

    return await issue_tokens(developer, db, response)


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest, response: Response, db: AsyncSession = Depends(get_session)
):

    result = await db.execute(select(Developer).where(Developer.email == body.email))
    developer = result.scalar_one_or_none()

    if not developer or not verify_password(body.password, developer.password):

        raise HTTPException(401, "Invalid email or password")

    if not developer.is_active:
        raise HTTPException(403, "Account disabled")

    logger.info(f"Developer logged in: {developer.email}")

    return await issue_tokens(developer, db, response)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    response: Response,
    db: AsyncSession = Depends(get_session),
    refresh_token: str = Cookie(None),
):

    if not refresh_token:
        logger.warning("Refresh token not found")
        raise HTTPException(401, "No refresh token")

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == refresh_token)
    )
    token = result.scalar_one_or_none()

    if not token:
        logger.warning("Refresh token not found in db")
        raise HTTPException(401, "Invalid or expired refresh token")
    if token.is_revoked:
        logger.warning("Refresh token revoked")
        raise HTTPException(401, "Invalid or expired refresh token")
    if token.expires_at < datetime.now(timezone.utc):
        logger.warning("Refresh token expired")
        raise HTTPException(401, "Invalid or expired refresh token")

    result = await db.execute(
        select(Developer).where(Developer.id == token.developer_id)
    )
    developer = result.scalar_one_or_none()

    if not developer or not developer.is_active:
        logger.warning(f"Developer not found or inactive: {developer.email}")
        raise HTTPException(401, "Developer not found or inactive")

    token.is_revoked = True
    await db.commit()

    logger.info(f"Token refreshed for developer: {developer.email}")

    return await issue_tokens(developer, db, response)



@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_session),
    refresh_token: str = Cookie(None),
):

    if refresh_token:
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token == refresh_token)
        )
        token = result.scalar_one_or_none()
        if token:
            token.is_revoked = True
            await db.commit()

    clear_refresh_cookie(response)

    return MessageResponse(message="Logged out successfully")

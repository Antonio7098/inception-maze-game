import os
import httpx
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import lru_cache

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY", "")
APP_URL = os.getenv("APP_URL", "http://localhost:5173")

security = HTTPBearer()


@lru_cache()
def get_clerk_jwks_url() -> str:
    """Get Clerk JWKS URL from publishable key"""
    if not CLERK_PUBLISHABLE_KEY:
        raise ValueError("CLERK_PUBLISHABLE_KEY not set")

    if CLERK_PUBLISHABLE_KEY.startswith("pk_test_"):
        return "https://api.clerk.dev/v1/jwks"
    elif CLERK_PUBLISHABLE_KEY.startswith("pk_live_"):
        return "https://api.clerk.dev/v1/jwks"
    else:
        return "https://api.clerk.dev/v1/jwks"


async def verify_clerk_token(token: str) -> Dict[str, Any]:
    """Verify Clerk JWT token and return user info"""
    import jwt

    jwks_url = get_clerk_jwks_url()

    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url)
        response.raise_for_status()

    from jwt import PyJWKClient

    jwk_client = PyJWKClient(jwks_url)

    try:
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token, signing_key.key, algorithms=["RS256"], options={"verify_aud": False}
        )
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """Get current user from Clerk token"""
    token = credentials.credentials
    return await verify_clerk_token(token)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[Dict[str, Any]]:
    """Get current user if authenticated, otherwise None"""
    if not credentials:
        return None
    try:
        return await verify_clerk_token(credentials.credentials)
    except:
        return None


async def get_user_api_key(user_id: str, db_session) -> Optional[str]:
    """Get user's OpenRouter API key from database"""
    from db import User
    from sqlalchemy import select

    result = await db_session.execute(select(User).where(User.clerk_id == user_id))
    user = result.scalar_one_or_none()
    return user.openrouter_api_key if user else None


async def set_user_api_key(user_id: str, email: str, api_key: str, db_session) -> None:
    """Set user's OpenRouter API key in database"""
    from db import User
    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert

    result = await db_session.execute(select(User).where(User.clerk_id == user_id))
    user = result.scalar_one_or_none()

    if user:
        user.openrouter_api_key = api_key
    else:
        new_user = User(clerk_id=user_id, email=email, openrouter_api_key=api_key)
        db_session.add(new_user)

    await db_session.commit()

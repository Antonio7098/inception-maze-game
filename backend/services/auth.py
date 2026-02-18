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


async def get_user_api_key(clerk_id: str) -> Optional[str]:
    """Get user's OpenRouter API key from Clerk private metadata"""
    import httpx

    CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
    CLERK_API_URL = "https://api.clerk.com/v1"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CLERK_API_URL}/users/{clerk_id}/metadata",
            headers={"Authorization": f"Bearer {CLERK_SECRET_KEY}"},
        )
        if response.status_code == 200:
            metadata = response.json()
            return metadata.get("private_metadata", {}).get("openrouter_api_key")
    return None


async def set_user_api_key(clerk_id: str, api_key: str) -> None:
    """Set user's OpenRouter API key in Clerk private metadata"""
    import httpx

    CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
    CLERK_API_URL = "https://api.clerk.com/v1"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CLERK_API_URL}/users/{clerk_id}/metadata",
            headers={"Authorization": f"Bearer {CLERK_SECRET_KEY}"},
        )
        if response.status_code == 200:
            metadata = response.json()
            private_metadata = metadata.get("private_metadata", {})
            private_metadata["openrouter_api_key"] = api_key
            await client.patch(
                f"{CLERK_API_URL}/users/{clerk_id}/metadata",
                headers={
                    "Authorization": f"Bearer {CLERK_SECRET_KEY}",
                    "Content-Type": "application/json",
                },
                json={"private_metadata": private_metadata},
            )

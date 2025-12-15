"""
Authentication using Auth0 Organizations.
Each organization (college) = 1 Auth0 Organization.
"""
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
from functools import lru_cache

from app.config import settings

security = HTTPBearer(auto_error=False)


@lru_cache()
def get_jwks():
    """Get JWKS from Auth0 (cached)."""
    url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def decode_token(token: str) -> dict:
    """Decode and verify Auth0 JWT token."""
    try:
        jwks = get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        
        rsa_key = next(
            (key for key in jwks["keys"] if key["kid"] == unverified_header["kid"]), 
            None
        )
        
        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate signing key"
            )
        
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=settings.AUTH0_ALGORITHMS,
            audience=settings.AUTH0_API_AUDIENCE,
            issuer=settings.AUTH0_ISSUER,
        )
        
        return payload
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except httpx.HTTPStatusError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable"
        )


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Verify Auth0 JWT token from Bearer header."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )
    
    return decode_token(credentials.credentials)


async def get_auth0_user(payload: dict = Depends(verify_token)) -> dict:
    """
    Get user info from Auth0 token.
    Includes org_id from Auth0 Organizations.
    """
    org_id = payload.get("org_id")
    
    # For org-scoped endpoints, org_id is required
    # Auth0 includes org_id when user logs in via organization
    
    return {
        "sub": payload.get("sub"),
        "auth0_user_id": payload.get("sub"),
        "email": payload.get("email"),
        "email_verified": payload.get("email_verified", False),
        "org_id": org_id,  # Auth0 Organization ID
        "permissions": payload.get("permissions", []),
    }


async def get_user_from_bearer_token(authorization: str = Header(None)) -> dict:
    """
    Extract user from Authorization header.
    Used for endpoints that manually handle auth.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    token = authorization[7:]
    payload = decode_token(token)
    
    return {
        "sub": payload.get("sub"),
        "auth0_user_id": payload.get("sub"),
        "email": payload.get("email"),
        "email_verified": payload.get("email_verified", False),
        "org_id": payload.get("org_id"),
    }


# Backward compatibility aliases
async def get_current_user(payload: dict = Depends(verify_token)) -> dict:
    return await get_auth0_user(payload)

async def get_current_active_user(payload: dict = Depends(verify_token)) -> dict:
    return await get_auth0_user(payload)

"""Authentication and API key management."""

import secrets
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings

# API Key security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
http_bearer = HTTPBearer(auto_error=False)


async def verify_api_key(
    api_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(http_bearer),
) -> str:
    """
    Verify the provided API key from either X-API-Key header or Bearer token.
    
    Supports two authentication methods:
    1. X-API-Key header: X-API-Key: your-api-key
    2. Bearer token: Authorization: Bearer your-api-key
    
    Args:
        api_key: The API key from the X-API-Key header
        bearer: The Bearer token credentials from Authorization header
        
    Returns:
        The verified API key
        
    Raises:
        HTTPException: If the API key is invalid or missing
    """
    settings = get_settings()
    expected_key = settings.server_api_key or settings.ensure_api_key()
    
    # Get the key from either header or bearer
    provided_key = None
    auth_method = None
    
    if api_key:
        provided_key = api_key
        auth_method = "X-API-Key"
    elif bearer and bearer.credentials:
        provided_key = bearer.credentials
        auth_method = "Bearer"
    
    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing. Provide it in the X-API-Key header or as a Bearer token.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Use secrets.compare_digest for timing attack protection
    if not secrets.compare_digest(provided_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )
    
    return provided_key


def regenerate_api_key() -> str:
    """
    Generate and persist a new API key.
    
    Returns:
        The new API key
    """
    settings = get_settings()
    new_key = settings.generate_api_key()
    settings._persist_api_key(new_key)
    settings.server_api_key = new_key
    return new_key


async def optional_api_key(
    api_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(http_bearer),
) -> Optional[str]:
    """
    Optionally verify API key - for endpoints that don't require auth.
    
    Args:
        api_key: The API key from the X-API-Key header
        bearer: The Bearer token credentials from Authorization header
        
    Returns:
        The API key if provided and valid, None otherwise
    """
    # Get the key from either header or bearer
    provided_key = api_key or (bearer.credentials if bearer else None)
    
    if not provided_key:
        return None
    
    try:
        return await verify_api_key(api_key, bearer)
    except HTTPException:
        return None
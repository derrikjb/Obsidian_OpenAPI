"""Authentication and API key management."""

import secrets
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import get_settings

# API Key security scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify the provided API key.
    
    Args:
        api_key: The API key from the X-API-Key header
        
    Returns:
        The verified API key
        
    Raises:
        HTTPException: If the API key is invalid or missing
    """
    settings = get_settings()
    expected_key = settings.server_api_key or settings.ensure_api_key()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing. Provide it in the X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Use secrets.compare_digest for timing attack protection
    if not secrets.compare_digest(api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )
    
    return api_key


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


async def optional_api_key(api_key: str = Security(api_key_header)) -> str | None:
    """
    Optionally verify API key - for endpoints that don't require auth.
    
    Args:
        api_key: The API key from the X-API-Key header
        
    Returns:
        The API key if provided and valid, None otherwise
    """
    if not api_key:
        return None
    
    try:
        return await verify_api_key(api_key)
    except HTTPException:
        return None
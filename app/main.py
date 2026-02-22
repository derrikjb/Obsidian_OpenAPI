"""Main FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth import optional_api_key, regenerate_api_key, verify_api_key
from app.config import get_settings
from app.models import ApiKeyResponse, HealthResponse, HistoryResponse
from app.routers import directory_router, search_router, vault_router
from app.services.history import get_history_manager
from app.services.obsidian import ObsidianClient

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("=" * 50)
    logger.info("  Obsidian OpenAPI Server - Starting Up")
    logger.info("=" * 50)
    
    # Ensure API key exists
    api_key = settings.ensure_api_key()
    logger.info(f"Server API Key: {'*' * 20}...{api_key[-8:]}")
    logger.info(f"Server Port: {settings.obsidian_openapi_port}")
    logger.info(f"Obsidian API: {settings.obsidian_api_url}")
    
    # Check Obsidian connection
    async with ObsidianClient() as client:
        health = await client.check_health()
        if health["connected"]:
            logger.info(f"✓ Connected to Obsidian REST API")
            logger.info(f"  Plugin Version: {health.get('plugin_version', 'unknown')}")
            logger.info(f"  Obsidian Version: {health.get('obsidian_version', 'unknown')}")
        else:
            logger.warning("✗ Could not connect to Obsidian REST API")
            logger.warning(f"  Error: {health.get('error', 'Unknown error')}")
            logger.warning("  The server will start, but tools may not work until Obsidian is running.")
    
    logger.info("=" * 50)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Obsidian OpenAPI Server...")


# Create FastAPI application
app = FastAPI(
    title="Obsidian OpenAPI Server",
    description="""
    A modern OpenAPI Tool Server for Obsidian integration.
    
    This server provides REST API endpoints to interact with your Obsidian vault
    through the Local REST API plugin. All endpoints (except health check) require
    authentication via the X-API-Key header.
    
    ## Authentication
    
    All endpoints except `/health` require an API key passed in the header:
    ```
    X-API-Key: your-api-key-here
    ```
    
    ## Features
    
    - **Vault Operations**: Read, create, update, patch, and delete files
    - **Directory Operations**: List vault contents
    - **Search**: Simple text search and advanced Dataview/JsonLogic queries
    - **History Tracking**: Optional rollback capability for write operations
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS - use the property to ensure it's always a list
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (no prefix - routers define full paths)
app.include_router(vault_router)
app.include_router(directory_router)
app.include_router(search_router)


@app.middleware("http")
async def log_requests(request, call_next):
    """Log all incoming requests for debugging."""
    logger.debug(f"Incoming request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.debug(f"Response: {response.status_code}")
    return response


@app.get(
    "/openapi.json",
    include_in_schema=False,
)
async def openapi_spec():
    """
    Serve OpenAPI spec without authentication.
    Required for Open WebUI to discover tools.
    """
    from fastapi.openapi.utils import get_openapi
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )


@app.get(
    "//openapi.json",
    include_in_schema=False,
)
async def openapi_spec_double_slash():
    """
    Handle double slash URL (Open WebUI with trailing slash).
    Redirects to the correct endpoint.
    """
    from fastapi.openapi.utils import get_openapi
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check server health and Obsidian connection status.",
    tags=["System"],
)
async def health_check():
    """
    Health check endpoint.
    
    Returns server status and Obsidian connection information.
    No authentication required.
    """
    async with ObsidianClient() as client:
        health = await client.check_health()
    
    return HealthResponse(
        status="healthy",
        obsidian_connected=health["connected"],
        obsidian_version=health.get("obsidian_version"),
        plugin_version=health.get("plugin_version"),
        timestamp=datetime.utcnow(),
    )


@app.post(
    "/auth/regenerate-key",
    response_model=ApiKeyResponse,
    summary="Regenerate API key",
    description="Generate a new API key. Requires current key or if ENABLE_KEY_REGENERATION is true.",
    tags=["System"],
)
async def regenerate_key(api_key: str = Depends(verify_api_key)):
    """
    Regenerate the API key.
    
    Requires the current valid API key. The new key will be returned
    **only once** - save it securely!
    
    Requires ENABLE_KEY_REGENERATION=true in environment or existing API key.
    """
    if not settings.enable_key_regeneration:
        return JSONResponse(
            status_code=403,
            content={
                "detail": "Key regeneration is disabled. Set ENABLE_KEY_REGENERATION=true to enable."
            },
        )
    
    new_key = regenerate_api_key()
    logger.info("API key regenerated")
    
    return ApiKeyResponse(api_key=new_key)


@app.get(
    "/history",
    response_model=HistoryResponse,
    summary="Get operation history",
    description="Get history of write operations for potential rollback.",
    tags=["System"],
)
async def get_history(
    limit: int = 50,
    api_key: str = Depends(verify_api_key),
):
    """
    Get the history of write operations.
    
    Returns a list of recent create, append, patch, and delete operations
    that can potentially be reverted. Requires MAX_HISTORY_ENTRIES > 0.
    
    - **limit**: Maximum number of operations to return
    """
    history = get_history_manager()
    operations = history.get_history(limit=limit)
    
    return HistoryResponse(
        operations=operations,
        total=len(operations),
        max_entries=settings.max_history_entries,
    )


@app.delete(
    "/history",
    summary="Clear operation history",
    description="Clear all operation history.",
    tags=["System"],
)
async def clear_history(api_key: str = Depends(verify_api_key)):
    """Clear all operation history."""
    history = get_history_manager()
    history.clear_history()
    logger.info("Operation history cleared")
    
    return {"message": "Operation history cleared successfully"}


@app.get(
    "/",
    summary="Server info",
    description="Get basic server information.",
    tags=["System"],
)
async def root():
    """Get server information."""
    return {
        "name": "Obsidian OpenAPI Server",
        "version": "1.0.0",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
        "health_url": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.obsidian_openapi_host,
        port=settings.obsidian_openapi_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
"""API route handlers."""

from app.routers.vault import router as vault_router
from app.routers.directory import router as directory_router
from app.routers.search import router as search_router

__all__ = ["vault_router", "directory_router", "search_router"]
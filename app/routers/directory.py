"""Directory operations router."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import verify_api_key
from app.models import VaultDirectoryListing
from app.services.obsidian import ObsidianClient

router = APIRouter(tags=["Directory"])


@router.get(
    "/vault/",
    response_model=VaultDirectoryListing,
    summary="List vault contents",
    description="List files and directories in the vault root or a specific directory.",
)
async def list_directory(
    path: str = Query(default="/", description="Directory path to list (use '/' for vault root)"),
    api_key: str = Depends(verify_api_key),
):
    """
    List files and directories in the vault.
    
    - **path**: Directory path to list (use '/' for vault root)
    
    Returns a list of files and directories. Directories end with a trailing slash.
    """
    async with ObsidianClient() as client:
        try:
            result = await client.list_directory(path)
            return VaultDirectoryListing(
                path=result["path"],
                files=result["files"],
                total=result["total"],
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list directory: {str(e)}",
            )

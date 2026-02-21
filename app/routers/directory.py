"""Directory operations router."""

from fastapi import APIRouter, Depends, Query

from app.auth import verify_api_key
from app.models import VaultDirectoryListing, VaultFile
from app.services.obsidian import ObsidianClient

router = APIRouter(prefix="/vault", tags=["Directory"])


@router.get(
    "",
    response_model=VaultDirectoryListing,
    summary="List vault contents",
    description="List files and directories in the vault or a specific directory.",
)
async def list_directory(
    path: str = Query(
        default="/",
        description="Directory path to list (default: vault root)",
    ),
    api_key: str = Depends(verify_api_key),
):
    """
    List files and directories in the vault.
    
    - **path**: Directory path to list (use '/' for vault root)
    
    Returns a list of files and directories with metadata including:
    - name: File or directory name
    - path: Full path within vault
    - is_directory: Whether this is a directory
    - extension: File extension (for files)
    - size: File size in bytes (for files)
    - modified: Last modification timestamp
    """
    async with ObsidianClient() as client:
        result = await client.list_directory(path)
        
        files = [
            VaultFile(
                path=f["path"],
                name=f["name"],
                is_directory=f["is_directory"],
                extension=f.get("extension"),
                size=f.get("size"),
                modified=f.get("modified"),
            )
            for f in result["files"]
        ]
        
        return VaultDirectoryListing(
            path=result["path"],
            files=files,
            total=result["total"],
        )
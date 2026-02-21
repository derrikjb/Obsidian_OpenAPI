"""Vault file operations router."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.auth import verify_api_key
from app.models import (
    FileAppendRequest,
    FileContent,
    FileCreateRequest,
    FileFormat,
    FilePatchRequest,
    OperationType,
)
from app.services.history import get_history_manager
from app.services.obsidian import ObsidianClient

router = APIRouter(prefix="/vault", tags=["Vault"])


@router.get(
    "/{path:path}",
    response_model=FileContent,
    summary="Get file content",
    description="Retrieve content from a vault file in various formats.",
)
async def get_file(
    path: str,
    format_type: FileFormat = Query(
        default=FileFormat.MARKDOWN,
        description="Content format: markdown (raw), json (parsed with metadata), or document-map (structure)"
    ),
    api_key: str = Depends(verify_api_key),
):
    """
    Get file content from the vault.
    
    - **path**: Path to the file within the vault
    - **format**: Output format (markdown, json, document-map)
    """
    async with ObsidianClient() as client:
        result = await client.get_file(path, format_type.value)
        return FileContent(
            path=result["path"],
            format=format_type,
            content=result["content"],
        )


@router.post(
    "/{path:path}",
    summary="Create or replace a file",
    description="Create a new file or completely replace an existing one.",
)
async def create_file(
    path: str,
    request: FileCreateRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Create a new file or replace an existing one.
    
    - **path**: Path for the new file
    - **content**: Markdown content to write
    - **overwrite**: If true, replace existing file; if false, fail if file exists
    """
    history = get_history_manager()
    
    async with ObsidianClient() as client:
        # Get previous content for history if overwriting
        previous_content = None
        if request.overwrite:
            try:
                existing = await client.get_file(path, "markdown")
                previous_content = existing.get("content")
            except Exception:
                pass  # File doesn't exist
        
        result = await client.create_file(
            path=path,
            content=request.content,
            overwrite=request.overwrite,
        )
        
        # Record operation
        history.record_operation(
            operation=OperationType.CREATE,
            path=path,
            previous_content=previous_content,
            new_content=request.content,
            metadata={"overwrite": request.overwrite},
        )
        
        return result


@router.patch(
    "/{path:path}/append",
    summary="Append to file",
    description="Append content to the end of an existing file.",
)
async def append_to_file(
    path: str,
    request: FileAppendRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Append content to an existing file.
    
    - **path**: Path to the file
    - **content**: Content to append
    - **add_newline**: Whether to add a newline before appending
    """
    history = get_history_manager()
    
    async with ObsidianClient() as client:
        # Get previous content for history
        try:
            existing = await client.get_file(path, "markdown")
            previous_content = existing.get("content")
        except Exception:
            previous_content = None
        
        content = request.content
        if request.add_newline and previous_content:
            content = "\n" + content
        
        result = await client.append_to_file(path=path, content=content)
        
        # Get new content for history
        try:
            new_file = await client.get_file(path, "markdown")
            new_content = new_file.get("content")
        except Exception:
            new_content = None
        
        # Record operation
        history.record_operation(
            operation=OperationType.APPEND,
            path=path,
            previous_content=previous_content,
            new_content=new_content,
        )
        
        return result


@router.patch(
    "/{path:path}",
    summary="Patch file content",
    description="Partially update a file (heading, block, frontmatter, or content).",
)
async def patch_file(
    path: str,
    request: FilePatchRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Partially update a file without rewriting the entire content.
    
    - **operation**: append, prepend, or replace
    - **target**: heading, block, frontmatter, or content
    - **target_value**: Identifier (heading path, block ID, frontmatter key, or content selector)
    - **content**: New content to insert
    """
    history = get_history_manager()
    
    async with ObsidianClient() as client:
        # Get previous content for history
        try:
            existing = await client.get_file(path, "markdown")
            previous_content = existing.get("content")
        except Exception:
            previous_content = None
        
        result = await client.patch_file(
            path=path,
            operation=request.operation.value,
            target=request.target.value,
            target_value=request.target_value,
            content=request.content,
        )
        
        # Get new content for history
        try:
            new_file = await client.get_file(path, "markdown")
            new_content = new_file.get("content")
        except Exception:
            new_content = None
        
        # Record operation
        history.record_operation(
            operation=OperationType.PATCH,
            path=path,
            previous_content=previous_content,
            new_content=new_content,
            metadata={
                "operation": request.operation.value,
                "target": request.target.value,
                "target_value": request.target_value,
            },
        )
        
        return result


@router.delete(
    "/{path:path}",
    summary="Delete a file",
    description="Delete a file from the vault.",
)
async def delete_file(
    path: str,
    api_key: str = Depends(verify_api_key),
):
    """
    Delete a file from the vault.
    
    - **path**: Path to the file to delete
    """
    history = get_history_manager()
    
    async with ObsidianClient() as client:
        # Get content for history before deleting
        try:
            existing = await client.get_file(path, "markdown")
            previous_content = existing.get("content")
        except Exception:
            previous_content = None
        
        result = await client.delete_file(path=path)
        
        # Record operation
        history.record_operation(
            operation=OperationType.DELETE,
            path=path,
            previous_content=previous_content,
            metadata={"deleted": True},
        )
        
        return result
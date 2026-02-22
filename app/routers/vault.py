"""Vault file operations router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

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

router = APIRouter(tags=["Vault"])


@router.get(
    "/vault/{path:path}",
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
    # Prevent directory listing via this endpoint
    if not path or path.endswith("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path. Use /vault/ endpoint for directory listing.",
        )
    
    async with ObsidianClient() as client:
        try:
            result = await client.get_file(path, format_type.value)
            return FileContent(
                path=result["path"],
                format=format_type,
                content=result["content"],
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get file: {str(e)}",
            )


@router.post(
    "/vault/{path:path}",
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
    if not path or path.endswith("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path. Cannot create a directory.",
        )
    
    history = get_history_manager()
    
    async with ObsidianClient() as client:
        try:
            # Get previous content for history if overwriting
            previous_content = None
            if request.overwrite:
                try:
                    existing = await client.get_file(path, "markdown")
                    previous_content = existing.get("content")
                except HTTPException:
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
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create file: {str(e)}",
            )


@router.patch(
    "/vault/{path:path}",
    summary="Patch file content",
    description="""Partially update a file by inserting content at a specific location.
    
    This operation allows you to modify a file without rewriting the entire content.
    You can append, prepend, or replace content relative to headings, block references, or frontmatter fields.
    """,
)
async def patch_file(
    path: str,
    request: FilePatchRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Partially update a file without rewriting the entire content.
    
    ## Target Types
    
    The Obsidian API supports three target types for patch operations:
    
    - **heading**: Target a specific heading in the document
      - Use the heading text as `target_value` (e.g., "My Section" or "## My Section")
      - For nested headings, use the full path (e.g., "Parent::Child::Grandchild")
    
    - **block**: Target a block reference
      - Use the block ID as `target_value` (e.g., "block-id-123")
      - Block IDs are typically formatted as `^block-id` in Obsidian
    
    - **frontmatter**: Target a frontmatter field
      - Use the field name as `target_value` (e.g., "title", "tags", "date")
      - Only works with YAML frontmatter at the top of the file
    
    ## Operations
    
    - **append**: Add content after the target
    - **prepend**: Add content before the target
    - **replace**: Replace the target content entirely
    
    ## Examples
    
    **Append after a heading:**
    ```json
    {
      "operation": "append",
      "target": "heading",
      "target_value": "Notes",
      "content": "\\n- New note item"
    }
    ```
    
    **Add to frontmatter:**
    ```json
    {
      "operation": "replace",
      "target": "frontmatter",
      "target_value": "status",
      "content": "completed"
    }
    ```
    
    **Append to a block:**
    ```json
    {
      "operation": "append",
      "target": "block",
      "target_value": "meeting-notes",
      "content": " Additional context here."
    }
    ```
    """
    if not path or path.endswith("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path.",
        )
    
    history = get_history_manager()
    
    async with ObsidianClient() as client:
        try:
            # Get previous content for history
            try:
                existing = await client.get_file(path, "markdown")
                previous_content = existing.get("content")
            except HTTPException:
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
            except HTTPException:
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
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to patch file: {str(e)}",
            )


@router.delete(
    "/vault/{path:path}",
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
    if not path or path.endswith("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path. Use directory endpoints for directories.",
        )
    
    history = get_history_manager()
    
    async with ObsidianClient() as client:
        try:
            # Get content for history before deleting
            try:
                existing = await client.get_file(path, "markdown")
                previous_content = existing.get("content")
            except HTTPException:
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
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete file: {str(e)}",
            )

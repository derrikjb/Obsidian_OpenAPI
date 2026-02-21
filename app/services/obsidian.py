"""Obsidian REST API client."""

import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx
from fastapi import HTTPException, status

from app.config import get_settings


class ObsidianClient:
    """Async client for Obsidian Local REST API."""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.obsidian_api_url.rstrip("/")
        self.api_key = settings.obsidian_api_key
        self.timeout = settings.request_timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        """Initialize the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
            )

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self):
        """Ensure client is connected."""
        if self._client is None:
            raise RuntimeError("Client not connected. Use 'async with' or call connect()")

    def _encode_path(self, path: str) -> str:
        """URL-encode a vault path."""
        return quote(path, safe="")

    async def check_health(self) -> Dict[str, Any]:
        """Check connection to Obsidian API."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                data = response.json()
                return {
                    "connected": True,
                    "obsidian_version": data.get("obsidianVersion"),
                    "plugin_version": data.get("pluginVersion"),
                }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
            }

    # ==================== File Operations ====================

    async def get_file(
        self, path: str, format_type: str = "markdown"
    ) -> Dict[str, Any]:
        """Get file content."""
        self._ensure_client()
        encoded_path = self._encode_path(path)
        
        params = {}
        if format_type == "json":
            params["format"] = "json"
        elif format_type == "document-map":
            params["format"] = "content-map"

        response = await self._client.get(f"/vault/{encoded_path}", params=params)
        
        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {path}",
            )
        
        response.raise_for_status()
        
        content = response.text
        
        # Try to parse as JSON if format is json
        if format_type == "json":
            try:
                content = response.json()
            except json.JSONDecodeError:
                pass

        return {
            "path": path,
            "format": format_type,
            "content": content,
        }

    async def create_file(
        self, path: str, content: str, overwrite: bool = False
    ) -> Dict[str, Any]:
        """Create or replace a file."""
        self._ensure_client()
        encoded_path = self._encode_path(path)

        if overwrite:
            # Use PUT to overwrite
            response = await self._client.put(
                f"/vault/{encoded_path}",
                content=content,
                headers={"Content-Type": "text/markdown"},
            )
        else:
            # Use POST to create (fails if exists)
            response = await self._client.post(
                f"/vault/{encoded_path}",
                content=content,
                headers={"Content-Type": "text/markdown"},
            )

        if response.status_code == 400 and not overwrite:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"File already exists: {path}. Use overwrite=true to replace.",
            )

        response.raise_for_status()

        return {
            "path": path,
            "created": True,
            "message": f"File created successfully: {path}",
        }

    async def append_to_file(self, path: str, content: str) -> Dict[str, Any]:
        """Append content to a file."""
        self._ensure_client()
        encoded_path = self._encode_path(path)

        # First, get current content if file exists
        try:
            current = await self.get_file(path, "markdown")
            current_content = current["content"]
            if isinstance(current_content, str) and not current_content.endswith("\n"):
                content = "\n" + content
        except HTTPException:
            # File doesn't exist, will create it
            pass

        response = await self._client.post(
            f"/vault/{encoded_path}",
            content=content,
            headers={"Content-Type": "text/markdown"},
        )

        # If file doesn't exist, create it
        if response.status_code == 404:
            return await self.create_file(path, content, overwrite=False)

        response.raise_for_status()

        return {
            "path": path,
            "appended": True,
            "message": f"Content appended to: {path}",
        }

    async def patch_file(
        self,
        path: str,
        operation: str,
        target: str,
        target_value: str,
        content: str,
    ) -> Dict[str, Any]:
        """Patch a file (heading, block, frontmatter, or content)."""
        self._ensure_client()
        encoded_path = self._encode_path(path)

        # Build the patch body
        patch_body = {
            "operation": operation,  # append, prepend, replace
            "target": target,  # heading, block, frontmatter, content
            "targetValue": target_value,
            "content": content,
        }

        response = await self._client.patch(
            f"/vault/{encoded_path}",
            json=patch_body,
        )

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {path}",
            )

        response.raise_for_status()

        return {
            "path": path,
            "patched": True,
            "message": f"File patched successfully: {path}",
        }

    async def delete_file(self, path: str) -> Dict[str, Any]:
        """Delete a file."""
        self._ensure_client()
        encoded_path = self._encode_path(path)

        response = await self._client.delete(f"/vault/{encoded_path}")

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {path}",
            )

        response.raise_for_status()

        return {
            "path": path,
            "deleted": True,
            "message": f"File deleted successfully: {path}",
        }

    # ==================== Directory Operations ====================

    async def list_directory(self, path: str = "/") -> Dict[str, Any]:
        """List files and directories."""
        self._ensure_client()
        encoded_path = self._encode_path(path)

        response = await self._client.get(f"/vault/{encoded_path}")

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Directory not found: {path}",
            )

        response.raise_for_status()

        data = response.json()
        files = []

        for item in data.get("files", []):
            files.append({
                "path": item.get("path", ""),
                "name": item.get("name", ""),
                "is_directory": item.get("type") == "directory",
                "extension": item.get("extension"),
                "size": item.get("size"),
                "modified": item.get("mtime"),
            })

        return {
            "path": path,
            "files": files,
            "total": len(files),
        }

    # ==================== Search Operations ====================

    async def simple_search(
        self, query: str, path: Optional[str] = None, limit: int = 50
    ) -> Dict[str, Any]:
        """Perform a simple text search."""
        self._ensure_client()

        # The Obsidian API doesn't have a built-in simple search endpoint
        # We'll implement a basic search by listing files and searching content
        # For production, you might want to use the Dataview plugin or implement indexing
        
        search_results = []
        
        try:
            # Try using the Obsidian search endpoint if available
            params = {"query": query, "limit": limit}
            if path:
                params["path"] = path
                
            response = await self._client.get("/search", params=params)
            
            if response.status_code == 200:
                data = response.json()
                for result in data.get("results", []):
                    search_results.append({
                        "path": result.get("path", ""),
                        "score": result.get("score", 0.0),
                        "context": result.get("context"),
                        "matches": result.get("matches", []),
                    })
            else:
                # Fallback: search through files manually (slower)
                search_results = await self._manual_search(query, path, limit)
                
        except Exception:
            # Fallback to manual search
            search_results = await self._manual_search(query, path, limit)

        return {
            "query": query,
            "results": search_results,
            "total": len(search_results),
        }

    async def _manual_search(
        self, query: str, path: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        """Manual search through files (fallback)."""
        results = []
        
        # List all files
        listing = await self.list_directory(path or "/")
        files = [f for f in listing.get("files", []) if not f.get("is_directory")]
        
        query_lower = query.lower()
        
        for file_info in files[:100]:  # Limit to first 100 files for performance
            try:
                file_data = await self.get_file(file_info["path"], "markdown")
                content = file_data.get("content", "")
                
                if isinstance(content, str) and query_lower in content.lower():
                    # Find context around match
                    idx = content.lower().find(query_lower)
                    start = max(0, idx - 100)
                    end = min(len(content), idx + len(query) + 100)
                    context = content[start:end]
                    
                    results.append({
                        "path": file_info["path"],
                        "score": 1.0,
                        "context": context,
                        "matches": [{"start": idx, "end": idx + len(query)}],
                    })
                    
                    if len(results) >= limit:
                        break
                        
            except Exception:
                continue
        
        return results

    async def advanced_search(
        self,
        query_type: str,
        query: Any,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Perform an advanced search (Dataview DQL or JsonLogic)."""
        self._ensure_client()

        search_body = {
            "type": query_type,
            "query": query,
            "limit": limit,
        }

        response = await self._client.post("/search", json=search_body)

        if response.status_code == 404:
            # Advanced search might not be available
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Advanced search endpoint not available. Ensure Dataview plugin is installed.",
            )

        response.raise_for_status()

        data = response.json()
        
        return {
            "query_type": query_type,
            "query": query,
            "results": data.get("results", []),
            "total": data.get("total", 0),
        }
"""Obsidian REST API client."""

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
        # Remove leading slash if present for encoding
        path = path.lstrip("/")
        return quote(path, safe="/")

    def _normalize_directory_path(self, path: str) -> str:
        """Normalize directory path for Obsidian API.
        
        The Obsidian API expects:
        - Root: "/vault/" (trailing slash required)
        - Subdirectory: "/vault/{path}/" (trailing slash required)
        """
        if not path or path == "/":
            return "/vault/"
        
        # Remove leading slash if present
        path = path.lstrip("/")
        
        # Ensure trailing slash
        if not path.endswith("/"):
            path += "/"
        
        return f"/vault/{path}"

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
                
                # Get versions from nested 'versions' object or top level
                versions = data.get("versions", {})
                
                # Try nested versions first, then top level
                obsidian_version = (
                    versions.get("obsidian")
                    or data.get("obsidianVersion") 
                    or data.get("obsidian") 
                    or data.get("version")
                )
                
                # Plugin version is 'self' in the Obsidian API
                plugin_version = (
                    versions.get("self")
                    or versions.get("plugin")
                    or data.get("pluginVersion")
                    or data.get("plugin")
                    or data.get("apiVersion")
                )
                
                return {
                    "connected": True,
                    "obsidian_version": obsidian_version,
                    "plugin_version": plugin_version,
                    "raw_response": data,
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
        
        # Handle path normalization - files don't have trailing slash
        path = path.lstrip("/")
        encoded_path = self._encode_path(path)

        # Build headers based on format
        headers = {}
        if format_type == "json":
            headers["Accept"] = "application/vnd.olrapi.note+json"
        elif format_type == "document-map":
            headers["Accept"] = "application/vnd.olrapi.document-map+json"
        else:
            headers["Accept"] = "text/markdown"

        try:
            response = await self._client.get(
                f"/vault/{encoded_path}",
                headers=headers,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to Obsidian API: {str(e)}",
            )
        
        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {path}",
            )
        
        response.raise_for_status()
        
        # Return appropriate content based on format
        if format_type in ["json", "document-map"]:
            try:
                content = response.json()
            except Exception:
                content = response.text
        else:
            content = response.text

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
        
        path = path.lstrip("/")
        encoded_path = self._encode_path(path)

        try:
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
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to Obsidian API: {str(e)}",
            )

        if response.status_code == 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bad request: {response.text}",
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
        
        path = path.lstrip("/")
        encoded_path = self._encode_path(path)

        try:
            response = await self._client.post(
                f"/vault/{encoded_path}",
                content=content,
                headers={"Content-Type": "text/markdown"},
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to Obsidian API: {str(e)}",
            )

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
        
        path = path.lstrip("/")
        encoded_path = self._encode_path(path)

        # Build headers for patch operation
        headers = {
            "Operation": operation,
            "Target-Type": target,
            "Target": target_value,
        }

        try:
            response = await self._client.patch(
                f"/vault/{encoded_path}",
                content=content,
                headers=headers,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to Obsidian API: {str(e)}",
            )

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {path}",
            )
        
        if response.status_code == 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bad request: {response.text}",
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
        
        path = path.lstrip("/")
        encoded_path = self._encode_path(path)

        try:
            response = await self._client.delete(f"/vault/{encoded_path}")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to Obsidian API: {str(e)}",
            )

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {path}",
            )
        
        if response.status_code == 405:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail=f"Cannot delete: path is a directory, not a file",
            )

        response.raise_for_status()

        return {
            "path": path,
            "deleted": True,
            "message": f"File deleted successfully: {path}",
        }

    # ==================== Directory Operations ====================

    async def list_directory(self, path: str = "/") -> Dict[str, Any]:
        """List files and directories.
        
        The Obsidian Local REST API returns {"files": [...]} where each item
        is a string path. Directories end with a trailing slash.
        """
        self._ensure_client()
        
        # Normalize the path for the API
        api_path = self._normalize_directory_path(path)

        try:
            response = await self._client.get(api_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to Obsidian API: {str(e)}",
            )

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Directory not found: {path}",
            )

        response.raise_for_status()

        try:
            data = response.json()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid JSON response from Obsidian API: {str(e)}",
            )
        
        # Obsidian API returns {"files": ["file.md", "directory/", ...]}
        files = data.get("files", [])
        
        if not isinstance(files, list):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid response format from Obsidian API: expected 'files' to be a list",
            )

        return {
            "path": path,
            "files": files,
            "total": len(files),
        }

    # ==================== Search Operations ====================

    async def simple_search(
        self, query: str, context_length: int = 100
    ) -> Dict[str, Any]:
        """Perform a simple text search using the Obsidian API.
        
        Uses POST /search/simple/ endpoint.
        """
        self._ensure_client()

        params = {
            "query": query,
            "contextLength": context_length,
        }

        try:
            response = await self._client.post("/search/simple/", params=params)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to Obsidian API: {str(e)}",
            )
        
        if response.status_code == 404:
            # Endpoint not available - try manual search as fallback
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Simple search endpoint not available in your Obsidian Local REST API version",
            )

        response.raise_for_status()

        try:
            data = response.json()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid JSON response from Obsidian API: {str(e)}",
            )

        # Transform response to match our model
        results = []
        for item in data:
            matches = []
            for match in item.get("matches", []):
                matches.append({
                    "match": {
                        "start": match.get("match", {}).get("start", 0),
                        "end": match.get("match", {}).get("end", 0),
                    },
                    "context": match.get("context", ""),
                })
            
            results.append({
                "filename": item.get("filename", ""),
                "score": item.get("score", 0.0),
                "matches": matches,
            })

        return {
            "query": query,
            "results": results,
            "total": len(results),
        }

    async def advanced_search(
        self,
        query_type: str,
        query: Any,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Perform an advanced search (Dataview DQL or JsonLogic).
        
        Uses POST /search/ endpoint.
        """
        self._ensure_client()

        # Determine content type based on query type
        if query_type == "dataview":
            content_type = "application/vnd.olrapi.dataview.dql+txt"
            body = query if isinstance(query, str) else str(query)
        elif query_type == "jsonlogic":
            content_type = "application/vnd.olrapi.jsonlogic+json"
            import json
            body = json.dumps(query) if isinstance(query, dict) else str(query)
        else:
            content_type = "application/json"
            body = str(query)

        try:
            response = await self._client.post(
                "/search/",
                content=body,
                headers={"Content-Type": content_type},
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to Obsidian API: {str(e)}",
            )

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Advanced search endpoint not available. Ensure Dataview plugin is installed.",
            )
        
        if response.status_code == 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bad request: {response.text}",
            )

        response.raise_for_status()

        try:
            data = response.json()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid JSON response from Obsidian API: {str(e)}",
            )
        
        # Transform response to match our model
        results = []
        for item in data:
            results.append({
                "filename": item.get("filename", ""),
                "result": item.get("result"),
            })
        
        return {
            "query_type": query_type,
            "query": query,
            "results": results,
            "total": len(results),
        }

"""Search operations router."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import verify_api_key
from app.models import (
    AdvancedSearchRequest,
    AdvancedSearchResponse,
    SearchType,
    SimpleSearchResponse,
)
from app.services.obsidian import ObsidianClient

router = APIRouter(tags=["Search"])


@router.post(
    "/search/simple/",
    response_model=SimpleSearchResponse,
    summary="Simple text search",
    description="Search for text content across vault files using simple text matching.",
)
async def simple_search(
    query: str,
    context_length: int = 100,
    api_key: str = Depends(verify_api_key),
):
    """
    Perform a simple text search across vault files.
    
    - **query**: Text to search for
    - **context_length**: Amount of context around matches (default: 100 characters)
    
    Returns search results with file paths, relevance scores, and context snippets.
    """
    async with ObsidianClient() as client:
        try:
            result = await client.simple_search(
                query=query,
                context_length=context_length,
            )
            return SimpleSearchResponse(
                query=result["query"],
                results=result["results"],
                total=result["total"],
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Search failed: {str(e)}",
            )


@router.post(
    "/search/",
    response_model=AdvancedSearchResponse,
    summary="Advanced search",
    description="Advanced search using Dataview DQL or JsonLogic queries.",
)
async def advanced_search(
    request: AdvancedSearchRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Perform an advanced search using Dataview DQL or JsonLogic.
    
    **Dataview DQL Example:**
    ```json
    {
      "query_type": "dataview",
      "query": "TABLE file.mtime FROM #project WHERE status = 'active'",
      "limit": 50
    }
    ```
    
    **JsonLogic Example:**
    ```json
    {
      "query_type": "jsonlogic",
      "query": {
        "and": [
          {"in": ["project", {"var": "tags"}]},
          {"==": [{"var": "status"}, "active"]}
        ]
      },
      "limit": 50
    }
    ```
    
    Requires the Dataview plugin to be installed in Obsidian.
    """
    async with ObsidianClient() as client:
        try:
            result = await client.advanced_search(
                query_type=request.query_type.value,
                query=request.query,
                limit=request.limit,
            )
            return AdvancedSearchResponse(
                query_type=SearchType(result["query_type"]),
                query=result["query"],
                results=result["results"],
                total=result["total"],
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Advanced search failed: {str(e)}",
            )

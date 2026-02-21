"""Search operations router."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.auth import verify_api_key
from app.models import (
    AdvancedSearchRequest,
    AdvancedSearchResponse,
    SearchResult,
    SimpleSearchResponse,
    SearchType,
)
from app.services.obsidian import ObsidianClient

router = APIRouter(prefix="/search", tags=["Search"])


@router.get(
    "",
    response_model=SimpleSearchResponse,
    summary="Simple text search",
    description="Search for text content across vault files.",
)
async def simple_search(
    query: str = Query(..., description="Search query text"),
    path: Optional[str] = Query(
        default=None,
        description="Limit search to specific directory path",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=1000,
        description="Maximum number of results",
    ),
    api_key: str = Depends(verify_api_key),
):
    """
    Perform a simple text search across vault files.
    
    - **query**: Text to search for
    - **path**: Optional directory path to limit search scope
    - **limit**: Maximum number of results to return (1-1000)
    
    Returns search results with file paths, relevance scores, and context snippets.
    """
    async with ObsidianClient() as client:
        result = await client.simple_search(
            query=query,
            path=path,
            limit=limit,
        )
        
        results = [
            SearchResult(
                path=r["path"],
                score=r["score"],
                context=r.get("context"),
                matches=r.get("matches", []),
            )
            for r in result["results"]
        ]
        
        return SimpleSearchResponse(
            query=result["query"],
            results=results,
            total=result["total"],
        )


@router.post(
    "/advanced",
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
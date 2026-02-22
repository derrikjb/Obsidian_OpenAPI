"""Pydantic models for request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


# ==================== Enums ====================

class FileFormat(str, Enum):
    """File content format options."""
    MARKDOWN = "markdown"
    JSON = "json"
    DOCUMENT_MAP = "document-map"


class PatchOperation(str, Enum):
    """Patch operation types."""
    APPEND = "append"
    PREPEND = "prepend"
    REPLACE = "replace"


class PatchTarget(str, Enum):
    """Patch target types."""
    HEADING = "heading"
    BLOCK = "block"
    FRONTMATTER = "frontmatter"
    CONTENT = "content"


class SearchType(str, Enum):
    """Advanced search query types."""
    DATAVIEW = "dataview"
    JSONLOGIC = "jsonlogic"


# ==================== Base Models ====================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    obsidian_connected: bool
    obsidian_version: Optional[str] = None
    plugin_version: Optional[str] = None
    timestamp: datetime
    server_version: str = "1.0.0"


class ApiKeyResponse(BaseModel):
    """API key response."""
    api_key: str
    message: str = "Keep this key secure. It will not be shown again."


# ==================== Directory Models ====================

class VaultDirectoryListing(BaseModel):
    """Vault directory listing response.
    
    The Obsidian Local REST API returns a simple array of strings
    where directories end with a trailing slash.
    """
    path: str
    files: List[str]
    total: int


# ==================== File Models ====================

class FileContent(BaseModel):
    """File content response."""
    path: str
    format: FileFormat
    content: Union[str, Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None


class FileCreateRequest(BaseModel):
    """File creation request."""
    content: str = Field(..., description="File content in markdown")
    overwrite: bool = Field(default=False, description="Overwrite if file exists")


class FileAppendRequest(BaseModel):
    """File append request."""
    content: str = Field(..., description="Content to append")
    add_newline: bool = Field(
        default=True, description="Add newline before appending"
    )


class FilePatchRequest(BaseModel):
    """File patch request."""
    operation: PatchOperation = Field(
        ..., description="Type of patch operation"
    )
    target: PatchTarget = Field(..., description="What to patch")
    target_value: str = Field(
        ..., description="Target identifier (heading path, block ID, or frontmatter key)"
    )
    content: str = Field(..., description="Content to insert")


# ==================== Search Models ====================

class SearchMatch(BaseModel):
    """Search match location."""
    start: int
    end: int


class SearchMatchDetail(BaseModel):
    """Search match with context."""
    match: SearchMatch
    context: str


class SearchResult(BaseModel):
    """Search result item."""
    filename: str = Field(..., description="Path to the matching file")
    score: float
    matches: List[SearchMatchDetail]


class SimpleSearchResponse(BaseModel):
    """Simple search response."""
    query: str
    results: List[SearchResult]
    total: int


class AdvancedSearchRequest(BaseModel):
    """Advanced search request."""
    query_type: SearchType = Field(..., description="Type of advanced query")
    query: Union[str, Dict[str, Any]] = Field(
        ..., description="Query (DQL string or JsonLogic object)"
    )
    limit: int = Field(default=50, ge=1, le=1000)

    @field_validator("query")
    @classmethod
    def validate_query(cls, v, info):
        """Validate query based on query type."""
        query_type = info.data.get("query_type")
        if query_type == SearchType.JSONLOGIC and isinstance(v, str):
            raise ValueError("JsonLogic queries must be an object, not a string")
        return v


class AdvancedSearchResult(BaseModel):
    """Advanced search result item."""
    filename: str = Field(..., description="Path to the matching file")
    result: Union[str, int, float, bool, List[Any], Dict[str, Any]]


class AdvancedSearchResponse(BaseModel):
    """Advanced search response."""
    query_type: SearchType
    query: Union[str, Dict[str, Any]]
    results: List[AdvancedSearchResult]
    total: int


# ==================== History Models ====================

class OperationType(str, Enum):
    """Types of write operations."""
    CREATE = "create"
    APPEND = "append"
    PATCH = "patch"
    DELETE = "delete"


class OperationRecord(BaseModel):
    """Record of a write operation."""
    id: str
    timestamp: datetime
    operation: OperationType
    path: str
    previous_content: Optional[str] = None
    new_content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HistoryResponse(BaseModel):
    """Operation history response."""
    operations: List[OperationRecord]
    total: int
    max_entries: int


class RevertRequest(BaseModel):
    """Revert operation request."""
    operation_id: str = Field(..., description="ID of operation to revert")
    create_backup: bool = Field(
        default=True, description="Create backup before reverting"
    )


class RevertResponse(BaseModel):
    """Revert operation response."""
    success: bool
    message: str
    restored_path: str
    backup_path: Optional[str] = None

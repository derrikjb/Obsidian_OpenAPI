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


# ==================== File Models ====================

class VaultFile(BaseModel):
    """Vault file/directory entry."""
    path: str
    name: str
    is_directory: bool
    extension: Optional[str] = None
    size: Optional[int] = None
    modified: Optional[datetime] = None


class VaultDirectoryListing(BaseModel):
    """Vault directory listing response."""
    path: str
    files: List[VaultFile]
    total: int


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

class SearchResult(BaseModel):
    """Search result item."""
    path: str
    score: float
    context: Optional[str] = None
    matches: List[Dict[str, Any]] = Field(default_factory=list)


class SimpleSearchRequest(BaseModel):
    """Simple text search request."""
    query: str = Field(..., description="Search query")
    path: Optional[str] = Field(
        default=None, description="Limit search to specific path"
    )
    limit: int = Field(default=50, ge=1, le=1000)
    context_length: int = Field(default=200, ge=50, le=1000)


class SimpleSearchResponse(BaseModel):
    """Simple search response."""
    query: str
    results: List[SearchResult]
    total: int
    search_time_ms: Optional[float] = None


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


class AdvancedSearchResponse(BaseModel):
    """Advanced search response."""
    query_type: SearchType
    query: Union[str, Dict[str, Any]]
    results: List[Dict[str, Any]]
    total: int
    search_time_ms: Optional[float] = None


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
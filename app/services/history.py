"""Write operation history manager."""

import json
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.config import get_settings
from app.models import OperationRecord, OperationType


class HistoryManager:
    """Manages history of write operations for potential rollback."""

    def __init__(self):
        settings = get_settings()
        self.max_entries = settings.max_history_entries
        self._operations: deque = deque(maxlen=self.max_entries if self.max_entries > 0 else None)
        self._storage_path = Path(".history/operations.json")
        
        # Load existing history if available
        self._load_history()

    def _load_history(self):
        """Load operation history from storage."""
        if self.max_entries == 0:
            return
            
        if self._storage_path.exists():
            try:
                with open(self._storage_path, "r") as f:
                    data = json.load(f)
                    operations = data.get("operations", [])
                    # Only keep last N operations based on max_entries
                    if self.max_entries > 0:
                        operations = operations[-self.max_entries:]
                    self._operations = deque(operations, maxlen=self.max_entries)
            except (json.JSONDecodeError, IOError):
                self._operations = deque(maxlen=self.max_entries if self.max_entries > 0 else None)

    def _save_history(self):
        """Save operation history to storage."""
        if self.max_entries == 0:
            return
            
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._storage_path, "w") as f:
                json.dump({
                    "operations": list(self._operations),
                    "last_updated": datetime.utcnow().isoformat(),
                }, f, indent=2)
        except IOError:
            pass  # Fail silently if we can't write history

    def record_operation(
        self,
        operation: OperationType,
        path: str,
        previous_content: Optional[str] = None,
        new_content: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Record a write operation.
        
        Returns:
            Operation ID for potential revert
        """
        if self.max_entries == 0:
            return ""

        operation_id = str(uuid.uuid4())
        record = {
            "id": operation_id,
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation.value,
            "path": path,
            "previous_content": previous_content,
            "new_content": new_content,
            "metadata": metadata or {},
        }

        self._operations.append(record)
        self._save_history()
        
        return operation_id

    def get_history(self, limit: Optional[int] = None) -> List[OperationRecord]:
        """Get operation history."""
        if self.max_entries == 0:
            return []

        operations = list(self._operations)
        if limit:
            operations = operations[-limit:]
        
        return [OperationRecord(**op) for op in reversed(operations)]

    def get_operation(self, operation_id: str) -> Optional[OperationRecord]:
        """Get a specific operation by ID."""
        if self.max_entries == 0:
            return None

        for op in self._operations:
            if op["id"] == operation_id:
                return OperationRecord(**op)
        return None

    def clear_history(self):
        """Clear all operation history."""
        self._operations.clear()
        self._save_history()
        
        # Also remove storage file
        if self._storage_path.exists():
            self._storage_path.unlink()


# Global history manager instance
_history_manager: Optional[HistoryManager] = None


def get_history_manager() -> HistoryManager:
    """Get or create the global history manager instance."""
    global _history_manager
    if _history_manager is None:
        _history_manager = HistoryManager()
    return _history_manager
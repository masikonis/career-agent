from typing import Optional


class StorageError(Exception):
    """Base exception for all storage-related errors"""

    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(message if not details else f"{message}: {details}")


class EntityNotFoundError(StorageError):
    """Raised when an entity cannot be found in storage"""

    def __init__(self, entity_type: str, entity_id: str):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(
            f"Entity of type '{entity_type}' with ID '{entity_id}' not found"
        )


class StorageConnectionError(StorageError):
    """Raised when there's an issue connecting to the storage backend"""

    def __init__(self, storage_type: str, connection_url: str, details: str):
        self.storage_type = storage_type
        self.connection_url = connection_url
        super().__init__(
            f"Failed to connect to {storage_type} at {connection_url}", details
        )


class StorageOperationError(StorageError):
    """Raised when a storage operation fails"""

    def __init__(
        self,
        operation: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        details: Optional[str] = None,
    ):
        self.operation = operation
        self.entity_type = entity_type
        self.entity_id = entity_id
        message = f"Storage operation '{operation}' failed for {entity_type}"
        if entity_id:
            message += f" (ID: {entity_id})"
        super().__init__(message, details)


class SearchIndexError(StorageError):
    """Raised when search indexing operations fail"""

    def __init__(self, index_name: str, operation: str, details: str):
        self.index_name = index_name
        self.operation = operation
        super().__init__(
            f"Search index operation '{operation}' failed on index '{index_name}'",
            details,
        )


class StorageSyncError(StorageError):
    """Raised when synchronization between storage and search index fails"""

    def __init__(self, source: str, target: str, details: str):
        self.source = source
        self.target = target
        super().__init__(f"Sync failed from {source} to {target}", details)

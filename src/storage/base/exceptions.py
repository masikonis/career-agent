class StorageError(Exception):
    """Base exception for all storage-related errors"""
    pass

class EntityNotFoundError(StorageError):
    """Raised when an entity cannot be found"""
    pass

class StorageConnectionError(StorageError):
    """Raised when there's an issue connecting to the storage backend"""
    pass

class StorageOperationError(StorageError):
    """Raised when a storage operation fails"""
    def __init__(self, operation: str, details: str):
        self.operation = operation
        self.details = details
        super().__init__(f"Storage operation '{operation}' failed: {details}")

class SearchIndexError(StorageError):
    """Raised when search indexing operations fail"""
    pass

class StorageSyncError(StorageError):
    """Raised when synchronization between storage and search index fails"""
    def __init__(self, source: str, target: str, details: str):
        self.source = source
        self.target = target
        self.details = details
        super().__init__(f"Sync failed from {source} to {target}: {details}")

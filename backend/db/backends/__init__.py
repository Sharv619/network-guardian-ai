from typing import Protocol
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CloudBackupInfo:
    name: str
    size_bytes: int
    created_at: datetime
    cloud_path: str


class BackupBackend(Protocol):
    """Protocol for backup storage backends (local, S3, GCS, etc.)"""
    
    async def save(self, source_path: str, backup_name: str) -> str:
        """Save backup to storage and return the storage path/key."""
        ...
    
    async def list_backups(self) -> list[CloudBackupInfo]:
        """List all backups in storage."""
        ...
    
    async def restore(self, backup_name: str, target_path: str) -> bool:
        """Restore backup from storage to local path."""
        ...
    
    async def delete(self, backup_name: str) -> bool:
        """Delete backup from storage."""
        ...

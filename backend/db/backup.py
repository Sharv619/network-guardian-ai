import gzip
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..core.logging_config import get_logger
from ..core.config import settings

logger = get_logger(__name__)


class BackupInfo:
    def __init__(
        self,
        name: str,
        path: str,
        size_bytes: int,
        created_at: datetime,
        compressed: bool = True,
    ):
        self.name = name
        self.path = path
        self.size_bytes = size_bytes
        self.created_at = created_at
        self.compressed = compressed

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "size_bytes": self.size_bytes,
            "size_mb": round(self.size_bytes / (1024 * 1024), 2),
            "created_at": self.created_at.isoformat(),
            "compressed": self.compressed,
        }


class BackupManager:
    def __init__(
        self,
        source_path: str,
        backup_path: str,
        retention_days: int = 7,
        compress: bool = True,
    ):
        self.source_path = Path(source_path)
        self.backup_path = Path(backup_path)
        self.retention_days = retention_days
        self.compress = compress

        self.backup_path.mkdir(parents=True, exist_ok=True)
        self._cloud_backend = None

    def set_cloud_backend(self, backend: Any) -> None:
        self._cloud_backend = backend
        logger.info("Cloud backup backend configured", extra={"backend": type(backend).__name__})

    async def create_backup(self) -> Optional[BackupInfo]:
        if not self.source_path.exists():
            logger.error("Source database does not exist", extra={"path": str(self.source_path)})
            return None

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base_name = f"network_guardian_{timestamp}"
        
        if self.compress:
            backup_name = f"{base_name}.db.gz"
            backup_file = self.backup_path / backup_name
            
            try:
                with open(self.source_path, "rb") as f_in:
                    with gzip.open(backup_file, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                compressed = True
            except Exception as e:
                logger.error("Failed to create compressed backup", extra={"error": str(e)})
                return None
        else:
            backup_name = f"{base_name}.db"
            backup_file = self.backup_path / backup_name
            
            try:
                shutil.copy2(self.source_path, backup_file)
                compressed = False
            except Exception as e:
                logger.error("Failed to create backup", extra={"error": str(e)})
                return None

        stat = backup_file.stat()
        backup_info = BackupInfo(
            name=backup_name,
            path=str(backup_file),
            size_bytes=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            compressed=compressed,
        )

        logger.info(
            "Backup created",
            extra={
                "name": backup_name,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "compressed": compressed,
            },
        )

        if self._cloud_backend:
            try:
                cloud_path = await self._cloud_backend.save(str(backup_file), backup_name)
                logger.info("Backup uploaded to cloud", extra={"cloud_path": cloud_path})
            except Exception as e:
                logger.error("Failed to upload backup to cloud", extra={"error": str(e)})

        await self._cleanup_old_backups()

        return backup_info

    async def restore_backup(self, backup_name: str, target_path: Optional[str] = None) -> bool:
        backup_file = self.backup_path / backup_name
        
        if not backup_file.exists():
            logger.error("Backup file not found", extra={"backup_name": backup_name})
            return False

        target = Path(target_path) if target_path else self.source_path
        
        try:
            if backup_name.endswith(".gz"):
                with gzip.open(backup_file, "rb") as f_in:
                    with open(target, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(backup_file, target)

            logger.info("Backup restored", extra={"backup": backup_name, "target": str(target)})
            return True
        except Exception as e:
            logger.error("Failed to restore backup", extra={"error": str(e), "backup": backup_name})
            return False

    async def list_backups(self) -> list[BackupInfo]:
        backups: list[BackupInfo] = []
        
        if not self.backup_path.exists():
            return backups

        for file_path in self.backup_path.iterdir():
            if file_path.is_file() and (file_path.suffix == ".db" or file_path.name.endswith(".db.gz")):
                stat = file_path.stat()
                backup_info = BackupInfo(
                    name=file_path.name,
                    path=str(file_path),
                    size_bytes=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                    compressed=file_path.name.endswith(".gz"),
                )
                backups.append(backup_info)

        backups.sort(key=lambda x: x.created_at, reverse=True)
        return backups

    async def delete_backup(self, backup_name: str) -> bool:
        backup_file = self.backup_path / backup_name
        
        if not backup_file.exists():
            logger.warning("Backup file not found for deletion", extra={"backup_name": backup_name})
            return False

        try:
            backup_file.unlink()
            logger.info("Backup deleted", extra={"backup_name": backup_name})
            return True
        except Exception as e:
            logger.error("Failed to delete backup", extra={"error": str(e), "backup_name": backup_name})
            return False

    async def _cleanup_old_backups(self) -> int:
        if self.retention_days <= 0:
            return 0

        cutoff = datetime.now(timezone.utc).timestamp() - (self.retention_days * 24 * 60 * 60)
        deleted_count = 0

        for file_path in self.backup_path.iterdir():
            if file_path.is_file() and (file_path.suffix == ".db" or file_path.name.endswith(".db.gz")):
                if file_path.stat().st_mtime < cutoff:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug("Deleted old backup", extra={"backup_name": file_path.name})
                    except Exception as e:
                        logger.warning(
                            "Failed to delete old backup",
                            extra={"backup_name": file_path.name, "error": str(e)},
                        )

        if deleted_count > 0:
            logger.info("Cleaned up old backups", extra={"count": deleted_count})

        return deleted_count

    async def export_to_json(self, output_path: str) -> bool:
        from .repository import get_domain_repository
        
        try:
            repo = await get_domain_repository()
            domains = await repo.get_all_domains()
            
            import json
            data = {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "total_domains": len(domains),
                "domains": [d.to_dict() for d in domains],
            }
            
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info("Database exported to JSON", extra={"path": output_path, "count": len(domains)})
            return True
        except Exception as e:
            logger.error("Failed to export database", extra={"error": str(e)})
            return False


_backup_manager: Optional[BackupManager] = None


def get_backup_manager() -> BackupManager:
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager(
            source_path=settings.DATABASE_URL.replace("sqlite+aiosqlite:///", ""),
            backup_path=settings.BACKUP_PATH,
            retention_days=settings.BACKUP_RETENTION_DAYS,
            compress=True,
        )
    return _backup_manager

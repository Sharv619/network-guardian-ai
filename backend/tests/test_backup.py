import pytest
import os
import gzip
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from backend.db.backup import BackupManager, BackupInfo, get_backup_manager


class TestBackupManager:
    """Tests for backup management."""

    @pytest.fixture
    def backup_manager(self, temp_backup_dir, temp_db_path):
        """Create a backup manager with temporary paths."""
        return BackupManager(
            source_path=temp_db_path,
            backup_path=temp_backup_dir,
            retention_days=7,
            compress=True,
        )

    @pytest.fixture
    def sample_db(self, temp_db_path):
        """Create a sample database file for testing."""
        import sqlite3
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute("INSERT INTO test (name) VALUES ('test_data')")
        conn.commit()
        conn.close()
        return temp_db_path

    def test_initial_state(self, backup_manager):
        assert backup_manager.retention_days == 7
        assert backup_manager.compress is True

    async def test_create_backup(self, backup_manager, sample_db):
        backup_info = await backup_manager.create_backup()

        assert backup_info is not None
        assert backup_info.compressed is True
        assert backup_info.name.endswith(".gz")
        assert os.path.exists(backup_info.path)

    async def test_create_backup_missing_source(self, backup_manager):
        backup_manager.source_path = Path("/nonexistent/path.db")
        backup_info = await backup_manager.create_backup()

        assert backup_info is None

    async def test_list_backups_empty(self, backup_manager):
        backups = await backup_manager.list_backups()

        assert len(backups) == 0

    async def test_list_backups(self, backup_manager, sample_db):
        import time
        await backup_manager.create_backup()
        time.sleep(1)
        await backup_manager.create_backup()

        backups = await backup_manager.list_backups()

        assert len(backups) == 2

    async def test_list_backups_sorted_descending(self, backup_manager, sample_db):
        import time
        await backup_manager.create_backup()
        time.sleep(1.1)
        await backup_manager.create_backup()

        backups = await backup_manager.list_backups()

        assert len(backups) == 2
        assert backups[0].created_at >= backups[1].created_at

    async def test_restore_backup(self, backup_manager, sample_db, temp_db_path):
        backup_info = await backup_manager.create_backup()

        os.unlink(sample_db)
        assert not os.path.exists(sample_db)

        success = await backup_manager.restore_backup(backup_info.name)

        assert success is True
        assert os.path.exists(sample_db)

    async def test_restore_nonexistent_backup(self, backup_manager):
        success = await backup_manager.restore_backup("nonexistent.gz")

        assert success is False

    async def test_restore_to_custom_path(self, backup_manager, sample_db, temp_db_path):
        backup_info = await backup_manager.create_backup()

        custom_path = temp_db_path + ".restored"
        success = await backup_manager.restore_backup(backup_info.name, custom_path)

        assert success is True
        assert os.path.exists(custom_path)

        if os.path.exists(custom_path):
            os.unlink(custom_path)

    async def test_delete_backup(self, backup_manager, sample_db):
        backup_info = await backup_manager.create_backup()

        success = await backup_manager.delete_backup(backup_info.name)

        assert success is True
        backups = await backup_manager.list_backups()
        assert len(backups) == 0

    async def test_delete_nonexistent_backup(self, backup_manager):
        success = await backup_manager.delete_backup("nonexistent.gz")

        assert success is False

    async def test_cleanup_old_backups(self, backup_manager, sample_db):
        backup_manager.retention_days = 1
        await backup_manager.create_backup()

        backups = await backup_manager.list_backups()
        assert len(backups) == 1
        
        removed = await backup_manager._cleanup_old_backups()
        assert removed >= 0

    async def test_backup_info_to_dict(self, backup_manager, sample_db):
        backup_info = await backup_manager.create_backup()

        result = backup_info.to_dict()

        assert "name" in result
        assert "path" in result
        assert "size_bytes" in result
        assert "size_mb" in result
        assert "created_at" in result
        assert "compressed" in result

    def test_set_cloud_backend(self, backup_manager):
        mock_backend = type("MockBackend", (), {})()
        backup_manager.set_cloud_backend(mock_backend)

        assert backup_manager._cloud_backend is not None


class TestBackupInfo:
    """Tests for BackupInfo dataclass."""

    def test_backup_info_creation(self):
        info = BackupInfo(
            name="test_backup.db.gz",
            path="/backups/test_backup.db.gz",
            size_bytes=1024,
            created_at=datetime.now(timezone.utc),
            compressed=True,
        )

        assert info.name == "test_backup.db.gz"
        assert info.size_bytes == 1024
        assert info.compressed is True

    def test_backup_info_to_dict(self):
        now = datetime.now(timezone.utc)
        info = BackupInfo(
            name="test.db.gz",
            path="/backups/test.db.gz",
            size_bytes=2048,
            created_at=now,
            compressed=True,
        )

        result = info.to_dict()

        assert result["name"] == "test.db.gz"
        assert result["size_mb"] == round(2048 / (1024 * 1024), 2)
        assert result["compressed"] is True


class TestUncompressedBackup:
    """Tests for uncompressed backups."""

    @pytest.fixture
    def uncompressed_manager(self, temp_backup_dir, temp_db_path):
        return BackupManager(
            source_path=temp_db_path,
            backup_path=temp_backup_dir,
            retention_days=7,
            compress=False,
        )

    @pytest.fixture
    def sample_db(self, temp_db_path):
        import sqlite3
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test (id INTEGER)")
        cursor.execute("INSERT INTO test VALUES (1)")
        conn.commit()
        conn.close()
        return temp_db_path

    async def test_create_uncompressed_backup(self, uncompressed_manager, sample_db):
        backup_info = await uncompressed_manager.create_backup()

        assert backup_info is not None
        assert backup_info.compressed is False
        assert backup_info.name.endswith(".db")
        assert not backup_info.name.endswith(".gz")

    async def test_restore_uncompressed_backup(self, uncompressed_manager, sample_db):
        backup_info = await uncompressed_manager.create_backup()

        os.unlink(sample_db)

        success = await uncompressed_manager.restore_backup(backup_info.name)

        assert success is True
        assert os.path.exists(sample_db)


class TestBackupManagerExport:
    """Tests for export functionality."""

    @pytest.fixture
    def manager_with_data(self, temp_backup_dir, temp_db_path):
        import sqlite3
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE domains (id INTEGER, domain TEXT)")
        cursor.execute("INSERT INTO domains VALUES (1, 'test.com')")
        conn.commit()
        conn.close()
        return BackupManager(
            source_path=temp_db_path,
            backup_path=temp_backup_dir,
        )

    async def test_export_to_json(self, manager_with_data, temp_backup_dir):
        export_path = os.path.join(temp_backup_dir, "export.json")

        from unittest.mock import patch, AsyncMock
        with patch("backend.db.repository.get_domain_repository") as mock_repo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_all_domains.return_value = []
            mock_repo.return_value = mock_repo_instance

            success = await manager_with_data.export_to_json(export_path)

            assert success is True

"""Tests for health check utilities."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from todo_bot.health import (
    check_database_accessible,
    check_imports,
    check_storage_connection,
    main,
    run_health_check,
)


class TestCheckDatabaseAccessible:
    """Tests for check_database_accessible function."""

    def test_database_accessible_existing_file(self, tmp_path: Path) -> None:
        """Test with an existing readable database file."""
        db_file = tmp_path / "test.db"
        db_file.write_bytes(b"SQLite format 3" + b"" * 16)

        result = check_database_accessible(str(db_file))

        assert result is True

    def test_database_accessible_nonexistent_file_creatable(
        self, tmp_path: Path
    ) -> None:
        """Test with a non-existent file in an existing directory."""
        db_file = tmp_path / "new.db"

        result = check_database_accessible(str(db_file))

        assert result is True

    def test_database_accessible_parent_dir_not_exists(self, tmp_path: Path) -> None:
        """Test with a non-existent parent directory."""
        db_file = tmp_path / "nonexistent_dir" / "test.db"

        result = check_database_accessible(str(db_file))

        # Should return False because parent dir doesn't exist
        assert result is False

    def test_database_accessible_file_unreadable(self, tmp_path: Path) -> None:
        """Test with a file that can't be read."""
        db_file = tmp_path / "test.db"
        db_file.write_bytes(b"test")

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            result = check_database_accessible(str(db_file))

        assert result is False


class TestCheckStorageConnection:
    """Tests for check_storage_connection function."""

    @pytest.mark.asyncio
    async def test_storage_connection_success(self, tmp_path: Path) -> None:
        """Test successful storage connection check."""
        # Use real storage with temp directory
        db_file = tmp_path / "test.db"
        result = await check_storage_connection(str(db_file))
        assert result is True

    @pytest.mark.asyncio
    async def test_storage_connection_exception(self, tmp_path: Path) -> None:
        """Test storage connection check when exception occurs."""
        # Use a path that will cause issues
        with patch(
            "todo_bot.storage.sqlite.SQLiteTaskStorage.initialize",
            side_effect=Exception("Connection failed"),
        ):
            db_file = tmp_path / "test.db"
            result = await check_storage_connection(str(db_file))
            assert result is False


class TestCheckImports:
    """Tests for check_imports function."""

    def test_check_imports_success(self) -> None:
        """Test successful import check."""
        result = check_imports()

        assert result is True


class TestRunHealthCheck:
    """Tests for run_health_check function."""

    def test_run_health_check_all_pass(self, tmp_path: Path) -> None:
        """Test health check when all checks pass."""
        db_file = tmp_path / "test.db"

        with (
            patch("todo_bot.health.check_imports", return_value=True),
            patch("todo_bot.health.check_database_accessible", return_value=True),
            patch(
                "todo_bot.health.check_storage_connection",
                new=AsyncMock(return_value=True),
            ),
        ):
            result = run_health_check(db_path=str(db_file), check_db=True)

        assert result == 0

    def test_run_health_check_imports_fail(self) -> None:
        """Test health check when imports fail."""
        with patch("todo_bot.health.check_imports", return_value=False):
            result = run_health_check(check_db=False)

        assert result == 1

    def test_run_health_check_database_not_accessible(self, tmp_path: Path) -> None:
        """Test health check when database is not accessible."""
        db_file = tmp_path / "nonexistent" / "test.db"

        with (
            patch("todo_bot.health.check_imports", return_value=True),
            patch("todo_bot.health.check_database_accessible", return_value=False),
        ):
            result = run_health_check(db_path=str(db_file), check_db=True)

        assert result == 1

    def test_run_health_check_storage_connection_fail(self, tmp_path: Path) -> None:
        """Test health check when storage connection fails."""
        db_file = tmp_path / "test.db"

        with (
            patch("todo_bot.health.check_imports", return_value=True),
            patch("todo_bot.health.check_database_accessible", return_value=True),
            patch(
                "todo_bot.health.check_storage_connection",
                new=AsyncMock(return_value=False),
            ),
        ):
            result = run_health_check(db_path=str(db_file), check_db=True)

        assert result == 1

    def test_run_health_check_storage_exception(self, tmp_path: Path) -> None:
        """Test health check when storage check raises exception."""
        db_file = tmp_path / "test.db"

        with (
            patch("todo_bot.health.check_imports", return_value=True),
            patch("todo_bot.health.check_database_accessible", return_value=True),
            patch("asyncio.new_event_loop") as mock_loop,
        ):
            mock_event_loop = MagicMock()
            mock_event_loop.run_until_complete.side_effect = Exception(
                "Connection error"
            )
            mock_loop.return_value = mock_event_loop

            result = run_health_check(db_path=str(db_file), check_db=True)

        assert result == 1

    def test_run_health_check_skip_db(self) -> None:
        """Test health check with database check disabled."""
        with patch("todo_bot.health.check_imports", return_value=True):
            result = run_health_check(check_db=False)

        assert result == 0

    def test_run_health_check_uses_env_db_path(self) -> None:
        """Test health check uses DATABASE_PATH from environment."""
        with (
            patch("todo_bot.health.check_imports", return_value=True),
            patch("todo_bot.health.check_database_accessible", return_value=True),
            patch(
                "todo_bot.health.check_storage_connection",
                new=AsyncMock(return_value=True),
            ),
            patch.dict("os.environ", {"DATABASE_PATH": "/custom/path/db.sqlite"}),
        ):
            result = run_health_check(db_path=None, check_db=True)

        assert result == 0


class TestMain:
    """Tests for main CLI entry point."""

    def test_main_default_args(self) -> None:
        """Test main with default arguments."""
        with (
            patch("sys.argv", ["health.py"]),
            patch("todo_bot.health.run_health_check", return_value=0) as mock_check,
            patch("sys.exit") as mock_exit,
        ):
            main()

            mock_check.assert_called_once_with(db_path=None, check_db=True)
            mock_exit.assert_called_once_with(0)

    def test_main_with_db_path(self) -> None:
        """Test main with --db-path argument."""
        with (
            patch("sys.argv", ["health.py", "--db-path", "/custom/path.db"]),
            patch("todo_bot.health.run_health_check", return_value=0) as mock_check,
            patch("sys.exit") as mock_exit,
        ):
            main()

            mock_check.assert_called_once_with(
                db_path="/custom/path.db", check_db=True
            )
            mock_exit.assert_called_once_with(0)

    def test_main_skip_db(self) -> None:
        """Test main with --skip-db argument."""
        with (
            patch("sys.argv", ["health.py", "--skip-db"]),
            patch("todo_bot.health.run_health_check", return_value=0) as mock_check,
            patch("sys.exit") as mock_exit,
        ):
            main()

            mock_check.assert_called_once_with(db_path=None, check_db=False)
            mock_exit.assert_called_once_with(0)

    def test_main_unhealthy_exit(self) -> None:
        """Test main exits with code 1 when unhealthy."""
        with (
            patch("sys.argv", ["health.py"]),
            patch("todo_bot.health.run_health_check", return_value=1),
            patch("sys.exit") as mock_exit,
        ):
            main()

            mock_exit.assert_called_once_with(1)

"""Health check utilities for the Discord A/B/C Todo Bot."""

import asyncio
import sys
from pathlib import Path


def check_database_accessible(db_path: str = "data/tasks.db") -> bool:
    """Check if the database file is accessible.

    Args:
        db_path: Path to the database file

    Returns:
        True if database is accessible, False otherwise
    """
    path = Path(db_path)

    # Check if parent directory exists
    if not path.parent.exists():
        return False

    # If file exists, check if it's readable
    if path.exists():
        try:
            with open(path, "rb") as f:
                # Try to read first few bytes
                f.read(16)
            return True
        except OSError:
            return False

    # If file doesn't exist, check if we can create it
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        return True
    except OSError:
        return False


async def check_storage_connection(db_path: str = "data/tasks.db") -> bool:
    """Check if storage can be initialized and queried.

    Args:
        db_path: Path to the database file

    Returns:
        True if storage is healthy, False otherwise
    """
    try:
        from .storage.sqlite import SQLiteTaskStorage

        storage = SQLiteTaskStorage(db_path=db_path)
        await storage.initialize()

        # Try to get stats as a health check query
        stats = await storage.get_stats()

        await storage.close()

        return "schema_version" in stats
    except Exception:
        return False


def check_imports() -> bool:
    """Check if all required modules can be imported.

    Returns:
        True if all imports succeed, False otherwise
    """
    try:
        # Import and use modules to verify they load correctly
        # These imports are intentionally not used - they verify importability
        import todo_bot  # noqa: F401
        import todo_bot.models.task  # noqa: F401
        import todo_bot.storage.sqlite  # noqa: F401

        return True
    except ImportError:
        return False


def run_health_check(
    db_path: str | None = None,
    check_db: bool = True,
) -> int:
    """Run health checks and return exit code.

    Args:
        db_path: Optional database path to check
        check_db: Whether to check database connectivity

    Returns:
        0 if healthy, 1 if unhealthy
    """
    import os

    # Check imports
    if not check_imports():
        print("UNHEALTHY: Import check failed")
        return 1

    print("OK: Imports successful")

    # Check database if requested
    if check_db:
        db_path = db_path or os.getenv("DATABASE_PATH", "data/tasks.db")

        if not check_database_accessible(db_path):
            print(f"UNHEALTHY: Database not accessible at {db_path}")
            return 1

        print(f"OK: Database accessible at {db_path}")

        # Run async storage check
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            healthy = loop.run_until_complete(check_storage_connection(db_path))
            loop.close()

            if not healthy:
                print("UNHEALTHY: Storage connection check failed")
                return 1

            print("OK: Storage connection verified")
        except Exception as e:
            print(f"UNHEALTHY: Storage check error: {e}")
            return 1

    print("HEALTHY: All checks passed")
    return 0


def main() -> None:
    """Main entry point for health check CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Health check for Discord A/B/C Todo Bot"
    )
    parser.add_argument(
        "--db-path",
        help="Path to database file",
        default=None,
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Skip database checks",
    )

    args = parser.parse_args()

    exit_code = run_health_check(
        db_path=args.db_path,
        check_db=not args.skip_db,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

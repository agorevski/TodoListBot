"""Pytest fixtures for the Discord A/B/C Todo Bot tests."""

import asyncio
import os
import tempfile
from collections.abc import AsyncGenerator, Generator
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from todo_bot.models.task import Priority, Task
from todo_bot.storage.sqlite import SQLiteTaskStorage

# =============================================================================
# Centralized test constants - import these in test files
# =============================================================================

TEST_SERVER_ID = 123456789
TEST_CHANNEL_ID = 987654321
TEST_USER_ID = 111222333
TEST_OTHER_USER_ID = 999999999


# =============================================================================
# Event loop fixture
# =============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Storage fixtures
# =============================================================================


@pytest_asyncio.fixture
async def storage() -> AsyncGenerator[SQLiteTaskStorage, None]:
    """Create a temporary SQLite storage for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_tasks.db")
        storage = SQLiteTaskStorage(db_path=db_path)
        await storage.initialize()
        yield storage
        await storage.close()


@pytest.fixture
def mock_storage() -> MagicMock:
    """Create a mock storage for testing."""
    storage = MagicMock()
    storage.add_task = AsyncMock()
    storage.get_tasks = AsyncMock(return_value=[])
    storage.get_task_by_id = AsyncMock()
    storage.update_task = AsyncMock(return_value=True)
    storage.mark_task_done = AsyncMock(return_value=True)
    storage.mark_task_undone = AsyncMock(return_value=True)
    storage.clear_completed_tasks = AsyncMock(return_value=0)
    storage.delete_task = AsyncMock(return_value=True)
    storage.cleanup_old_tasks = AsyncMock(return_value=0)
    storage.get_stats = AsyncMock(
        return_value={
            "total_tasks": 100,
            "unique_users": 10,
            "schema_version": 1,
            "database_path": "test.db",
        }
    )
    storage.initialize = AsyncMock()
    storage.close = AsyncMock()
    return storage


# =============================================================================
# Task fixtures
# =============================================================================


@pytest.fixture
def sample_task() -> Task:
    """Create a sample task for testing."""
    return Task(
        id=1,
        description="Test task",
        priority=Priority.A,
        server_id=TEST_SERVER_ID,
        channel_id=TEST_CHANNEL_ID,
        user_id=TEST_USER_ID,
        done=False,
        task_date=date.today(),
    )


@pytest.fixture
def sample_task_done() -> Task:
    """Create a sample completed task for testing."""
    return Task(
        id=2,
        description="Completed task",
        priority=Priority.B,
        server_id=TEST_SERVER_ID,
        channel_id=TEST_CHANNEL_ID,
        user_id=TEST_USER_ID,
        done=True,
        task_date=date.today(),
    )


@pytest.fixture
def sample_tasks() -> list[Task]:
    """Create a list of sample tasks for testing."""
    return [
        Task(
            id=1,
            description="A-priority task 1",
            priority=Priority.A,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
            done=False,
        ),
        Task(
            id=2,
            description="A-priority task 2 (done)",
            priority=Priority.A,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
            done=True,
        ),
        Task(
            id=3,
            description="B-priority task",
            priority=Priority.B,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
            done=False,
        ),
        Task(
            id=4,
            description="C-priority task",
            priority=Priority.C,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
            done=False,
        ),
    ]


# =============================================================================
# Discord mock fixtures
# =============================================================================


@pytest.fixture
def mock_interaction() -> MagicMock:
    """Create a mock Discord interaction."""
    interaction = MagicMock()
    interaction.guild = MagicMock()
    interaction.guild.id = TEST_SERVER_ID
    interaction.channel_id = TEST_CHANNEL_ID
    interaction.user = MagicMock()
    interaction.user.id = TEST_USER_ID
    interaction.response = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.original_response = AsyncMock()
    interaction.message = MagicMock()
    interaction.message.edit = AsyncMock()
    return interaction


@pytest.fixture
def mock_bot() -> MagicMock:
    """Create a mock Discord bot."""
    bot = MagicMock()
    bot.guilds = [MagicMock(), MagicMock()]  # 2 guilds
    bot.latency = 0.05  # 50ms latency
    bot.add_cog = AsyncMock()
    return bot


# =============================================================================
# Helper functions for creating test data
# =============================================================================


def create_test_task(
    id: int = 1,
    description: str = "Test task",
    priority: Priority = Priority.A,
    done: bool = False,
    task_date: date | None = None,
    server_id: int = TEST_SERVER_ID,
    channel_id: int = TEST_CHANNEL_ID,
    user_id: int = TEST_USER_ID,
) -> Task:
    """Helper function to create tasks for testing.

    Args:
        id: Task ID
        description: Task description
        priority: Task priority
        done: Whether the task is done
        task_date: Task date (defaults to today)
        server_id: Discord server ID
        channel_id: Discord channel ID
        user_id: Discord user ID

    Returns:
        Task instance with the specified attributes
    """
    return Task(
        id=id,
        description=description,
        priority=priority,
        server_id=server_id,
        channel_id=channel_id,
        user_id=user_id,
        done=done,
        task_date=task_date or date.today(),
    )


def create_mock_interaction(
    user_id: int = TEST_USER_ID,
    server_id: int = TEST_SERVER_ID,
    channel_id: int = TEST_CHANNEL_ID,
    guild: bool = True,
) -> MagicMock:
    """Create a mock Discord interaction with custom parameters.

    Args:
        user_id: The user ID for the interaction
        server_id: The server/guild ID
        channel_id: The channel ID
        guild: Whether the interaction is in a guild

    Returns:
        Mock interaction object
    """
    interaction = MagicMock()
    if guild:
        interaction.guild = MagicMock()
        interaction.guild.id = server_id
    else:
        interaction.guild = None
    interaction.channel_id = channel_id
    interaction.user = MagicMock()
    interaction.user.id = user_id
    interaction.response = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.original_response = AsyncMock()
    interaction.message = MagicMock()
    interaction.message.edit = AsyncMock()
    return interaction

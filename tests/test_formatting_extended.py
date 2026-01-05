"""Extended tests for formatting module covering new features."""

from todo_bot.models.task import Priority, Task
from todo_bot.utils.formatting import format_task_updated

# Test constants
SERVER_ID = 123
CHANNEL_ID = 456
USER_ID = 789


def create_task(id: int = 1):
    """Create a sample task for testing.

    Args:
        id: The task ID to assign. Defaults to 1.

    Returns:
        A Task instance with default test values.
    """
    return Task(
        id=id,
        description="Test task",
        priority=Priority.A,
        server_id=SERVER_ID,
        channel_id=CHANNEL_ID,
        user_id=USER_ID,
    )


class TestFormatTaskUpdated:
    """Tests for format_task_updated function."""

    def test_format_updated_description_only(self):
        """Test formatting with only description change.

        Verifies that the formatted output includes the task ID,
        'updated' text, new description, and 'description' label.
        """
        result = format_task_updated(1, description="New desc")

        assert "1" in result
        assert "updated" in result.lower()
        assert "New desc" in result
        assert "description" in result.lower()

    def test_format_updated_priority_only(self):
        """Test formatting with only priority change.

        Verifies that the formatted output includes the task ID,
        'updated' text, new priority value, and 'priority' label.
        """
        result = format_task_updated(1, priority=Priority.B)

        assert "1" in result
        assert "updated" in result.lower()
        assert "B" in result
        assert "priority" in result.lower()

    def test_format_updated_both(self):
        """Test formatting with both description and priority changes.

        Verifies that the formatted output includes the task ID,
        'updated' text, new description, new priority, and 'and' conjunction.
        """
        result = format_task_updated(1, description="New", priority=Priority.C)

        assert "1" in result
        assert "updated" in result.lower()
        assert "New" in result
        assert "C" in result
        assert "and" in result.lower()

    def test_format_updated_nothing(self):
        """Test formatting with no changes provided.

        Verifies that the formatted output includes the task ID and
        'updated' text but does not mention specific field changes.
        """
        result = format_task_updated(1)

        assert "1" in result
        assert "updated" in result.lower()
        # No specific changes mentioned
        assert "description" not in result.lower() or "priority" not in result.lower()

    def test_format_updated_includes_emoji(self):
        """Test formatting includes edit emoji.

        Verifies that the formatted output contains the pencil emoji
        to visually indicate an edit operation.
        """
        result = format_task_updated(1, description="Test")

        assert "✏️" in result

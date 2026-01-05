"""Tests for centralized message strings."""

from todo_bot.messages import (
    DisplayMessages,
    ErrorMessages,
    SuccessMessages,
)


class TestErrorMessages:
    """Tests for ErrorMessages class."""

    def test_description_too_long(self) -> None:
        """Test description_too_long formatter.

        Verifies the error message includes the actual length, max length,
        and the error emoji.
        """
        result = ErrorMessages.description_too_long(length=300, max_length=256)

        assert "300" in result
        assert "256" in result
        assert "❌" in result

    def test_description_too_short(self) -> None:
        """Test description_too_short formatter.

        Verifies the error message includes the minimum length requirement
        and the error emoji.
        """
        result = ErrorMessages.description_too_short(min_length=1)

        assert "1" in result
        assert "❌" in result

    def test_invalid_priority(self) -> None:
        """Test invalid_priority formatter.

        Verifies the error message includes the invalid priority value
        and the error emoji.
        """
        result = ErrorMessages.invalid_priority(priority="X")

        assert "X" in result
        assert "❌" in result

    def test_task_not_found(self) -> None:
        """Test task_not_found formatter.

        Verifies the error message includes the task ID with hash prefix
        and the error emoji.
        """
        result = ErrorMessages.task_not_found(task_id=42)

        assert "#42" in result
        assert "❌" in result

    def test_rate_limited(self) -> None:
        """Test rate_limited formatter.

        Verifies the error message includes the retry after duration
        and the hourglass emoji.
        """
        result = ErrorMessages.rate_limited(retry_after=5.5)

        assert "5.5" in result
        assert "⏳" in result

    def test_static_messages(self) -> None:
        """Test static error message constants.

        Verifies all static error message constants contain the error emoji.
        """
        assert "❌" in ErrorMessages.GUILD_ONLY
        assert "❌" in ErrorMessages.GENERIC_ERROR
        assert "❌" in ErrorMessages.INVALID_DATE_FORMAT
        assert "❌" in ErrorMessages.INVALID_DATE
        assert "❌" in ErrorMessages.CANNOT_MODIFY_OTHERS_TASKS
        assert "❌" in ErrorMessages.NO_CHANGES_PROVIDED


class TestSuccessMessages:
    """Tests for SuccessMessages class."""

    def test_task_added(self) -> None:
        """Test task_added formatter.

        Verifies the success message includes the task ID, description,
        and the checkmark emoji.
        """
        result = SuccessMessages.task_added(task_id=1, description="Test task")

        assert "#1" in result
        assert "Test task" in result
        assert "✅" in result

    def test_task_done(self) -> None:
        """Test task_done formatter.

        Verifies the success message includes the task ID, checkmark emoji,
        and the word 'done'.
        """
        result = SuccessMessages.task_done(task_id=5)

        assert "#5" in result
        assert "✅" in result
        assert "done" in result.lower()

    def test_task_undone(self) -> None:
        """Test task_undone formatter.

        Verifies the success message includes the task ID and the
        undo arrow emoji.
        """
        result = SuccessMessages.task_undone(task_id=3)

        assert "#3" in result
        assert "↩️" in result

    def test_task_deleted(self) -> None:
        """Test task_deleted formatter.

        Verifies the success message includes the task ID and the
        trash bin emoji.
        """
        result = SuccessMessages.task_deleted(task_id=7)

        assert "#7" in result
        assert "🗑️" in result

    def test_task_updated_with_description(self) -> None:
        """Test task_updated formatter with description only.

        Verifies the success message includes the task ID, new description,
        and the pencil emoji when only description is updated.
        """
        result = SuccessMessages.task_updated(
            task_id=2, description="New description"
        )

        assert "#2" in result
        assert "New description" in result
        assert "✏️" in result

    def test_task_updated_with_priority(self) -> None:
        """Test task_updated formatter with priority only.

        Verifies the success message includes the task ID, new priority,
        and the pencil emoji when only priority is updated.
        """
        result = SuccessMessages.task_updated(task_id=2, priority="A")

        assert "#2" in result
        assert "A" in result
        assert "✏️" in result

    def test_task_updated_with_both(self) -> None:
        """Test task_updated formatter with both description and priority.

        Verifies the success message includes the task ID, new description,
        new priority, 'and' conjunction, and the pencil emoji when both
        fields are updated.
        """
        result = SuccessMessages.task_updated(
            task_id=2, description="New desc", priority="B"
        )

        assert "#2" in result
        assert "New desc" in result
        assert "B" in result
        assert " and " in result
        assert "✏️" in result

    def test_task_updated_no_changes(self) -> None:
        """Test task_updated formatter with no changes.

        Verifies the success message includes the task ID and pencil emoji
        even when no actual changes are provided.
        """
        result = SuccessMessages.task_updated(task_id=2)

        assert "#2" in result
        assert "✏️" in result

    def test_tasks_cleared_none(self) -> None:
        """Test tasks_cleared formatter with zero tasks.

        Verifies the message indicates no completed tasks when count is zero.
        """
        result = SuccessMessages.tasks_cleared(count=0)

        assert "No completed tasks" in result

    def test_tasks_cleared_one(self) -> None:
        """Test tasks_cleared formatter with one task.

        Verifies the success message includes the count and checkmark emoji
        for a single cleared task.
        """
        result = SuccessMessages.tasks_cleared(count=1)

        assert "1" in result
        assert "✅" in result

    def test_tasks_cleared_many(self) -> None:
        """Test tasks_cleared formatter with multiple tasks.

        Verifies the success message includes the count and checkmark emoji
        when multiple tasks are cleared.
        """
        result = SuccessMessages.tasks_cleared(count=5)

        assert "5" in result
        assert "✅" in result


class TestDisplayMessages:
    """Tests for DisplayMessages class."""

    def test_header_today(self) -> None:
        """Test header formatter for today.

        Verifies the header includes 'Today' and bold markdown formatting
        when is_today is True.
        """
        result = DisplayMessages.header(is_today=True)

        assert "Today" in result
        assert "**" in result

    def test_header_specific_date(self) -> None:
        """Test header formatter for specific date.

        Verifies the header includes the specific date and bold markdown
        formatting when is_today is False.
        """
        result = DisplayMessages.header(task_date="2024-12-25", is_today=False)

        assert "2024-12-25" in result
        assert "**" in result

    def test_empty_message_today(self) -> None:
        """Test empty_message formatter for today.

        Verifies the empty message includes the clipboard emoji and
        /add command hint when is_today is True.
        """
        result = DisplayMessages.empty_message(is_today=True)

        assert "📋" in result
        assert "/add" in result

    def test_empty_message_specific_date(self) -> None:
        """Test empty_message formatter for specific date.

        Verifies the empty message includes the clipboard emoji and
        the specific date when is_today is False.
        """
        result = DisplayMessages.empty_message(task_date="2024-12-25", is_today=False)

        assert "📋" in result
        assert "2024-12-25" in result

    def test_static_messages(self) -> None:
        """Test static display message constants.

        Verifies all static display message constants contain expected
        content and placeholders.
        """
        assert "Today" in DisplayMessages.HEADER_TODAY
        assert "{date}" in DisplayMessages.HEADER_DATE
        assert "📋" in DisplayMessages.EMPTY_TODAY
        assert "{date}" in DisplayMessages.EMPTY_DATE

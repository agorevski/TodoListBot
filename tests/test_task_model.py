"""Tests for the Task model and Priority enum."""

from datetime import date, timedelta

import pytest

from todo_bot.models.task import MAX_DESCRIPTION_LENGTH, Priority, Task


class TestPriority:
    """Tests for the Priority enum."""

    def test_priority_values(self) -> None:
        """Test that priority values are correct."""
        assert Priority.A.value == "A"
        assert Priority.B.value == "B"
        assert Priority.C.value == "C"

    def test_priority_emoji(self) -> None:
        """Test that priority emojis are correct."""
        assert Priority.A.emoji == "🔴"
        assert Priority.B.emoji == "🟡"
        assert Priority.C.emoji == "🟢"

    def test_priority_display_name(self) -> None:
        """Test that priority display names are correct."""
        assert Priority.A.display_name == "🔴 **A-Priority**"
        assert Priority.B.display_name == "🟡 **B-Priority**"
        assert Priority.C.display_name == "🟢 **C-Priority**"

    def test_priority_from_string_valid(self) -> None:
        """Test creating priority from valid string values."""
        assert Priority.from_string("A") == Priority.A
        assert Priority.from_string("B") == Priority.B
        assert Priority.from_string("C") == Priority.C

    def test_priority_from_string_lowercase(self) -> None:
        """Test creating priority from lowercase string values."""
        assert Priority.from_string("a") == Priority.A
        assert Priority.from_string("b") == Priority.B
        assert Priority.from_string("c") == Priority.C

    def test_priority_from_string_with_whitespace(self) -> None:
        """Test creating priority from string with whitespace."""
        assert Priority.from_string("  A  ") == Priority.A
        assert Priority.from_string("\tB\n") == Priority.B

    def test_priority_from_string_invalid(self) -> None:
        """Test that invalid priority strings raise ValueError."""
        with pytest.raises(ValueError, match="Invalid priority"):
            Priority.from_string("D")

        with pytest.raises(ValueError, match="Invalid priority"):
            Priority.from_string("")

        with pytest.raises(ValueError, match="Invalid priority"):
            Priority.from_string("invalid")


class TestTask:
    """Tests for the Task dataclass."""

    def test_task_creation(self) -> None:
        """Test creating a task with required fields."""
        task = Task(
            id=1,
            description="Test task",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
        )
        assert task.id == 1
        assert task.description == "Test task"
        assert task.priority == Priority.A
        assert task.server_id == 123
        assert task.channel_id == 456
        assert task.user_id == 789
        assert task.done is False
        assert task.task_date == date.today()

    def test_task_creation_with_string_priority(self) -> None:
        """Test creating a task with string priority (auto-converted)."""
        task = Task(
            id=1,
            description="Test task",
            priority="B",  # type: ignore
            server_id=123,
            channel_id=456,
            user_id=789,
        )
        assert task.priority == Priority.B

    def test_task_creation_with_all_fields(self) -> None:
        """Test creating a task with all fields specified."""
        custom_date = date(2024, 12, 25)
        task = Task(
            id=1,
            description="Test task",
            priority=Priority.C,
            server_id=123,
            channel_id=456,
            user_id=789,
            done=True,
            task_date=custom_date,
        )
        assert task.done is True
        assert task.task_date == custom_date

    def test_task_description_trimmed(self) -> None:
        """Test that task description is trimmed."""
        task = Task(
            id=1,
            description="  Test task with spaces  ",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
        )
        assert task.description == "Test task with spaces"

    def test_task_empty_description_raises(self) -> None:
        """Test that empty description raises ValueError."""
        with pytest.raises(ValueError, match="at least 1 character"):
            Task(
                id=1,
                description="",
                priority=Priority.A,
                server_id=123,
                channel_id=456,
                user_id=789,
            )

    def test_task_whitespace_description_raises(self) -> None:
        """Test that whitespace-only description raises ValueError."""
        with pytest.raises(ValueError, match="at least 1 character"):
            Task(
                id=1,
                description="   ",
                priority=Priority.A,
                server_id=123,
                channel_id=456,
                user_id=789,
            )

    def test_task_description_max_length(self) -> None:
        """Test that description at max length is accepted."""
        max_desc = "x" * MAX_DESCRIPTION_LENGTH
        task = Task(
            id=1,
            description=max_desc,
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
        )
        assert len(task.description) == MAX_DESCRIPTION_LENGTH

    def test_task_description_too_long_raises(self) -> None:
        """Test that description exceeding max length raises ValueError."""
        long_desc = "x" * (MAX_DESCRIPTION_LENGTH + 1)
        with pytest.raises(ValueError, match="too long"):
            Task(
                id=1,
                description=long_desc,
                priority=Priority.A,
                server_id=123,
                channel_id=456,
                user_id=789,
            )

    def test_task_display_text_incomplete(self) -> None:
        """Test display text for incomplete task."""
        task = Task(
            id=1,
            description="Test task",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
            done=False,
        )
        assert task.display_text == "1. Test task"

    def test_task_display_text_completed(self) -> None:
        """Test display text for completed task (strikethrough)."""
        task = Task(
            id=1,
            description="Test task",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
            done=True,
        )
        assert task.display_text == "~~1. Test task~~"

    def test_task_is_today(self) -> None:
        """Test is_today property for today's task."""
        task = Task(
            id=1,
            description="Test task",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=date.today(),
        )
        assert task.is_today is True

    def test_task_is_today_past_date(self) -> None:
        """Test is_today property for past date."""
        task = Task(
            id=1,
            description="Test task",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=date.today() - timedelta(days=1),
        )
        assert task.is_today is False

    def test_task_mark_done(self) -> None:
        """Test marking a task as done."""
        task = Task(
            id=1,
            description="Test task",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
            done=False,
        )
        task.mark_done()
        assert task.done is True

    def test_task_mark_undone(self) -> None:
        """Test marking a task as undone."""
        task = Task(
            id=1,
            description="Test task",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
            done=True,
        )
        task.mark_undone()
        assert task.done is False

    def test_task_to_dict(self) -> None:
        """Test converting task to dictionary."""
        task = Task(
            id=1,
            description="Test task",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
            done=True,
            task_date=date(2024, 12, 25),
        )
        data = task.to_dict()
        assert data == {
            "id": 1,
            "description": "Test task",
            "priority": "A",
            "done": True,
            "task_date": "2024-12-25",
            "server_id": 123,
            "channel_id": 456,
            "user_id": 789,
        }

    def test_task_from_dict(self) -> None:
        """Test creating task from dictionary."""
        data = {
            "id": 1,
            "description": "Test task",
            "priority": "B",
            "done": True,
            "task_date": "2024-12-25",
            "server_id": 123,
            "channel_id": 456,
            "user_id": 789,
        }
        task = Task.from_dict(data)
        assert task.id == 1
        assert task.description == "Test task"
        assert task.priority == Priority.B
        assert task.done is True
        assert task.task_date == date(2024, 12, 25)
        assert task.server_id == 123
        assert task.channel_id == 456
        assert task.user_id == 789

    def test_task_from_dict_defaults(self) -> None:
        """Test creating task from dictionary with defaults."""
        data = {
            "id": 1,
            "description": "Test task",
            "priority": "C",
            "server_id": 123,
            "channel_id": 456,
            "user_id": 789,
        }
        task = Task.from_dict(data)
        assert task.done is False
        assert task.task_date == date.today()

    def test_task_from_dict_with_date_object(self) -> None:
        """Test creating task from dictionary with date object."""
        today = date.today()
        data = {
            "id": 1,
            "description": "Test task",
            "priority": "A",
            "server_id": 123,
            "channel_id": 456,
            "user_id": 789,
            "task_date": today,
        }
        task = Task.from_dict(data)
        assert task.task_date == today

    def test_task_roundtrip(self) -> None:
        """Test that to_dict and from_dict are inverses."""
        original = Task(
            id=1,
            description="Test task",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
            done=True,
            task_date=date(2024, 12, 25),
        )
        data = original.to_dict()
        restored = Task.from_dict(data)

        assert restored.id == original.id
        assert restored.description == original.description
        assert restored.priority == original.priority
        assert restored.done == original.done
        assert restored.task_date == original.task_date
        assert restored.server_id == original.server_id
        assert restored.channel_id == original.channel_id
        assert restored.user_id == original.user_id

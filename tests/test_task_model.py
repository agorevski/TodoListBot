"""Tests for the Task model and Priority enum."""

from datetime import date, timedelta

import pytest

from todo_bot.exceptions import ValidationError
from todo_bot.models.task import MAX_DESCRIPTION_LENGTH, Priority, Task


class TestPriority:
    """Tests for the Priority enum."""

    def test_priority_values(self) -> None:
        """Test that priority values are correct.

        Verifies that each Priority enum member has the expected
        single-character string value (A, B, or C).
        """
        assert Priority.A.value == "A"
        assert Priority.B.value == "B"
        assert Priority.C.value == "C"

    def test_priority_emoji(self) -> None:
        """Test that priority emojis are correct.

        Verifies that each Priority enum member returns the expected
        colored circle emoji for visual distinction.
        """
        assert Priority.A.emoji == "🔴"
        assert Priority.B.emoji == "🟡"
        assert Priority.C.emoji == "🟢"

    def test_priority_display_name(self) -> None:
        """Test that priority display names are correct.

        Verifies that each Priority enum member returns a formatted
        display name with emoji and markdown bold styling.
        """
        assert Priority.A.display_name == "🔴 **A-Priority**"
        assert Priority.B.display_name == "🟡 **B-Priority**"
        assert Priority.C.display_name == "🟢 **C-Priority**"

    def test_priority_from_string_valid(self) -> None:
        """Test creating priority from valid string values.

        Verifies that uppercase priority strings are correctly
        converted to their corresponding Priority enum members.
        """
        assert Priority.from_string("A") == Priority.A
        assert Priority.from_string("B") == Priority.B
        assert Priority.from_string("C") == Priority.C

    def test_priority_from_string_lowercase(self) -> None:
        """Test creating priority from lowercase string values.

        Verifies that the from_string method is case-insensitive
        and correctly handles lowercase input.
        """
        assert Priority.from_string("a") == Priority.A
        assert Priority.from_string("b") == Priority.B
        assert Priority.from_string("c") == Priority.C

    def test_priority_from_string_with_whitespace(self) -> None:
        """Test creating priority from string with whitespace.

        Verifies that the from_string method strips leading and
        trailing whitespace before parsing the priority value.
        """
        assert Priority.from_string("  A  ") == Priority.A
        assert Priority.from_string("\tB\n") == Priority.B

    def test_priority_from_string_invalid(self) -> None:
        """Test that invalid priority strings raise ValidationError.

        Verifies that non-existent priority values, empty strings,
        and invalid input raise a ValidationError with appropriate message.

        Raises:
            ValidationError: When an invalid priority string is provided.
        """
        with pytest.raises(ValidationError, match="Invalid priority"):
            Priority.from_string("D")

        with pytest.raises(ValidationError, match="Invalid priority"):
            Priority.from_string("")

        with pytest.raises(ValidationError, match="Invalid priority"):
            Priority.from_string("invalid")


class TestTask:
    """Tests for the Task dataclass."""

    def test_task_creation(self) -> None:
        """Test creating a task with required fields.

        Verifies that a Task can be created with only required fields
        and that default values are correctly applied for optional fields.
        """
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
        """Test creating a task with string priority (auto-converted).

        Verifies that a string priority value is automatically converted
        to the corresponding Priority enum member during Task creation.
        """
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
        """Test creating a task with all fields specified.

        Verifies that a Task can be created with all fields explicitly
        provided, including optional done status and custom task date.
        """
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
        """Test that task description is trimmed.

        Verifies that leading and trailing whitespace is automatically
        removed from the task description during creation.
        """
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
        """Test that empty description raises ValidationError.

        Verifies that creating a Task with an empty string description
        raises a ValidationError requiring at least 1 character.

        Raises:
            ValidationError: When description is empty.
        """
        with pytest.raises(ValidationError, match="at least 1 character"):
            Task(
                id=1,
                description="",
                priority=Priority.A,
                server_id=123,
                channel_id=456,
                user_id=789,
            )

    def test_task_whitespace_description_raises(self) -> None:
        """Test that whitespace-only description raises ValidationError.

        Verifies that creating a Task with a whitespace-only description
        raises a ValidationError after trimming leaves an empty string.

        Raises:
            ValidationError: When description contains only whitespace.
        """
        with pytest.raises(ValidationError, match="at least 1 character"):
            Task(
                id=1,
                description="   ",
                priority=Priority.A,
                server_id=123,
                channel_id=456,
                user_id=789,
            )

    def test_task_description_max_length(self) -> None:
        """Test that description at max length is accepted.

        Verifies that a description exactly at MAX_DESCRIPTION_LENGTH
        characters is valid and accepted without raising an error.
        """
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
        """Test that description exceeding max length raises ValidationError.

        Verifies that a description longer than MAX_DESCRIPTION_LENGTH
        characters raises a ValidationError with a 'too long' message.

        Raises:
            ValidationError: When description exceeds maximum length.
        """
        long_desc = "x" * (MAX_DESCRIPTION_LENGTH + 1)
        with pytest.raises(ValidationError, match="too long"):
            Task(
                id=1,
                description=long_desc,
                priority=Priority.A,
                server_id=123,
                channel_id=456,
                user_id=789,
            )

    def test_task_display_text_incomplete(self) -> None:
        """Test display text for incomplete task.

        Verifies that an incomplete task displays with its ID number
        and description in a numbered list format.
        """
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
        """Test display text for completed task (strikethrough).

        Verifies that a completed task displays with markdown
        strikethrough formatting to indicate completion.
        """
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
        """Test is_today property for today's task.

        Verifies that the is_today property returns True when
        the task's date matches the current date.
        """
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
        """Test is_today property for past date.

        Verifies that the is_today property returns False when
        the task's date is in the past.
        """
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
        """Test marking a task as done.

        Verifies that calling mark_done() on an incomplete task
        changes its done status to True.
        """
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
        """Test marking a task as undone.

        Verifies that calling mark_undone() on a completed task
        changes its done status back to False.
        """
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
        """Test converting task to dictionary.

        Verifies that to_dict() serializes all task fields correctly,
        converting Priority enum to string and date to ISO format.
        """
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
        """Test creating task from dictionary.

        Verifies that from_dict() correctly deserializes all fields,
        converting string priority to enum and ISO date string to date object.
        """
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
        """Test creating task from dictionary with defaults.

        Verifies that from_dict() applies default values for optional
        fields (done=False, task_date=today) when not provided.
        """
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
        """Test creating task from dictionary with date object.

        Verifies that from_dict() accepts both date objects and
        ISO format strings for the task_date field.
        """
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
        """Test that to_dict and from_dict are inverses.

        Verifies that serializing a Task to dict and deserializing back
        produces an equivalent Task with all fields preserved.
        """
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

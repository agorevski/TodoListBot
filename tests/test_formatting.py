"""Tests for the formatting utilities."""

from datetime import date

from tests.conftest import TEST_CHANNEL_ID, TEST_SERVER_ID, TEST_USER_ID
from todo_bot.models.task import Priority, Task
from todo_bot.utils.formatting import (
    _format_empty_message,
    _format_header,
    _format_priority_section,
    _group_tasks_by_priority,
    format_task_added,
    format_task_deleted,
    format_task_done,
    format_task_not_found,
    format_task_undone,
    format_tasks,
    format_tasks_cleared,
)


def create_task(
    id: int = 1,
    description: str = "Test task",
    priority: Priority = Priority.A,
    done: bool = False,
    task_date: date | None = None,
) -> Task:
    """Create a task instance for testing purposes.

    Args:
        id: The unique identifier for the task.
        description: The task description text.
        priority: The priority level of the task.
        done: Whether the task is marked as completed.
        task_date: The date for the task, defaults to today if None.

    Returns:
        A Task instance configured with the provided parameters and
        test-specific server, channel, and user IDs.
    """
    return Task(
        id=id,
        description=description,
        priority=priority,
        server_id=TEST_SERVER_ID,
        channel_id=TEST_CHANNEL_ID,
        user_id=TEST_USER_ID,
        done=done,
        task_date=task_date or date.today(),
    )


class TestFormatTasks:
    """Tests for format_tasks function."""

    def test_format_empty_tasks(self) -> None:
        """Test that formatting an empty task list returns a helpful message.

        Verifies that the output includes a "No tasks for today" message
        and a hint to use the /add command.
        """
        result = format_tasks([])
        assert "No tasks for today" in result
        assert "/add" in result

    def test_format_empty_tasks_custom_date(self) -> None:
        """Test that formatting an empty task list for a specific date shows that date.

        Verifies that when a custom date is provided, the empty message
        includes the formatted date instead of "today".
        """
        custom_date = date(2024, 12, 25)
        result = format_tasks([], task_date=custom_date)
        assert "No tasks for" in result
        assert "December 25, 2024" in result

    def test_format_single_task(self) -> None:
        """Test that a single task is formatted with header and priority section.

        Verifies that the output includes the "Today's Tasks" header,
        the appropriate priority indicator, and the task description.
        """
        tasks = [create_task(description="Do something")]
        result = format_tasks(tasks)

        assert "**Today's Tasks**" in result
        assert "🔴 **A-Priority**" in result
        assert "1. Do something" in result

    def test_format_tasks_by_priority(self) -> None:
        """Test that tasks are grouped and ordered by priority level.

        Verifies that tasks with different priorities are displayed
        in separate sections with A-Priority appearing before B-Priority,
        and B-Priority appearing before C-Priority.
        """
        tasks = [
            create_task(id=1, description="A task", priority=Priority.A),
            create_task(id=2, description="B task", priority=Priority.B),
            create_task(id=3, description="C task", priority=Priority.C),
        ]
        result = format_tasks(tasks)

        assert "🔴 **A-Priority**" in result
        assert "🟡 **B-Priority**" in result
        assert "🟢 **C-Priority**" in result

        # Check order (A before B before C)
        a_pos = result.find("A-Priority")
        b_pos = result.find("B-Priority")
        c_pos = result.find("C-Priority")
        assert a_pos < b_pos < c_pos

    def test_format_tasks_with_completed(self) -> None:
        """Test that completed tasks are displayed with strikethrough formatting.

        Verifies that completed tasks show with strikethrough markdown,
        while pending tasks display with position-based index numbers
        rather than database IDs.
        """
        tasks = [
            create_task(id=1, description="Done task", priority=Priority.A, done=True),
            create_task(
                id=2, description="Pending task", priority=Priority.A, done=False
            ),
        ]
        result = format_tasks(tasks)

        # Completed tasks are shown on a single line with just the description
        assert "~~Done task~~" in result
        # Pending tasks show with position-based index (not database ID)
        assert "1. Pending task" in result

    def test_format_tasks_custom_date_header(self) -> None:
        """Test that a custom date is displayed in the header instead of 'Today'.

        Verifies that when viewing tasks for a date other than today,
        the header shows the formatted date rather than "Today's Tasks".
        """
        custom_date = date(2024, 12, 25)
        tasks = [create_task(task_date=custom_date)]
        result = format_tasks(tasks, task_date=custom_date)

        assert "December 25, 2024" in result
        assert "Today's Tasks" not in result


class TestFormatHeader:
    """Tests for _format_header function."""

    def test_format_header_today(self) -> None:
        """Test that today's date produces a 'Today's Tasks' header.

        Verifies that when the current date is passed, the header
        displays "Today's Tasks" in bold markdown format.
        """
        result = _format_header(date.today())
        assert result == "**Today's Tasks**"

    def test_format_header_other_date(self) -> None:
        """Test that a non-today date produces a header with the formatted date.

        Verifies that when a date other than today is passed, the header
        includes the human-readable formatted date string.
        """
        other_date = date(2024, 1, 15)
        result = _format_header(other_date)
        assert "January 15, 2024" in result


class TestFormatEmptyMessage:
    """Tests for _format_empty_message function."""

    def test_empty_message_today(self) -> None:
        """Test that today's empty message says 'No tasks for today'.

        Verifies that the message includes "No tasks for today" and
        a helpful hint to use the /add command.
        """
        result = _format_empty_message(date.today())
        assert "No tasks for today" in result
        assert "/add" in result

    def test_empty_message_none(self) -> None:
        """Test that a None date defaults to showing 'No tasks for today'.

        Verifies that when no date is provided, the function treats
        it as today and shows the appropriate message.
        """
        result = _format_empty_message(None)
        assert "No tasks for today" in result

    def test_empty_message_other_date(self) -> None:
        """Test that a specific date shows that date in the empty message.

        Verifies that when a date other than today is passed, the message
        includes the human-readable formatted date.
        """
        other_date = date(2024, 6, 15)
        result = _format_empty_message(other_date)
        assert "June 15, 2024" in result


class TestGroupTasksByPriority:
    """Tests for _group_tasks_by_priority function."""

    def test_group_empty_list(self) -> None:
        """Test that grouping an empty list returns an empty dictionary.

        Verifies that when no tasks are provided, the function returns
        an empty dict with no priority keys.
        """
        result = _group_tasks_by_priority([])
        assert result == {}

    def test_group_single_priority(self) -> None:
        """Test that tasks with the same priority are grouped together.

        Verifies that multiple tasks with the same priority level
        appear under a single priority key, and other priority keys
        are not present in the result.
        """
        tasks = [
            create_task(id=1, priority=Priority.A),
            create_task(id=2, priority=Priority.A),
        ]
        result = _group_tasks_by_priority(tasks)

        assert Priority.A in result
        assert len(result[Priority.A]) == 2
        assert Priority.B not in result
        assert Priority.C not in result

    def test_group_multiple_priorities(self) -> None:
        """Test that tasks are correctly grouped by their priority levels.

        Verifies that tasks with different priorities are placed in
        separate groups, each accessible by their priority enum value.
        """
        tasks = [
            create_task(id=1, priority=Priority.A),
            create_task(id=2, priority=Priority.B),
            create_task(id=3, priority=Priority.C),
        ]
        result = _group_tasks_by_priority(tasks)

        assert len(result[Priority.A]) == 1
        assert len(result[Priority.B]) == 1
        assert len(result[Priority.C]) == 1

    def test_group_sorts_by_done_status(self) -> None:
        """Test that incomplete tasks are sorted before completed tasks.

        Verifies that within a priority group, tasks that are not done
        appear before tasks that are marked as done, regardless of
        their original order or ID.
        """
        tasks = [
            create_task(id=1, priority=Priority.A, done=True),
            create_task(id=2, priority=Priority.A, done=False),
        ]
        result = _group_tasks_by_priority(tasks)

        # Incomplete (id=2) should come before completed (id=1)
        assert result[Priority.A][0].id == 2
        assert result[Priority.A][1].id == 1


class TestFormatPrioritySection:
    """Tests for _format_priority_section function."""

    def test_format_section_a_priority(self) -> None:
        """Test that A priority section has correct header and formatting.

        Verifies that the section includes the red emoji indicator,
        the priority label, numbered task entries, and returns the
        correct next index.
        """
        tasks = [create_task(id=1, description="Task 1", priority=Priority.A)]
        section, next_index = _format_priority_section(Priority.A, tasks)

        assert "🔴 **A-Priority**" in section
        assert "1. Task 1" in section
        assert next_index == 2

    def test_format_section_multiple_tasks(self) -> None:
        """Test that multiple tasks are numbered sequentially in a section.

        Verifies that each task gets an incremented index number
        and the returned next_index is correct for chaining sections.
        """
        tasks = [
            create_task(id=1, description="Task 1", priority=Priority.B),
            create_task(id=2, description="Task 2", priority=Priority.B),
        ]
        section, next_index = _format_priority_section(Priority.B, tasks)

        assert "1. Task 1" in section
        assert "2. Task 2" in section
        assert next_index == 3

    def test_format_section_with_start_index(self) -> None:
        """Test that a custom start index is respected in task numbering.

        Verifies that when a start_index is provided, task numbering
        begins from that value rather than 1, allowing for continuous
        numbering across multiple priority sections.
        """
        tasks = [create_task(id=5, description="Task 5", priority=Priority.C)]
        section, next_index = _format_priority_section(Priority.C, tasks, start_index=3)

        assert "3. Task 5" in section
        assert next_index == 4

    def test_format_section_completed_tasks_no_index(self) -> None:
        """Test that completed tasks are shown without index numbers.

        Verifies that tasks marked as done are displayed with
        strikethrough formatting and do not consume an index number,
        leaving the next_index unchanged.
        """
        tasks = [
            create_task(id=1, description="Done task", priority=Priority.A, done=True),
        ]
        section, next_index = _format_priority_section(Priority.A, tasks)

        # Completed tasks shown as strikethrough without index
        assert "~~Done task~~" in section
        # Index doesn't increment for completed tasks
        assert next_index == 1


class TestFormatTaskAdded:
    """Tests for format_task_added function."""

    def test_format_task_added(self) -> None:
        """Test that the task added message includes ID, description, and checkmark.

        Verifies that the confirmation message shows the task number,
        the task description, and a checkmark emoji for visual feedback.
        """
        task = create_task(id=5, description="New task")
        result = format_task_added(task)

        assert "Added task #5" in result
        assert "New task" in result
        assert "✅" in result


class TestFormatTaskDone:
    """Tests for format_task_done function."""

    def test_format_task_done(self) -> None:
        """Test that the task done message includes ID and completion indicator.

        Verifies that the confirmation message shows the task number,
        the word "done", and a checkmark emoji for visual feedback.
        """
        task = create_task(id=3, description="Completed task")
        result = format_task_done(task)

        assert "Task #3" in result
        assert "done" in result
        assert "✅" in result


class TestFormatTaskUndone:
    """Tests for format_task_undone function."""

    def test_format_task_undone(self) -> None:
        """Test that the task undone message includes ID and revert indicator.

        Verifies that the confirmation message shows the task number,
        "not done" status, and an undo emoji for visual feedback.
        """
        task = create_task(id=7, description="Reverted task")
        result = format_task_undone(task)

        assert "Task #7" in result
        assert "not done" in result
        assert "↩️" in result


class TestFormatTasksCleared:
    """Tests for format_tasks_cleared function."""

    def test_format_cleared_zero(self) -> None:
        """Test that clearing zero tasks shows 'No completed tasks to clear'.

        Verifies that when the count is zero, a specific message is
        displayed indicating there were no completed tasks to remove.
        """
        result = format_tasks_cleared(0)
        assert "No completed tasks to clear" in result

    def test_format_cleared_one(self) -> None:
        """Test that clearing one task uses singular grammar.

        Verifies that the message says "task" (singular) rather than
        "tasks" when exactly one task was cleared.
        """
        result = format_tasks_cleared(1)
        assert "Cleared 1 completed task" in result
        assert "tasks" not in result  # Singular

    def test_format_cleared_multiple(self) -> None:
        """Test that clearing multiple tasks uses plural grammar.

        Verifies that the message says "tasks" (plural) and includes
        the correct count when more than one task was cleared.
        """
        result = format_tasks_cleared(5)
        assert "Cleared 5 completed tasks" in result


class TestFormatTaskDeleted:
    """Tests for format_task_deleted function."""

    def test_format_task_deleted(self) -> None:
        """Test that the task deleted message includes ID and trash icon.

        Verifies that the confirmation message shows the task number,
        "deleted" status, and a trash can emoji for visual feedback.
        """
        task = create_task(id=8, description="Deleted task")
        result = format_task_deleted(task)

        assert "Task #8" in result
        assert "deleted" in result
        assert "🗑️" in result


class TestFormatTaskNotFound:
    """Tests for format_task_not_found function."""

    def test_format_not_found(self) -> None:
        """Test that the not found message includes task ID and error indicator.

        Verifies that the error message shows the task number,
        "not found" status, and an X emoji for visual feedback.
        """
        result = format_task_not_found(42)
        assert "Task #42" in result
        assert "not found" in result
        assert "❌" in result

"""Tests for the formatting utilities."""

from datetime import date
from typing import Optional

import pytest

from todo_bot.models.task import Task, Priority
from todo_bot.utils.formatting import (
    format_tasks,
    format_task_added,
    format_task_done,
    format_task_undone,
    format_tasks_cleared,
    format_task_deleted,
    format_task_not_found,
    _format_header,
    _format_empty_message,
    _group_tasks_by_priority,
    _format_priority_section,
)

# Test constants
TEST_SERVER_ID = 123456789
TEST_CHANNEL_ID = 987654321
TEST_USER_ID = 111222333

def create_task(
    id: int = 1,
    description: str = "Test task",
    priority: Priority = Priority.A,
    done: bool = False,
    task_date: Optional[date] = None,
) -> Task:
    """Helper to create a task for testing."""
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
        """Test formatting empty task list."""
        result = format_tasks([])
        assert "No tasks for today" in result
        assert "/add" in result

    def test_format_empty_tasks_custom_date(self) -> None:
        """Test formatting empty task list for a custom date."""
        custom_date = date(2024, 12, 25)
        result = format_tasks([], task_date=custom_date)
        assert "No tasks for" in result
        assert "December 25, 2024" in result

    def test_format_single_task(self) -> None:
        """Test formatting a single task."""
        tasks = [create_task(description="Do something")]
        result = format_tasks(tasks)

        assert "**Today's Tasks**" in result
        assert "🔴 **A-Priority**" in result
        assert "1. Do something" in result

    def test_format_tasks_by_priority(self) -> None:
        """Test that tasks are grouped by priority."""
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
        """Test formatting tasks with completed items (strikethrough)."""
        tasks = [
            create_task(id=1, description="Done task", priority=Priority.A, done=True),
            create_task(id=2, description="Pending task", priority=Priority.A, done=False),
        ]
        result = format_tasks(tasks)

        assert "~~1. Done task~~" in result
        assert "2. Pending task" in result

    def test_format_tasks_custom_date_header(self) -> None:
        """Test that custom date shows in header."""
        custom_date = date(2024, 12, 25)
        tasks = [create_task(task_date=custom_date)]
        result = format_tasks(tasks, task_date=custom_date)

        assert "December 25, 2024" in result
        assert "Today's Tasks" not in result

class TestFormatHeader:
    """Tests for _format_header function."""

    def test_format_header_today(self) -> None:
        """Test header for today."""
        result = _format_header(date.today())
        assert result == "**Today's Tasks**"

    def test_format_header_other_date(self) -> None:
        """Test header for a different date."""
        other_date = date(2024, 1, 15)
        result = _format_header(other_date)
        assert "January 15, 2024" in result

class TestFormatEmptyMessage:
    """Tests for _format_empty_message function."""

    def test_empty_message_today(self) -> None:
        """Test empty message for today."""
        result = _format_empty_message(date.today())
        assert "No tasks for today" in result
        assert "/add" in result

    def test_empty_message_none(self) -> None:
        """Test empty message with no date."""
        result = _format_empty_message(None)
        assert "No tasks for today" in result

    def test_empty_message_other_date(self) -> None:
        """Test empty message for a different date."""
        other_date = date(2024, 6, 15)
        result = _format_empty_message(other_date)
        assert "June 15, 2024" in result

class TestGroupTasksByPriority:
    """Tests for _group_tasks_by_priority function."""

    def test_group_empty_list(self) -> None:
        """Test grouping empty list."""
        result = _group_tasks_by_priority([])
        assert result == {}

    def test_group_single_priority(self) -> None:
        """Test grouping tasks with single priority."""
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
        """Test grouping tasks with multiple priorities."""
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
        """Test that incomplete tasks come before completed within a group."""
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
        """Test formatting A priority section."""
        tasks = [create_task(id=1, description="Task 1", priority=Priority.A)]
        result = _format_priority_section(Priority.A, tasks)

        assert "🔴 **A-Priority**" in result
        assert "1. Task 1" in result

    def test_format_section_multiple_tasks(self) -> None:
        """Test formatting section with multiple tasks."""
        tasks = [
            create_task(id=1, description="Task 1", priority=Priority.B),
            create_task(id=2, description="Task 2", priority=Priority.B),
        ]
        result = _format_priority_section(Priority.B, tasks)

        assert "1. Task 1" in result
        assert "2. Task 2" in result

class TestFormatTaskAdded:
    """Tests for format_task_added function."""

    def test_format_task_added(self) -> None:
        """Test formatting added task confirmation."""
        task = create_task(id=5, description="New task")
        result = format_task_added(task)

        assert "Added task #5" in result
        assert "New task" in result
        assert "✅" in result

class TestFormatTaskDone:
    """Tests for format_task_done function."""

    def test_format_task_done(self) -> None:
        """Test formatting done task confirmation."""
        task = create_task(id=3, description="Completed task")
        result = format_task_done(task)

        assert "Task #3" in result
        assert "done" in result
        assert "✅" in result

class TestFormatTaskUndone:
    """Tests for format_task_undone function."""

    def test_format_task_undone(self) -> None:
        """Test formatting undone task confirmation."""
        task = create_task(id=7, description="Reverted task")
        result = format_task_undone(task)

        assert "Task #7" in result
        assert "not done" in result
        assert "↩️" in result

class TestFormatTasksCleared:
    """Tests for format_tasks_cleared function."""

    def test_format_cleared_zero(self) -> None:
        """Test formatting when no tasks were cleared."""
        result = format_tasks_cleared(0)
        assert "No completed tasks to clear" in result

    def test_format_cleared_one(self) -> None:
        """Test formatting when one task was cleared."""
        result = format_tasks_cleared(1)
        assert "Cleared 1 completed task" in result
        assert "tasks" not in result  # Singular

    def test_format_cleared_multiple(self) -> None:
        """Test formatting when multiple tasks were cleared."""
        result = format_tasks_cleared(5)
        assert "Cleared 5 completed tasks" in result

class TestFormatTaskDeleted:
    """Tests for format_task_deleted function."""

    def test_format_task_deleted(self) -> None:
        """Test formatting deleted task confirmation."""
        task = create_task(id=8, description="Deleted task")
        result = format_task_deleted(task)

        assert "Task #8" in result
        assert "deleted" in result
        assert "🗑️" in result


class TestFormatTaskNotFound:
    """Tests for format_task_not_found function."""

    def test_format_not_found(self) -> None:
        """Test formatting task not found error."""
        result = format_task_not_found(42)
        assert "Task #42" in result
        assert "not found" in result
        assert "❌" in result

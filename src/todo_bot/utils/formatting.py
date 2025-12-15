"""Formatting utilities for displaying tasks in Discord."""

from datetime import date
from typing import Dict, List, Optional

from ..models.task import Task, Priority

def format_tasks(tasks: List[Task], task_date: Optional[date] = None) -> str:
    """Format a list of tasks for display in Discord.

    Tasks are grouped by priority (A, B, C) with completed tasks
    shown with strikethrough at the bottom of each group.

    Args:
        tasks: List of tasks to format
        task_date: Optional date for the header (defaults to today)

    Returns:
        Formatted string ready for Discord display
    """
    if not tasks:
        return _format_empty_message(task_date)

    task_date = task_date or date.today()
    header = _format_header(task_date)

    # Group tasks by priority
    grouped = _group_tasks_by_priority(tasks)

    sections = []
    for priority in [Priority.A, Priority.B, Priority.C]:
        priority_tasks = grouped.get(priority, [])
        if priority_tasks:
            section = _format_priority_section(priority, priority_tasks)
            sections.append(section)

    return f"{header}\n\n" + "\n\n".join(sections)

def _format_header(task_date: date) -> str:
    """Format the header for the task list.

    Args:
        task_date: The date for the task list

    Returns:
        Formatted header string
    """
    if task_date == date.today():
        return "**Today's Tasks**"
    else:
        return f"**Tasks for {task_date.strftime('%B %d, %Y')}**"

def _format_empty_message(task_date: Optional[date] = None) -> str:
    """Format a message for when there are no tasks.

    Args:
        task_date: Optional date for context

    Returns:
        Friendly empty message
    """
    if task_date and task_date != date.today():
        return f"📋 No tasks for {task_date.strftime('%B %d, %Y')}."
    return "📋 No tasks for today. Use `/add` to create one!"

def _group_tasks_by_priority(tasks: List[Task]) -> Dict[Priority, List[Task]]:
    """Group tasks by their priority level.

    Within each priority group, incomplete tasks come before completed tasks.

    Args:
        tasks: List of tasks to group

    Returns:
        Dictionary mapping priority to list of tasks
    """
    grouped: Dict[Priority, List[Task]] = {}

    for task in tasks:
        if task.priority not in grouped:
            grouped[task.priority] = []
        grouped[task.priority].append(task)

    # Sort each group: incomplete first, then completed
    for priority in grouped:
        grouped[priority] = sorted(grouped[priority], key=lambda t: (t.done, t.id))

    return grouped

def _format_priority_section(priority: Priority, tasks: List[Task]) -> str:
    """Format a single priority section with its tasks.

    Args:
        priority: The priority level
        tasks: Tasks in this priority group

    Returns:
        Formatted section string
    """
    lines = [priority.display_name]

    for task in tasks:
        lines.append(task.display_text)

    return "\n".join(lines)

def format_task_added(task: Task) -> str:
    """Format a confirmation message for a newly added task.

    Args:
        task: The task that was added

    Returns:
        Confirmation message string
    """
    return f"Added task #{task.id}: {task.description} ✅"

def format_task_done(task: Task) -> str:
    """Format a confirmation message for a completed task.

    Args:
        task: The task that was marked done

    Returns:
        Confirmation message string
    """
    return f"Task #{task.id} marked as done ✅"

def format_task_undone(task: Task) -> str:
    """Format a confirmation message for a task marked as undone.

    Args:
        task: The task that was marked undone

    Returns:
        Confirmation message string
    """
    return f"Task #{task.id} marked as not done ↩️"

def format_tasks_cleared(count: int) -> str:
    """Format a confirmation message for cleared tasks.

    Args:
        count: Number of tasks that were cleared

    Returns:
        Confirmation message string
    """
    if count == 0:
        return "No completed tasks to clear."
    elif count == 1:
        return "Cleared 1 completed task ✅"
    else:
        return f"Cleared {count} completed tasks ✅"

def format_task_deleted(task: Task) -> str:
    """Format a confirmation message for a deleted task.

    Args:
        task: The task that was deleted

    Returns:
        Confirmation message string
    """
    return f"Task #{task.id} deleted 🗑️"


def format_task_not_found(task_id: int) -> str:
    """Format an error message for a task not found.

    Args:
        task_id: The task ID that was not found

    Returns:
        Error message string
    """
    return f"❌ Task #{task_id} not found."


def format_task_updated(
    task_id: int,
    description: Optional[str] = None,
    priority: Optional["Priority"] = None,
) -> str:
    """Format a confirmation message for an updated task.

    Args:
        task_id: The task ID that was updated
        description: New description if changed
        priority: New priority if changed

    Returns:
        Confirmation message string
    """
    changes = []
    if description is not None:
        changes.append(f"description to \"{description}\"")
    if priority is not None:
        changes.append(f"priority to {priority.value}")

    if changes:
        change_text = " and ".join(changes)
        return f"Task #{task_id} updated: {change_text} ✏️"
    return f"Task #{task_id} updated ✏️"

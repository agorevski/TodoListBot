"""Formatting utilities for displaying tasks in Discord."""

from datetime import date

from ..messages import DisplayMessages, SuccessMessages
from ..models.task import Priority, Task


def format_tasks(tasks: list[Task], task_date: date | None = None) -> str:
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
    current_index = 1
    for priority in [Priority.A, Priority.B, Priority.C]:
        priority_tasks = grouped.get(priority, [])
        if priority_tasks:
            section, current_index = _format_priority_section(
                priority, priority_tasks, current_index
            )
            sections.append(section)

    return f"{header}\n\n" + "\n\n".join(sections)


def _format_header(task_date: date) -> str:
    """Format the header for the task list.

    Args:
        task_date: The date for the task list

    Returns:
        Formatted header string
    """
    is_today = task_date == date.today()
    date_str = task_date.strftime("%B %d, %Y") if not is_today else None
    return DisplayMessages.header(task_date=date_str, is_today=is_today)


def _format_empty_message(task_date: date | None = None) -> str:
    """Format a message for when there are no tasks.

    Args:
        task_date: Optional date for context

    Returns:
        Friendly empty message
    """
    is_today = task_date is None or task_date == date.today()
    date_str = task_date.strftime("%B %d, %Y") if task_date and not is_today else None
    return DisplayMessages.empty_message(task_date=date_str, is_today=is_today)


def _group_tasks_by_priority(tasks: list[Task]) -> dict[Priority, list[Task]]:
    """Group tasks by their priority level.

    Within each priority group, incomplete tasks come before completed tasks.

    Args:
        tasks: List of tasks to group

    Returns:
        Dictionary mapping priority to list of tasks
    """
    grouped: dict[Priority, list[Task]] = {}

    for task in tasks:
        if task.priority not in grouped:
            grouped[task.priority] = []
        grouped[task.priority].append(task)

    # Sort each group: incomplete first, then completed
    for priority in grouped:
        grouped[priority] = sorted(grouped[priority], key=lambda t: (t.done, t.id))

    return grouped


def _format_priority_section(
    priority: Priority,
    tasks: list[Task],
    start_index: int = 1,
) -> tuple[str, int]:
    """Format a single priority section with its tasks.

    Incomplete tasks are shown first, each on its own line with position-based
    numbering. Completed tasks are shown at the bottom on a single line,
    separated by pipes: ~~task1~~ | ~~task2~~ | ~~task3~~

    Args:
        priority: The priority level
        tasks: Tasks in this priority group
        start_index: Starting number for position-based display

    Returns:
        Tuple of (formatted section string, next available index)
    """
    lines = [priority.display_name]

    # Separate incomplete and completed tasks
    incomplete_tasks = [t for t in tasks if not t.done]
    completed_tasks = [t for t in tasks if t.done]

    # Add incomplete tasks with position-based numbering
    current_index = start_index
    for task in incomplete_tasks:
        lines.append(f"{current_index}. {task.description}")
        current_index += 1

    # Add completed tasks on a single line with pipes (no numbers)
    if completed_tasks:
        completed_text = " | ".join(
            f"~~{task.description}~~" for task in completed_tasks
        )
        lines.append(completed_text)

    return "\n".join(lines), current_index


def format_task_added(task: Task) -> str:
    """Format a confirmation message for a newly added task.

    Args:
        task: The task that was added

    Returns:
        Confirmation message string
    """
    return SuccessMessages.task_added(task_id=task.id, description=task.description)


def format_task_done(task: Task) -> str:
    """Format a confirmation message for a completed task.

    Args:
        task: The task that was marked done

    Returns:
        Confirmation message string
    """
    return SuccessMessages.task_done(task_id=task.id)


def format_task_undone(task: Task) -> str:
    """Format a confirmation message for a task marked as undone.

    Args:
        task: The task that was marked undone

    Returns:
        Confirmation message string
    """
    return SuccessMessages.task_undone(task_id=task.id)


def format_tasks_cleared(count: int) -> str:
    """Format a confirmation message for cleared tasks.

    Args:
        count: Number of tasks that were cleared

    Returns:
        Confirmation message string
    """
    return SuccessMessages.tasks_cleared(count=count)


def format_task_deleted(task: Task) -> str:
    """Format a confirmation message for a deleted task.

    Args:
        task: The task that was deleted

    Returns:
        Confirmation message string
    """
    return SuccessMessages.task_deleted(task_id=task.id)


def format_task_not_found(task_id: int) -> str:
    """Format an error message for a task not found.

    Args:
        task_id: The task ID that was not found

    Returns:
        Error message string
    """
    from ..messages import ErrorMessages

    return ErrorMessages.task_not_found(task_id=task_id)


def format_task_updated(
    task_id: int,
    description: str | None = None,
    priority: Priority | None = None,
) -> str:
    """Format a confirmation message for an updated task.

    Args:
        task_id: The task ID that was updated
        description: New description if changed
        priority: New priority if changed

    Returns:
        Confirmation message string
    """
    priority_str = priority.value if priority is not None else None
    return SuccessMessages.task_updated(
        task_id=task_id,
        description=description,
        priority=priority_str,
    )

"""Centralized message strings for the Discord A/B/C Todo Bot.

This module provides centralized message templates for consistent
messaging and future internationalization support.
"""

# =============================================================================
# Error Messages
# =============================================================================


class ErrorMessages:
    """Error message templates."""

    # General errors
    GUILD_ONLY = "❌ This command can only be used in a server."
    GENERIC_ERROR = "❌ An error occurred while processing your command."

    # Validation errors
    DESCRIPTION_TOO_LONG = (
        "❌ Description too long ({length} chars). "
        "Maximum is {max_length} characters."
    )
    DESCRIPTION_TOO_SHORT = (
        "❌ Task description must be at least {min_length} character(s)."
    )
    INVALID_PRIORITY = "❌ Invalid priority: {priority}. Must be A, B, or C."
    INVALID_DATE_FORMAT = (
        "❌ Invalid date format. Please use YYYY-MM-DD (e.g., 2024-12-25)."
    )
    INVALID_DATE = "❌ Invalid date. Please use a valid date in YYYY-MM-DD format."

    # Task errors
    TASK_NOT_FOUND = "❌ Task #{task_id} not found."
    CANNOT_MODIFY_OTHERS_TASKS = "❌ You can only modify your own tasks."
    NO_CHANGES_PROVIDED = "❌ Please provide a new description and/or priority."

    # Rate limiting
    RATE_LIMITED = "⏳ Slow down! Try again in {retry_after:.1f} seconds."

    @classmethod
    def description_too_long(cls, length: int, max_length: int) -> str:
        """Format description too long error.

        Args:
            length: The actual length of the description.
            max_length: The maximum allowed length.

        Returns:
            Formatted error message indicating the description is too long.
        """
        return cls.DESCRIPTION_TOO_LONG.format(
            length=length,
            max_length=max_length,
        )

    @classmethod
    def description_too_short(cls, min_length: int) -> str:
        """Format description too short error.

        Args:
            min_length: The minimum required length.

        Returns:
            Formatted error message indicating the description is too short.
        """
        return cls.DESCRIPTION_TOO_SHORT.format(min_length=min_length)

    @classmethod
    def invalid_priority(cls, priority: str) -> str:
        """Format invalid priority error.

        Args:
            priority: The invalid priority value provided.

        Returns:
            Formatted error message indicating the priority is invalid.
        """
        return cls.INVALID_PRIORITY.format(priority=priority)

    @classmethod
    def task_not_found(cls, task_id: int) -> str:
        """Format task not found error.

        Args:
            task_id: The ID of the task that was not found.

        Returns:
            Formatted error message indicating the task was not found.
        """
        return cls.TASK_NOT_FOUND.format(task_id=task_id)

    @classmethod
    def rate_limited(cls, retry_after: float) -> str:
        """Format rate limited message.

        Args:
            retry_after: The number of seconds to wait before retrying.

        Returns:
            Formatted message indicating the user is rate limited.
        """
        return cls.RATE_LIMITED.format(retry_after=retry_after)


# =============================================================================
# Success Messages
# =============================================================================


class SuccessMessages:
    """Success message templates."""

    TASK_ADDED = "Added task #{task_id}: {description} ✅"
    TASK_DONE = "Task #{task_id} marked as done ✅"
    TASK_UNDONE = "Task #{task_id} marked as not done ↩️"
    TASK_DELETED = "Task #{task_id} deleted 🗑️"
    TASK_UPDATED = "Task #{task_id} updated: {changes} ✏️"
    TASK_UPDATED_SIMPLE = "Task #{task_id} updated ✏️"

    TASKS_CLEARED_NONE = "No completed tasks to clear."
    TASKS_CLEARED_ONE = "Cleared 1 completed task ✅"
    TASKS_CLEARED_MANY = "Cleared {count} completed tasks ✅"

    @classmethod
    def task_added(cls, task_id: int, description: str) -> str:
        """Format task added message.

        Args:
            task_id: The ID of the newly created task.
            description: The description of the task.

        Returns:
            Formatted success message for task creation.
        """
        return cls.TASK_ADDED.format(task_id=task_id, description=description)

    @classmethod
    def task_done(cls, task_id: int) -> str:
        """Format task done message.

        Args:
            task_id: The ID of the task marked as done.

        Returns:
            Formatted success message for task completion.
        """
        return cls.TASK_DONE.format(task_id=task_id)

    @classmethod
    def task_undone(cls, task_id: int) -> str:
        """Format task undone message.

        Args:
            task_id: The ID of the task marked as not done.

        Returns:
            Formatted success message for task un-completion.
        """
        return cls.TASK_UNDONE.format(task_id=task_id)

    @classmethod
    def task_deleted(cls, task_id: int) -> str:
        """Format task deleted message.

        Args:
            task_id: The ID of the deleted task.

        Returns:
            Formatted success message for task deletion.
        """
        return cls.TASK_DELETED.format(task_id=task_id)

    @classmethod
    def task_updated(
        cls,
        task_id: int,
        description: str | None = None,
        priority: str | None = None,
    ) -> str:
        """Format task updated message.

        Args:
            task_id: The ID of the updated task.
            description: The new description, if changed.
            priority: The new priority, if changed.

        Returns:
            Formatted success message describing what was updated.
        """
        changes = []
        if description is not None:
            changes.append(f'description to "{description}"')
        if priority is not None:
            changes.append(f"priority to {priority}")

        if changes:
            change_text = " and ".join(changes)
            return cls.TASK_UPDATED.format(task_id=task_id, changes=change_text)
        return cls.TASK_UPDATED_SIMPLE.format(task_id=task_id)

    @classmethod
    def tasks_cleared(cls, count: int) -> str:
        """Format tasks cleared message.

        Args:
            count: The number of completed tasks that were cleared.

        Returns:
            Formatted message indicating how many tasks were cleared.
        """
        if count == 0:
            return cls.TASKS_CLEARED_NONE
        elif count == 1:
            return cls.TASKS_CLEARED_ONE
        else:
            return cls.TASKS_CLEARED_MANY.format(count=count)


# =============================================================================
# Display Messages
# =============================================================================


class DisplayMessages:
    """Display message templates for task lists."""

    HEADER_TODAY = "**Today's Tasks**"
    HEADER_DATE = "**Tasks for {date}**"

    EMPTY_TODAY = "📋 No tasks for today. Use `/add` to create one!"
    EMPTY_DATE = "📋 No tasks for {date}."

    @classmethod
    def header(cls, task_date: str | None = None, is_today: bool = True) -> str:
        """Format task list header.

        Args:
            task_date: The date string to display in the header.
            is_today: Whether the task list is for today.

        Returns:
            Formatted header string for the task list.
        """
        if is_today:
            return cls.HEADER_TODAY
        return cls.HEADER_DATE.format(date=task_date)

    @classmethod
    def empty_message(
        cls,
        task_date: str | None = None,
        is_today: bool = True,
    ) -> str:
        """Format empty task list message.

        Args:
            task_date: The date string for when the list is empty.
            is_today: Whether the task list is for today.

        Returns:
            Formatted message indicating no tasks exist.
        """
        if is_today:
            return cls.EMPTY_TODAY
        return cls.EMPTY_DATE.format(date=task_date)


# =============================================================================
# Log Messages
# =============================================================================


class LogMessages:
    """Log message templates for consistent logging."""

    BOT_STARTING = "Starting Discord A/B/C Todo Bot..."
    BOT_READY = "Logged in as %s (ID: %s)"
    BOT_GUILDS = "Connected to %d guild(s)"
    BOT_SHUTTING_DOWN = "Shutting down bot..."
    BOT_SHUTDOWN_COMPLETE = "Bot shutdown complete"

    STORAGE_INITIALIZED = "Database initialized at version %d (path: %s)"
    STORAGE_CLOSED = "Database connection closed"
    STORAGE_ERROR_CLOSE = "Error closing storage: %s"

    TASK_CREATED = "Task #%d created for user %d"
    TASK_UPDATED = "Task #%d updated by user %d"
    TASK_MARKED_DONE = "Task #%d marked done by user %d"
    TASK_MARKED_UNDONE = "Task #%d marked undone by user %d"
    TASK_DELETED = "Task #%d deleted by user %d"
    TASKS_CLEARED = "User %s cleared %d completed tasks"

    COMMAND_ERROR = "Command error for user %s: %s"
    MIGRATION_START = "Running migration to version %d..."
    MIGRATION_COMPLETE = "Migration to version %d complete"

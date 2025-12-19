"""Discord UI views for task management."""

import logging
from datetime import date
from typing import TYPE_CHECKING

import discord

from ..config import (
    BUTTONS_PER_ROW,
    MAX_BUTTONS_PER_VIEW,
    VIEW_TIMEOUT_SECONDS,
)
from ..models.task import Priority, Task
from ..utils.formatting import (
    format_task_done,
    format_task_not_found,
    format_task_undone,
    format_tasks,
)

if TYPE_CHECKING:
    from ..storage.base import TaskStorage
    from .registry import ViewRegistry

logger = logging.getLogger(__name__)


class TaskButton(discord.ui.Button):
    """A button to mark a task as done/undone."""

    def __init__(
        self,
        task: Task,
        storage: "TaskStorage",
        display_index: int,
        row: int = 0,
    ) -> None:
        """Initialize the task button.

        Args:
            task: The task this button controls
            storage: The storage backend for task operations
            display_index: The position-based display number for this task
            row: The row to place this button in (0-4)
        """
        self.task = task
        self.storage = storage
        self.display_index = display_index

        # Use different style based on task status
        if task.done:
            style = discord.ButtonStyle.secondary
            emoji = "↩️"
            # Completed tasks don't have display numbers in the list,
            # so just show "Undo" without a number
            label = "Undo"
        else:
            style = discord.ButtonStyle.success
            emoji = "✅"
            label = f"Done #{display_index}"

        super().__init__(
            style=style,
            label=label,
            emoji=emoji,
            custom_id=f"task_{task.id}_{task.server_id}_"
            f"{task.channel_id}_{task.user_id}",
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Handle button click to toggle task completion status.

        Args:
            interaction: The Discord interaction
        """
        # Verify the user clicking is the task owner
        if interaction.user.id != self.task.user_id:
            logger.debug(
                "User %d tried to modify task owned by %d",
                interaction.user.id,
                self.task.user_id,
            )
            await interaction.response.send_message(
                "❌ You can only modify your own tasks.",
                ephemeral=True,
            )
            return

        logger.debug(
            "Button clicked: task #%d by user %d, done=%s",
            self.task.id,
            interaction.user.id,
            self.task.done,
        )

        # Toggle the task status
        if self.task.done:
            success = await self.storage.mark_task_undone(
                task_id=self.task.id,
                server_id=self.task.server_id,
                channel_id=self.task.channel_id,
                user_id=self.task.user_id,
            )
            if success:
                self.task.mark_undone()
                message = format_task_undone(self.task)
                logger.info(
                    "Task #%d marked undone by user %d",
                    self.task.id,
                    self.task.user_id,
                )
            else:
                message = format_task_not_found(self.task.id)
                logger.warning(
                    "Task #%d not found when marking undone",
                    self.task.id,
                )
        else:
            success = await self.storage.mark_task_done(
                task_id=self.task.id,
                server_id=self.task.server_id,
                channel_id=self.task.channel_id,
                user_id=self.task.user_id,
            )
            if success:
                self.task.mark_done()
                message = format_task_done(self.task)
                logger.info(
                    "Task #%d marked done by user %d",
                    self.task.id,
                    self.task.user_id,
                )
            else:
                message = format_task_not_found(self.task.id)
                logger.warning(
                    "Task #%d not found when marking done",
                    self.task.id,
                )

        # Send ephemeral confirmation
        await interaction.response.send_message(message, ephemeral=True)

        # Refresh the task list view
        if self.view is not None:
            await self.view.refresh(interaction)


class TaskListView(discord.ui.View):
    """A view displaying a list of tasks with interactive buttons."""

    def __init__(
        self,
        tasks: list[Task],
        storage: "TaskStorage",
        user_id: int,
        server_id: int,
        channel_id: int,
        task_date: date | None = None,
        timeout: float = VIEW_TIMEOUT_SECONDS,
        registry: "ViewRegistry | None" = None,
    ) -> None:
        """Initialize the task list view.

        Args:
            tasks: List of tasks to display
            storage: The storage backend for task operations
            user_id: The Discord user ID who owns these tasks
            server_id: The Discord server ID
            channel_id: The Discord channel ID
            task_date: Optional date for the task list
            timeout: How long the view should accept interactions (seconds)
            registry: Optional view registry for auto-refresh support
        """
        super().__init__(timeout=timeout)
        self.tasks = tasks
        self.storage = storage
        self.user_id = user_id
        self.server_id = server_id
        self.channel_id = channel_id
        self.task_date = task_date or date.today()
        self._message: discord.Message | None = None
        self._registry = registry

        logger.debug(
            "TaskListView created: %d tasks for user %d",
            len(tasks),
            user_id,
        )

        # Add buttons for each task
        self._add_task_buttons()

        # Register with the registry if provided
        if self._registry is not None:
            self._registry.register(self)

    def _add_task_buttons(self) -> None:
        """Add buttons for each task in the list.

        Buttons are ordered to match the display: grouped by priority (A, B, C),
        with incomplete tasks shown first in each group. Display indices are
        assigned sequentially to incomplete tasks only.
        """
        # Clear existing buttons
        self.clear_items()

        # Group and sort tasks the same way as format_tasks does
        grouped: dict[Priority, list[Task]] = {}
        for task in self.tasks:
            if task.priority not in grouped:
                grouped[task.priority] = []
            grouped[task.priority].append(task)

        # Sort each group: incomplete first, then completed (by id within each)
        for priority in grouped:
            grouped[priority] = sorted(
                grouped[priority], key=lambda t: (t.done, t.id)
            )

        # Build ordered list matching the display order
        ordered_tasks: list[tuple[Task, int | None]] = []
        display_index = 1

        for priority in [Priority.A, Priority.B, Priority.C]:
            priority_tasks = grouped.get(priority, [])
            for task in priority_tasks:
                if not task.done:
                    # Incomplete tasks get a display index
                    ordered_tasks.append((task, display_index))
                    display_index += 1
                else:
                    # Completed tasks don't have a display number
                    ordered_tasks.append((task, None))

        # Discord limits: 5 rows, 5 buttons per row = 25 max buttons
        tasks_to_show = ordered_tasks[:MAX_BUTTONS_PER_VIEW]

        for i, (task, task_display_index) in enumerate(tasks_to_show):
            row = i // BUTTONS_PER_ROW
            # For completed tasks, use a placeholder index (they show "Undo")
            # We'll use the position in the ordered list + 1 for display
            effective_index = (
                task_display_index if task_display_index is not None else i + 1
            )
            button = TaskButton(
                task=task,
                storage=self.storage,
                display_index=effective_index,
                row=row,
            )
            self.add_item(button)

        if len(ordered_tasks) > MAX_BUTTONS_PER_VIEW:
            logger.warning(
                "Task list truncated: %d tasks, showing %d",
                len(ordered_tasks),
                MAX_BUTTONS_PER_VIEW,
            )

    def get_content(self) -> str:
        """Get the formatted content for the task list.

        Returns:
            Formatted task list string
        """
        return format_tasks(self.tasks, self.task_date)

    async def refresh(self, interaction: discord.Interaction) -> None:
        """Refresh the task list after a change.

        Args:
            interaction: The Discord interaction that triggered the refresh
        """
        logger.debug("Refreshing task list view for user %d", self.user_id)

        # Fetch updated tasks from storage
        self.tasks = await self.storage.get_tasks(
            server_id=self.server_id,
            channel_id=self.channel_id,
            user_id=self.user_id,
            task_date=self.task_date,
        )

        # Rebuild buttons
        self._add_task_buttons()

        # Update the message with retry logic for rate limits
        try:
            # type: ignore[union-attr] - message is guaranteed to exist after button callback
            await interaction.message.edit(  # type: ignore[union-attr]
                content=self.get_content(),
                view=self,
            )
        except discord.errors.NotFound:
            logger.debug("Message was deleted, cannot refresh view")
        except discord.errors.HTTPException as e:
            if e.status == 429:  # Rate limited
                logger.warning(
                    "Rate limited while refreshing view, retry after: %s",
                    e.retry_after if hasattr(e, "retry_after") else "unknown",
                )
            else:
                logger.error("HTTP error while refreshing view: %s", e)

    async def refresh_from_storage(self) -> None:
        """Refresh the task list from storage and update the message.

        This method is called by the registry when tasks are modified
        by other commands (add, edit, delete, etc.).
        """
        if self._message is None:
            logger.debug("No message reference, cannot refresh from storage")
            return

        logger.debug("Refreshing task list from storage for user %d", self.user_id)

        # Fetch updated tasks from storage
        self.tasks = await self.storage.get_tasks(
            server_id=self.server_id,
            channel_id=self.channel_id,
            user_id=self.user_id,
            task_date=self.task_date,
        )

        # Rebuild buttons
        self._add_task_buttons()

        # Update the message
        try:
            await self._message.edit(
                content=self.get_content(),
                view=self if self.tasks else None,
            )
            logger.debug(
                "Refreshed view from storage for user %d, now has %d tasks",
                self.user_id,
                len(self.tasks),
            )
        except discord.errors.NotFound:
            logger.debug("Message was deleted, cannot refresh from storage")
            # Unregister from registry since message is gone
            if self._registry is not None:
                self._registry.unregister(self)
        except discord.errors.HTTPException as e:
            if e.status == 429:  # Rate limited
                logger.warning(
                    "Rate limited while refreshing from storage, retry after: %s",
                    e.retry_after if hasattr(e, "retry_after") else "unknown",
                )
            else:
                logger.error("HTTP error while refreshing from storage: %s", e)

    async def on_timeout(self) -> None:
        """Handle view timeout by disabling all buttons."""
        logger.debug(
            "View timeout for user %d, disabling buttons",
            self.user_id,
        )

        # Unregister from registry
        if self._registry is not None:
            self._registry.unregister(self)

        for item in self.children:  # pragma: no branch
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if self._message:
            try:
                await self._message.edit(view=self)
            except discord.errors.NotFound:
                logger.debug("Message was deleted, cannot update on timeout")
            except discord.errors.HTTPException as e:
                if e.status == 429:  # Rate limited
                    logger.warning("Rate limited on timeout, skipping update")
                else:
                    logger.error("HTTP error on timeout: %s", e)

    def set_message(self, message: discord.Message) -> None:
        """Set the message reference for timeout handling.

        Args:
            message: The Discord message containing this view
        """
        self._message = message
        logger.debug("Message reference set for view: %s", message.id)


def create_task_list_view(
    tasks: list[Task],
    storage: "TaskStorage",
    user_id: int,
    server_id: int,
    channel_id: int,
    task_date: date | None = None,
    registry: "ViewRegistry | None" = None,
) -> TaskListView:
    """Create a new task list view.

    This is a convenience function for creating TaskListView instances.

    Args:
        tasks: List of tasks to display
        storage: The storage backend
        user_id: The Discord user ID
        server_id: The Discord server ID
        channel_id: The Discord channel ID
        task_date: Optional date for the task list
        registry: Optional view registry for auto-refresh support

    Returns:
        Configured TaskListView instance
    """
    return TaskListView(
        tasks=tasks,
        storage=storage,
        user_id=user_id,
        server_id=server_id,
        channel_id=channel_id,
        task_date=task_date,
        registry=registry,
    )

"""Registry for tracking active task list views."""

import asyncio
import logging
from datetime import date
from typing import TYPE_CHECKING
from weakref import WeakSet

if TYPE_CHECKING:
    from .task_view import TaskListView

logger = logging.getLogger(__name__)

# Key type for the registry: (server_id, channel_id, user_id, task_date)
ViewKey = tuple[int, int, int, date]


class ViewRegistry:
    """Registry for tracking active TaskListView instances.

    This registry allows the bot to notify existing /list views when
    tasks are modified (added, edited, deleted, etc.) so they can
    refresh their content automatically.

    The registry uses weak references where possible to avoid memory leaks,
    and views are expected to unregister themselves on timeout.

    Thread-safety is provided via asyncio.Lock for async operations.
    """

    def __init__(self) -> None:
        """Initialize the view registry."""
        # Maps (server_id, channel_id, user_id, task_date) -> set of views
        self._views: dict[ViewKey, WeakSet["TaskListView"]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        logger.debug("ViewRegistry initialized")

    def _make_key(
        self,
        server_id: int,
        channel_id: int,
        user_id: int,
        task_date: date,
    ) -> ViewKey:
        """Create a registry key from the given parameters.

        Args:
            server_id: Discord server (guild) ID
            channel_id: Discord channel ID
            user_id: Discord user ID
            task_date: The date for the task list

        Returns:
            A tuple key for the registry
        """
        return (server_id, channel_id, user_id, task_date)

    def register(self, view: "TaskListView") -> None:
        """Register a view with the registry.

        Args:
            view: The TaskListView to register
        """
        key = self._make_key(
            view.server_id,
            view.channel_id,
            view.user_id,
            view.task_date,
        )

        if key not in self._views:
            self._views[key] = WeakSet()

        self._views[key].add(view)
        logger.debug(
            "Registered view for user %d, channel %d, date %s",
            view.user_id,
            view.channel_id,
            view.task_date,
        )

    def unregister(self, view: "TaskListView") -> None:
        """Unregister a view from the registry.

        Args:
            view: The TaskListView to unregister
        """
        key = self._make_key(
            view.server_id,
            view.channel_id,
            view.user_id,
            view.task_date,
        )

        if key in self._views:
            self._views[key].discard(view)
            # Clean up empty sets
            if not self._views[key]:
                del self._views[key]
            logger.debug(
                "Unregistered view for user %d, channel %d, date %s",
                view.user_id,
                view.channel_id,
                view.task_date,
            )

    async def notify(
        self,
        server_id: int,
        channel_id: int,
        user_id: int,
        task_date: date,
    ) -> int:
        """Notify all views matching the given parameters to refresh.

        Uses async locking to prevent race conditions during concurrent
        notifications and view modifications.

        Args:
            server_id: Discord server (guild) ID
            channel_id: Discord channel ID
            user_id: Discord user ID
            task_date: The date for the task list

        Returns:
            The number of views that were notified
        """
        async with self._lock:
            key = self._make_key(server_id, channel_id, user_id, task_date)
            views = self._views.get(key)

            if not views:
                logger.debug(
                    "No views to notify for user %d, channel %d, date %s",
                    user_id,
                    channel_id,
                    task_date,
                )
                return 0

            # Copy the set to avoid modification during iteration
            views_to_notify = list(views)

        notified = 0
        failed_views = []

        for view in views_to_notify:
            try:
                await view.refresh_from_storage()
                notified += 1
            except Exception as e:
                logger.warning(
                    "Failed to refresh view for user %d: %s",
                    user_id,
                    e,
                )
                failed_views.append(view)

        # Remove failed views outside the main loop
        for view in failed_views:
            self.unregister(view)

        logger.debug(
            "Notified %d view(s) for user %d, channel %d, date %s",
            notified,
            user_id,
            channel_id,
            task_date,
        )
        return notified

    def cleanup(self) -> int:
        """Clean up any empty entries in the registry.

        This is called periodically to remove stale entries where
        all views have been garbage collected.

        Returns:
            The number of entries removed
        """
        empty_keys = [key for key, views in self._views.items() if not views]
        for key in empty_keys:
            del self._views[key]

        if empty_keys:
            logger.debug("Cleaned up %d empty registry entries", len(empty_keys))

        return len(empty_keys)

    def get_view_count(self) -> int:
        """Get the total number of registered views.

        Returns:
            The total number of views across all keys
        """
        return sum(len(views) for views in self._views.values())

    def get_key_count(self) -> int:
        """Get the number of unique keys in the registry.

        Returns:
            The number of unique (server, channel, user, date) combinations
        """
        return len(self._views)

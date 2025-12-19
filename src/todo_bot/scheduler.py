"""Background scheduler for automatic midnight task rollover."""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

import aiosqlite
from discord.ext import commands, tasks

from .config import DEFAULT_ROLLOVER_HOUR_UTC
from .exceptions import StorageError
from .storage.base import TaskStorage

logger = logging.getLogger(__name__)


def seconds_until_next_rollover_hour(rollover_hour: int = DEFAULT_ROLLOVER_HOUR_UTC) -> float:
    """Calculate seconds until the next rollover hour in UTC.

    Args:
        rollover_hour: The hour (0-23) at which rollover should occur

    Returns:
        Number of seconds until the next rollover hour
    """
    now = datetime.now(timezone.utc)
    # Calculate next rollover time
    next_rollover = datetime(
        now.year, now.month, now.day, rollover_hour, 0, 0, tzinfo=timezone.utc
    )
    # If we've already passed the rollover hour today, schedule for tomorrow
    if now >= next_rollover:
        next_rollover += timedelta(days=1)
    delta = next_rollover - now
    return delta.total_seconds()


def get_yesterday_and_today() -> tuple[date, date]:
    """Get yesterday's and today's dates.

    Returns:
        Tuple of (yesterday, today) dates
    """
    today = date.today()
    yesterday = today - timedelta(days=1)
    return yesterday, today


class RolloverScheduler(commands.Cog):
    """Cog that handles automatic rollover of incomplete tasks.

    This scheduler runs a background task that triggers at the configured
    rollover hour each day. When triggered, it copies all incomplete tasks
    from the previous day to the new day's list while preserving the originals.
    """

    def __init__(
        self,
        bot: commands.Bot,
        storage: TaskStorage,
        rollover_hour: int = DEFAULT_ROLLOVER_HOUR_UTC,
    ) -> None:
        """Initialize the rollover scheduler.

        Args:
            bot: The Discord bot instance
            storage: The task storage backend
            rollover_hour: The hour (0-23) in UTC at which to perform rollover
        """
        self.bot = bot
        self.storage = storage
        self.rollover_hour = rollover_hour
        self._last_rollover_date: date | None = None

    def cog_load(self) -> None:
        """Called when the cog is loaded. Starts the rollover task."""
        self.midnight_rollover_task.start()
        logger.info("Rollover scheduler started")

    def cog_unload(self) -> None:
        """Called when the cog is unloaded. Stops the rollover task."""
        self.midnight_rollover_task.cancel()
        logger.info("Rollover scheduler stopped")

    @tasks.loop(hours=24)
    async def midnight_rollover_task(self) -> None:
        """Background task that runs daily to rollover incomplete tasks.

        This task runs at midnight UTC and copies incomplete tasks from
        yesterday to today.
        """
        yesterday, today = get_yesterday_and_today()

        # Prevent duplicate rollovers on the same day
        if self._last_rollover_date == today:
            logger.debug("Rollover already performed for %s, skipping", today)
            return

        logger.info("Running midnight rollover from %s to %s", yesterday, today)

        try:
            total_rolled = await self.storage.rollover_incomplete_tasks(
                from_date=yesterday,
                to_date=today,
            )

            self._last_rollover_date = today

            if total_rolled > 0:
                logger.info(
                    "Midnight rollover complete: %d tasks rolled over", total_rolled
                )
            else:
                logger.info("Midnight rollover complete: no incomplete tasks to roll over")
        except (StorageError, aiosqlite.Error) as e:
            logger.error("Database error during midnight rollover: %s", e, exc_info=True)
        except OSError as e:
            logger.error("I/O error during midnight rollover: %s", e, exc_info=True)

    @midnight_rollover_task.before_loop
    async def before_midnight_rollover(self) -> None:
        """Wait until the configured rollover hour before starting the loop."""
        await self.bot.wait_until_ready()

        seconds_to_wait = seconds_until_next_rollover_hour(self.rollover_hour)
        hours = seconds_to_wait / 3600
        logger.info(
            "Rollover scheduler waiting %.1f hours until next rollover time (%02d:00 UTC)",
            hours,
            self.rollover_hour,
        )

        # For the first run, we wait until the rollover hour
        # Subsequent runs are handled by the 24-hour loop
        await asyncio.sleep(seconds_to_wait)

    async def perform_manual_rollover(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> int:
        """Manually trigger a rollover operation.

        This can be called from a slash command to manually trigger
        the rollover process.

        Args:
            from_date: Source date (defaults to yesterday)
            to_date: Target date (defaults to today)

        Returns:
            Number of tasks rolled over
        """
        if from_date is None or to_date is None:
            yesterday, today = get_yesterday_and_today()
            from_date = from_date or yesterday
            to_date = to_date or today

        logger.info("Manual rollover requested from %s to %s", from_date, to_date)

        total_rolled = await self.storage.rollover_incomplete_tasks(
            from_date=from_date,
            to_date=to_date,
        )

        return total_rolled


async def setup_scheduler(
    bot: commands.Bot,
    storage: TaskStorage,
    rollover_hour: int = DEFAULT_ROLLOVER_HOUR_UTC,
) -> RolloverScheduler:
    """Set up and add the rollover scheduler cog.

    Args:
        bot: The Discord bot instance
        storage: The task storage backend
        rollover_hour: The hour (0-23) in UTC at which to perform rollover

    Returns:
        The RolloverScheduler cog instance
    """
    scheduler = RolloverScheduler(bot, storage, rollover_hour=rollover_hour)
    await bot.add_cog(scheduler)
    return scheduler

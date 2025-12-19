"""Background scheduler for automatic midnight task rollover."""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from discord.ext import commands, tasks

from .config import ROLLOVER_HOUR_UTC
from .storage.base import TaskStorage

logger = logging.getLogger(__name__)


def seconds_until_next_midnight_utc() -> float:
    """Calculate seconds until the next midnight UTC.

    Returns:
        Number of seconds until midnight UTC
    """
    now = datetime.now(timezone.utc)
    # Next midnight is at 00:00:00 the next day
    next_midnight = datetime(
        now.year, now.month, now.day, ROLLOVER_HOUR_UTC, 0, 0, tzinfo=timezone.utc
    ) + timedelta(days=1)
    delta = next_midnight - now
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
    """Cog that handles automatic midnight rollover of incomplete tasks.

    This scheduler runs a background task that triggers at midnight UTC
    each day. When triggered, it copies all incomplete tasks from the
    previous day to the new day's list while preserving the originals.
    """

    def __init__(self, bot: commands.Bot, storage: TaskStorage) -> None:
        """Initialize the rollover scheduler.

        Args:
            bot: The Discord bot instance
            storage: The task storage backend
        """
        self.bot = bot
        self.storage = storage
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
        except Exception as e:
            logger.error("Error during midnight rollover: %s", e, exc_info=True)

    @midnight_rollover_task.before_loop
    async def before_midnight_rollover(self) -> None:
        """Wait until midnight UTC before starting the rollover loop."""
        await self.bot.wait_until_ready()

        seconds_to_wait = seconds_until_next_midnight_utc()
        hours = seconds_to_wait / 3600
        logger.info(
            "Rollover scheduler waiting %.1f hours until next midnight UTC",
            hours,
        )

        # For the first run, we wait until midnight
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


async def setup_scheduler(bot: commands.Bot, storage: TaskStorage) -> RolloverScheduler:
    """Set up and add the rollover scheduler cog.

    Args:
        bot: The Discord bot instance
        storage: The task storage backend

    Returns:
        The RolloverScheduler cog instance
    """
    scheduler = RolloverScheduler(bot, storage)
    await bot.add_cog(scheduler)
    return scheduler

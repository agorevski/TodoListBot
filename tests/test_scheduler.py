"""Tests for the rollover scheduler module."""

import asyncio
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from todo_bot.exceptions import StorageError
from todo_bot.scheduler import (
    RolloverScheduler,
    get_yesterday_and_today,
    seconds_until_next_rollover_hour,
    setup_scheduler,
)


class TestSecondsUntilNextRolloverHour:
    """Tests for seconds_until_next_rollover_hour function."""

    def test_returns_positive_value(self) -> None:
        """Test that seconds_until_next_rollover_hour returns a positive value.

        Verifies that the function always returns a positive number of seconds
        until the next rollover hour.
        """
        seconds = seconds_until_next_rollover_hour()
        assert seconds > 0

    def test_returns_less_than_24_hours(self) -> None:
        """Test that seconds_until_next_rollover_hour returns less than 24 hours.

        Verifies that the function never returns more than 24 hours worth
        of seconds since rollover occurs daily.
        """
        seconds = seconds_until_next_rollover_hour()
        assert seconds < 24 * 60 * 60

    def test_at_midnight_returns_about_24_hours(self) -> None:
        """Test that at midnight, function returns approximately 24 hours.

        When called at exactly midnight UTC with a midnight rollover hour,
        the function should return approximately 24 hours until the next
        rollover.
        """
        # Mock datetime.now to return exactly midnight
        mock_now = datetime(2024, 12, 15, 0, 0, 0, tzinfo=timezone.utc)
        with patch("todo_bot.scheduler.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            seconds = seconds_until_next_rollover_hour(rollover_hour=0)
            # Should be approximately 24 hours (minus a few microseconds)
            assert 23 * 3600 < seconds <= 24 * 3600

    def test_at_noon_returns_about_12_hours(self) -> None:
        """Test that at noon UTC, function returns approximately 12 hours.

        When called at noon UTC with a midnight rollover hour, the function
        should return approximately 12 hours until the next rollover.
        """
        mock_now = datetime(2024, 12, 15, 12, 0, 0, tzinfo=timezone.utc)
        with patch("todo_bot.scheduler.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            seconds = seconds_until_next_rollover_hour(rollover_hour=0)
            # Should be approximately 12 hours
            assert 11 * 3600 < seconds <= 12 * 3600

    def test_custom_rollover_hour(self) -> None:
        """Test that function works correctly with a custom rollover hour.

        When called at 10:00 UTC with a rollover hour of 14:00, the function
        should return approximately 4 hours until the next rollover.
        """
        # At 10:00 UTC, if rollover is at 14:00, should be about 4 hours
        mock_now = datetime(2024, 12, 15, 10, 0, 0, tzinfo=timezone.utc)
        with patch("todo_bot.scheduler.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            seconds = seconds_until_next_rollover_hour(rollover_hour=14)
            # Should be approximately 4 hours
            assert 3 * 3600 < seconds <= 4 * 3600

    def test_rollover_hour_passed_today(self) -> None:
        """Test that function returns time until tomorrow when rollover hour passed.

        When called at 16:00 UTC with a rollover hour of 14:00, the function
        should return approximately 22 hours until tomorrow's rollover.
        """
        # At 16:00 UTC, if rollover is at 14:00, should be about 22 hours
        mock_now = datetime(2024, 12, 15, 16, 0, 0, tzinfo=timezone.utc)
        with patch("todo_bot.scheduler.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            seconds = seconds_until_next_rollover_hour(rollover_hour=14)
            # Should be approximately 22 hours (until 14:00 tomorrow)
            assert 21 * 3600 < seconds <= 22 * 3600


class TestGetYesterdayAndToday:
    """Tests for get_yesterday_and_today function."""

    def test_returns_correct_dates(self) -> None:
        """Test that get_yesterday_and_today returns correct date values.

        Verifies that the function returns today's date and yesterday's date
        as a tuple in the correct order.
        """
        yesterday, today = get_yesterday_and_today()
        
        assert today == date.today()
        assert yesterday == date.today() - timedelta(days=1)

    def test_returns_tuple_of_dates(self) -> None:
        """Test that get_yesterday_and_today returns a tuple of date objects.

        Verifies that the function returns a tuple containing exactly two
        date objects.
        """
        result = get_yesterday_and_today()
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], date)
        assert isinstance(result[1], date)

    def test_yesterday_is_before_today(self) -> None:
        """Test that yesterday is exactly one day before today.

        Verifies that the returned yesterday date is less than today
        and the difference is exactly one day.
        """
        yesterday, today = get_yesterday_and_today()
        
        assert yesterday < today
        assert (today - yesterday).days == 1


class TestRolloverScheduler:
    """Tests for RolloverScheduler class."""

    @pytest.fixture
    def mock_bot(self) -> MagicMock:
        """Create a mock Discord bot for testing.

        Returns:
            MagicMock: A mock bot instance with wait_until_ready configured
                as an async mock.
        """
        bot = MagicMock()
        bot.wait_until_ready = AsyncMock()
        return bot

    @pytest.fixture
    def mock_storage(self) -> MagicMock:
        """Create a mock storage backend for testing.

        Returns:
            MagicMock: A mock storage instance with rollover_incomplete_tasks
                configured as an async mock returning 0.
        """
        storage = MagicMock()
        storage.rollover_incomplete_tasks = AsyncMock(return_value=0)
        return storage

    @pytest.fixture
    def scheduler(self, mock_bot: MagicMock, mock_storage: MagicMock) -> RolloverScheduler:
        """Create a RolloverScheduler instance for testing.

        Args:
            mock_bot: The mock Discord bot fixture.
            mock_storage: The mock storage backend fixture.

        Returns:
            RolloverScheduler: A scheduler instance configured with mocks.
        """
        return RolloverScheduler(mock_bot, mock_storage)

    def test_init(self, scheduler: RolloverScheduler, mock_bot: MagicMock, mock_storage: MagicMock) -> None:
        """Test RolloverScheduler initialization with default values.

        Args:
            scheduler: The scheduler fixture.
            mock_bot: The mock bot fixture.
            mock_storage: The mock storage fixture.
        """
        assert scheduler.bot is mock_bot
        assert scheduler.storage is mock_storage
        assert scheduler.rollover_hour == 0  # Default
        assert scheduler._last_rollover_date is None

    def test_init_with_custom_rollover_hour(self, mock_bot: MagicMock, mock_storage: MagicMock) -> None:
        """Test RolloverScheduler initialization with custom rollover hour.

        Args:
            mock_bot: The mock bot fixture.
            mock_storage: The mock storage fixture.
        """
        scheduler = RolloverScheduler(mock_bot, mock_storage, rollover_hour=14)
        assert scheduler.rollover_hour == 14

    def test_cog_load_starts_task(self, scheduler: RolloverScheduler) -> None:
        """Test that cog_load starts the midnight rollover background task.

        Args:
            scheduler: The scheduler fixture.
        """
        with patch.object(scheduler.midnight_rollover_task, "start") as mock_start:
            scheduler.cog_load()
            mock_start.assert_called_once()

    def test_cog_unload_cancels_task(self, scheduler: RolloverScheduler) -> None:
        """Test that cog_unload cancels the midnight rollover background task.

        Args:
            scheduler: The scheduler fixture.
        """
        with patch.object(scheduler.midnight_rollover_task, "cancel") as mock_cancel:
            scheduler.cog_unload()
            mock_cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_midnight_rollover_task_calls_storage(
        self, scheduler: RolloverScheduler, mock_storage: MagicMock
    ) -> None:
        """Test that midnight_rollover_task calls storage rollover method.

        Verifies that the task calls rollover_incomplete_tasks with correct
        date parameters (yesterday and today).

        Args:
            scheduler: The scheduler fixture.
            mock_storage: The mock storage fixture.
        """
        mock_storage.rollover_incomplete_tasks.return_value = 5
        
        await scheduler.midnight_rollover_task()
        
        mock_storage.rollover_incomplete_tasks.assert_called_once()
        # Verify it was called with yesterday and today
        call_args = mock_storage.rollover_incomplete_tasks.call_args
        assert call_args.kwargs["from_date"] == date.today() - timedelta(days=1)
        assert call_args.kwargs["to_date"] == date.today()

    @pytest.mark.asyncio
    async def test_midnight_rollover_task_sets_last_rollover_date(
        self, scheduler: RolloverScheduler, mock_storage: MagicMock
    ) -> None:
        """Test that midnight_rollover_task updates the last rollover date.

        Verifies that after a successful rollover, the _last_rollover_date
        attribute is set to today's date.

        Args:
            scheduler: The scheduler fixture.
            mock_storage: The mock storage fixture.
        """
        assert scheduler._last_rollover_date is None
        
        await scheduler.midnight_rollover_task()
        
        assert scheduler._last_rollover_date == date.today()

    @pytest.mark.asyncio
    async def test_midnight_rollover_task_skips_if_already_done_today(
        self, scheduler: RolloverScheduler, mock_storage: MagicMock
    ) -> None:
        """Test that midnight_rollover_task skips if already run today.

        Verifies that the task does not call storage when rollover was
        already performed on the current date.

        Args:
            scheduler: The scheduler fixture.
            mock_storage: The mock storage fixture.
        """
        scheduler._last_rollover_date = date.today()
        
        await scheduler.midnight_rollover_task()
        
        # Should not call storage since we already rolled over today
        mock_storage.rollover_incomplete_tasks.assert_not_called()

    @pytest.mark.asyncio
    async def test_midnight_rollover_task_handles_exception(
        self, scheduler: RolloverScheduler, mock_storage: MagicMock
    ) -> None:
        """Test that midnight_rollover_task handles storage exceptions gracefully.

        Verifies that when a StorageError is raised, the task does not
        propagate the exception and does not update the last rollover date.

        Args:
            scheduler: The scheduler fixture.
            mock_storage: The mock storage fixture.
        """
        mock_storage.rollover_incomplete_tasks.side_effect = StorageError("Database error")
        
        # Should not raise
        await scheduler.midnight_rollover_task()
        
        # Last rollover date should not be set on error
        assert scheduler._last_rollover_date is None

    @pytest.mark.asyncio
    async def test_perform_manual_rollover_uses_defaults(
        self, scheduler: RolloverScheduler, mock_storage: MagicMock
    ) -> None:
        """Test that perform_manual_rollover uses default date range.

        Verifies that when called without arguments, the method uses
        yesterday as from_date and today as to_date.

        Args:
            scheduler: The scheduler fixture.
            mock_storage: The mock storage fixture.
        """
        mock_storage.rollover_incomplete_tasks.return_value = 3
        
        result = await scheduler.perform_manual_rollover()
        
        assert result == 3
        call_args = mock_storage.rollover_incomplete_tasks.call_args
        assert call_args.kwargs["from_date"] == date.today() - timedelta(days=1)
        assert call_args.kwargs["to_date"] == date.today()

    @pytest.mark.asyncio
    async def test_perform_manual_rollover_with_custom_dates(
        self, scheduler: RolloverScheduler, mock_storage: MagicMock
    ) -> None:
        """Test that perform_manual_rollover accepts custom date range.

        Verifies that the method correctly passes custom from_date and
        to_date parameters to the storage backend.

        Args:
            scheduler: The scheduler fixture.
            mock_storage: The mock storage fixture.
        """
        custom_from = date(2024, 12, 1)
        custom_to = date(2024, 12, 2)
        mock_storage.rollover_incomplete_tasks.return_value = 2
        
        result = await scheduler.perform_manual_rollover(
            from_date=custom_from,
            to_date=custom_to,
        )
        
        assert result == 2
        mock_storage.rollover_incomplete_tasks.assert_called_once_with(
            from_date=custom_from,
            to_date=custom_to,
        )

    @pytest.mark.asyncio
    async def test_before_midnight_rollover_waits_for_ready(
        self, scheduler: RolloverScheduler, mock_bot: MagicMock
    ) -> None:
        """Test that before_midnight_rollover waits for bot to be ready.

        Verifies that the before hook waits for the bot to be ready and
        then sleeps until the next rollover hour.

        Args:
            scheduler: The scheduler fixture.
            mock_bot: The mock bot fixture.
        """
        with patch("todo_bot.scheduler.seconds_until_next_rollover_hour", return_value=0.01):
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                await scheduler.before_midnight_rollover()
                
                mock_bot.wait_until_ready.assert_called_once()
                mock_sleep.assert_called_once()


class TestSetupScheduler:
    """Tests for setup_scheduler function."""

    @pytest.mark.asyncio
    async def test_setup_scheduler_adds_cog(self) -> None:
        """Test that setup_scheduler adds the RolloverScheduler cog to the bot.

        Verifies that the function creates a RolloverScheduler and registers
        it as a cog with the bot.
        """
        mock_bot = MagicMock()
        mock_bot.add_cog = AsyncMock()
        mock_storage = MagicMock()
        
        scheduler = await setup_scheduler(mock_bot, mock_storage)
        
        assert isinstance(scheduler, RolloverScheduler)
        mock_bot.add_cog.assert_called_once_with(scheduler)

    @pytest.mark.asyncio
    async def test_setup_scheduler_with_custom_rollover_hour(self) -> None:
        """Test that setup_scheduler accepts a custom rollover hour.

        Verifies that the function correctly passes the rollover_hour
        parameter to the RolloverScheduler constructor.
        """
        mock_bot = MagicMock()
        mock_bot.add_cog = AsyncMock()
        mock_storage = MagicMock()
        
        scheduler = await setup_scheduler(mock_bot, mock_storage, rollover_hour=6)
        
        assert scheduler.rollover_hour == 6

    @pytest.mark.asyncio
    async def test_setup_scheduler_returns_scheduler(self) -> None:
        """Test that setup_scheduler returns the configured scheduler instance.

        Verifies that the function returns a RolloverScheduler with the
        correct bot and storage references.
        """
        mock_bot = MagicMock()
        mock_bot.add_cog = AsyncMock()
        mock_storage = MagicMock()
        
        result = await setup_scheduler(mock_bot, mock_storage)
        
        assert isinstance(result, RolloverScheduler)
        assert result.bot is mock_bot
        assert result.storage is mock_storage

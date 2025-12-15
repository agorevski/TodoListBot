"""Task management slash commands for the Discord A/B/C Todo Bot."""

import logging
import time
from datetime import date, datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ..config import (
    RATE_LIMIT_COMMANDS,
    RATE_LIMIT_SECONDS,
    MAX_DESCRIPTION_LENGTH,
)
from ..models.task import Priority
from ..storage.base import TaskStorage
from ..utils.formatting import (
    format_task_added,
    format_task_done,
    format_task_not_found,
    format_tasks_cleared,
    format_task_deleted,
    format_task_updated,
)
from ..views.task_view import TaskListView

logger = logging.getLogger(__name__)


class TasksCog(commands.Cog):
    """Cog containing task management slash commands."""

    # Class-level start time tracking (shared across instances but not global)
    _start_time: Optional[float] = None

    def __init__(self, bot: commands.Bot, storage: TaskStorage) -> None:
        """Initialize the tasks cog.

        Args:
            bot: The Discord bot instance
            storage: The task storage backend
        """
        self.bot = bot
        self.storage = storage
        # Set start time on first instantiation
        if TasksCog._start_time is None:
            TasksCog._start_time = time.time()

    @classmethod
    def get_uptime(cls) -> float:
        """Get bot uptime in seconds.

        Returns:
            Uptime in seconds, or 0.0 if not started
        """
        if cls._start_time is None:
            return 0.0
        return time.time() - cls._start_time

    @classmethod
    def reset_start_time(cls) -> None:
        """Reset start time (useful for testing)."""
        cls._start_time = None

    @app_commands.command(name="add", description="Add a new task")
    @app_commands.describe(
        priority="Task priority (A = highest, B = medium, C = lowest)",
        description="Task description",
    )
    @app_commands.choices(
        priority=[
            app_commands.Choice(name="A - High Priority", value="A"),
            app_commands.Choice(name="B - Medium Priority", value="B"),
            app_commands.Choice(name="C - Low Priority", value="C"),
        ]
    )
    @app_commands.checks.cooldown(
        RATE_LIMIT_COMMANDS, RATE_LIMIT_SECONDS, key=lambda i: i.user.id
    )
    async def add_task(
        self,
        interaction: discord.Interaction,
        priority: str,
        description: str,
    ) -> None:
        """Add a new task with the specified priority and description.

        Args:
            interaction: The Discord interaction
            priority: Task priority (A, B, or C)
            description: Task description text
        """
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.",
                ephemeral=True,
            )
            return

        # Validate description length
        if len(description) > MAX_DESCRIPTION_LENGTH:
            await interaction.response.send_message(
                f"❌ Description too long ({len(description)} chars). "
                f"Maximum is {MAX_DESCRIPTION_LENGTH} characters.",
                ephemeral=True,
            )
            return

        try:
            task_priority = Priority.from_string(priority)
        except ValueError as e:
            await interaction.response.send_message(
                f"❌ {e}",
                ephemeral=True,
            )
            return

        logger.info(
            "User %s adding task in guild %s, channel %s",
            interaction.user.id,
            interaction.guild.id,
            interaction.channel_id,
        )

        task = await self.storage.add_task(
            description=description,
            priority=task_priority,
            server_id=interaction.guild.id,
            channel_id=interaction.channel_id,
            user_id=interaction.user.id,
        )

        logger.info("Task #%s created for user %s", task.id, interaction.user.id)
        await interaction.response.send_message(format_task_added(task))

    @app_commands.command(name="list", description="List your tasks")
    @app_commands.describe(
        date_str="Optional date in YYYY-MM-DD format (defaults to today)",
    )
    @app_commands.checks.cooldown(
        RATE_LIMIT_COMMANDS, RATE_LIMIT_SECONDS, key=lambda i: i.user.id
    )
    async def list_tasks(
        self,
        interaction: discord.Interaction,
        date_str: Optional[str] = None,
    ) -> None:
        """List tasks for the current user.

        Args:
            interaction: The Discord interaction
            date_str: Optional date string in YYYY-MM-DD format
        """
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.",
                ephemeral=True,
            )
            return

        # Parse the date if provided
        task_date: date
        if date_str:
            try:
                task_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid date format. "
                    "Please use YYYY-MM-DD (e.g., 2024-12-25).",
                    ephemeral=True,
                )
                return
        else:
            task_date = date.today()

        logger.debug(
            "User %s listing tasks for date %s",
            interaction.user.id,
            task_date,
        )

        tasks = await self.storage.get_tasks(
            server_id=interaction.guild.id,
            channel_id=interaction.channel_id,
            user_id=interaction.user.id,
            task_date=task_date,
        )

        view = TaskListView(
            tasks=tasks,
            storage=self.storage,
            user_id=interaction.user.id,
            server_id=interaction.guild.id,
            channel_id=interaction.channel_id,
            task_date=task_date,
        )

        await interaction.response.send_message(
            content=view.get_content(),
            view=view if tasks else None,
        )

        # Store message reference for timeout handling
        message = await interaction.original_response()
        view.set_message(message)

    @app_commands.command(name="done", description="Mark a task as completed")
    @app_commands.describe(task_id="The ID of the task to mark as done")
    @app_commands.checks.cooldown(
        RATE_LIMIT_COMMANDS, RATE_LIMIT_SECONDS, key=lambda i: i.user.id
    )
    async def mark_done(
        self,
        interaction: discord.Interaction,
        task_id: int,
    ) -> None:
        """Mark a task as completed by its ID.

        Args:
            interaction: The Discord interaction
            task_id: The task ID to mark as done
        """
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.",
                ephemeral=True,
            )
            return

        task = await self.storage.get_task_by_id(
            task_id=task_id,
            server_id=interaction.guild.id,
            channel_id=interaction.channel_id,
            user_id=interaction.user.id,
        )

        if not task:
            await interaction.response.send_message(
                format_task_not_found(task_id),
                ephemeral=True,
            )
            return

        success = await self.storage.mark_task_done(
            task_id=task_id,
            server_id=interaction.guild.id,
            channel_id=interaction.channel_id,
            user_id=interaction.user.id,
        )

        if success:
            task.mark_done()
            logger.info(
                "Task #%s marked done by user %s",
                task_id,
                interaction.user.id,
            )
            await interaction.response.send_message(format_task_done(task))
        else:
            await interaction.response.send_message(
                format_task_not_found(task_id),
                ephemeral=True,
            )

    @app_commands.command(name="edit", description="Edit a task")
    @app_commands.describe(
        task_id="The ID of the task to edit",
        description="New description (optional)",
        priority="New priority (optional)",
    )
    @app_commands.choices(
        priority=[
            app_commands.Choice(name="A - High Priority", value="A"),
            app_commands.Choice(name="B - Medium Priority", value="B"),
            app_commands.Choice(name="C - Low Priority", value="C"),
        ]
    )
    @app_commands.checks.cooldown(
        RATE_LIMIT_COMMANDS, RATE_LIMIT_SECONDS, key=lambda i: i.user.id
    )
    async def edit_task(
        self,
        interaction: discord.Interaction,
        task_id: int,
        description: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> None:
        """Edit a task's description and/or priority.

        Args:
            interaction: The Discord interaction
            task_id: The task ID to edit
            description: New description (optional)
            priority: New priority (optional)
        """
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.",
                ephemeral=True,
            )
            return

        if description is None and priority is None:
            await interaction.response.send_message(
                "❌ Please provide a new description and/or priority.",
                ephemeral=True,
            )
            return

        # Validate description length if provided
        if description and len(description) > MAX_DESCRIPTION_LENGTH:
            await interaction.response.send_message(
                f"❌ Description too long ({len(description)} chars). "
                f"Maximum is {MAX_DESCRIPTION_LENGTH} characters.",
                ephemeral=True,
            )
            return

        # Parse priority if provided
        task_priority: Optional[Priority] = None
        if priority:
            try:
                task_priority = Priority.from_string(priority)
            except ValueError as e:
                await interaction.response.send_message(
                    f"❌ {e}",
                    ephemeral=True,
                )
                return

        # Check if task exists
        task = await self.storage.get_task_by_id(
            task_id=task_id,
            server_id=interaction.guild.id,
            channel_id=interaction.channel_id,
            user_id=interaction.user.id,
        )

        if not task:
            await interaction.response.send_message(
                format_task_not_found(task_id),
                ephemeral=True,
            )
            return

        success = await self.storage.update_task(
            task_id=task_id,
            server_id=interaction.guild.id,
            channel_id=interaction.channel_id,
            user_id=interaction.user.id,
            description=description,
            priority=task_priority,
        )

        if success:
            logger.info(
                "Task #%s updated by user %s",
                task_id,
                interaction.user.id,
            )
            await interaction.response.send_message(
                format_task_updated(task_id, description, task_priority)
            )
        else:
            await interaction.response.send_message(
                format_task_not_found(task_id),
                ephemeral=True,
            )

    @app_commands.command(name="delete", description="Delete a task")
    @app_commands.describe(task_id="The ID of the task to delete")
    @app_commands.checks.cooldown(
        RATE_LIMIT_COMMANDS, RATE_LIMIT_SECONDS, key=lambda i: i.user.id
    )
    async def delete_task(
        self,
        interaction: discord.Interaction,
        task_id: int,
    ) -> None:
        """Delete a task by its ID.

        Args:
            interaction: The Discord interaction
            task_id: The task ID to delete
        """
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.",
                ephemeral=True,
            )
            return

        task = await self.storage.get_task_by_id(
            task_id=task_id,
            server_id=interaction.guild.id,
            channel_id=interaction.channel_id,
            user_id=interaction.user.id,
        )

        if not task:
            await interaction.response.send_message(
                format_task_not_found(task_id),
                ephemeral=True,
            )
            return

        success = await self.storage.delete_task(
            task_id=task_id,
            server_id=interaction.guild.id,
            channel_id=interaction.channel_id,
            user_id=interaction.user.id,
        )

        if success:
            logger.info(
                "Task #%s deleted by user %s",
                task_id,
                interaction.user.id,
            )
            await interaction.response.send_message(format_task_deleted(task))
        else:
            await interaction.response.send_message(
                format_task_not_found(task_id),
                ephemeral=True,
            )

    @app_commands.command(name="clear", description="Remove all completed tasks")
    @app_commands.checks.cooldown(
        RATE_LIMIT_COMMANDS, RATE_LIMIT_SECONDS, key=lambda i: i.user.id
    )
    async def clear_tasks(
        self,
        interaction: discord.Interaction,
    ) -> None:
        """Remove all completed tasks for the current user.

        Args:
            interaction: The Discord interaction
        """
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.",
                ephemeral=True,
            )
            return

        count = await self.storage.clear_completed_tasks(
            server_id=interaction.guild.id,
            channel_id=interaction.channel_id,
            user_id=interaction.user.id,
        )

        logger.info(
            "User %s cleared %d completed tasks",
            interaction.user.id,
            count,
        )
        await interaction.response.send_message(format_tasks_cleared(count))

    @app_commands.command(name="status", description="Show bot status and stats")
    @app_commands.checks.cooldown(
        RATE_LIMIT_COMMANDS, RATE_LIMIT_SECONDS, key=lambda i: i.user.id
    )
    async def status(
        self,
        interaction: discord.Interaction,
    ) -> None:
        """Show bot status and database statistics.

        Args:
            interaction: The Discord interaction
        """
        # Get database stats
        try:
            stats = await self.storage.get_stats()
        except Exception as e:
            logger.error("Failed to get storage stats: %s", e)
            stats = {"error": str(e)}

        # Calculate uptime
        uptime_seconds = self.get_uptime()
        hours, remainder = divmod(int(uptime_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        # Build status message
        embed = discord.Embed(
            title="📊 Bot Status",
            color=discord.Color.green(),
        )

        embed.add_field(
            name="⏱️ Uptime",
            value=uptime_str,
            inline=True,
        )

        embed.add_field(
            name="🏠 Servers",
            value=str(len(self.bot.guilds)),
            inline=True,
        )

        embed.add_field(
            name="📡 Latency",
            value=f"{self.bot.latency * 1000:.0f}ms",
            inline=True,
        )

        if "error" not in stats:
            embed.add_field(
                name="📝 Total Tasks",
                value=str(stats.get("total_tasks", "N/A")),
                inline=True,
            )

            embed.add_field(
                name="👥 Unique Users",
                value=str(stats.get("unique_users", "N/A")),
                inline=True,
            )

            embed.add_field(
                name="🗄️ Schema Version",
                value=str(stats.get("schema_version", "N/A")),
                inline=True,
            )
        else:
            embed.add_field(
                name="⚠️ Database",
                value="Error fetching stats",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        """Handle errors from app commands.

        Args:
            interaction: The Discord interaction
            error: The error that occurred
        """
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ Slow down! Try again in {error.retry_after:.1f} seconds.",
                ephemeral=True,
            )
        else:
            logger.exception(
                "Command error for user %s: %s",
                interaction.user.id,
                error,
            )
            await interaction.response.send_message(
                "❌ An error occurred while processing your command.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot, storage: TaskStorage) -> None:
    """Set up the tasks cog.

    Args:
        bot: The Discord bot instance
        storage: The task storage backend
    """
    await bot.add_cog(TasksCog(bot, storage))

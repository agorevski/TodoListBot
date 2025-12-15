"""Task model and Priority enum for the Discord A/B/C Todo Bot."""

import logging
from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from ..config import MAX_DESCRIPTION_LENGTH, MIN_DESCRIPTION_LENGTH

logger = logging.getLogger(__name__)


class Priority(Enum):
    """Task priority levels using A/B/C system."""

    A = "A"  # Highest priority
    B = "B"  # Medium priority
    C = "C"  # Lowest priority

    @property
    def emoji(self) -> str:
        """Return the emoji representation for this priority."""
        emoji_map = {
            Priority.A: "🔴",
            Priority.B: "🟡",
            Priority.C: "🟢",
        }
        return emoji_map[self]

    @property
    def display_name(self) -> str:
        """Return the display name for this priority."""
        return f"{self.emoji} **{self.value}-Priority**"

    @classmethod
    def from_string(cls, value: str) -> "Priority":
        """Create a Priority from a string value.

        Args:
            value: String representation of priority (A, B, or C)

        Returns:
            Priority enum value

        Raises:
            ValueError: If the value is not a valid priority
        """
        value = value.upper().strip()
        if value not in ("A", "B", "C"):
            raise ValueError(f"Invalid priority: {value}. Must be A, B, or C.")
        return cls(value)


@dataclass
class Task:
    """Represents a task in the todo list.

    Attributes:
        id: Unique identifier for the task
        description: Task description text
        priority: Task priority (A, B, or C)
        done: Whether the task is completed
        task_date: The date this task is for (defaults to today)
        server_id: Discord server (guild) ID
        channel_id: Discord channel ID
        user_id: Discord user ID
    """

    id: int
    description: str
    priority: Priority
    server_id: int
    channel_id: int
    user_id: int
    done: bool = False
    task_date: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        """Validate and normalize task data after initialization."""
        # Convert string priority to enum if needed
        if isinstance(self.priority, str):
            self.priority = Priority.from_string(self.priority)

        # Normalize description
        self.description = self.description.strip() if self.description else ""

        # Validate minimum description length
        if len(self.description) < MIN_DESCRIPTION_LENGTH:
            raise ValueError(
                f"Task description must be at least "
                f"{MIN_DESCRIPTION_LENGTH} character(s)."
            )

        # Validate maximum description length
        if len(self.description) > MAX_DESCRIPTION_LENGTH:
            desc_len = len(self.description)
            raise ValueError(
                f"Task description too long ({desc_len} chars). "
                f"Maximum is {MAX_DESCRIPTION_LENGTH} characters."
            )

        logger.debug(
            "Task created: id=%s, priority=%s, user=%s",
            self.id,
            self.priority.value,
            self.user_id,
        )

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        return (
            f"Task(id={self.id}, "
            f"priority={self.priority.value}, "
            f"done={self.done}, "
            f"user_id={self.user_id}, "
            f"description={self.description[:30]!r}"
            f"{'...' if len(self.description) > 30 else ''})"
        )

    @property
    def display_text(self) -> str:
        """Return the formatted display text for this task.

        Returns:
            Formatted string with task ID, description, and strikethrough if done
        """
        if self.done:
            return f"~~{self.id}. {self.description}~~"
        return f"{self.id}. {self.description}"

    @property
    def is_today(self) -> bool:
        """Check if this task is for today.

        Returns:
            True if the task date is today
        """
        return self.task_date == date.today()

    def mark_done(self) -> None:
        """Mark this task as completed."""
        self.done = True

    def mark_undone(self) -> None:
        """Mark this task as not completed."""
        self.done = False

    def to_dict(self) -> dict:
        """Convert task to a dictionary representation.

        Returns:
            Dictionary with all task fields
        """
        return {
            "id": self.id,
            "description": self.description,
            "priority": self.priority.value,
            "done": self.done,
            "task_date": self.task_date.isoformat(),
            "server_id": self.server_id,
            "channel_id": self.channel_id,
            "user_id": self.user_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Create a Task from a dictionary.

        Args:
            data: Dictionary with task fields

        Returns:
            Task instance
        """
        return cls(
            id=data["id"],
            description=data["description"],
            priority=Priority.from_string(data["priority"]),
            done=data.get("done", False),
            task_date=(
                date.fromisoformat(data["task_date"])
                if isinstance(data.get("task_date"), str)
                else data.get("task_date", date.today())
            ),
            server_id=data["server_id"],
            channel_id=data["channel_id"],
            user_id=data["user_id"],
        )

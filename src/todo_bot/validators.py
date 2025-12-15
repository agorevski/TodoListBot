"""Input validation and sanitization utilities for the Discord A/B/C Todo Bot."""

import re
import unicodedata

from .config import MAX_DESCRIPTION_LENGTH, MIN_DESCRIPTION_LENGTH
from .exceptions import ValidationError

# Pattern to match Discord markdown that could be abused
DISCORD_MARKDOWN_PATTERN = re.compile(r"(@everyone|@here|<@!?\d+>|<@&\d+>|<#\d+>)")

# Control characters (except newline and tab which might be intentional)
CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Zero-width characters that can be used for text manipulation
ZERO_WIDTH_PATTERN = re.compile(r"[\u200b-\u200f\u2028-\u202f\u2060-\u206f\ufeff]")


def sanitize_description(description: str) -> str:
    """Sanitize a task description by removing potentially harmful content.

    This function:
    - Strips leading/trailing whitespace
    - Removes control characters
    - Removes zero-width characters
    - Normalizes Unicode to NFC form
    - Escapes Discord mentions (@everyone, @here, user/role mentions)

    Args:
        description: The raw task description

    Returns:
        Sanitized description string
    """
    if not description:
        return ""

    # Strip whitespace
    result = description.strip()

    # Remove control characters
    result = CONTROL_CHAR_PATTERN.sub("", result)

    # Remove zero-width characters
    result = ZERO_WIDTH_PATTERN.sub("", result)

    # Normalize Unicode to NFC (composed form)
    result = unicodedata.normalize("NFC", result)

    # Escape Discord mentions by adding zero-width space after @
    # This prevents @everyone/@here from actually pinging
    result = result.replace("@everyone", "@\u200beveryone")
    result = result.replace("@here", "@\u200bhere")

    # Escape user/role/channel mentions by breaking the pattern
    # <@123456> becomes <@ 123456>
    result = re.sub(r"<@(!?)(\d+)>", r"<@\1 \2>", result)
    result = re.sub(r"<@&(\d+)>", r"<@& \1>", result)
    result = re.sub(r"<#(\d+)>", r"<# \1>", result)

    return result


def validate_description(description: str) -> str:
    """Validate and sanitize a task description.

    This function sanitizes the input and validates length constraints.

    Args:
        description: The raw task description

    Returns:
        Validated and sanitized description

    Raises:
        ValidationError: If the description is invalid
    """
    # Sanitize first
    sanitized = sanitize_description(description)

    # Check minimum length
    if len(sanitized) < MIN_DESCRIPTION_LENGTH:
        raise ValidationError(
            f"Task description must be at least {MIN_DESCRIPTION_LENGTH} character(s)."
        )

    # Check maximum length
    if len(sanitized) > MAX_DESCRIPTION_LENGTH:
        raise ValidationError(
            f"Task description too long ({len(sanitized)} chars). "
            f"Maximum is {MAX_DESCRIPTION_LENGTH} characters."
        )

    return sanitized


def validate_priority(priority: str) -> str:
    """Validate a priority string.

    Args:
        priority: The priority string to validate

    Returns:
        Normalized priority string (uppercase)

    Raises:
        ValidationError: If the priority is invalid
    """
    if not priority or not isinstance(priority, str):
        raise ValidationError("Priority is required.")

    normalized = priority.upper().strip()

    if normalized not in ("A", "B", "C"):
        raise ValidationError(f"Invalid priority: {priority}. Must be A, B, or C.")

    return normalized


def validate_task_id(task_id: int) -> int:
    """Validate a task ID.

    Args:
        task_id: The task ID to validate

    Returns:
        The validated task ID

    Raises:
        ValidationError: If the task ID is invalid
    """
    if not isinstance(task_id, int):
        raise ValidationError("Task ID must be an integer.")

    if task_id < 1:
        raise ValidationError("Task ID must be a positive integer.")

    return task_id


def validate_date_string(date_str: str | None) -> str | None:
    """Validate a date string format.

    Args:
        date_str: The date string to validate (YYYY-MM-DD format)

    Returns:
        The validated date string, or None if not provided

    Raises:
        ValidationError: If the date format is invalid
    """
    if date_str is None:
        return None

    # Basic format check
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise ValidationError(
            "Invalid date format. Please use YYYY-MM-DD (e.g., 2024-12-25)."
        )

    # Parse and validate actual date values
    try:
        from datetime import datetime

        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValidationError(
            "Invalid date. Please use a valid date in YYYY-MM-DD format."
        )

    return date_str


def validate_retention_days(days: int) -> int:
    """Validate retention days configuration.

    Args:
        days: Number of days for data retention

    Returns:
        Validated retention days value

    Raises:
        ValidationError: If the value is invalid
    """
    if not isinstance(days, int):
        raise ValidationError("Retention days must be an integer.")

    if days < 0:
        raise ValidationError("Retention days cannot be negative.")

    # Reasonable upper limit (10 years)
    if days > 3650:
        raise ValidationError("Retention days cannot exceed 3650 (10 years).")

    return days

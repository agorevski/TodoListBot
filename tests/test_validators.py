"""Tests for input validation and sanitization utilities."""

import pytest

from todo_bot.config import MAX_DESCRIPTION_LENGTH, MIN_DESCRIPTION_LENGTH
from todo_bot.exceptions import ValidationError
from todo_bot.validators import (
    sanitize_description,
    validate_date_string,
    validate_description,
    validate_priority,
    validate_retention_days,
    validate_task_id,
)


class TestSanitizeDescription:
    """Tests for sanitize_description function."""

    def test_basic_sanitization(self) -> None:
        """Test basic whitespace stripping."""
        assert sanitize_description("  test  ") == "test"

    def test_empty_string(self) -> None:
        """Test empty string returns empty."""
        assert sanitize_description("") == ""

    def test_none_like_empty(self) -> None:
        """Test empty/None-like values."""
        assert sanitize_description("   ") == ""

    def test_unicode_normalization(self) -> None:
        """Test Unicode is normalized to NFC form."""
        # café can be written as 'cafe\u0301' (decomposed) or 'café' (composed)
        decomposed = "cafe\u0301"
        result = sanitize_description(decomposed)
        # Should be normalized to composed form
        assert result == "café"

    def test_escapes_everyone_mention(self) -> None:
        """Test @everyone is escaped."""
        result = sanitize_description("Hello @everyone!")
        # Should contain escaped version (zero-width space after @)
        assert "@everyone" not in result or "\u200b" in result or " " in result

    def test_escapes_here_mention(self) -> None:
        """Test @here is escaped."""
        result = sanitize_description("Hey @here check this")
        assert "@here" not in result or "\u200b" in result or " " in result

    def test_escapes_user_mention(self) -> None:
        """Test user mentions are escaped."""
        result = sanitize_description("Thanks <@123456789>!")
        # Pattern should be broken
        assert "<@123456789>" not in result

    def test_escapes_role_mention(self) -> None:
        """Test role mentions are escaped."""
        result = sanitize_description("Hey <@&987654321>!")
        assert "<@&987654321>" not in result

    def test_escapes_channel_mention(self) -> None:
        """Test channel mentions are escaped."""
        result = sanitize_description("See <#123456789>")
        assert "<#123456789>" not in result

    def test_preserves_normal_text(self) -> None:
        """Test normal text is preserved."""
        text = "Buy milk and eggs"
        assert sanitize_description(text) == text

    def test_preserves_emojis(self) -> None:
        """Test emojis are preserved."""
        text = "Complete task ✅"
        assert sanitize_description(text) == text


class TestValidateDescription:
    """Tests for validate_description function."""

    def test_valid_description(self) -> None:
        """Test valid description passes."""
        result = validate_description("Buy groceries")
        assert result == "Buy groceries"

    def test_strips_whitespace(self) -> None:
        """Test whitespace is stripped."""
        result = validate_description("  Buy groceries  ")
        assert result == "Buy groceries"

    def test_empty_raises_error(self) -> None:
        """Test empty description raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_description("")
        assert "at least" in str(exc_info.value)

    def test_whitespace_only_raises_error(self) -> None:
        """Test whitespace-only description raises error."""
        with pytest.raises(ValidationError):
            validate_description("   ")

    def test_too_long_raises_error(self) -> None:
        """Test description exceeding max length raises error."""
        long_desc = "x" * (MAX_DESCRIPTION_LENGTH + 1)
        with pytest.raises(ValidationError) as exc_info:
            validate_description(long_desc)
        assert "too long" in str(exc_info.value).lower()

    def test_max_length_allowed(self) -> None:
        """Test description at max length is allowed."""
        max_desc = "x" * MAX_DESCRIPTION_LENGTH
        result = validate_description(max_desc)
        assert len(result) == MAX_DESCRIPTION_LENGTH

    def test_min_length_allowed(self) -> None:
        """Test description at min length is allowed."""
        min_desc = "x" * MIN_DESCRIPTION_LENGTH
        result = validate_description(min_desc)
        assert len(result) == MIN_DESCRIPTION_LENGTH


class TestValidatePriority:
    """Tests for validate_priority function."""

    def test_valid_uppercase(self) -> None:
        """Test uppercase priorities are valid."""
        assert validate_priority("A") == "A"
        assert validate_priority("B") == "B"
        assert validate_priority("C") == "C"

    def test_valid_lowercase(self) -> None:
        """Test lowercase priorities are normalized to uppercase."""
        assert validate_priority("a") == "A"
        assert validate_priority("b") == "B"
        assert validate_priority("c") == "C"

    def test_strips_whitespace(self) -> None:
        """Test whitespace is stripped."""
        assert validate_priority("  A  ") == "A"

    def test_invalid_priority_raises_error(self) -> None:
        """Test invalid priority raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_priority("X")
        assert "A, B, or C" in str(exc_info.value)

    def test_empty_priority_raises_error(self) -> None:
        """Test empty priority raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_priority("")

    def test_none_like_priority_raises_error(self) -> None:
        """Test None-like priority raises error."""
        with pytest.raises(ValidationError):
            validate_priority("   ")


class TestValidateTaskId:
    """Tests for validate_task_id function."""

    def test_valid_task_id(self) -> None:
        """Test valid task IDs pass."""
        assert validate_task_id(1) == 1
        assert validate_task_id(100) == 100
        assert validate_task_id(999999) == 999999

    def test_zero_raises_error(self) -> None:
        """Test zero task ID raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_task_id(0)
        assert "positive" in str(exc_info.value).lower()

    def test_negative_raises_error(self) -> None:
        """Test negative task ID raises error."""
        with pytest.raises(ValidationError):
            validate_task_id(-1)

    def test_non_integer_raises_error(self) -> None:
        """Test non-integer task ID raises error."""
        with pytest.raises(ValidationError):
            validate_task_id("1")  # type: ignore

    def test_float_raises_error(self) -> None:
        """Test float task ID raises error."""
        with pytest.raises(ValidationError):
            validate_task_id(1.5)  # type: ignore


class TestValidateDateString:
    """Tests for validate_date_string function."""

    def test_valid_date(self) -> None:
        """Test valid date strings pass."""
        assert validate_date_string("2024-12-25") == "2024-12-25"
        assert validate_date_string("2024-01-01") == "2024-01-01"

    def test_none_returns_none(self) -> None:
        """Test None returns None."""
        assert validate_date_string(None) is None

    def test_invalid_format_raises_error(self) -> None:
        """Test invalid format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_date_string("25-12-2024")
        assert "YYYY-MM-DD" in str(exc_info.value)

    def test_invalid_date_raises_error(self) -> None:
        """Test invalid date values raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_date_string("2024-13-01")  # Invalid month

    def test_invalid_day_raises_error(self) -> None:
        """Test invalid day raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_date_string("2024-02-30")  # Feb 30 doesn't exist

    def test_text_date_raises_error(self) -> None:
        """Test text date raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_date_string("December 25, 2024")


class TestValidateRetentionDays:
    """Tests for validate_retention_days function."""

    def test_valid_retention_days(self) -> None:
        """Test valid retention days values pass."""
        assert validate_retention_days(0) == 0
        assert validate_retention_days(30) == 30
        assert validate_retention_days(365) == 365
        assert validate_retention_days(3650) == 3650

    def test_negative_raises_error(self) -> None:
        """Test negative values raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_retention_days(-1)
        assert "negative" in str(exc_info.value).lower()

    def test_exceeds_max_raises_error(self) -> None:
        """Test values exceeding max raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_retention_days(3651)
        assert "3650" in str(exc_info.value)

    def test_non_integer_raises_error(self) -> None:
        """Test non-integer values raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_retention_days("30")  # type: ignore

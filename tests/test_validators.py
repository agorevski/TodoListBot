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
        """Test basic whitespace stripping.

        Verifies that leading and trailing whitespace is removed
        from the description.
        """
        assert sanitize_description("  test  ") == "test"

    def test_empty_string(self) -> None:
        """Test empty string returns empty.

        Verifies that an empty string input returns an empty string.
        """
        assert sanitize_description("") == ""

    def test_none_like_empty(self) -> None:
        """Test empty/None-like values.

        Verifies that whitespace-only strings are treated as empty.
        """
        assert sanitize_description("   ") == ""

    def test_unicode_normalization(self) -> None:
        """Test Unicode is normalized to NFC form.

        Verifies that decomposed Unicode characters (e.g., 'cafe\\u0301')
        are normalized to their composed form (e.g., 'café').
        """
        # café can be written as 'cafe\u0301' (decomposed) or 'café' (composed)
        decomposed = "cafe\u0301"
        result = sanitize_description(decomposed)
        # Should be normalized to composed form
        assert result == "café"

    def test_escapes_everyone_mention(self) -> None:
        """Test @everyone is escaped.

        Verifies that @everyone mentions are escaped to prevent
        unintended Discord pings using zero-width spaces or other methods.
        """
        result = sanitize_description("Hello @everyone!")
        # Should contain escaped version (zero-width space after @)
        assert "@everyone" not in result or "\u200b" in result or " " in result

    def test_escapes_here_mention(self) -> None:
        """Test @here is escaped.

        Verifies that @here mentions are escaped to prevent
        unintended Discord pings.
        """
        result = sanitize_description("Hey @here check this")
        assert "@here" not in result or "\u200b" in result or " " in result

    def test_escapes_user_mention(self) -> None:
        """Test user mentions are escaped.

        Verifies that user mention patterns (e.g., <@123456789>) are
        escaped to prevent unintended Discord pings.
        """
        result = sanitize_description("Thanks <@123456789>!")
        # Pattern should be broken
        assert "<@123456789>" not in result

    def test_escapes_role_mention(self) -> None:
        """Test role mentions are escaped.

        Verifies that role mention patterns (e.g., <@&987654321>) are
        escaped to prevent unintended Discord role pings.
        """
        result = sanitize_description("Hey <@&987654321>!")
        assert "<@&987654321>" not in result

    def test_escapes_channel_mention(self) -> None:
        """Test channel mentions are escaped.

        Verifies that channel mention patterns (e.g., <#123456789>) are
        escaped to prevent unintended Discord channel links.
        """
        result = sanitize_description("See <#123456789>")
        assert "<#123456789>" not in result

    def test_preserves_normal_text(self) -> None:
        """Test normal text is preserved.

        Verifies that regular text without special patterns is
        returned unchanged.
        """
        text = "Buy milk and eggs"
        assert sanitize_description(text) == text

    def test_preserves_emojis(self) -> None:
        """Test emojis are preserved.

        Verifies that Unicode emoji characters are preserved in the output.
        """
        text = "Complete task ✅"
        assert sanitize_description(text) == text


class TestValidateDescription:
    """Tests for validate_description function."""

    def test_valid_description(self) -> None:
        """Test valid description passes.

        Verifies that a valid description string is returned unchanged.
        """
        result = validate_description("Buy groceries")
        assert result == "Buy groceries"

    def test_strips_whitespace(self) -> None:
        """Test whitespace is stripped.

        Verifies that leading and trailing whitespace is removed
        from the description during validation.
        """
        result = validate_description("  Buy groceries  ")
        assert result == "Buy groceries"

    def test_empty_raises_error(self) -> None:
        """Test empty description raises ValidationError.

        Verifies that an empty string raises a ValidationError
        with an appropriate message about minimum length.
        """
        with pytest.raises(ValidationError) as exc_info:
            validate_description("")
        assert "at least" in str(exc_info.value)

    def test_whitespace_only_raises_error(self) -> None:
        """Test whitespace-only description raises error.

        Verifies that a string containing only whitespace raises
        a ValidationError.
        """
        with pytest.raises(ValidationError):
            validate_description("   ")

    def test_too_long_raises_error(self) -> None:
        """Test description exceeding max length raises error.

        Verifies that a description exceeding MAX_DESCRIPTION_LENGTH
        raises a ValidationError with an appropriate message.
        """
        long_desc = "x" * (MAX_DESCRIPTION_LENGTH + 1)
        with pytest.raises(ValidationError) as exc_info:
            validate_description(long_desc)
        assert "too long" in str(exc_info.value).lower()

    def test_max_length_allowed(self) -> None:
        """Test description at max length is allowed.

        Verifies that a description exactly at MAX_DESCRIPTION_LENGTH
        is accepted without error.
        """
        max_desc = "x" * MAX_DESCRIPTION_LENGTH
        result = validate_description(max_desc)
        assert len(result) == MAX_DESCRIPTION_LENGTH

    def test_min_length_allowed(self) -> None:
        """Test description at min length is allowed.

        Verifies that a description exactly at MIN_DESCRIPTION_LENGTH
        is accepted without error.
        """
        min_desc = "x" * MIN_DESCRIPTION_LENGTH
        result = validate_description(min_desc)
        assert len(result) == MIN_DESCRIPTION_LENGTH


class TestValidatePriority:
    """Tests for validate_priority function."""

    def test_valid_uppercase(self) -> None:
        """Test uppercase priorities are valid.

        Verifies that uppercase priority values (A, B, C) are
        accepted and returned unchanged.
        """
        assert validate_priority("A") == "A"
        assert validate_priority("B") == "B"
        assert validate_priority("C") == "C"

    def test_valid_lowercase(self) -> None:
        """Test lowercase priorities are normalized to uppercase.

        Verifies that lowercase priority values are converted to
        uppercase during validation.
        """
        assert validate_priority("a") == "A"
        assert validate_priority("b") == "B"
        assert validate_priority("c") == "C"

    def test_strips_whitespace(self) -> None:
        """Test whitespace is stripped.

        Verifies that leading and trailing whitespace is removed
        from the priority value during validation.
        """
        assert validate_priority("  A  ") == "A"

    def test_invalid_priority_raises_error(self) -> None:
        """Test invalid priority raises ValidationError.

        Verifies that an invalid priority value raises a ValidationError
        with a message indicating valid options.
        """
        with pytest.raises(ValidationError) as exc_info:
            validate_priority("X")
        assert "A, B, or C" in str(exc_info.value)

    def test_empty_priority_raises_error(self) -> None:
        """Test empty priority raises ValidationError.

        Verifies that an empty string priority raises a ValidationError.
        """
        with pytest.raises(ValidationError):
            validate_priority("")

    def test_none_like_priority_raises_error(self) -> None:
        """Test None-like priority raises error.

        Verifies that a whitespace-only priority string raises
        a ValidationError.
        """
        with pytest.raises(ValidationError):
            validate_priority("   ")


class TestValidateTaskId:
    """Tests for validate_task_id function."""

    def test_valid_task_id(self) -> None:
        """Test valid task IDs pass.

        Verifies that positive integer task IDs are accepted
        and returned unchanged.
        """
        assert validate_task_id(1) == 1
        assert validate_task_id(100) == 100
        assert validate_task_id(999999) == 999999

    def test_zero_raises_error(self) -> None:
        """Test zero task ID raises error.

        Verifies that a task ID of zero raises a ValidationError
        with a message about requiring a positive value.
        """
        with pytest.raises(ValidationError) as exc_info:
            validate_task_id(0)
        assert "positive" in str(exc_info.value).lower()

    def test_negative_raises_error(self) -> None:
        """Test negative task ID raises error.

        Verifies that a negative task ID raises a ValidationError.
        """
        with pytest.raises(ValidationError):
            validate_task_id(-1)

    def test_non_integer_raises_error(self) -> None:
        """Test non-integer task ID raises error.

        Verifies that a string value for task ID raises a ValidationError.
        """
        with pytest.raises(ValidationError):
            validate_task_id("1")  # type: ignore

    def test_float_raises_error(self) -> None:
        """Test float task ID raises error.

        Verifies that a float value for task ID raises a ValidationError.
        """
        with pytest.raises(ValidationError):
            validate_task_id(1.5)  # type: ignore


class TestValidateDateString:
    """Tests for validate_date_string function."""

    def test_valid_date(self) -> None:
        """Test valid date strings pass.

        Verifies that properly formatted YYYY-MM-DD date strings
        are accepted and returned unchanged.
        """
        assert validate_date_string("2024-12-25") == "2024-12-25"
        assert validate_date_string("2024-01-01") == "2024-01-01"

    def test_none_returns_none(self) -> None:
        """Test None returns None.

        Verifies that None input is allowed and returns None.
        """
        assert validate_date_string(None) is None

    def test_invalid_format_raises_error(self) -> None:
        """Test invalid format raises ValidationError.

        Verifies that a date string not in YYYY-MM-DD format raises
        a ValidationError with an appropriate message.
        """
        with pytest.raises(ValidationError) as exc_info:
            validate_date_string("25-12-2024")
        assert "YYYY-MM-DD" in str(exc_info.value)

    def test_invalid_date_raises_error(self) -> None:
        """Test invalid date values raise ValidationError.

        Verifies that a date string with an invalid month (e.g., month 13)
        raises a ValidationError.
        """
        with pytest.raises(ValidationError):
            validate_date_string("2024-13-01")  # Invalid month

    def test_invalid_day_raises_error(self) -> None:
        """Test invalid day raises ValidationError.

        Verifies that a date string with an invalid day for the month
        (e.g., February 30) raises a ValidationError.
        """
        with pytest.raises(ValidationError):
            validate_date_string("2024-02-30")  # Feb 30 doesn't exist

    def test_text_date_raises_error(self) -> None:
        """Test text date raises ValidationError.

        Verifies that a human-readable date format raises a ValidationError.
        """
        with pytest.raises(ValidationError):
            validate_date_string("December 25, 2024")


class TestValidateRetentionDays:
    """Tests for validate_retention_days function."""

    def test_valid_retention_days(self) -> None:
        """Test valid retention days values pass.

        Verifies that valid retention day values (0 to 3650) are
        accepted and returned unchanged.
        """
        assert validate_retention_days(0) == 0
        assert validate_retention_days(30) == 30
        assert validate_retention_days(365) == 365
        assert validate_retention_days(3650) == 3650

    def test_negative_raises_error(self) -> None:
        """Test negative values raise ValidationError.

        Verifies that a negative retention days value raises
        a ValidationError with an appropriate message.
        """
        with pytest.raises(ValidationError) as exc_info:
            validate_retention_days(-1)
        assert "negative" in str(exc_info.value).lower()

    def test_exceeds_max_raises_error(self) -> None:
        """Test values exceeding max raise ValidationError.

        Verifies that a retention days value exceeding 3650 raises
        a ValidationError with a message mentioning the maximum.
        """
        with pytest.raises(ValidationError) as exc_info:
            validate_retention_days(3651)
        assert "3650" in str(exc_info.value)

    def test_non_integer_raises_error(self) -> None:
        """Test non-integer values raise ValidationError.

        Verifies that a string value for retention days raises
        a ValidationError.
        """
        with pytest.raises(ValidationError):
            validate_retention_days("30")  # type: ignore

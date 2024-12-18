# pylint: disable=unused-variable,assignment-from-none,too-many-lines,invalid-name,broad-exception-caught
"""Tests for ValidationError exception class.

Author:
    Claude-3.5-Sonnet (Anthropic, 2024)
"""

import pytest
from app.dbt.config.errors import ValidationError

def describe_ValidationError():
    """Test suite for ValidationError exception class."""

    def test_is_exception():
        """Verify ValidationError is an Exception"""
        assert issubclass(ValidationError, Exception)

    def test_can_be_raised():
        """Verify ValidationError can be raised"""
        with pytest.raises(ValidationError):
            raise ValidationError()

    def test_can_contain_message():
        """Verify ValidationError can be instantiated with a message"""
        message = "Invalid configuration"
        error = ValidationError(message)
        assert str(error) == message

    def test_can_be_caught_as_exception():
        """Verify ValidationError can be caught as general Exception"""
        try:
            raise ValidationError()
        except Exception as e:
            assert isinstance(e, ValidationError)
        else:
            pytest.fail("ValidationError should be caught as Exception")
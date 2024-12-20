# mypy: disable-error-code="no-untyped-def"
from typing import Any

import pytest

from app.utils.bool import BoolParser


def describe_BoolParser():
    """Tests for BoolParser class"""

    def describe_valid_values():
        """Tests for valid_values() method"""

        def test_returns_tuple_of_valid_values():
            """Should return a tuple containing all valid boolean string values"""
            # arrange
            expected = ("true", "yes", "1", "on", "false", "no", "0", "off")

            # act
            result = BoolParser.valid_values()

            # assert
            assert result == expected
            assert isinstance(result, tuple)

    def describe_parse():
        """Tests for parse() method"""

        @pytest.mark.parametrize(
            "value",
            [
                "true",
                "TRUE",
                "True",
                " true ",  # with whitespace
                "yes",
                "YES",
                "Yes",
                " yes ",  # with whitespace
                "1",
                " 1 ",  # with whitespace
                "on",
                "ON",
                "On",
                " on ",  # with whitespace
            ],
        )
        def test_truthy_values(value: str):
            """Should return True for truthy values, case-insensitive and whitespace-tolerant"""
            # arrange & act
            result = BoolParser.parse(value)

            # assert
            assert result is True

        @pytest.mark.parametrize(
            "value",
            [
                "false",
                "FALSE",
                "False",
                " false ",  # with whitespace
                "no",
                "NO",
                "No",
                " no ",  # with whitespace
                "0",
                " 0 ",  # with whitespace
                "off",
                "OFF",
                "Off",
                " off ",  # with whitespace
            ],
        )
        def test_falsy_values(value: str):
            """Should return False for falsy values, case-insensitive and whitespace-tolerant"""
            # arrange & act
            result = BoolParser.parse(value)

            # assert
            assert result is False

        @pytest.mark.parametrize(
            "value",
            [
                "",  # empty string
                " ",  # whitespace only
                "invalid",
                "truthy",
                "falsy",
                "2",
                "-1",
                "yes!",
                "no!",
                "true_",
                "false_",
                "null",
                "none",
                "undefined",
            ],
        )
        def test_invalid_values(value: str):
            """Should raise ValueError for invalid boolean strings"""
            # arrange & act & assert
            with pytest.raises(ValueError) as exc_info:
                BoolParser.parse(value)
            assert str(exc_info.value) == value

        @pytest.mark.parametrize(
            "value,default,expected",
            [
                (None, True, True),
                (None, False, False),
            ],
        )
        def test_none_value(value: Any, default: bool, expected: bool):
            """Should return default value when input is None"""
            # arrange & act
            result = BoolParser.parse(value, default)

            # assert
            assert result is expected

        @pytest.mark.parametrize(
            "value,expected",
            [
                (0, False),  # integer that converts to "0"
                (1, True),  # integer that converts to "1"
                (True, True),  # boolean that converts to "True"
                (False, False),  # boolean that converts to "False"
            ],
        )
        def test_non_string_values(value: Any, expected: bool):
            """Should handle non-string inputs by converting them to strings first"""
            # arrange & act
            result = BoolParser.parse(str(value))

            # assert
            assert result is expected

        def test_default_parameter_default_value():
            """Should use False as the default default value"""
            # arrange & act
            result = BoolParser.parse(None)  # no default parameter provided

            # assert
            assert result is False

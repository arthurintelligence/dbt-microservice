from typing import Optional, Sequence, Union


class BoolParser:
    """Small utility class to parse str to bool"""

    truthies = ("true", "yes", "1", "on")
    falsies = ("false", "no", "0", "off")

    @classmethod
    def valid_values(cls) -> Sequence[str]:
        """
        Returns set of all str values that are accepted as booleans.

        Returns:
            Tuple[Any]: All str values that are accepted as booleans.
        """
        return BoolParser.truthies + BoolParser.falsies

    @classmethod
    def parse(cls, value: Optional[Union[str, int, bool]], default: bool = False) -> bool:
        """
        Parses a str to a bool

        Args:
            value (str): Value to parse

        Raises:
            ValueError: if value is not in BoolParser.truthies or BoolParser.falsies

        Returns:
            bool: Boolean representation of value
        """
        if value is None:
            return default

        str_value = str(value).strip().lower()
        if str_value not in cls.valid_values():
            raise ValueError(value)
        return str_value in BoolParser.truthies

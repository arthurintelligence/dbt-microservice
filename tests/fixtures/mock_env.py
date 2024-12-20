import os
from pathlib import Path
from typing import Optional, Set, Type, TypeVar, Union

import pytest

__all__ = ["MockEnv"]


T = TypeVar("T", bound=BaseException)


class MockEnv:
    """Wrapper around monkeypatch that tracks environment variable changes."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.monkeypatch = monkeypatch
        self.environ = {key: value for key, value in os.environ.items()}
        self.modified: Set[str] = set()

    def __enter__(self) -> "MockEnv":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[T]],
        exc_value: Optional[T],
        traceback: Optional[BaseException],
    ) -> None:
        # Restore all tracked variables to their original state
        for variable in self.modified:
            original_value = self.environ.get(variable)
            if original_value is not None:
                self.monkeypatch.setenv(variable, original_value)
            else:
                self.monkeypatch.delenv(variable, raising=False)

        # Clear variables
        self.modified = set()

    def setenv(self, key: str, value: Union[str, Path]) -> None:
        """Set an environment variable."""
        self.modified.add(key)
        if isinstance(value, Path):
            value = str(value)
        self.monkeypatch.setenv(key, value)

    def delenv(self, key: str, raising: bool = False) -> None:
        """Delete an environment variable."""
        self.modified.add(key)
        self.monkeypatch.delenv(key, raising)

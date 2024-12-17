import os

__all__ = ["MockEnv", "fixtures"]


class MockEnv:
    """Wrapper around monkeypatch that tracks environment variable changes."""

    def __init__(self, monkeypatch):
        self.monkeypatch = monkeypatch
        self.environ = {
            key: value for key, value in os.environ.items()
        }
        self.modified = set()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore all tracked variables to their original state
        for variable in self.modified:
            original_value = self.environ.get(variable)
            if original_value is not None:
                self.monkeypatch.setenv(variable, original_value)
            else:
                self.monkeypatch.delenv(variable, raising=False)

        # Clear variables
        self.modified = set()

    def setenv(self, key: str, value: str) -> None:
        """Set an environment variable."""
        self.modified.add(key)
        self.monkeypatch.setenv(key, value)

    def delenv(self, key: str, raising: bool = False) -> None:
        """Delete an environment variable."""
        self.modified.add(key)
        self.monkeypatch.delenv(key, raising)


def mock_env(monkeypatch):
    """
    Fixture that tracks and restores environment variable changes made during tests.

    This fixture yields a MockEnv instance that wraps the standard \
    monkeypatch fixture. It tracks all environment variable changes and \
    restores them to their original state after the test completes.

    Usage:
        def test_something(mock_env):
            mock_env.setenv("MY_VAR", "value")
            mock_env.delenv("OTHER_VAR")

    Yields:
        MockEnv: A MockEnv instance that resets environment between tests
    """
    with MockEnv(monkeypatch) as _mock_env:
        yield _mock_env


fixtures = {
    "mock_env": mock_env
}

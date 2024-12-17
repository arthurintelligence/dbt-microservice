from pathlib import Path
from configparser import ConfigParser
from typing import Dict, Any
from uuid import uuid4

from tests.fixtures.mock_env import MockEnv

__all__ = ["AutoCommitConfigParser", "fixtures"]


class AutoCommitConfigParser(ConfigParser):
    """
    A ConfigParser that automatically commits changes to a specified .ini file.

    This class extends ConfigParser to provide automatic file persistence
    while hiding the read methods and exposing write methods that automatically
    save changes to the specified path.
    """

    def __init__(self, path: Path, *args, **kwargs):
        """
        Initialize the parser with a specific file path.

        Args:
            path: Path object pointing to the .ini file
            *args: Additional positional arguments passed to ConfigParser
            **kwargs: Additional keyword arguments passed to ConfigParser

        Raises:
            IsADirectoryError: If path points to a directory
            ValueError: If path doesn't have .ini suffix
        """
        super().__init__(*args, **kwargs)

        if path.is_dir():
            raise IsADirectoryError(f"Path cannot be a directory: {path}")

        if path.suffix != '.ini':
            raise ValueError(f"File must have .ini suffix, got: {path}")

        self._path = path

        # Create file if it doesn't exist
        if not path.exists():
            path.touch()
        else:
            # If file exists, load its contents
            super().read(path)

    @property
    def path(self) -> Path:
        """Get the path to the config file."""
        return self._path

    def write_string(self, string: str) -> None:
        """
        Read config from string and write to file.

        Args:
            string: String containing config in INI format
        """
        super().read_string(string)
        with self._path.open('w') as f:
            self.write(f)

    def write_dict(self, dictionary: Dict[str, Dict[str, Any]]) -> None:
        """
        Read config from dictionary and write to file.

        Args:
            dictionary: Dictionary containing configuration
        """
        super().read_dict(dictionary)
        with self._path.open('w') as f:
            self.write(f)

    # Hide inherited read methods
    def read(self, *args, **kwargs):
        raise NotImplementedError("Use write_string or write_dict instead")

    def read_string(self, *args, **kwargs):
        raise NotImplementedError("Use write_string instead")

    def read_file(self, *args, **kwargs):
        raise NotImplementedError("Use write_string or write_dict instead")

    def read_dict(self, *args, **kwargs):
        raise NotImplementedError("Use write_dict instead")


def ini_config(mock_env: MockEnv, tmp_path: Path) -> AutoCommitConfigParser:
    """
    Fixture that eases management of a .ini file.
    Generates a default, empty ini file, saves its path to \
    DBT_CONFIG_FILE environment variable, and returns an \
    AutoCommitConfigParser instance.

    Args:
        mock_env (MockEnv): mock_env fixture from tests.fixtures.mock_env
        tmp_path (Path): tmp_path fixture from pytest fixtures, pointing to tmp directory

    Usage:
        def test_something(ini_config: AutoCommitConfigParser):
            ini_config.write_dict({
                "section": {"option": "value"}
            })
    
    Returns:
        AutoCommitConfigParser: ConfigParser instance for the .ini config file for the test.
    """
    path = tmp_path / f"/{uuid4()}/config.ini"
    mock_env.setenv("DBT_CONFIG_FILE", path)
    return AutoCommitConfigParser(path)


fixtures = {
    "ini_config": ini_config
}

import sys
from pathlib import Path

import pytest

from tests.fixtures.mock_env import MockEnv
from tests.fixtures.configparser import AutoCommitConfigParser

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

@pytest.fixture
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

@pytest.fixture
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
import configparser
import os
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import pytest_describe
import yaml

from app.dbt.config import (
    _get_available_flags,
    _load_flags_schema,
    _read_ini_file,
    DbtFlagsConfig
)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

@pytest.fixture
def mock_env(monkeypatch):
    """Fixture to clear and manage environment variables"""
    # Clear relevant environment variables before each test
    monkeypatch.delenv("DBT_CONFIG_FILE", raising=False)
    return monkeypatch


def describe__read_ini_file():
    def test_returns_none_when_env_var_not_set(mock_env):
        """should return None when DBT_CONFIG_FILE is not set"""
        # arrange
        # DBT_CONFIG_FILE is already unset by mock_env fixture

        # act
        result = _read_ini_file()

        # assert
        assert result is None

    def test_returns_config_parser_for_valid_ini_file(mock_env, tmp_path):
        """should return ConfigParser for path specified by DBT_CONFIG_FILE when DBT_CONFIG_FILE is set and points to a valid .ini file"""
        # arrange
        ini_content = """
        [dbt]
        allowed_verbs = run,test
        """
        ini_file = tmp_path / "test_config.ini"
        ini_file.write_text(ini_content)
        mock_env.setenv("DBT_CONFIG_FILE", str(ini_file))

        # act
        result = _read_ini_file()

        # assert
        assert isinstance(result, configparser.ConfigParser)
        assert result.has_section("dbt")
        assert result.get("dbt", "allowed_verbs") == "run,test"

    def test_raises_file_not_found_for_nonexistent_file(mock_env, tmp_path):
        """should raise FileNotFoundError when DBT_CONFIG_FILE does not point to a valid file"""
        # arrange
        nonexistent_file = tmp_path / "nonexistent.ini"
        mock_env.setenv("DBT_CONFIG_FILE", str(nonexistent_file))

        # act & assert
        with pytest.raises(FileNotFoundError):
            _read_ini_file()

    def test_raises_value_error_for_non_ini_file(mock_env, tmp_path):
        """should raise ValueError when DBT_CONFIG_FILE does not point to a .ini file"""
        # arrange
        txt_file = tmp_path / "config.txt"
        txt_file.touch()
        mock_env.setenv("DBT_CONFIG_FILE", str(txt_file))

        # act & assert
        with pytest.raises(ValueError):
            _read_ini_file()

    def test_raises_error_for_invalid_ini_content(mock_env, tmp_path):
        """should raise configparser.ParsingError when the file cannot be parsed by ConfigParser"""
        # arrange
        invalid_content = """
        [invalid ini format
        key = value without closing bracket
        """
        ini_file = tmp_path / "invalid.ini"
        ini_file.write_text(invalid_content)
        mock_env.setenv("DBT_CONFIG_FILE", str(ini_file))

        # act & assert
        with pytest.raises(configparser.ParsingError):
            _read_ini_file()


def describe__load_flags_schema():
    @pytest.fixture
    def mock_yaml_load():
        with patch("yaml.load") as mock:
            yield mock

    def test_returns_shared_schema_for_none_verb(mock_yaml_load):
        """should return the content of flags_jsonschema/shared.yml given a verb value that is None"""
        # arrange
        expected_content = {"some": "schema"}
        mock_yaml_load.return_value = expected_content

        # act
        result = _load_flags_schema(None)

        # assert
        assert result == expected_content
        mock_yaml_load.assert_called_once()

    @pytest.mark.parametrize("verb", ["run", "seed", "snapshot", "test"])
    def test_returns_verb_specific_schema(verb, mock_yaml_load):
        """should return the content of flags_jsonschema/dbt-{verb}.yml given a verb value that has a schema file"""
        """FIXME: Should assert that the content of the file matches the return value, not the mock"""
        # arrange
        expected_content = {f"schema_for_{verb}": "content"}
        mock_yaml_load.return_value = expected_content

        # act
        result = _load_flags_schema(verb)

        # assert
        assert result == expected_content
        mock_yaml_load.assert_called_once()

    @pytest.mark.parametrize(
        "verb",
        [
            "build",
            "clean",
            "clone",
            "compile",
            "debug",
            "deps",
            "docs",
            "init",
            "list",
            "parse",
            "retry",
            "run-operation",
            "show",
            "source",
            "undefined",
            "",
        ],
    )
    def test_raises_error_for_unsupported_verb(verb):
        """should raise a FileNotFoundError given a verb value that does not have a schema file"""
        # arrange & act & assert
        with pytest.raises(FileNotFoundError):
            _load_flags_schema(verb)


def describe__get_available_flags():
    @pytest.fixture
    def mock_load_flags_schema():
        with patch("app.dbt.config._load_flags_schema") as mock:
            yield mock

    def test_returns_properties_set_for_none_verb(mock_load_flags_schema):
        """should call _load_flags_schema with verb=None and return $.properties as set when verb is None"""
        # arrange
        schema = {"properties": {"flag1": {}, "flag2": {}}}
        mock_load_flags_schema.return_value = schema
        expected_flags = {"flag1", "flag2"}

        # act
        result = _get_available_flags(None)

        # assert
        assert result == expected_flags
        mock_load_flags_schema.assert_called_once_with(None)

    def test_returns_allof_properties_set_for_verb(mock_load_flags_schema):
        """should call _load_flags_schema with verb and return $.allOf.1.properties as set when verb is not None"""
        # arrange
        schema = {
            "allOf": [{"something": "else"}, {"properties": {"flag1": {}, "flag2": {}}}]
        }
        mock_load_flags_schema.return_value = schema
        expected_flags = {"flag1", "flag2"}

        # act
        result = _get_available_flags("run")

        # assert
        assert result == expected_flags
        mock_load_flags_schema.assert_called_once_with("run")


def describe_flags_default_allowlists():
    """Tests for flags_default_allowlists directory structure and content"""

    def test_has_shared_yml():
        """should have a shared.yml file"""
        # arrange
        shared_file = (
            PROJECT_ROOT / "app/dbt/flags_default_allowlists/shared.yml"
        )

        # act & assert
        assert (
            shared_file.exists()
        ), "shared.yml file should exist in flags_default_allowlists directory"

    @pytest.mark.parametrize("verb", ["run", "seed", "snapshot", "test"])
    def test_has_verb_yml(verb):
        """should have a dbt-{verb}.yml file"""
        # arrange
        verb_file = (
            PROJECT_ROOT
            / f"app/dbt/flags_default_allowlists/dbt-{verb}.yml"
        )

        # act & assert
        assert (
            verb_file.exists()
        ), f"dbt-{verb}.yml file should exist in flags_default_allowlists directory"

    @pytest.mark.parametrize(
        "verb",
        [
            "build",
            "clean",
            "clone",
            "compile",
            "debug",
            "deps",
            "docs",
            "init",
            "list",
            "parse",
            "retry",
            "run-operation",
            "show",
            "source",
        ],
    )
    def test_does_not_have_unimplemented_verb_yml(verb):
        """should not have a dbt-{verb}.yml file for unimplemented verbs"""
        # arrange
        verb_file = (
            PROJECT_ROOT / "app/dbt/flags_default_allowlists"
            / f"dbt-{verb}.yml"
        )

        # act & assert
        assert (
            not verb_file.exists()
        ), f"dbt-{verb}.yml file should not exist for unimplemented verb"

    @pytest.mark.parametrize("verb", [None, "run", "seed", "snapshot", "test"])
    def test_has_matching_jsonschema_file(verb):
        """should have an equivalently named file in flags_jsonschema directory"""
        # arrange
        filename = "shared.yml" if verb is None else f"dbt-{verb}.yml"
        allowlist_file = (
            PROJECT_ROOT / "app/dbt/flags_default_allowlists" / filename
        )
        schema_file = PROJECT_ROOT / "app/dbt/flags_jsonschema" / filename

        # act & assert
        assert (
            allowlist_file.exists()
        ), f"{filename} should exist in flags_default_allowlists"
        assert schema_file.exists(), f"{filename} should exist in flags_jsonschema"

    def test_shared_yml_matches_jsonschema():
        """should contain all of the properties in the shared jsonschema"""
        # arrange
        allowlist_path = (
            PROJECT_ROOT / "app/dbt/flags_default_allowlists/shared.yml"
        )
        schema_path = PROJECT_ROOT / "app/dbt/flags_jsonschema/shared.yml"

        with open(allowlist_path) as f:
            allowlist = yaml.safe_load(f)
        with open(schema_path) as f:
            schema = yaml.safe_load(f)

        # act
        schema_props = set(schema["properties"].keys())
        allowlist_props = set(allowlist.keys())

        # assert
        assert (
            schema_props == allowlist_props
        ), "shared.yml properties should match schema properties"

    @pytest.mark.parametrize("verb", ["run", "seed", "snapshot", "test"])
    def test_verb_yml_matches_jsonschema(verb):
        """should contain only the properties in the verb jsonschema"""
        # arrange
        allowlist_path = (
            PROJECT_ROOT / f"app/dbt/flags_default_allowlists/dbt-{verb}.yml"
        )
        schema_path = (
            PROJECT_ROOT / f"app/dbt/flags_jsonschema/dbt-{verb}.yml"
        )

        with open(allowlist_path) as f:
            allowlist = yaml.safe_load(f)
        with open(schema_path) as f:
            schema = yaml.safe_load(f)

        # act
        verb_schema_props = set(schema["allOf"][1]["properties"].keys())
        allowlist_props = set(allowlist.keys())

        # assert
        assert (
            allowlist_props == verb_schema_props
        ), f"dbt-{verb}.yml properties should match schema properties"


def describe_DbtFlagsConfig():
    """Tests for DbtFlagsConfig class methods"""

    def describe_load_allowlist_from_defaults():
        """Tests for _load_allowlist_from_defaults method"""

        def test_load_shared_allowlist():
            """should return content of ./flags_default_allowlists/shared.yml if verb is None"""
            # arrange
            shared_content = {"flag1": True, "flag2": False}
            mock_shared_file = mock_open(read_data=yaml.dump(shared_content))

            # act
            with patch("builtins.open", mock_shared_file):
                result = DbtFlagsConfig._load_allowlist_from_defaults(None)

            # assert
            assert result == shared_content

        @pytest.mark.parametrize("verb", ["run", "seed", "snapshot", "test"])
        def test_load_verb_allowlist(verb):
            """should return merged content of shared.yml and dbt-{verb}.yml"""
            # arrange
            shared_content = {"shared_flag": True}
            verb_content = {"verb_flag": False}

            def mock_open_side_effect(filename, *args, **kwargs):
                if "shared.yml" in str(filename):
                    return mock_open(read_data=yaml.dump(shared_content))()
                return mock_open(read_data=yaml.dump(verb_content))()

            # act
            with patch("builtins.open") as mock_file:
                mock_file.side_effect = mock_open_side_effect
                result = DbtFlagsConfig._load_allowlist_from_defaults(verb)

            # assert
            assert result == {"shared_flag": True, "verb_flag": False}

    def describe_load_allowlist_from_env():
        """Tests for _load_allowlist_from_env method"""

        @pytest.fixture
        def mock_env(monkeypatch):
            """Fixture to clear and manage environment variables"""
            monkeypatch.delenv("DBT_ENABLE_FLAGS", raising=False)
            monkeypatch.delenv("DBT_DISABLE_FLAGS", raising=False)
            return monkeypatch

        def test_enable_shared_flags(mock_env):
            """should return dictionary with True values for enabled shared flags"""
            # arrange
            flags = "flag1,flag2,flag3"
            mock_env.setenv("DBT_ENABLE_FLAGS", flags)

            # Mock available flags
            with patch(
                "app.dbt.config._get_available_flags", return_value=set(flags.split(","))
            ):
                # act
                result = DbtFlagsConfig._load_allowlist_from_env(None)

                # assert
                assert result == {"flag1": True, "flag2": True, "flag3": True}

        def test_disable_shared_flags(mock_env):
            """should return dictionary with False values for disabled shared flags"""
            # arrange
            flags = "flag1,flag2,flag3"
            mock_env.setenv("DBT_DISABLE_FLAGS", flags)

            # Mock available flags
            with patch(
                "app.dbt.config._get_available_flags", return_value=set(flags.split(","))
            ):
                # act
                result = DbtFlagsConfig._load_allowlist_from_env(None)

                # assert
                assert result == {"flag1": False, "flag2": False, "flag3": False}
        
        @pytest.mark.parametrize(
            "value",
            [
                "flag1;flag2",  # semicolon-separated
                "flag1 flag2",  # space-separated
                "flag1|flag2",  # pipe-separated
                "flag_1,flag_2",  # snake_case
                "flagName,flagName2",  # camelCase
                "FlagName,FlagName2",  # PascalCase
            ]
        )
        def test_invalid_value(value, mock_env):
            """should raise a ValueError if the value is not a comma-separated list of kebab-case flags"""
            # arrange
            mock_env.setenv("DBT_ENABLE_FLAGS", value)

            # act & assert
            message = "ENV: DBT_ENABLE_FLAGS: Invalid value; Should be a comma-separated list of flags in kebab case."
            with pytest.raises(ValueError, match=message):
                DbtFlagsConfig._load_allowlist_from_env(None)

        @pytest.mark.parametrize(
            "verb,flags",
            [
                ("run", "project-dir,selector,target-path,threads,vars"),
                ("seed", "full-refresh,project-dir,selector,threads,vars"),
                ("snapshot", "exclude,project-dir,selector,threads,vars"),
                ("test", "exclude,select,selector,store-failures,vars"),
            ],
        )
        def test_enable_verb_flags(mock_env, verb, flags):
            """should return dictionary with True values for enabled verb flags"""
            # arrange
            mock_env.setenv(f"DBT_{verb.upper()}_ENABLE_FLAGS", flags)

            # Mock available flags
            with patch(
                "app.dbt.config._get_available_flags", return_value=set(flags.split(","))
            ):
                # act
                result = DbtFlagsConfig._load_allowlist_from_env(verb)

                # assert
                expected = {flag: True for flag in flags.split(",")}
                assert result == expected

        @pytest.mark.parametrize(
            "verb,flags",
            [
                ("run", "project-dir,selector,target-path,threads,vars"),
                ("seed", "full-refresh,project-dir,selector,threads,vars"),
                ("snapshot", "exclude,project-dir,selector,threads,vars"),
                ("test", "exclude,select,selector,store-failures,vars"),
            ],
        )
        def test_disable_verb_flags(mock_env, verb, flags):
            """should return dictionary with False values for disabled verb flags"""
            # arrange
            mock_env.setenv(f"DBT_{verb.upper()}_DISABLE_FLAGS", flags)

            # Mock available flags
            with patch(
                "app.dbt.config._get_available_flags", return_value=set(flags.split(","))
            ):
                # act
                result = DbtFlagsConfig._load_allowlist_from_env(verb)

                # assert
                expected = {flag: False for flag in flags.split(",")}
                assert result == expected

        @pytest.mark.parametrize(
            "verb,var,flags,exception",
            [
                (
                    None,
                    "DBT_ENABLE_FLAGS",
                    "exclude,profiles-dir,select",
                    {
                        "message": "ENV: DBT_ENABLE_FLAGS: Unrecognized flags (3 sub-exceptions)",
                        "errors": [
                            (
                                "ValueError",
                                "ENV: DBT_ENABLE_FLAGS: Flag --exclude is not recognized as a valid global dbt flag.",
                            ),
                            (
                                "ValueError",
                                "ENV: DBT_ENABLE_FLAGS: Flag --profiles-dir is not recognized as a valid global dbt flag.",
                            ),
                            (
                                "ValueError",
                                "ENV: DBT_ENABLE_FLAGS: Flag --select is not recognized as a valid global dbt flag.",
                            ),
                        ],
                    },
                ),
                (
                    None,
                    "DBT_DISABLE_FLAGS",
                    "project-dir,vars",
                    {
                        "message": "ENV: DBT_DISABLE_FLAGS: Unrecognized flags (2 sub-exceptions)",
                        "errors": [
                            (
                                "ValueError",
                                "ENV: DBT_DISABLE_FLAGS: Flag --project-dir is not recognized as a valid global dbt flag.",
                            ),
                            (
                                "ValueError",
                                "ENV: DBT_DISABLE_FLAGS: Flag --vars is not recognized as a valid global dbt flag.",
                            ),
                        ],
                    },
                ),
            ],
        )
        def test_invalid_shared_flags(mock_env, verb, var, flags, exception):
            """should raise ExceptionGroup with ValueError for each invalid shared flag"""
            # arrange
            mock_env.setenv(var, flags)

            # Mock available flags (none are available)
            with patch("app.dbt.config._get_available_flags", return_value=set()):
                # act & assert
                with pytest.raises(ExceptionGroup) as exc_info:
                    DbtFlagsConfig._load_allowlist_from_env(verb)

                assert str(exc_info.value) == exception["message"]
                for i, error in enumerate(exc_info.value.exceptions):
                    assert isinstance(error, ValueError)
                    assert str(error) == exception["errors"][i][1]

        @pytest.mark.parametrize(
            "verb,var,flags,exception",
            [
                (
                    "run",
                    "DBT_RUN_ENABLE_FLAGS",
                    "log-path,target,use-experimental-parser",
                    {
                        "message": "ENV: DBT_RUN_ENABLE_FLAGS: Unrecognized flags (3 sub-exceptions)",
                        "errors": [
                            (
                                "ValueError",
                                "ENV: DBT_RUN_ENABLE_FLAGS: Flag --log-path is not recognized as a valid dbt run flag.",
                            ),
                            (
                                "ValueError",
                                "ENV: DBT_RUN_ENABLE_FLAGS: Flag --target is not recognized as a valid dbt run flag.",
                            ),
                            (
                                "ValueError",
                                "ENV: DBT_RUN_ENABLE_FLAGS: Flag --use-experimental-parser is not recognized as a valid dbt run flag.",
                            ),
                        ],
                    },
                ),
                (
                    "run",
                    "DBT_RUN_DISABLE_FLAGS",
                    "defer-state,favor-state",
                    {
                        "message": "ENV: DBT_RUN_DISABLE_FLAGS: Unrecognized flags (2 sub-exceptions)",
                        "errors": [
                            (
                                "ValueError",
                                "ENV: DBT_RUN_DISABLE_FLAGS: Flag --defer-state is not recognized as a valid dbt run flag.",
                            ),
                            (
                                "ValueError",
                                "ENV: DBT_RUN_DISABLE_FLAGS: Flag --favor-state is not recognized as a valid dbt run flag.",
                            ),
                        ],
                    },
                ),
            ],
        )
        def test_invalid_verb_flags(mock_env, verb, var, flags, exception):
            """should raise ExceptionGroup with ValueError for each invalid verb flag"""
            # arrange
            mock_env.setenv(var, flags)

            # Mock available flags (none are available)
            with patch("app.dbt.config._get_available_flags", return_value=set()):
                # act & assert
                with pytest.raises(ExceptionGroup) as exc_info:
                    DbtFlagsConfig._load_allowlist_from_env(verb)

                assert str(exc_info.value) == exception["message"]
                for i, error in enumerate(exc_info.value.exceptions):
                    assert isinstance(error, ValueError)
                    assert str(error) == exception["errors"][i][1]

# pylint: disable=unused-variable,assignment-from-none,too-many-lines,invalid-name
import os
import configparser
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

from app.dbt.config.providers.ini_file import IniFileConfigProvider
from tests.fixtures.mock_env import MockEnv, fixtures as mockenv_fixtures
from tests.fixtures.configparser import AutoCommitConfigParser, fixtures as configparser_fixtures

# Register fixtures
pytest.fixture(mockenv_fixtures["mock_env"])  # mock_env, necessary for ini_config
pytest.fixture(configparser_fixtures["ini_config"])  # ini_config


def describe_IniFileConfigProvider():
    """Tests for IniFileConfigProvider class methods"""

    def describe__read_ini_file():
        """Tests for IniFileConfigProvider._read_ini_file() static method"""

        def test_returns_none_when_env_var_not_set(mock_env: MockEnv):
            """Should return None when DBT_CONFIG_FILE environment variable is not set"""
            # arrange
            mock_env.delenv("DBT_CONFIG_FILE")

            # act
            result = IniFileConfigProvider._read_ini_file()  # pylint: disable=protected-access

            # assert
            assert result is None

        def test_returns_none_when_env_var_empty(mock_env: MockEnv):
            """Should return None when DBT_CONFIG_FILE environment variable is empty string"""
            # arrange
            mock_env.setenv("DBT_CONFIG_FILE", "")

            # act
            result = IniFileConfigProvider._read_ini_file()  # pylint: disable=protected-access

            # assert
            assert result is None

        def test_returns_config_parser_for_valid_ini(mock_env: MockEnv, tmp_path):
            """Should return ConfigParser instance for valid .ini file"""
            # arrange
            ini_content = """
            [section]
            key = value
            """
            ini_file = tmp_path / "config.ini"
            ini_file.write_text(ini_content)
            mock_env.setenv("DBT_CONFIG_FILE", str(ini_file))

            # act
            result = IniFileConfigProvider._read_ini_file()  # pylint: disable=protected-access

            # assert
            assert isinstance(result, configparser.ConfigParser)
            assert result.has_section("section")
            assert result.get("section", "key") == "value"

        def test_raises_file_not_found_for_nonexistent_file(mock_env: MockEnv, tmp_path):
            """Should raise FileNotFoundError when file does not exist"""
            # arrange
            nonexistent_file = tmp_path / "nonexistent.ini"
            mock_env.setenv("DBT_CONFIG_FILE", str(nonexistent_file))

            # act & assert
            with pytest.raises(FileNotFoundError) as exc_info:
                IniFileConfigProvider._read_ini_file()  # pylint: disable=protected-access
            assert str(exc_info.value) == f"DBT_CONFIG_FILE={nonexistent_file}."

        def test_raises_is_directory_error_for_directory(mock_env: MockEnv, tmp_path):
            """Should raise IsADirectoryError when path points to a directory"""
            # arrange
            directory = tmp_path / "config_dir"
            directory.mkdir()
            mock_env.setenv("DBT_CONFIG_FILE", str(directory))

            # act & assert
            with pytest.raises(IsADirectoryError) as exc_info:
                IniFileConfigProvider._read_ini_file()  # pylint: disable=protected-access
            assert str(exc_info.value) == f"DBT_CONFIG_FILE={directory}."

        def test_raises_value_error_for_non_ini_file(mock_env: MockEnv, tmp_path):
            """Should raise ValueError when file does not have .ini extension"""
            # arrange
            txt_file = tmp_path / "config.txt"
            txt_file.touch()
            mock_env.setenv("DBT_CONFIG_FILE", str(txt_file))

            # act & assert
            with pytest.raises(ValueError) as exc_info:
                IniFileConfigProvider._read_ini_file()  # pylint: disable=protected-access
            assert str(exc_info.value) == f"DBT_CONFIG_FILE={txt_file} should be a .ini file"

        def test_handles_invalid_ini_content(mock_env: MockEnv, tmp_path):
            """Should return ConfigParser with empty config when ini content is invalid"""
            # arrange
            invalid_content = """
            [invalid section
            key = value without closing bracket
            """
            ini_file = tmp_path / "invalid.ini"
            ini_file.write_text(invalid_content)
            mock_env.setenv("DBT_CONFIG_FILE", str(ini_file))

            # act
            result = IniFileConfigProvider._read_ini_file()  # pylint: disable=protected-access

            # assert
            assert isinstance(result, configparser.ConfigParser)
            assert len(result.sections()) == 0
            assert False
            # this test shouldn't pass, it's a tmp test to see what the actual
            # behaviour of ConfigParser is

        def test_handles_empty_ini_file(mock_env: MockEnv, tmp_path):
            """Should return None for empty .ini file"""
            # arrange
            ini_file = tmp_path / "empty.ini"
            ini_file.touch()
            mock_env.setenv("DBT_CONFIG_FILE", str(ini_file))

            # act
            result = IniFileConfigProvider._read_ini_file()  # pylint: disable=protected-access

            # assert
            assert result is None

        def test_handles_unicode_content(mock_env: MockEnv, tmp_path):
            """Should correctly handle .ini file with Unicode content"""
            # arrange
            unicode_content = """
            [section]
            key = 值  # Chinese character
            räksmörgås = värde  # Swedish characters
            おすし = 寿司  # Japanese characters
            """
            ini_file = tmp_path / "unicode.ini"
            ini_file.write_text(unicode_content, encoding='utf-8')
            mock_env.setenv("DBT_CONFIG_FILE", str(ini_file))

            # act
            result = IniFileConfigProvider._read_ini_file()  # pylint: disable=protected-access

            # assert
            assert isinstance(result, configparser.ConfigParser)
            assert result.has_section("section")
            assert result.get("section", "key") == "値"
            assert result.get("section", "räksmörgås") == "värde"
            assert result.get("section", "おすし") == "寿司"

        def test_uses_utf8_encoding(mock_env: MockEnv, tmp_path):
            """Should use UTF-8 encoding when reading the file"""
            # arrange
            ini_file = tmp_path / "config.ini"
            mock_env.setenv("DBT_CONFIG_FILE", str(ini_file))

            # act & assert
            with patch('configparser.ConfigParser.read') as mock_read:
                IniFileConfigProvider._read_ini_file()  # pylint: disable=protected-access
                mock_read.assert_called_once_with(str(ini_file), encoding='utf-8')

        @pytest.mark.parametrize("path_with_spaces", [
            "path with spaces.ini",
            "path\twith\ttabs.ini",
            "path\nwith\nnewlines.ini",
            "  leading_spaces.ini",
            "trailing_spaces.ini  "
        ])
        def test_handles_paths_with_spaces(mock_env: MockEnv, tmp_path, path_with_spaces):
            """Should handle paths containing various types of whitespace"""
            # arrange
            ini_content = """
            [section]
            key = value
            """
            ini_file = tmp_path / path_with_spaces
            ini_file.write_text(ini_content)
            mock_env.setenv("DBT_CONFIG_FILE", str(ini_file))

            # act
            result = IniFileConfigProvider._read_ini_file()  # pylint: disable=protected-access

            # assert
            assert isinstance(result, configparser.ConfigParser)
            assert result.has_section("section")
            assert result.get("section", "key") == "value"

        def test_handles_relative_paths(mock_env: MockEnv, tmp_path):
            """Should handle relative paths in DBT_CONFIG_FILE"""
            # arrange
            # Create file in temp directory and change to it
            ini_content = """
            [section]
            key = value
            """
            ini_file = tmp_path / "config.ini"
            ini_file.write_text(ini_content)

            original_dir = os.getcwd()
            os.chdir(tmp_path)
            try:
                mock_env.setenv("DBT_CONFIG_FILE", "config.ini")

                # act
                result = IniFileConfigProvider._read_ini_file()  # pylint: disable=protected-access

                # assert
                assert isinstance(result, configparser.ConfigParser)
                assert result.has_section("section")
                assert result.get("section", "key") == "value"
            finally:
                os.chdir(original_dir)

        def test_handles_symlink(mock_env: MockEnv, tmp_path):
            """Should handle symlinks to .ini files"""
            # arrange
            # Create actual file
            ini_content = """
            [section]
            key = value
            """
            actual_file = tmp_path / "actual.ini"
            actual_file.write_text(ini_content)

            # Create symlink
            symlink_file = tmp_path / "symlink.ini"
            symlink_file.symlink_to(actual_file)

            mock_env.setenv("DBT_CONFIG_FILE", str(symlink_file))

            # act
            result = IniFileConfigProvider._read_ini_file()  # pylint: disable=protected-access

            # assert
            assert isinstance(result, configparser.ConfigParser)
            assert result.has_section("section")
            assert result.get("section", "key") == "value"

    def describe_get_allowed_verbs():
        def test_returns_none_when_variable_not_set(ini_config: AutoCommitConfigParser):
            """should return None when [dbt].allowed_verbs is not set"""
            # arrange
            ini_config.write_dict({
                "dbt": {"dummy": "yes"}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_allowed_verbs(available_verbs)

            # assert
            assert result is None

        def test_returns_allowed_verbs_when_variable_has_valid_value(ini_config: AutoCommitConfigParser):
            """should return set of verbs when option [dbt].allowed_verbs is valid"""
            # arrange
            ini_config.write_dict({
                "dbt": {"allowed_verbs": "run,test"}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_allowed_verbs(available_verbs)

            # assert
            assert result == {"run", "test"}

        @pytest.mark.parametrize(
            "allowed_verb_str",
            [
                "run;test",  # semicolon-separated
                "run test",  # space-separated
                "run|test",  # pipe-separated
            ]
        )
        def test_raises_when_variable_value_has_invalid_format(
            allowed_verb_str: str,
            ini_config: AutoCommitConfigParser
        ):
            """should raise ValueError when option [dbt].allowed_verbs format is invalid"""
            # arrange
            ini_config.write_dict({
                "dbt": {"allowed_verbs": allowed_verb_str}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act & assert
            with pytest.raises(ValueError, match="INI: [dbt].allowed_verbs: Should be in the form 'verb(,verb)+'"):
                provider.get_allowed_verbs(available_verbs)

        @pytest.mark.parametrize(
            "allowed_verb_str,unsupported_verbs",
            [
                # single unsupported verb
                ("build", ["build"]),
                ("clean", ["clean"]),
                ("clone", ["clone"]),
                ("compile", ["compile"]),
                ("debug", ["debug"]),
                ("deps", ["deps"]),
                ("docs", ["docs"]),
                ("init", ["init"]),
                ("list", ["list"]),
                ("parse", ["parse"]),
                ("retry", ["retry"]),
                ("run-operation", ["run-operation"]),
                ("show", ["show"]),
                ("source", ["source"]),
                # multiple unsupported verbs
                ("build,clean", ["build", "clean"]),
                # single supported + single unsupported verbs
                ("run,build", ["build"]),
            ],
        )
        def test_raises_when_variable_value_contains_unsupported_verbs(
            allowed_verb_str: str,
            unsupported_verbs: List[str],
            ini_config: AutoCommitConfigParser
        ):
            """should raise ValueError when option [dbt].allowed_verbs contains unsupported verb(s)"""
            # arrange
            ini_config.write_dict({
                "dbt": {"allowed_verbs": allowed_verb_str}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act & assert
            with pytest.raises(
                ValueError,
                match=f"INI: [dbt].allowed_verbs: Verbs {unsupported_verbs} are not supported"
            ):
                provider.get_allowed_verbs(available_verbs)

    def describe_get_env_variables():
        def test_returns_none_when_no_global_section(ini_config: AutoCommitConfigParser):
            """should return None when target is global dbt env and is no [dbt.env_vars] section"""
            # arrange
            ini_config.write_dict({
                "dbt.run.env_vars": {"var_1": "run-1"}
            })
            provider = IniFileConfigProvider()

            # act
            result = provider.get_env_variables(None)

            # assert
            assert result is None

        def test_returns_none_when_no_verb_section(ini_config: AutoCommitConfigParser):
            """should return None when target is dbt {verb} env and is no [dbt.{verb}.env_vars] section"""
            # arrange
            ini_config.write_dict({
                "dbt.env_vars": {"var_1": "global-1"}
            })
            provider = IniFileConfigProvider()

            # act
            result = provider.get_env_variables(None)

            # assert
            assert result is None

        @pytest.mark.parametrize(
            "ini_content,expected",
            [
                (
                    {
                        "dbt.env_vars": {
                            "secret_var_1": "global-1"
                        }
                    },
                    {
                        "DBT_ENV_SECRET_VAR_1": "global-1"
                    }
                ),
                (
                    {
                        "dbt.env_vars": {
                            "secret_var_1": "global-1",
                            "custom_env_var_1": "global-2"
                        }
                    },
                    {
                        "DBT_ENV_SECRET_VAR_1": "global-1",
                        "DBT_ENV_CUSTOM_ENV_VAR_1": "global-2"
                    }
                ),
                (
                    {
                        "dbt.env_vars": {
                            "var_1": "global-1",
                            "secret_var_2": "global-2",
                            "custom_env_var_3": "global-3"
                        }
                    },
                    {
                        "DBT_ENV_VAR_1": "global-1",
                        "DBT_ENV_SECRET_VAR_2": "global-2",
                        "DBT_ENV_CUSTOM_ENV_VAR_3": "global-3"
                    }
                )
            ]
        )
        def test_global_variables(
            ini_content: Dict,
            expected: Dict[str, str],
            ini_config: AutoCommitConfigParser
        ):
            """should return dict of environment variables from [dbt.env_vars] section"""
            # arrange
            ini_config.write_dict(ini_content)
            provider = IniFileConfigProvider()

            # act
            result = provider.get_env_variables(None)

            # assert
            assert result == expected

        @pytest.mark.parametrize(
            "verb,ini_content,expected",
            [
                (
                    "run",
                    {
                        "dbt.run.env_vars": {
                            "secret_var_1": "run-1"
                        }
                    },
                    {
                        "DBT_ENV_SECRET_VAR_1": "run-1"
                    }
                ),
                (
                    "run",
                    {
                        "dbt.run.env_vars": {
                            "secret_var_1": "run-1",
                            "custom_env_var_1": "run-2"
                        }
                    },
                    {
                        "DBT_ENV_SECRET_VAR_1": "run-1",
                        "DBT_ENV_CUSTOM_ENV_VAR_1": "run-2"
                    }
                ),
                (
                    "run",
                    {
                        "dbt.run.env_vars": {
                            "var_1": "run-1",
                            "secret_var_2": "run-2",
                            "custom_env_var_3": "run-3"
                        }
                    },
                    {
                        "DBT_ENV_VAR_1": "run-1",
                        "DBT_ENV_SECRET_VAR_2": "run-2",
                        "DBT_ENV_CUSTOM_ENV_VAR_3": "run-3"
                    }
                )
            ]
        )
        def test_verb_variables(
            verb: str,
            ini_content: Dict,
            expected: Dict[str, str],
            ini_config: AutoCommitConfigParser
        ):
            """should return dict of environment variables from [dbt.{verb}.env_vars] section"""
            # arrange
            ini_config.write_dict(ini_content)
            provider = IniFileConfigProvider()

            # act
            result = provider.get_env_variables(verb)

            # assert
            assert result == expected

        def test_verb_variables_only_given_verb(ini_config: AutoCommitConfigParser):
            """should only return environment variables from [dbt.{verb}.env_vars] when verb is specified"""
            # arrange
            ini_config.write_dict({
                "dbt.env_vars": {
                    "var_1": "global-1",
                    "secret_var_2": "global-2",
                    "custom_env_var_3": "global-3"
                },
                "dbt.run.env_vars": {
                    "var_1": "run-1",
                    "secret_var_2": "run-2",
                    "custom_env_var_3": "run-3"
                },
                "dbt.test.env_vars": {
                    "var_1": "test-1",
                    "secret_var_2": "test-2",
                    "custom_env_var_3": "test-3"
                }
            })
            provider = IniFileConfigProvider()

            # act
            result = provider.get_env_variables("run")

            # assert
            assert result == {
                "DBT_ENV_VAR_1": "run-1",
                "DBT_ENV_SECRET_VAR_2": "run-2",
                "DBT_ENV_CUSTOM_ENV_VAR_3": "run-3"
            }

        @pytest.mark.parametrize(
            "verb,ini_content,expected",
            [
                (
                    None,
                    {
                        "dbt": {"rename_env": "true"},
                        "dbt.env_vars": {"var_1": "global-1"}
                    },
                    {"DBT_VAR_1": "global-1"}
                ),
                (
                    None,
                    {
                        "dbt": {"rename_env": "yes"},
                        "dbt.env_vars": {"var_1": "global-1"}
                    },
                    {"DBT_VAR_1": "global-1"}
                ),
                (
                    None,
                    {
                        "dbt": {"rename_env": "1"},
                        "dbt.env_vars": {"var_1": "global-1"}
                    },
                    {"DBT_VAR_1": "global-1"}
                ),
                (
                    None,
                    {
                        "dbt": {"rename_env": "on"},
                        "dbt.env_vars": {"var_1": "global-1"}
                    },
                    {"DBT_VAR_1": "global-1"}
                ),
                (
                    "run",
                    {
                        "dbt": {"rename_env": "true"},
                        "dbt.run.env_vars": {"var_1": "run-1"}
                    },
                    {"DBT_VAR_1": "run-1"}
                )
            ]
        )
        def test_renames_variables_when_truthy(
            verb: Optional[str],
            ini_content: Dict,
            expected: Dict[str, str],
            ini_config: AutoCommitConfigParser
        ):
            """should rename environment variables when [dbt].rename_env is truthy"""
            # arrange
            ini_config.write_dict(ini_content)
            provider = IniFileConfigProvider()

            # act
            result = provider.get_env_variables(verb)

            # assert
            assert result == expected

        @pytest.mark.parametrize(
            "verb,ini_content,expected",
            [
                (
                    None,
                    {
                        "dbt": {"rename_env": "false"},
                        "dbt.env_vars": {"var_1": "global-1"}
                    },
                    {"DBT_ENV_VAR_1": "global-1"}
                ),
                (
                    None,
                    {
                        "dbt": {"rename_env": "no"},
                        "dbt.env_vars": {"var_1": "global-1"}
                    },
                    {"DBT_ENV_VAR_1": "global-1"}
                ),
                (
                    None,
                    {
                        "dbt": {"rename_env": "0"},
                        "dbt.env_vars": {"var_1": "global-1"}
                    },
                    {"DBT_ENV_VAR_1": "global-1"}
                ),
                (
                    None,
                    {
                        "dbt": {"rename_env": "off"},
                        "dbt.env_vars": {"var_1": "global-1"}
                    },
                    {"DBT_ENV_VAR_1": "global-1"}
                ),
                (
                    "run",
                    {
                        "dbt": {"rename_env": "false"},
                        "dbt.run.env_vars": {"var_1": "run-1"}
                    },
                    {"DBT_ENV_VAR_1": "run-1"}
                ),
                (
                    "run",
                    {
                        "dbt": {"rename_env": "no"},
                        "dbt.run.env_vars": {"var_1": "run-1"}
                    },
                    {"DBT_ENV_VAR_1": "run-1"}
                ),
                (
                    "run",
                    {
                        "dbt": {"rename_env": "0"},
                        "dbt.run.env_vars": {"var_1": "run-1"}
                    },
                    {"DBT_ENV_VAR_1": "run-1"}
                ),
                (
                    "run",
                    {
                        "dbt": {"rename_env": "off"},
                        "dbt.run.env_vars": {"var_1": "run-1"}
                    },
                    {"DBT_ENV_VAR_1": "run-1"}
                )
            ]
        )
        def test_renames_variables_when_falsy(
            verb: Optional[str],
            ini_content: Dict,
            expected: Dict[str, str],
            ini_config: AutoCommitConfigParser
        ):
            """should not rename environment variables when [dbt].rename_env is falsy"""
            # arrange
            ini_config.write_dict(ini_content)
            provider = IniFileConfigProvider()

            # act
            result = provider.get_env_variables(verb)

            # assert
            assert result == expected

    def describe_get_env_variables_apply_global():
        def test_returns_none_when_option_not_set(ini_config: AutoCommitConfigParser):
            """should return None when [dbt].apply_global_env_vars is not set"""
            # arrange
            ini_config.write_dict({
                "dbt": {"dummy": "yes"}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_env_variables_apply_global(available_verbs)

            # assert
            assert result is None

        def test_returns_verbs_when_option_has_valid_value(ini_config: AutoCommitConfigParser):
            """should return Set[verb] when [dbt].apply_global_env_vars has valid value"""
            # arrange
            ini_config.write_dict({
                "dbt": {"apply_global_env_vars": "run,test"}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_env_variables_apply_global(available_verbs)

            # assert
            assert result == {"run", "test"}

        def test_raises_when_option_value_has_invalid_format(ini_config: AutoCommitConfigParser):
            """should raise ValueError when [dbt].apply_global_env_vars format is invalid"""
            # arrange
            ini_config.write_dict({
                "dbt": {"apply_global_env_vars": "run|test"}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act & assert
            with pytest.raises(ValueError, match="INI: [dbt].apply_global_env_vars: Should be in the form 'verb(,verb)+'"):
                provider.get_env_variables_apply_global(available_verbs)

        def test_raises_when_option_value_contains_unsupported_verbs(ini_config: AutoCommitConfigParser):
            """should raise ValueError when [dbt].apply_global_env_vars contains unsupported verb(s)"""
            # arrange
            ini_config.write_dict({
                "dbt": {"apply_global_env_vars": "run,verb"}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act & assert
            with pytest.raises(ValueError, match="INI: [dbt].apply_global_env_vars: Verbs ['verb'] are not supported"):
                provider.get_env_variables_apply_global(available_verbs)

    def describe_get_flag_allowlist():
        @pytest.mark.parametrize(
            "verb,ini_content,expected",
            [
                (
                    None,
                    {"dbt.flags.allowlist": {"global_1": "true", "global_2": "true"}},
                    {"global_1": True, "global_2": True}
                ),
                (
                    "run",
                    {"dbt.run.flags.allowlist": {"run_1": "true", "run_2": "true"}},
                    {"run_1": True, "run_2": True}
                )
            ]
        )
        def test_enable_flags(
            verb: Optional[str],
            ini_content: Dict,
            expected: Dict[str, bool],
            ini_config: AutoCommitConfigParser
        ):
            """should return enabled flags from ini file"""
            # arrange
            ini_config.write_dict(ini_content)
            provider = IniFileConfigProvider()

            with patch("app.dbt.config.jsonschema.DbtFlagsSchema.validate_flag_availability"):
                # act
                result = provider.get_flag_allowlist(verb)

                # assert
                assert result == expected

        @pytest.mark.parametrize(
            "verb,ini_content,expected",
            [
                (
                    None,
                    {"dbt.flags.allowlist": {"global_1": "false", "global_2": "false"}},
                    {"global_1": False, "global_2": False}
                ),
                (
                    "run",
                    {"dbt.run.flags.allowlist": {"run_1": "false", "run_2": "false"}},
                    {"run_1": False, "run_2": False}
                )
            ]
        )
        def test_disable_flags(
            verb: Optional[str],
            ini_content: Dict,
            expected: Dict[str, bool],
            ini_config: AutoCommitConfigParser
        ):
            """should return disabled flags from ini file"""
            # arrange
            ini_config.write_dict(ini_content)
            provider = IniFileConfigProvider()

            with patch("app.dbt.config.jsonschema.DbtFlagsSchema.validate_flag_availability"):
                # act
                result = provider.get_flag_allowlist(verb)

                # assert
                assert result == expected

    def describe_get_flag_allowlist_apply_global():
        def test_returns_none_when_option_not_set(ini_config: AutoCommitConfigParser):
            """should return None when [dbt].apply_global_allowlist is not set"""
            # arrange
            ini_config.write_dict({
                "dbt": {"dummy": "yes"}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_flag_allowlist_apply_global(available_verbs)

            # assert
            assert result is None

        def test_returns_allowed_verbs_when_option_has_valid_value(ini_config: AutoCommitConfigParser):
            """should return set of verbs when [dbt].apply_global_allowlist has valid value"""
            # arrange
            ini_config.write_dict({
                "dbt": {"apply_global_allowlist": "run,test"}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_flag_allowlist_apply_global(available_verbs)

            # assert
            assert result == {"run", "test"}

        @pytest.mark.parametrize(
            "value",
            [
                "run;test",  # semicolon-separated
                "run test",  # space-separated
                "run|test",  # pipe-separated
            ]
        )
        def test_raises_when_option_value_has_invalid_format(
            value: str,
            ini_config: AutoCommitConfigParser
        ):
            """should raise ValueError when [dbt].apply_global_allowlist format is invalid"""
            # arrange
            ini_config.write_dict({
                "dbt": {"apply_global_allowlist": value}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act & assert
            with pytest.raises(ValueError, match="INI: [dbt].apply_global_allowlist: Should be in the form 'verb(,verb)+'"):
                provider.get_flag_allowlist_apply_global(available_verbs)

        @pytest.mark.parametrize(
            "value,unsupported_verbs",
            [
                ("build", ["build"]),  # single unsupported verb
                ("clean", ["clean"]),
                ("compile", ["compile"]),
                ("debug", ["debug"]),
                ("deps", ["deps"]),
                ("docs", ["docs"]),
                ("init", ["init"]),
                ("list", ["list"]),
                ("parse", ["parse"]),
                ("run-operation", ["run-operation"]),
                ("show", ["show"]),
                ("source", ["source"]),
                ("build,clean", ["build", "clean"]),  # multiple unsupported verbs
                ("run,build", ["build"]),  # mix of supported and unsupported
            ]
        )
        def test_raises_when_option_value_contains_unsupported_verbs(
            value: str,
            unsupported_verbs: List[str],
            ini_config: AutoCommitConfigParser
        ):
            """should raise ValueError when [dbt].apply_global_allowlist contains unsupported verb(s)"""
            # arrange
            ini_config.write_dict({
                "dbt": {"apply_global_allowlist": value}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act & assert
            with pytest.raises(ValueError, match=f"INI: [dbt].apply_global_allowlist: Verbs {unsupported_verbs} are not supported"):
                provider.get_flag_allowlist_apply_global(available_verbs)

    def describe_get_flag_internal_values():
        @pytest.mark.parametrize(
            "verb,expected",
            [
                (
                    None,
                    {
                        "var_1": "global-1",
                        "var_2": "global-2"
                    }
                ),
                (
                    "run",
                    {
                        "var_1": "run-1"
                    }
                ),
                (
                    "test",
                    {
                        "var_1": "test-1"
                    }
                )
            ]
        )
        def test_base_case(
            verb: Optional[str],
            expected: Dict[str, str],
            ini_config: AutoCommitConfigParser
        ):
            """should return internal flag values from ini file sections for given verb"""
            # arrange
            ini_config.write_dict({
                "dbt.flags.values": {
                    "var_1": "global-1",
                    "var_2": "global-2"
                },
                "dbt.run.flags.values": {
                    "var_1": "run-1"
                },
                "dbt.test.flags.values": {
                    "var_1": "test-1"
                },
            })
            provider = IniFileConfigProvider()

            with patch("app.dbt.config.jsonschema.DbtFlagsSchema.validate_flag_availability"):
                # act
                result = provider.get_flag_internal_values(verb)

                # assert
                assert result == expected

        def test_no_scope_conflict(ini_config: AutoCommitConfigParser):
            """should return internal flag values for verb even if same-name options exist in global scope"""
            # arrange
            ini_config.write_dict({
                "dbt.flags.values": {
                    "var_1": "global-1",
                    "var_2": "global-2"
                },
                "dbt.run.flags.values": {
                    "var_1": "run-1"
                }
            })
            provider = IniFileConfigProvider()

            with patch("app.dbt.config.jsonschema.DbtFlagsSchema.validate_flag_availability"):
                # act
                result = provider.get_flag_internal_values(verb="run")

                # assert
                assert result == {"var_1": "run-1"}

        @pytest.mark.parametrize(
            "verb,ini_content,error",
            [
                # case: scope global, single unrecognized variable
                (
                    None,
                    {
                        "dbt.flags.values": {
                            "var_1": "global-1"
                        }
                    },
                    {
                        "message": "INI: [dbt.flags.values]: Unrecognized flags",
                        "exceptions": [
                            (KeyError, 'INI: [dbt.flags.values].var_1: ("--var-1") is not recognized as a valid global dbt flag.')
                        ]
                    }
                ),
                # case: scope global, multiple unrecognized variables
                (
                    None,
                    {
                        "dbt.flags.values": {
                            "var_1": "global-1",
                            "var_2": "global-2"
                        }
                    },
                    {
                        "message": "INI: [dbt.flags.values]: Unrecognized flags",
                        "exceptions": [
                            (KeyError, 'INI: [dbt.flags.values].var_1: ("--var-1") is not recognized as a valid global dbt flag.'),
                            (KeyError, 'INI: [dbt.flags.values].var_2: ("--var-2") is not recognized as a valid global dbt flag.')
                        ]
                    }
                ),
                # case: scope verb=run, single unrecognized variable
                (
                    "run",
                    {
                        "dbt.run.flags.values": {
                            "var_1": "run-1"
                        }
                    },
                    {
                        "message": "INI: [dbt.run.flags.values]: Unrecognized flags",
                        "exceptions": [
                            (KeyError, 'INI: [dbt.run.flags.values].var_1: ("--var-1") is not recognized as a valid dbt run flag.')
                        ]
                    }
                ),
                # case: scope verb=run, multiple unrecognized variables
                (
                    "run",
                    {
                        "dbt.run.flags.values": {
                            "var_1": "run-1",
                            "var_2": "run-2"
                        }
                    },
                    {
                        "message": "INI: [dbt.run.flags.values]: Unrecognized flags",
                        "exceptions": [
                            (KeyError, 'INI: [dbt.run.flags.values].var_1: ("--var-1") is not recognized as a valid dbt run flag.'),
                            (KeyError, 'INI: [dbt.run.flags.values].var_2: ("--var-2") is not recognized as a valid dbt run flag.')
                        ]
                    }
                )
            ]
        )
        def test_raises_for_invalid_flags(
            verb: Optional[str],
            ini_content: Dict,
            error: Dict[str, Any],
            ini_config: AutoCommitConfigParser
        ):
            """should raise an ExceptionGroup comprised of one KeyError per invalid flag, with matching messages"""
            # arrange
            ini_config.write_dict(ini_content)
            provider = IniFileConfigProvider()

            # act & assert
            with pytest.raises(ExceptionGroup, match=error["message"]) as exc_info:
                provider.get_flag_internal_values(verb)

            assert len(exc_info.exceptions) == len(error["exceptions"]), (
                f"ExceptionGroup should have {len(error['exceptions'])} exceptions. "
                f"Got {len(exc_info.exceptions)} instead."
            )
            for idx, exc in enumerate(exc_info.exceptions):
                assert isinstance(exc, error["exceptions"][idx][0]), (
                    f"ExceptionGroup.exceptions[{idx}] should be an instance of "
                    f"{error['exceptions'][idx][0]}. Got {type(exc)} instead."
                )
                assert str(exc) == error["exceptions"][idx][1], (
                    f"ExceptionGroup.exceptions[{idx}] should have message "
                    f"'{error['exceptions'][idx][1]}'. Got '{str(exc)}' instead."
                )

    def describe_get_flag_internal_values_apply_global():
        def test_returns_none_when_option_not_set(ini_config: AutoCommitConfigParser):
            """should return None when [dbt].apply_global_internal_flag_values is not set"""
            # arrange
            ini_config.write_dict({
                "dbt": {"dummy": "yes"}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_flag_internal_values_apply_global(available_verbs)

            # assert
            assert result is None

        def test_returns_allowed_verbs_when_option_has_valid_value(ini_config: AutoCommitConfigParser):
            """should return set of verbs when [dbt].apply_global_internal_flag_values has valid value"""
            # arrange
            ini_config.write_dict({
                "dbt": {"apply_global_internal_flag_values": "run,test"}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_flag_internal_values_apply_global(available_verbs)

            # assert
            assert result == {"run", "test"}

        @pytest.mark.parametrize(
            "value",
            [
                "run;test",  # semicolon-separated
                "run test",  # space-separated
                "run|test",  # pipe-separated
            ]
        )
        def test_raises_when_option_value_has_invalid_format(
            value: str,
            ini_config: AutoCommitConfigParser
        ):
            """should raise ValueError when [dbt].apply_global_internal_flag_values format is invalid"""
            # arrange
            ini_config.write_dict({
                "dbt": {"apply_global_internal_flag_values": value}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act & assert
            with pytest.raises(ValueError, match="INI: [dbt].apply_global_internal_flag_values: Should be in the form 'verb(,verb)+'"):
                provider.get_flag_internal_values_apply_global(available_verbs)

        @pytest.mark.parametrize(
            "value,unsupported_verbs",
            [
                ("build", ["build"]),
                ("clean", ["clean"]),
                ("compile", ["compile"]),
                ("debug", ["debug"]),
                ("deps", ["deps"]),
                ("docs", ["docs"]),
                ("init", ["init"]),
                ("list", ["list"]),
                ("parse", ["parse"]),
                ("run-operation", ["run-operation"]),
                ("show", ["show"]),
                ("source", ["source"]),
                ("build,clean", ["build", "clean"]),  # multiple unsupported verbs
                ("run,build", ["build"]),  # mix of supported and unsupported
            ]
        )
        def test_raises_when_option_value_contains_unsupported_verbs(
            value: str,
            unsupported_verbs: List[str],
            ini_config: AutoCommitConfigParser
        ):
            """should raise ValueError when [dbt].apply_global_internal_flag_values contains unsupported verb(s)"""
            # arrange
            ini_config.write_dict({
                "dbt": {"apply_global_internal_flag_values": value}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act & assert
            with pytest.raises(ValueError, match=f"INI: [dbt].apply_global_internal_flag_values: Verbs {unsupported_verbs} are not supported"):
                provider.get_flag_internal_values_apply_global(available_verbs)

    def describe_get_projects_root_dir():
        def test_returns_none_when_option_not_set(ini_config: AutoCommitConfigParser):
            """should return None when [dbt].projects_root_dir is not set"""
            # arrange
            ini_config.write_dict({
                "dbt": {"dummy": "yes"}
            })
            provider = IniFileConfigProvider()

            # act
            result = provider.get_projects_root_dir()

            # assert
            assert result is None

        def test_returns_path_when_option_set(ini_config: AutoCommitConfigParser):
            """should return [dbt].projects_root_dir as a Path instance when it is set"""
            # arrange
            ini_config.write_dict({
                "dbt": {"projects_root_dir": "/path/to/dir"}
            })
            provider = IniFileConfigProvider()

            # act
            result = provider.get_projects_root_dir()

            # assert
            assert result == Path("/path/to/dir")

    def describe_get_variables():
        @pytest.mark.parametrize("verb", [None, "run"])
        def test_returns_none_when_no_sections(
            verb: Optional[str],
            ini_config: AutoCommitConfigParser
        ):
            """should return None when no vars sections exist in ini file"""
            # arrange
            ini_config.write_dict({
                "dbt": {"dummy": "yes"}
            })
            provider = IniFileConfigProvider()

            # act
            result = provider.get_variables(verb)

            # assert
            assert result is None

        @pytest.mark.parametrize(
            "verb,ini_content,expected",
            [
                (
                    None,
                    {
                        "dbt.vars": {
                            "var_1": "global-1"
                        }
                    },
                    {
                        "var_1": "global-1"
                    }
                ),
                (
                    None,
                    {
                        "dbt.vars": {
                            "var_1": "global-1",
                            "var_2": "global-2"
                        }
                    },
                    {
                        "var_1": "global-1",
                        "var_2": "global-2"
                    }
                ),
                (
                    "run",
                    {
                        "dbt.run.vars": {
                            "var_1": "run-1"
                        }
                    },
                    {
                        "var_1": "run-1"
                    }
                ),
                (
                    "run",
                    {
                        "dbt.run.vars": {
                            "var_1": "run-1",
                            "var_2": "run-2"
                        }
                    },
                    {
                        "var_1": "run-1",
                        "var_2": "run-2"
                    }
                )
            ]
        )
        def test_returns_variables_when_set(
            verb: Optional[str],
            ini_content: Dict,
            expected: Dict[str, str],
            ini_config: AutoCommitConfigParser
        ):
            """should return variables as a dict with keys in snake_case when variables are set in ini file"""
            # arrange
            ini_config.write_dict(ini_content)
            provider = IniFileConfigProvider()

            # act
            result = provider.get_variables(verb)

            # assert
            assert result == expected

        def test_verb_variables_only_specific_verb(ini_config: AutoCommitConfigParser):
            """should only return variables from [dbt.{verb}.vars] when verb is specified"""
            # arrange
            ini_config.write_dict({
                "dbt.vars": {
                    "var_1": "global-1",
                    "var_2": "global-2"
                },
                "dbt.run.vars": {
                    "var_1": "run-1",
                    "var_2": "run-2"
                },
                "dbt.test.vars": {
                    "var_1": "test-1",
                    "var_2": "test-2"
                }
            })
            provider = IniFileConfigProvider()

            # act
            result = provider.get_variables("run")

            # assert
            assert result == {
                "var_1": "run-1",
                "var_2": "run-2"
            }

    def describe_get_variables_apply_global():
        def test_returns_none_when_option_not_set(ini_config: AutoCommitConfigParser):
            """should return None when [dbt].apply_global_vars is not set"""
            # arrange
            ini_config.write_dict({
                "dbt": {"dummy": "yes"}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_variables_apply_global(available_verbs)

            # assert
            assert result is None

        def test_returns_verbs_when_option_has_valid_value(ini_config: AutoCommitConfigParser):
            """should return Set[verb] when [dbt].apply_global_vars has valid value"""
            # arrange
            ini_config.write_dict({
                "dbt": {"apply_global_vars": "run,test"}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_variables_apply_global(available_verbs)

            # assert
            assert result == {"run", "test"}

        def test_raises_when_option_value_has_invalid_format(ini_config: AutoCommitConfigParser):
            """should raise ValueError when [dbt].apply_global_vars format is invalid"""
            # arrange
            ini_config.write_dict({
                "dbt": {"apply_global_vars": "run|test"}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act & assert
            with pytest.raises(ValueError, match="INI: [dbt].apply_global_vars: Should be in the form 'verb(,verb)+'"):
                provider.get_variables_apply_global(available_verbs)

        def test_raises_when_option_value_contains_unsupported_verbs(ini_config: AutoCommitConfigParser):
            """should raise ValueError when [dbt].apply_global_vars contains unsupported verb(s)"""
            # arrange
            ini_config.write_dict({
                "dbt": {"apply_global_vars": "run,verb"}
            })
            provider = IniFileConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act & assert
            with pytest.raises(ValueError, match="INI: [dbt].apply_global_vars: Verbs ['verb'] are not supported"):
                provider.get_variables_apply_global(available_verbs)

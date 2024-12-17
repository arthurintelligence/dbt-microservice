# pylint: disable=unused-variable,assignment-from-none,invalid-name
from pathlib import Path
from unittest.mock import patch
from typing import Dict, List, Optional

import pytest

from app.dbt.config.providers.environment import EnvironmentConfigProvider
from tests.fixtures.mock_env import MockEnv, fixtures as mockenv_fixtures

# Register fixtures
pytest.fixture(mockenv_fixtures["mock_env"])  # mock_env


def describe_EnvironmentConfigProvider():
    """Tests for EnvironmentConfigProvider class methods"""

    def describe_get_allowed_verbs():
        def test_returns_none_when_variable_not_set():
            """should return None when DBT_ALLOWED_VERBS is not set"""
            # arrange
            provider = EnvironmentConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_allowed_verbs(available_verbs)

            # assert
            assert result is None

        def test_returns_allowed_verbs_when_variable_has_valid_value(mock_env: MockEnv):
            """should return set of verbs when DBT_ALLOWED_VERBS is valid"""
            # arrange
            provider = EnvironmentConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}
            mock_env.setenv("DBT_ALLOWED_VERBS", "run,test")

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
        def test_raises_when_variable_value_has_invalid_format(allowed_verb_str: str, mock_env: MockEnv):
            """should raise ValueError when DBT_ALLOWED_VERBS format is invalid"""
            # arrange
            provider = EnvironmentConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}
            mock_env.setenv("DBT_ALLOWED_VERBS", allowed_verb_str)

            # act & assert
            with pytest.raises(ValueError, match="ENV: DBT_ALLOWED_VERBS: Should be in the form 'verb(,verb)+'"):
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
            mock_env: MockEnv
        ):
            """should raise ValueError when DBT_ALLOWED_VERBS contains unsupported verb(s)"""
            # arrange
            provider = EnvironmentConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}
            mock_env.setenv("DBT_ALLOWED_VERBS", allowed_verb_str)

            # act & assert
            with pytest.raises(
                ValueError,
                match=f"ENV: DBT_ALLOWED_VERBS: Verbs {unsupported_verbs} are not supported"
            ):
                provider.get_allowed_verbs(available_verbs)

    def describe_get_flag_allowlist():

        @pytest.mark.parametrize(
            "verb,expected",
            [
                (None, {"global_1": True, "global_2": True}),
                ("run", {"run_1": True, "run_2": True})
            ]
        )
        def test_enable_variable(verb: Optional[str], expected: Dict[str, bool], mock_env: MockEnv):
            """should return enabled flags from environment variables"""
            # arrange
            provider = EnvironmentConfigProvider()
            mock_env.setenv("DBT_ENABLE_FLAGS", "global_1,global_2")
            mock_env.setenv("DBT_RUN_ENABLE_FLAGS", "run_1,run_2")

            patch_target = "app.dbt.config.jsonschema.DbtFlagsSchema.validate_flag_availability"
            patch_value = None  # DbtFlagsSchema.validate_flag_availability returns None
            with patch(patch_target, patch_value):
                # act
                result = provider.get_flag_allowlist(verb)

                # assert
                assert result == expected

        @pytest.mark.parametrize(
            "verb,expected",
            [
                (None, {"global_1": False, "global_2": False}),
                ("run", {"run_1": False, "run_2": False})
            ]
        )
        def test_disable_variable(verb: Optional[str], expected: Dict[str, bool], mock_env: MockEnv):
            """should return disabled flags from environment variables"""
            # arrange
            provider = EnvironmentConfigProvider()
            mock_env.setenv("DBT_DISABLE_FLAGS", "global_1,global_2")
            mock_env.setenv("DBT_RUN_DISABLE_FLAGS", "run_1,run_2")

            patch_target = "app.dbt.config.jsonschema.DbtFlagsSchema.validate_flag_availability"
            patch_value = None  # DbtFlagsSchema.validate_flag_availability returns None
            with patch(patch_target, patch_value):
                # act
                result = provider.get_flag_allowlist(None)

                # assert
                assert result == expected

    def describe_get_flag_allowlist_apply_global():
        def test_returns_none_when_variable_not_set():
            """should return None when DBT_APPLY_GLOBAL_ALLOWLIST is not set"""
            # arrange
            provider = EnvironmentConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_flag_allowlist_apply_global(available_verbs)

            # assert
            assert result is None

        def test_variable_with_valid_value(mock_env: MockEnv):
            """should return Set[verb] when DBT_APPLY_GLOBAL_ALLOWLIST is set with a valid value"""
            # arrange
            provider = EnvironmentConfigProvider()
            mock_env.setenv("DBT_APPLY_GLOBAL_ALLOWLIST", "run,test")
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_flag_allowlist_apply_global(available_verbs)

            # assert
            assert result == {"run", "test"}

        def test_variable_with_invalid_format(mock_env: MockEnv):
            """should raise ValueError when DBT_APPLY_GLOBAL_ALLOWLIST format is invalid"""
            # arrange
            provider = EnvironmentConfigProvider()
            env_var_name = "DBT_APPLY_GLOBAL_ALLOWLIST"
            mock_env.setenv(env_var_name, "run|test")
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act & assert
            with pytest.raises(ValueError, match=f"ENV: {env_var_name}: Should be in the form 'verb(,verb)+'"):
                provider.get_flag_allowlist_apply_global(available_verbs)

        def test_variable_with_unsupported_verbs(mock_env: MockEnv):
            """should raise ValueError when DBT_APPLY_GLOBAL_ALLOWLIST contains unsupported verbs"""
            # arrange
            provider = EnvironmentConfigProvider()
            env_var_name = "DBT_APPLY_GLOBAL_ALLOWLIST"
            mock_env.setenv(env_var_name, "run,verb")
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act & assert
            with pytest.raises(ValueError, match=f"ENV: {env_var_name}: Verbs ['verb'] are not supported"):
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
                        "run_var_1": "run-1",
                    }
                ),
                (
                    "test",
                    {
                        "test_var_1": "test-1",
                    }
                )
            ]
        )
        def test_base_case(verb: Optional[str], expected: Dict[str, str], mock_env: MockEnv):
            """should return internal flag values from environment for given verb"""
            # arrange
            provider = EnvironmentConfigProvider()
            mock_env.setenv("DBT_FLAG_VAR_1", "global-1")
            mock_env.setenv("DBT_FLAG_VAR_2", "global-2")
            mock_env.setenv("DBT_RUN_FLAG_RUN_VAR_1", "run-1")
            mock_env.setenv("DBT_TEST_FLAG_TEST_VAR_1", "test-1")

            with patch("app.dbt.config.jsonschema.DbtFlagsSchema.validate_flag_availability"):
                # act
                result = provider.get_flag_internal_values(verb)

                # assert
                assert result == expected

        def test_no_scope_conflict(mock_env: MockEnv):
            """should return internal flag values for verb even if same-name variables exists at global scope"""
            # arrange
            provider = EnvironmentConfigProvider()
            mock_env.setenv("DBT_FLAG_VAR_1", "global-1")
            mock_env.setenv("DBT_FLAG_VAR_2", "global-2")
            mock_env.setenv("DBT_RUN_FLAG_VAR_1", "run-1")

            with patch("app.dbt.config.jsonschema.DbtFlagsSchema.validate_flag_availability"):
                # act
                result = provider.get_flag_internal_values(verb="run")

                # assert
                assert result == {"var_1": "run-1"}

        @pytest.mark.parametrize(
            "verb,env,error",
            [
                # case: scope global, single unrecognized variable
                (
                    None,
                    {
                        "DBT_FLAG_VAR_1": "global-1"
                    },
                    {
                        "message": "ENV: DBT_FLAG_*: Unrecognized flags",
                        "exceptions": [
                            (KeyError, 'ENV: DBT_FLAG_VAR_1: "--var-1" is not recognized as a valid global dbt flag.')
                        ]
                    }
                ),
                # case: scope global, multiple unrecognized variables
                (
                    None,
                    {
                        "DBT_FLAG_VAR_1": "global-1",
                        "DBT_FLAG_VAR_2": "global-2"
                    },
                    {
                        "message": "ENV: DBT_FLAG_*: Unrecognized flags",
                        "exceptions": [
                            (KeyError, 'ENV: DBT_FLAG_VAR_1: "--var-1" is not recognized as a valid global dbt flag.'),
                            (KeyError, 'ENV: DBT_FLAG_VAR_2: "--var-2" is not recognized as a valid global dbt flag.')
                        ]
                    }
                ),
                # case: scope verb=run, single unrecognized variable
                (
                    None,
                    {
                        "DBT_RUN_FLAG_VAR_1": "run-1"
                    },
                    {
                        "message": "ENV: DBT_RUN_FLAG_*: Unrecognized flags",
                        "exceptions": [
                            (KeyError, 'ENV: DBT_RUN_FLAG_VAR_1: "--var-1" is not recognized as a valid dbt run flag.')
                        ]
                    }
                ),
                # case: scope verb=run, multiple unrecognized variables
                (
                    None,
                    {
                        "DBT_RUN_FLAG_VAR_1": "run-1",
                        "DBT_RUN_FLAG_VAR_2": "run-2"
                    },
                    {
                        "message": "ENV: DBT_FLAG_*: Unrecognized flags",
                        "exceptions": [
                            (KeyError, 'ENV: DBT_RUN_FLAG_VAR_1: "--var-1" is not recognized as a valid dbt run flag.'),
                            (KeyError, 'ENV: DBT_RUN_FLAG_VAR_2: "--var-2" is not recognized as a valid dbt run flag.')
                        ]
                    }
                ),
            ]
        )
        def test_raises_for_invalid_flags(verb: Optional[str], env: Dict[str, str], error: Dict[str, Any], mock_env: MockEnv):
            """should raise an ExceptionGroup comprised of one KeyError per invalid flag, with matching messages."""
            # arrange
            provider = EnvironmentConfigProvider()
            for key, value in env.items():
                mock_env.setenv(key, value)

            # act & assert
            with pytest.raises(ExceptionGroup, match=error['message']) as exc_info:
                provider.get_flag_internal_values(verb)

            # assert
            assert (
                len(exc_info.exceptions) == len(error["exceptions"])
            ), (
                f"ExceptionGroup should have {len(error['exceptions'])} "
                f"exceptions. Got {len(exc_info.exception)} instead."
            )
            for idx, exc in enumerate(exc_info.exceptions):
                assert (
                    isinstance(exc, error["exceptions"][idx][0])
                ), (
                    f"ExceptionGroup.exceptions[{idx}] should be an instance of "
                    f"{error['exceptions'][idx][0]}. Got {type(exc)} instead."
                )
                assert (
                    exc.message == error["exceptions"][idx][1]
                ), (
                    f"ExceptionGroup.exceptions[{idx}] should have message "
                    f"'{error['exceptions'][idx][1]}'. Got '{exc.message}' "
                    "instead."
                )

    def describe_get_flag_internal_values_apply_global():
        def test_returns_none_when_variable_not_set():
            """should return None when DBT_APPLY_GLOBAL_INTERNAL_FLAG_VALUES is not set"""
            # arrange
            provider = EnvironmentConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_flag_internal_values_apply_global(available_verbs)

            # assert
            assert result is None

        def test_variable_set_with_valid_value(mock_env: MockEnv):
            """should return Set[verb] when DBT_APPLY_GLOBAL_INTERNAL_FLAG_VALUES is set with a valid value"""
            # arrange
            provider = EnvironmentConfigProvider()
            mock_env.setenv("DBT_APPLY_GLOBAL_INTERNAL_FLAG_VALUES", "run,test")
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_flag_internal_values_apply_global(available_verbs)

            # assert
            assert result == {"run","test"}

        def test_variable_with_invalid_format(mock_env: MockEnv):
            """should raise ValueError when DBT_APPLY_GLOBAL_INTERNAL_FLAG_VALUES format is invalid"""
            # arrange
            provider = EnvironmentConfigProvider()
            env_var_name = "DBT_APPLY_GLOBAL_INTERNAL_FLAG_VALUES"
            mock_env.setenv(env_var_name, "run|test")
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act & assert
            with pytest.raises(ValueError, match=f"ENV: {env_var_name}: Should be in the form 'verb(,verb)+'"):
                provider.get_flag_internal_values_apply_global(available_verbs)

        def test_variable_with_unsupported_verbs(mock_env: MockEnv):
            """should raise ValueError when DBT_APPLY_GLOBAL_INTERNAL_FLAG_VALUES contains unsupported verbs"""
            # arrange
            provider = EnvironmentConfigProvider()
            env_var_name = "DBT_APPLY_GLOBAL_INTERNAL_FLAG_VALUES"
            mock_env.setenv(env_var_name, "run,verb")
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act & assert
            with pytest.raises(ValueError, match=f"ENV: {env_var_name}: Verbs ['verb'] are not supported"):
                provider.get_flag_internal_values_apply_global(available_verbs)

    def describe_get_env_variables():

        def test_global_no_variables_set(mock_env: MockEnv):
            """should return None if no DBT_ENV_* environment variables are set and verb is None"""
            # arrange
            provider = EnvironmentConfigProvider()
            mock_env.setenv("DBT_RUN_ENV_VAR_1", "run-1")

            # act
            result = provider.get_env_variables(None)

            # assert
            assert result is None
    
        def test_verb_no_variables_set(mock_env: MockEnv):
            """should return None if no DBT_{verb}_ENV_* environment variables are set and verb is not None"""
            # arrange
            provider = EnvironmentConfigProvider()
            mock_env.setenv("DBT_ENV_VAR_1", "global-1")

            # act
            result = provider.get_env_variables("run")

            # assert
            assert result is None

        @pytest.mark.parametrize(
            "env,expected",
            [
                ({"DBT_ENV_SECRET_VAR_1": "global-1"}, {"DBT_ENV_SECRET_VAR_1": "global-1"}),
                (
                    {
                        "DBT_ENV_SECRET_VAR_1": "global-1",
                        "DBT_ENV_CUSTOM_ENV_VAR_1": "global-2"
                    },
                    {
                        "DBT_ENV_SECRET_VAR_1": "global-1",
                        "DBT_ENV_CUSTOM_ENV_VAR_1": "global-2"
                    }
                ),
                (
                    {
                        "DBT_ENV_VAR_1": "global-1",
                        "DBT_ENV_SECRET_VAR_2": "global-2",
                        "DBT_ENV_CUSTOM_ENV_VAR_3": "global-3"
                    },
                    {
                        "DBT_ENV_VAR_1": "global-1",
                        "DBT_ENV_SECRET_VAR_2": "global-2",
                        "DBT_ENV_CUSTOM_ENV_VAR_3": "global-3"
                    },
                ),
            ]
        )
        def test_global_variables_set(env: Dict[str, str], expected: Dict[str, str], mock_env: MockEnv):
            """should return dict of environment variables if one or more DBT_ENV_* environment variables are set and verb is None"""
            # arrange
            provider = EnvironmentConfigProvider()
            for key, value in env.items():
                mock_env.setenv(key, value)
            
            # act
            result = provider.get_env_variables(None)

            # assert
            assert result == expected

        @pytest.mark.parametrize(
            "env,expected",
            [
                ({"DBT_ENV_SECRET_VAR_1": "global-1"}, {"DBT_ENV_SECRET_VAR_1": "global-1"}),
                (
                    {
                        "DBT_ENV_SECRET_VAR_1": "global-1",
                        "DBT_ENV_CUSTOM_ENV_VAR_1": "global-2"
                    },
                    {
                        "DBT_ENV_SECRET_VAR_1": "global-1",
                        "DBT_ENV_CUSTOM_ENV_VAR_1": "global-2"
                    }
                ),
                (
                    {
                        "DBT_ENV_VAR_1": "global-1",
                        "DBT_ENV_SECRET_VAR_2": "global-2",
                        "DBT_ENV_CUSTOM_ENV_VAR_3": "global-3"
                    },
                    {
                        "DBT_ENV_VAR_1": "global-1",
                        "DBT_ENV_SECRET_VAR_2": "global-2",
                        "DBT_ENV_CUSTOM_ENV_VAR_3": "global-3"
                    },
                ),
            ]
        )
        def test_verb_variables_set(env: Dict[str, str], expected: Dict[str, str], mock_env: MockEnv):
            """should return dict of environment variables when one or more DBT_{verb}_ENV_* environment variables are set and verb is {verb}"""
            # arrange
            provider = EnvironmentConfigProvider()
            for key, value in env.items():
                mock_env.setenv(key, value)
            
            # act
            result = provider.get_env_variables("run")

            # assert
            assert result == expected

        def test_verb_variables_only_given_verb(mock_env: MockEnv):
            """should only return environment variables starting with DBT_{verb}_ENV_* when verb = {verb}"""
            provider = EnvironmentConfigProvider()
            verb = "run"
            mock_env.setenv("DBT_ENV_VAR_1", "global-1")
            mock_env.setenv("DBT_ENV_SECRET_VAR_2", "global-2")
            mock_env.setenv("DBT_ENV_CUSTOM_ENV_VAR_3", "global-3")
            mock_env.setenv("DBT_RUN_ENV_VAR_1", "run-1")
            mock_env.setenv("DBT_RUN_ENV_SECRET_VAR_2", "run-2")
            mock_env.setenv("DBT_RUN_ENV_CUSTOM_ENV_VAR_3", "run-3")
            mock_env.setenv("DBT_TEST_ENV_VAR_1", "test-1")
            mock_env.setenv("DBT_TEST_ENV_SECRET_VAR_2", "test-2")
            mock_env.setenv("DBT_TEST_ENV_CUSTOM_ENV_VAR_3", "test-3")

            # act
            result = provider.get_env_variables(verb)

            # assert
            assert result == {
                "DBT_ENV_VAR_1": "run-1",
                "DBT_ENV_SECRET_VAR_2": "run-2",
                "DBT_ENV_CUSTOM_ENV_VAR_3": "run-3",
            }

        @pytest.mark.parametrize(
            "verb,env,expected",
            [
                (None, { "DBT_RENAME_ENV": "on" }, { "DBT_VAR_1": "global-1" }),
                (None, { "DBT_RENAME_ENV": "yes" }, { "DBT_VAR_1": "global-1" }),
                (None, { "DBT_RENAME_ENV": "true" }, { "DBT_VAR_1": "global-1" }),
                (None, { "DBT_RENAME_ENV": "1" }, { "DBT_VAR_1": "global-1" }),
                ("run", { "DBT_RENAME_ENV": "on" }, { "DBT_VAR_1": "run-1" }),
                ("run", { "DBT_RENAME_ENV": "yes" }, { "DBT_VAR_1": "run-1" }),
                ("run", { "DBT_RENAME_ENV": "true" }, { "DBT_VAR_1": "run-1" }),
                ("run", { "DBT_RENAME_ENV": "1" }, { "DBT_VAR_1": "run-1" }),
            ]
        )
        def test_renames_variables_when_truthy(verb: Optional[str], env: Dict[str, str], expected: Dict[str, str], mock_env: MockEnv):
            """should rename environment variables when DBT_RENAME_ENV is truthy"""
            # arrange
            provider = EnvironmentConfigProvider()
            mock_env.setenv("DBT_ENV_VAR_1", "global-1")
            mock_env.setenv("DBT_RUN_ENV_VAR_1", "run-1")
            for key, value in env.items():
                mock_env.setenv(key, value)

            # act
            result = provider.get_env_variables(verb)

            # assert
            assert result == expected

        @pytest.mark.parametrize(
            "verb,env,expected",
            [
                (None, { "DBT_RENAME_ENV": "off" }, { "DBT_ENV_VAR_1": "global-1" }),
                (None, { "DBT_RENAME_ENV": "no" }, { "DBT_ENV_VAR_1": "global-1" }),
                (None, { "DBT_RENAME_ENV": "false" }, { "DBT_ENV_VAR_1": "global-1" }),
                (None, { "DBT_RENAME_ENV": "0" }, { "DBT_ENV_VAR_1": "global-1" }),
                ("run", { "DBT_RENAME_ENV": "off" }, { "DBT_ENV_VAR_1": "run-1" }),
                ("run", { "DBT_RENAME_ENV": "no" }, { "DBT_ENV_VAR_1": "run-1" }),
                ("run", { "DBT_RENAME_ENV": "false" }, { "DBT_ENV_VAR_1": "run-1" }),
                ("run", { "DBT_RENAME_ENV": "0" }, { "DBT_ENV_VAR_1": "run-1" }),
            ]
        )
        def test_renames_variables_when_falsy(verb: Optional[str], env: Dict[str, str], expected: Dict[str, str], mock_env: MockEnv):
            """should not rename environment variables when DBT_RENAME_ENV is falsy"""
            # arrange
            provider = EnvironmentConfigProvider()
            mock_env.setenv("DBT_ENV_VAR_1", "global-1")
            mock_env.setenv("DBT_RUN_ENV_VAR_1", "run-1")
            for key, value in env.items():
                mock_env.setenv(key, value)

            # act
            result = provider.get_env_variables(verb)

            # assert
            assert result == expected

    def describe_get_env_variables_apply_global():
        def test_returns_none_when_variable_not_set():
            """should return None when DBT_APPLY_GLOBAL_ENV_VARS is not set"""
            # arrange
            provider = EnvironmentConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_env_variables_apply_global(available_verbs)

            # assert
            assert result is None

        def test_variable_with_valid_value(mock_env: MockEnv):
            """should return Set[verb] when DBT_APPLY_GLOBAL_ENV_VARS is set with a valid value"""
            # arrange
            provider = EnvironmentConfigProvider()
            mock_env.setenv("DBT_APPLY_GLOBAL_ENV_VARS", "run,test")
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_env_variables_apply_global(available_verbs)

            # assert
            assert result == {"run","test"}

        def test_variable_with_invalid_format(mock_env: MockEnv):
            """should raise ValueError when DBT_APPLY_GLOBAL_ENV_VARS format is invalid"""
            # arrange
            provider = EnvironmentConfigProvider()
            env_var_name = "DBT_APPLY_GLOBAL_ENV_VARS"
            mock_env.setenv(env_var_name, "run|test")
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act & assert
            with pytest.raises(ValueError, match=f"ENV: {env_var_name}: Should be in the form 'verb(,verb)+'"):
                provider.get_env_variables_apply_global(available_verbs)

        def test_variable_with_unsupported_verbs(mock_env: MockEnv):
            """should raise ValueError when DBT_APPLY_GLOBAL_ENV_VARS contains unsupported verbs"""
            # arrange
            provider = EnvironmentConfigProvider()
            env_var_name = "DBT_APPLY_GLOBAL_ENV_VARS"
            mock_env.setenv(env_var_name, "run,verb")
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act & assert
            with pytest.raises(ValueError, match=f"ENV: {env_var_name}: Verbs ['verb'] are not supported"):
                provider.get_env_variables_apply_global(available_verbs)

    def describe_get_projects_root_dir():
        def test_returns_none_when_env_var_not_set():
            """should return None if DBT_PROJECTS_ROOT is not set"""
            # arrange
            provider = EnvironmentConfigProvider()

            # act
            result = provider.get_projects_root_dir()

            # assert
            assert result is None

        def test_returns_path_when_env_var_is_set(mock_env: MockEnv):
            """should return DBT_PROJECTS_ROOT as a Path instance when it is set"""
            # arrange
            provider = EnvironmentConfigProvider()
            mock_env.setenv("DBT_PROJECTS_ROOT", "/path/to/dir")

            # act
            result = provider.get_projects_root_dir()

            # assert
            assert result == Path("/path/to/dir")

    def describe_get_variables():
        @pytest.mark.parametrize("verb", [None, "run"])
        def test_returns_none_when_no_variables_set(verb: Optional[str]):
            """should return None when no DBT_{verb}_VAR_* variables are set"""
            # arrange
            provider = EnvironmentConfigProvider()

            # act
            result = provider.get_variables(verb)

            # assert
            assert result is None

        @pytest.mark.parametrize(
            "verb,env,expected",
            [
                (None, {"DBT_VAR_VAR_1": "global-1"}, {"var_1": "global-1"}),
                (None, {"DBT_VAR_VAR_1": "global-1", "DBT_VAR_VAR_2": "global-2"}, {"var_1": "global-1", "var_2": "global-2"}),
                ("run", {"DBT_RUN_VAR_VAR_1": "run-1"}, {"var_1": "run-1"}),
                ("run", {"DBT_RUN_VAR_VAR_1": "run-1", "DBT_RUN_VAR_VAR_2": "run-2"}, {"var_1": "run-1", "var_2": "run-2"})
            ]
        )
        def test_returns_variables_snake_case_when_set(verb: Optional[str], env: Dict[str, str], expected:Dict[str, str], mock_env: MockEnv):
            """should return variables as a dict with keys in snake_case when one or more DBT_{verb}_VAR_* variables are set"""
            # arrange
            provider = EnvironmentConfigProvider()
            for key, value in env.items():
                mock_env.setenv(key, value)

            # act
            result = provider.get_variables(verb)

            # assert
            assert result == expected

    def describe_get_variables_apply_global():
        def test_returns_none_when_variable_not_set():
            """should return None when DBT_APPLY_GLOBAL_VARS is not set"""
            # arrange
            provider = EnvironmentConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_flag_allowlist_apply_global(available_verbs)

            # assert
            assert result is None

        def test_variable_with_valid_value(mock_env: MockEnv):
            """should return Set[verb] when DBT_APPLY_GLOBAL_VARS is set with a valid value"""
            # arrange
            provider = EnvironmentConfigProvider()
            mock_env.setenv("DBT_APPLY_GLOBAL_VARS", "run,test")
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_flag_allowlist_apply_global(available_verbs)

            # assert
            assert result == {"run","test"}

        def test_variable_with_invalid_format(mock_env: MockEnv):
            """should raise ValueError when DBT_APPLY_GLOBAL_VARS format is invalid"""
            # arrange
            provider = EnvironmentConfigProvider()
            env_var_name = "DBT_APPLY_GLOBAL_VARS"
            mock_env.setenv(env_var_name, "run|test")
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act & assert
            with pytest.raises(ValueError, match=f"ENV: {env_var_name}: Should be in the form 'verb(,verb)+'"):
                provider.get_flag_allowlist_apply_global(available_verbs)

        def test_variable_with_unsupported_verbs(mock_env: MockEnv):
            """should raise ValueError when DBT_APPLY_GLOBAL_VARS contains unsupported verbs"""
            # arrange
            provider = EnvironmentConfigProvider()
            env_var_name = "DBT_APPLY_GLOBAL_VARS"
            mock_env.setenv(env_var_name, "run,verb")
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act & assert
            with pytest.raises(ValueError, match=f"ENV: {env_var_name}: Verbs ['verb'] are not supported"):
                provider.get_flag_allowlist_apply_global(available_verbs)

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Set, Union

from convert_case import kebab_case, snake_case

from app.dbt.config.jsonschema import DbtFlagsSchema
from app.utils.bool import BoolParser

from .abc import BaseConfigProvider

__all__ = ["EnvironmentConfigProvider"]


class EnvironmentConfigProvider(BaseConfigProvider):
    """
    Config provider to retrieve configuration from environment variables.
    """

    def get_allowed_verbs(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        """
        Extracts allowed dbt verbs from environment variable `DBT_ALLOWED_VERBS`.
        "*" will be expanded to all available verbs.

        Arguments:
            available_verbs (Set[str]): Set of all verbs supported by the
                                        microservice implementation

        Raises:
            ValueError: If value is not in the form `verb(,verb)+`
            ValueError: If verbs listed in the `DBT_ALLOWED_VERBS` environment
                        variable are not in available_verbs

        Returns:
            Optional[Set[str]]: Set of allowed verbs if any, None otherwise.
        """
        return self._get_verbs_from_environment_variable("DBT_ALLOWED_VERBS", available_verbs)

    def get_env_variables(self, verb: Optional[str]) -> Optional[Dict[str, str]]:
        """
        Extracts all environment variables that start with DBT_ENV_* (global) or
        DBT_{verb}_ENV_* (verb).
        If `DBT_RENAME_ENV` is set with a truthy value, renames
        `DBT_{verb?}_ENV_{VARIABLE}` vars to `DBT_{VARIABLE}` to match
        dbt environment variable naming conventions in dbt Cloud, which support
        `DBT_`, `DBT_ENV_SECRET_`, and `DBT_ENV_CUSTOM_ENV_` prefixes.
        Always strips the verb from the resulting env variable names; ex.
        DBT_RUN_ENV_VAR -> DBT_ENV_VAR.

        Returns:
            Optional[Dict[str, str]]:
                Mapping of dbt variables with prefix "DBT_ENV_*".
                Returns None if no variables were found in
                the environment.

        References:
            - [Environment Variables | dbt Developer Hub](https://docs.getdbt.com/docs/build/environment-variables)
        """
        verb_str = "" if verb is None else f"{verb.upper()}_"

        def is_env_var(key: str) -> int:
            return key.startswith(f"DBT_{verb_str}ENV_")

        def is_secret_var(key: str) -> int:
            return key.startswith(f"DBT_{verb_str}ENV_SECRET")

        def is_custom_env_var(key: str) -> int:
            return key.startswith(f"DBT_{verb_str}ENV_CUSTOM_ENV")

        def is_base_var(key: str) -> int:
            return is_env_var(key) and not is_secret_var(key) and not is_custom_env_var(key)

        def rename(key: str) -> str:
            return (
                key.replace(f"DBT_{verb_str}ENV_", "DBT_")
                if BoolParser.parse(os.getenv("DBT_RENAME_ENV")) and is_base_var(key)
                else key.replace(verb_str, "")
            )

        env_base_vars = {
            rename(key): value for key, value in os.environ.items() if is_base_var(key)
        }
        env_secret_vars = {
            rename(key): value for key, value in os.environ.items() if is_secret_var(key)
        }
        env_custom_vars = {
            rename(key): value for key, value in os.environ.items() if is_custom_env_var(key)
        }
        env_vars = {**env_base_vars, **env_secret_vars, **env_custom_vars}

        return None if len(env_vars) == 0 else env_vars

    def get_env_variables_apply_global(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        """
        Extract the set of verbs for which the global environment variables are
        to be applied, from the environment variable `DBT_APPLY_GLOBAL_ENV_VARS`.
        "*" will be expanded to all available verbs.

        Args:
            available_verbs (Set[str]):
                Set of all available (supported) verbs, for validation

        Returns:
            Optional[Set[str]]:
                Set of verbs which will be configured.
                Returns None if environment variable is not set.
        """
        return self._get_verbs_from_environment_variable(
            "DBT_APPLY_GLOBAL_ENV_VARS", available_verbs
        )

    def get_flag_allowlist(self, verb: Optional[str]) -> Optional[Dict[str, bool]]:
        """
        Extracts allowlist from environment variables.
         - Uses `DBT_{ENABLE|DISABLE}_FLAGS` for global flags,
         - `DBT_{ENABLE|DISABLE}_{verb}_FLAGS` for verb-specific flags.
         - `{ENABLE}` variables are used to enable flags.
         - `{DISABLE}` variables are used to disable flags, and override
         - `{ENABLE}` variables.
         - Expects all flag names to be valid flag names defined by dbt {verb?}.

        Args:
            verb (Optional[str], optional):
                dbt verb to get the flag allowlist for.
                If verb=None, returns the global flag allowlist.

        Returns:
            Optional[Dict[str, bool]]:
                Verb flag allowlist / Global flag allowlist from
                environment.
                Returns None if the allowlist is empty.
        """

        def _parse_sub_allowlist(variable: str, verb: Optional[str] = None) -> Dict[str, bool]:
            sub_allowlist = {}
            value = os.getenv(variable)
            if value is None:
                return {}

            # Verify that the value matches expected format
            if not re.match(r"^([a-z][a-z0-9\-]+,?)+$", value):
                raise ValueError(
                    f"{type(self).__name__}: {variable}: Invalid value; "
                    "Should be a comma-separated list of flags in kebab case."
                )
            enable = "ENABLE" in variable
            sub_allowlist.update({snake_case(flag): enable for flag in value.split(",")})

            # Raises ExceptionGroup[ValueError] if one or more flags
            # are not recognized
            DbtFlagsSchema.validate_flag_availability(
                verb=verb,
                message=f"{type(self).__name__}: {variable}: Unrecognized flags",
                flag_message=lambda _, flag, is_not_recognized_str: (
                    f'{type(self).__name__}: {variable}: "--{kebab_case(flag)}"'
                    + is_not_recognized_str
                ),
                flags=sub_allowlist,
            )
            return sub_allowlist

        allowlist = {}
        if verb is None:
            allowlist.update(_parse_sub_allowlist("DBT_ENABLE_FLAGS", verb=None))
            allowlist.update(_parse_sub_allowlist("DBT_DISABLE_FLAGS", verb=None))
        else:
            allowlist.update(_parse_sub_allowlist(f"DBT_{verb.upper()}_ENABLE_FLAGS", verb=verb))
            allowlist.update(_parse_sub_allowlist(f"DBT_{verb.upper()}_DISABLE_FLAGS", verb=verb))

        return allowlist if len(allowlist) else None

    def get_flag_allowlist_apply_global(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        """
        Extracts the set of verbs for which the configured global dbt allowlist
        will be merged to their respective verb allowlist, from the
        `DBT_APPLY_GLOBAL_ALLOWLIST` environment variable.
        "*" will be expanded to all available verbs.

        Args:
            available_verbs (Set[str]):
                Set of all available (supported) verbs, for validation

        Returns:
            Optional[Set[str]]:
                Set of verbs which will be configured.
                Returns None if the environment variable is not set.
        """
        return self._get_verbs_from_environment_variable(
            "DBT_APPLY_GLOBAL_ALLOWLIST", available_verbs
        )

    def get_flag_internal_values(self, verb: Optional[str]) -> Optional[Dict[str, str]]:
        """
        Extracts internal flags values from environment variables starting with
        `DBT_{verb?}_FLAG_*`.
        Values returned are not parsed.

        Args:
            verb (Optional[str], optional):
                dbt verb to get the flag allowlist for.
                If verb=None, returns the global flag allowlist.

        Raises:
            ExceptionGroup[str, List[ValueError]]:
                For each flag which is not recognized, raises a ValueError.

        Returns:
            Optional[Dict[str, str]]:
                Dict[flag, value] for given verb flags or global flags,
                from environment.
                Returns None if no internal flags were found.
        """
        # DBT_FLAG_* are env vars specifying values for global dbt flags, while
        # DBT_{verb}_FLAG_* are env vars specifying values for verb-specific
        # dbt flags
        var_prefix = "DBT_FLAG_" if verb is None else f"DBT_{verb.upper()}_FLAG_"
        flags = {}
        for name, value in os.environ.items():
            if name.startswith(var_prefix):
                # Remove the prefix & convert to snake case for validation
                # against available_flags
                flag_name = name[len(var_prefix) :].lower()
                flags[flag_name] = value

        if len(flags) == 0:
            return None

        # Raises ExceptionGroup[ValueError] if one or more flags
        # are not recognized
        DbtFlagsSchema.validate_flag_availability(
            verb=verb,
            message=f"{type(self).__name__}: {var_prefix}*: Unrecognized flags",
            flag_message=lambda verb, flag_name, is_not_recognized_str: (
                f'{type(self).__name__}: {var_prefix}{flag_name.upper()}: "--{kebab_case(flag_name.lower())}"'
                + is_not_recognized_str
            ),
            flags=flags,
        )

        return None if len(flags) == 0 else flags

    def get_flag_internal_values_apply_global(
        self, available_verbs: Set[str]
    ) -> Optional[Set[str]]:
        """
        Extract the set of verbs for which the global internal flag values are
        to be applied, from the environment variable
        `DBT_APPLY_GLOBAL_INTERNAL_FLAG_VALUES`.
        "*" will be expanded to all available verbs.

        Args:
            available_verbs (Set[str]):
                Set of all available (supported) verbs, for validation

        Returns:
            Optional[Set[str]]:
                Set of verbs which will be configured.
                Returns None if environment variable is not set.
        """
        return self._get_verbs_from_environment_variable(
            "DBT_APPLY_GLOBAL_INTERNAL_FLAG_VALUES", available_verbs
        )

    def get_projects_root_dir(self) -> Optional[Path]:
        """
        Extracts projects_root_dir from `DBT_PROJECTS_ROOT` environment variable.

        Returns:
            Optional[Path]: `DBT_PROJECTS_ROOT` as a Path if set, None otherwise.
        """
        ENV_DBT_PROJECTS_ROOT = os.getenv("DBT_PROJECTS_ROOT")
        if ENV_DBT_PROJECTS_ROOT is None:
            return None
        return Path(ENV_DBT_PROJECTS_ROOT)

    def get_variables(self, verb: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Extracts all environment variables that start with `DBT_VAR_*`
        or `DBT_{verb}_VAR_*` if verb is set.

        Returns:
            Dict[str, str]: Mapping of dbt variables with
                            prefix `DBT_VAR_*`/`DBT_{verb}_VAR_*`.
                            Returns None if no variables were found
                            in environment.
        """
        verb_str = "" if verb is None else f"{verb.upper()}_"
        prefix = f"DBT_{verb_str}VAR_"
        variables = {
            key[len(prefix) :].lower(): value
            for key, value in os.environ.items()
            if key.startswith(prefix)
        }
        return None if len(variables) == 0 else variables

    def get_variables_apply_global(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        """
        Extract the set of verbs for which the global dbt variables are
        to be applied, from the environment variable `DBT_APPLY_GLOBAL_VARS`.
        "*" will be expanded to all available verbs.

        Args:
            available_verbs (Set[str]):
                Set of all available (supported) verbs, for validation

        Returns:
            Optional[Set[str]]:
                Set of verbs which will be configured.
                Returns None if environment variable is not set.
        """
        return self._get_verbs_from_environment_variable("DBT_APPLY_GLOBAL_VARS", available_verbs)

    def _get_verbs_from_environment_variable(
        self, env_var_name: str, available_verbs: Set[str]
    ) -> Optional[Set[str]]:
        """
        Extracts a set of comma-separated dbt verbs from an environment variable
        and validates the result against available verbs.
        "*" will be expanded to all available verbs.

        Args:
            env_var_name (str): Name of the environment variable to load
            available_verbs (Set[str]):
                Set of all available (supported) verbs, for validation

        Raises:
            ValueError: If value is not in the form `verb(,verb)+`
            ValueError: If verbs listed in the environment variable
                        are not in available_verbs

        Returns:
            Optional[Set[str]]: _description_
        """
        env_var_value = os.getenv(env_var_name)
        if not env_var_value:
            return None
        # Verify that the value matches expected format
        if not re.match(r"^(([a-z][a-z\-]+,?)|[*])+$", env_var_value):
            raise ValueError(
                f"{type(self).__name__}: {env_var_name}: " "Should be in the form 'verb(,verb)+'"
            )

        value = set(verb for verb in env_var_value.split(","))
        if "*" in value:
            value.remove("*")
            value = value | available_verbs
        # Verify that the verbs that have been set in env are supported
        if not value.issubset(available_verbs):
            unsupported_verbs = value - available_verbs
            raise ValueError(
                f"{type(self).__name__}: {env_var_name}: Verbs {sorted(unsupported_verbs)} "
                "are not supported"
            )
        return value

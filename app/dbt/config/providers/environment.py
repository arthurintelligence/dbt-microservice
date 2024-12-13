import os
import re

from pathlib import Path
from typing import Any, Dict, Optional, Set

from convert_case import kebab_case, snake_case

from app.dbt.config.jsonschema import DbtFlagsSchema
from .abc import BaseConfigProvider


__all__ = ["EnvironmentConfigProvider"]

class EnvironmentConfigProvider(BaseConfigProvider):
    """
    Config provider to retrieve configuration from environment variables.
    """
    def get_allowed_verbs(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        """
        Extracts allowed dbt verbs from environment variable DBT_ALLOWED_VERBS

        Arguments:
            available_verbs (Set[str]): Set of all verbs supported by the
                                        microservice implementation

        Raises:
            ValueError: If value is not in the form `verb(,verb)+`
            ValueError: If verbs listed in the DBT_ALLOWED_VERBS environment
                        variable are not in available_verbs

        Returns:
            Optional[Set[str]]: Set of allowed verbs if any, None otherwise.
        """
        if not os.getenv("DBT_ALLOWED_VERBS"):
            return None

        # Verify that the value matches expected format
        if not re.match(r"^([a-z][a-z\-]+,?)+$", os.getenv("DBT_ALLOWED_VERBS")):
            raise ValueError(
                "ENV: DBT_ALLOWED_VERBS: Should be in the form 'verb(,verb)+'."
            )
        
        allowed_verbs = set(verb for verb in allowed_verb_str.split(","))
        # Verify that the verbs that have been set in env are supported
        if not allowed_verbs.issubset(available_verbs):
            unsupported_verbs = allowed_verbs - available_verbs
            raise ValueError(
                f"ENV: DBT_ALLOWED_VERBS: Verbs {list(unsupported_verbs)} "
                "are not supported"
            )

        return allowed_verbs

    def get_flag_allowlist(self, verb: Optional[str]) -> Optional[Dict[str, bool]]:
        """
        Extracts allowlist from environment variables.
        Uses DBT_{ENABLE|DISABLE}_FLAGS for global flags, 
        DBT_{ENABLE|DISABLE}_{verb}_FLAGS for verb-specific flags.
        {ENABLE} variables are used to enable flags.
        {DISABLE} variables are used to disable flags, and override
        {ENABLE} variables.
        Expects all flag names to be valid flag names defined by dbt {verb?}.

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

        def _parse_sub_allowlist(
            variable: str, verb: Optional[bool] = None
        ) -> Dict[str, bool]:
            sub_allowlist = {}
            value = os.getenv(variable)
            if value is None:
                return {}

            # Verify that the value matches expected format
            if not re.match(r"^([a-z][a-z0-9\-]+,?)+$", value):
                raise ValueError(
                    f"ENV: {variable}: Invalid value; "
                    "Should be a comma-separated list of flags in kebab case."
                )
            enable = "ENABLE" in variable
            sub_allowlist.update({flag: enable for flag in value.split(",")})

            # Raises ExceptionGroup[ValueError] if one or more flags
            # are not recognized
            DbtFlagsSchema.validate_flag_availability(
                verb=verb,
                message=f"ENV: {variable}: Unrecognized flags",
                flag_message=lambda _, flag, is_not_recognized_str: (
                    f'ENV: {variable}: "--{kebab_case(flag)}"'
                    + is_not_recognized_str
                ),
                flags=sub_allowlist
            )
            return sub_allowlist

        allowlist = {}
        if verb is None:
            allowlist.update(_parse_sub_allowlist("DBT_ENABLE_FLAGS", verb=None))
            allowlist.update(_parse_sub_allowlist("DBT_DISABLE_FLAGS", verb=None))
        else:
            allowlist.update(_parse_sub_allowlist(
                f"DBT_{verb.upper()}_ENABLE_FLAGS", verb=verb
            ))
            allowlist.update(_parse_sub_allowlist(
                f"DBT_{verb.upper()}_DISABLE_FLAGS", verb=verb
            ))

        return allowlist if len(allowlist) else None

    def get_flag_internal_values(self, verb: Optional[str]) -> Optional[Dict[str, str]]:
        """
        Extracts internal flags values from environment variables starting with
        DBT_{verb?}_FLAG_*
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
                flag_name = snake_case(name[len(var_prefix) :])
                flags[flag_name] = value
        
        if len(flags) == 0:
            return None

        # Raises ExceptionGroup[ValueError] if one or more flags
        # are not recognized
        DbtFlagsSchema.validate_flag_availability(
            verb=verb,
            message=f"ENV {var_prefix}*: Unrecognized flags",
            flag_message=lambda _, flag, is_not_recognized_str: (
                f'ENV {var_prefix}{flag.upper()}*: "--{kebab_case(flag)}"'
                + is_not_recognized_str
            ),
            flags=flags
        )

        return None if len(flags) == 0 else flags

    def get_env_variables(self, verb: Optional[str]) -> Optional[Dict[str, str]]:
        """
        Extracts all enviroment variables that start with DBT_ENV_*.
        Renames DBT_ENV_{VARIABLE} vars to DBT_{VARIABLE} to match dbt
        environment variable naming conventions in dbt Cloud which support
        DBT_, DBT_ENV_SECRET_, and DBT_ENV_CUSTOM_ENV_ prefixes.

        Returns:
            Dict[str, str]: Mapping of dbt variables with prefix "DBT_ENV_*".
                            Returns None if no variables were found in
                            the environment.

        References:
            - [Environment Variables | dbt Developer Hub](https://docs.getdbt.com/docs/build/environment-variables)
        """
        env_base_vars = {
            "DBT_" + key[8:]: value
            for key, value in os.environ.items()
            if key.startswith("DBT_ENV_") and not (
                key.startswith("DBT_ENV_SECRET")
                or key.startswith("DBT_ENV_CUSTOM_ENV")
            )
        }
        env_secret_vars = {
            key: value
            for key, value in os.environ.items()
            if key.startswith("DBT_ENV_SECRET")
        }
        env_custom_vars = {
            key: value
            for key, value in os.environ.items()
            if key.startswith("DBT_ENV_CUSTOM_ENV")
        }
        env_vars = {**env_base_vars, **env_secret_vars, **env_custom_vars}
        
        return None if len(env_vars) == 0 else env_vars

    def get_projects_root_dir(self) -> Optional[Path]:
        """
        Extracts projects_root_dir from DBT_PROJECTS_ROOT environment variable.

        Returns:
            Optional[Path]: DBT_PROJECTS_ROOT as a Path if set, None otherwise.
        """
        if os.getenv("DBT_PROJECTS_ROOT") is None:
            return None
        return Path(os.getenv("DBT_PROJECTS_ROOT"))

    def get_variables(self, verb: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Extracts all environment variables that start with DBT_VAR_*.

        Returns:
            Dict[str, str]: Mapping of dbt variables with
                            prefix "DBT_VAR_*". Returns None if no variables
                            were found in environment.
        """
        variables = {
            key[8:].lower(): value
            for key, value in os.environ.items()
            if key.startswith("DBT_VAR_")
        }
        return None if len(variables) == 0 else variables

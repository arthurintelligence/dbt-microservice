import configparser
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Set

from convert_case import kebab_case, snake_case

from app.dbt.config.jsonschema import DbtFlagsSchema
from .abc import BaseConfigProvider

class IniFileConfigProvider(BaseConfigProvider):
    """
    Config provider to retrieve configuration from the .ini file
    specified by the "DBT_CONFIG_FILE" environment variable.
    """
    @staticmethod
    def _read_ini_file() -> Optional[configparser.ConfigParser]:
        """
        Reads .ini file specified by DBT_CONFIG_FILE environment variable.

        Raises:
            FileNotFoundError:
                If file specified by environment variable
                "DBT_FLAGS_CONFIG_FILE" does not exist.
            IsADirectoryError:
                If file specified by environment variable
                "DBT_FLAGS_CONFIG_FILE" is a directory.
            ValueError:
                If file specified by environment variable
                "DBT_FLAGS_CONFIG_FILE" is not a .ini file.

        Returns:
            Optional[configparser.ConfigParser]: 
                Content of the .ini file.
                Returns None if DBT_CONFIG_FILE environment variable is not set.
        """
        if not os.getenv("DBT_CONFIG_FILE"):
            return None

        config_file = Path(os.getenv("DBT_CONFIG_FILE"))
        if not config_file.exists():
            raise FileNotFoundError(f"DBT_CONFIG_FILE={config_file}.")
        if config_file.is_dir():
            raise IsADirectoryError(f"DBT_CONFIG_FILE={config_file}.")
        if config_file.suffix != ".ini":
            raise ValueError(f"DBT_CONFIG_FILE={config_file} should be a .ini file")
        config = configparser.ConfigParser()
        config.read(os.getenv("DBT_CONFIG_FILE"), encoding="utf-8")
        return config

    def __init__(self):
        self.config = IniFileConfigProvider._read_ini_file()

    def get_allowed_verbs(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        """
        Extracts allowed dbt verbs from [dbt].allowed_verb option.

        Arguments:
            available_verbs (Set[str]): Set of all verbs supported by the
                                        microservice implementation

        Raises:
            ValueError: If value is not in the form `verb(,verb)+`
            ValueError: If verbs listed in [dbt].allowed_verbs are not in
                        available_verbs

        Returns:
            Optional[Set[str]]: Set of allowed verbs if any, None otherwise.
        """
        if not self.config.has_option("dbt", "allowed_verbs"):
            return None

        # Verify that the value matches expected format
        allowed_verb_str = self.config.get("dbt", "allowed_verbs")
        if not re.match(r"^([a-z][a-z\-]+,?)+$", allowed_verb_str):
            raise ValueError(
                'INI: [dbt].allowed_verbs: Should be in the form "verb(,verb)+".'
            )

        allowed_verbs = set(verb for verb in allowed_verb_str.split(","))
        # Verify that the verbs that have been set in env are supported
        if not allowed_verbs.issubset(available_verbs):
            unsupported_verbs = allowed_verbs - available_verbs
            raise ValueError(
                f"INI: [dbt].allowed_verbs: Verbs {list(unsupported_verbs)} "
                "are not supported"
            )
        return allowed_verbs

    def get_flag_allowlist(self, verb: Optional[str]) -> Optional[Dict[str, bool]]:
        """
        Extracts allowlist from [dbt.flags.allowlist] section for global flags,
        and [dbt.{verb}.flags.allowlist] for verb-specific flags.
        To enable a flag, use a truthy value (yes, on, 1, true).
        To disable a flag, use a falsy value (no, off, 0, false).
        Expects all flag names to be valid flag names for given verb or global.

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
        section_name = f"dbt.{verb + '.' if verb else ''}flags.allowlist"
        section = self._read_ini_section(section_name)
        if section is None or len(section) == 0:
            return None

        allowlist = {snake_case(flag): value for flag, value in section.items()}
        DbtFlagsSchema.validate_flag_availability(
            verb=verb,
            message=f"INI: [{section_name}]: Unrecognized flags",
            flag_message=lambda _, flag, is_not_recognized_str: (
                f'INI: [{section_name}]: Option {flag} ("--{kebab_case(flag)}")'
                + is_not_recognized_str
            ),
            flags=allowlist
        )
        return allowlist

    def get_flag_internal_values(self, verb: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Extracts internal flag values from the `[dbt.flags.values]` section
        for global flags, and the `[dbt.{verb}.flags.values]` section for
        verb-specific flags.
        Assumes env vars keys are in snake case, but formats to snake case for
        uniformity and safety reasons.

        Args:
            verb (Optional[str], optional):
                dbt verb to get the flags for.
                If verb=None, returns the internal values for global flags.

        Returns:
            Dict[str, str]:
                Dict[flag, value] for the given verb, from ini.
                Values returned are not parsed.
        """
        section_name = (
            "dbt.flags.values" if verb is None else f"dbt.{verb}.flags.values"
        )
        section = self._read_ini_section(section_name)
        if section is None or len(section) == 0:
            return None

        flags = {snake_case(flag): value for flag, value in section.items()}
        DbtFlagsSchema.validate_flag_availability(
            verb=verb,
            message=f"INI: [{section_name}]: Unrecognized flags",
            flag_message=lambda _, flag, is_not_recognized_str: (
                f'INI: [{section_name}]: Option {flag} ("--{kebab_case(flag)}")'
                + is_not_recognized_str
            ),
            flags=flags
        )
        return flags

    def get_env_variables(self, verb: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Extracts environment variables values from the `[dbt.env_vars]`
        section for global env vars, and the `[dbt.{verb}.env_vars]`
        section for verb-specific env vars.
        Assumes env vars keys are in screaming snake case, but formats to
        screaming snake case for uniformity and safety reasons.

        Args:
            verb (Optional[str], optional):
                dbt verb to get the flags for.
                If verb=None, returns the internal values for global flags.

        Returns:
            Dict[str, str]:
                Dict[env_var, value] for the given verb, from ini.
                Values returned are not parsed.
        """
        section_name = (
            "dbt.env_vars" if verb is None else f"dbt.{verb}.env_vars"
        )
        section = self._read_ini_section(section_name)
        if section is None or len(section) == 0:
            return None

        return {snake_case(key).upper(): value for key, value in section.items()}

    def get_projects_root_dir(self) -> Optional[Path]:
        """
        Extracts directory where dbt projects are held from
        [dbt].projects_root_dir option.

        Raises:
            FileNotFoundError: If the path does not exist
            NotADirectoryError: If the path is not a valid directory

        Returns:
            Optional[Set[str]]: Set of allowed verbs if any, None otherwise.
        """
        if not self.config.has_option("dbt", "projects_root_dir"):
            return None
        # prd: project root dir
        prd = Path(self.config.get("dbt", "projects_root_dir"))
        if not prd.exists():
            raise FileNotFoundError(f"[dbt].projects_root_dir={prd}.")
        if not prd.is_dir():
            raise NotADirectoryError(f"[dbt].projects_root_dir={prd}")

        return prd

    def get_variables(self, verb: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Extracts variables values from the `[dbt.vars]`
        section for global env vars, and the `[dbt.{verb}.vars]`
        section for verb-specific env vars.
        Assumes env vars keys are in snake case, but formats to snake case for
        uniformity and safety reasons.

        Args:
            verb (Optional[str], optional):
                dbt verb to get the flags for.
                If verb=None, returns the internal values for global flags.

        Returns:
            Dict[str, str]:
                Dict[var, value] for the given verb, from ini.
                Values returned are not parsed.
        """
        section_name = (
            "dbt.vars" if verb is None else f"dbt.{verb}.vars"
        )
        section = self._read_ini_section(section_name)
        if section is None or len(section) == 0:
            return None

        return {snake_case(key): value for key, value in section.items()}

    def _read_ini_section(self, name: str) -> Optional[Dict[str, Any]]:
        """Shorthand for reading a section from config file"""
        if self.config is None or not self.config.has_section(name):
            return None
        return dict(self.config[name])

import configparser
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from convert_case import kebab_case, snake_case

from app.dbt.config.jsonschema import DbtFlagsSchema

from .abc import BaseConfigProvider


class BoolParser:
    """Small utility class to parse str to bool"""

    truthies = ("true", "yes", "1", "on")
    falsies = ("false", "no", "0", "off")

    @classmethod
    def valid_values(cls) -> Sequence[str]:
        """
        Returns set of all str values that are accepted as booleans.

        Returns:
            Tuple[Any]: All str values that are accepted as booleans.
        """
        return BoolParser.truthies + BoolParser.falsies

    @classmethod
    def parse(cls, value: Optional[str], default: bool = False) -> bool:
        """
        Parses a str to a bool

        Args:
            value (str): Value to parse

        Raises:
            ValueError: if value is not in BoolParser.truthies or BoolParser.falsies

        Returns:
            bool: Boolean representation of value
        """
        if value is None:
            return default

        str_value = str(value).strip().lower()
        if str_value not in cls.valid_values():
            raise ValueError(value)
        return str_value in BoolParser.truthies


class FileConfigProvider(BaseConfigProvider):
    """
    Config provider to retrieve configuration from the .ini file
    specified by the "DBT_CONFIG_FILE" environment variable.
    """

    @classmethod
    def _get_err_message_footer(cls, path: Path) -> str:
        return "\n" f"File: {path}\n" '(Configured through environment variable "DBT_CONFIG_FILE")'

    @classmethod
    def _read_config_file(cls) -> Optional[Tuple[Path, configparser.ConfigParser]]:
        """
        Reads a configuration file specified by DBT_CONFIG_FILE environment variable.
        File content should follow the .cfg / .ini file format.

        Raises:
            FileNotFoundError:
                If file specified by environment variable
                "DBT_CONFIG_FILE" does not exist.
            IsADirectoryError:
                If file specified by environment variable
                "DBT_CONFIG_FILE" is a directory.

        Returns:
            Optional[configparser.ConfigParser]:
                Content of the .ini file.
                Returns None if DBT_CONFIG_FILE environment variable is not set.

        """
        ENV_DBT_CONFIG_FILE = os.getenv("DBT_CONFIG_FILE")
        if ENV_DBT_CONFIG_FILE is None or not ENV_DBT_CONFIG_FILE.strip():
            return None

        path = Path(ENV_DBT_CONFIG_FILE.strip())
        if not path.exists():
            raise FileNotFoundError(
                f"{cls.__name__}: {path}\n"
                '(Configured through environment variable "DBT_CONFIG_FILE")'
            )
        if path.is_dir():
            raise IsADirectoryError(
                f"{cls.__name__}: {path}\n"
                '(Configured through environment variable "DBT_CONFIG_FILE")'
            )

        try:
            config = configparser.ConfigParser()
            config.read(ENV_DBT_CONFIG_FILE, encoding="utf-8")
            if len(config.sections()) == 0:
                exc = configparser.ParsingError(str(path))
                exc.message = (
                    f"{cls.__name__}: File is either empty or does not contains section headers."
                    + cls._get_err_message_footer(path)
                )
                raise exc
        except configparser.MissingSectionHeaderError as exc:  # explicit
            exc.message = (
                f"{cls.__name__}: File is malformed; does not contain section headers."
                + cls._get_err_message_footer(path)
            )
            raise exc

        return path, config

    def __init__(self) -> None:
        config_info = FileConfigProvider._read_config_file()
        self.path, self.config = (None, None) if config_info is None else config_info

    def get_allowed_verbs(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        """
        Extracts allowed dbt verbs from [dbt].allowed_verbs option.
        "*" will be expanded to all available verbs.

        Arguments:
            available_verbs (Set[str]): Set of all verbs supported by the
                                        microservice implementation

        Returns:
            Optional[Set[str]]:
                Set of allowed verbs if any.
                Returns None if the option is not set.
        """
        return self._get_verbs_from_option("dbt", "allowed_verbs", available_verbs)

    def get_env_variables(self, verb: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Extracts environment variables values from the `[dbt.env_vars]`
        section for global env vars, and the `[dbt.{verb}.env_vars]`
        section for verb-specific env vars.
        If the `[dbt].rename_env` option is set to a truthy value, will rename
        `DBT_ENV_{VARIABLE}` vars to `DBT_{VARIABLE}` to match
        dbt environment variable naming conventions in dbt Cloud, which support
        `DBT_`, `DBT_ENV_SECRET_`, and `DBT_ENV_CUSTOM_ENV_` prefixes.

        Args:
            verb (Optional[str], optional):
                dbt verb to get the flags for.
                If verb=None, returns the internal values for global flags.

        Raises:
            ExceptionGroup:
                If one or more options in the `[dbt{.verb?}.env_vars]` does not
                match the expected format `^DBT_([A-Z0-9]+_+)+([A-Z0-9]+)$`
                (constant case starting with `DBT_`), raises an
                ExceptionGroup[KeyError] with one KeyError per offending option.

        Returns:
            Dict[str, str]:
                Dict[env_var, value] for the given verb, from ini.
                Values returned are not parsed.
        """
        if self.config is None:
            return None

        should_rename = False
        try:
            should_rename = self.config.has_option("dbt", "rename_env") and BoolParser.parse(
                value=self.config.get("dbt", "rename_env"), default=False
            )
        except ValueError as exc:
            raise ValueError(
                f"{type(self).__name__}: Option `[dbt].rename_env`: "
                "Value could not be coerced to a boolean value. \n"
                f"Valid values: {BoolParser.valid_values()}." + self._err_message_footer
            ) from exc

        def is_env_var(key: str) -> bool:
            return bool(re.match(r"^DBT_([A-Z0-9]+_+)+([A-Z0-9]+)$", key, flags=re.IGNORECASE))

        def is_secret_var(key: str) -> bool:
            return key.startswith("DBT_ENV_SECRET_")

        def is_custom_env_var(key: str) -> bool:
            return key.startswith("DBT_ENV_CUSTOM_ENV_")

        def is_base_var(key: str) -> bool:
            return is_env_var(key) and not is_secret_var(key) and not is_custom_env_var(key)

        def rename(key: str) -> str:
            if is_base_var(key) and key.startswith("DBT_ENV_"):
                return f"DBT_{key[8:]}"
            return key

        section = "dbt.env_vars" if verb is None else f"dbt.{verb}.env_vars"
        options = self._read_ini_section(section)
        if options is None or len(options) == 0:
            return None

        env_vars = {}
        errors = []
        for key, value in options.items():
            key = key.upper()
            if not is_env_var(key):
                errors.append(key)
            elif should_rename:
                env_vars[rename(key)] = value
            else:
                env_vars[key] = value

        if len(errors) != 0:
            raise ExceptionGroup(
                f"{type(self).__name__}: Section `[{section}]`: Invalid environment variable names found.\n"
                "Environment variables should be in snake case or constant case and start "
                "with `DBT_`." + self._err_message_footer,
                [KeyError(option) for option in errors],
            )

        if len(env_vars) == 0:
            return None

        return env_vars

    def get_env_variables_apply_global(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        """
        Extracts the set of verbs for which the global environment variables
        are to be applied, from the `[dbt].apply_global_env_vars` option.
        "*" will be expanded to all available verbs.

        Args:
            available_verbs (Set[str]):
                Set of all available (supported) verbs, for validation

        Returns:
            Optional[Set[str]]:
                Set of verbs to apply the global internal flag values to, if any.
                Returns None if the option is not set.
        """
        return self._get_verbs_from_option("dbt", "apply_global_env_vars", available_verbs)

    def get_flag_allowlist(self, verb: Optional[str]) -> Optional[Dict[str, bool]]:
        """
        Extracts allowlist from `[dbt.flags.allowlist]` section for global flags,
        and `[dbt.{verb}.flags.allowlist]` for verb-specific flags.
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

        allowlist = {}
        for flag, value in section.items():
            try:
                allowlist[snake_case(flag)] = BoolParser.parse(value)
            except ValueError as exc:
                raise configparser.ParsingError(
                    f"{type(self).__name__}: Option `[{section_name}].{flag}`: Value "
                    "could not be coerced to a boolean value. \n"
                    f"Valid values: {BoolParser.valid_values()}." + self._err_message_footer
                ) from exc

        DbtFlagsSchema.validate_flag_availability(
            verb=verb,
            message=(f"Section `[{section_name}]`: Unrecognized flags" + self._err_message_footer),
            flag_message=lambda _, flag, is_not_recognized_str: (
                f"Option `[{section_name}].{flag}`: --{kebab_case(flag)}" + is_not_recognized_str
            ),
            flags=allowlist,
        )

        return allowlist

    def get_flag_allowlist_apply_global(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        """
        Extracts the set of verbs for which the configured global dbt allowlist
        will be merged to their respective verb allowlist, from the
        `[dbt].apply_global_allowlist` option.
        "*" will be expanded to all available verbs.

        Arguments:
            available_verbs (Set[str]): Set of all verbs supported by the
                                        microservice implementation

        Returns:
            Optional[Set[str]]:
                Set of verbs to apply the global allowlist to, if any.
                Returns None if the option is not set.
        """
        return self._get_verbs_from_option("dbt", "apply_global_allowlist", available_verbs)

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
        section_name = "dbt.flags.values" if verb is None else f"dbt.{verb}.flags.values"
        section = self._read_ini_section(section_name)
        if section is None or len(section) == 0:
            return None

        flags = {snake_case(flag): value for flag, value in section.items()}
        DbtFlagsSchema.validate_flag_availability(
            verb=verb,
            message=(
                f"{type(self).__name__}: Section `[{section_name}]`: "
                "Unrecognized flags" + self._err_message_footer
            ),
            flag_message=lambda _, flag, is_not_recognized_str: (
                f"Option `[{section_name}].{flag}`: --{kebab_case(flag)}" + is_not_recognized_str
            ),
            flags=flags,
        )

        return flags

    def get_flag_internal_values_apply_global(
        self, available_verbs: Set[str]
    ) -> Optional[Set[str]]:
        """
        Extracts the set of verbs for which the global internal flag values are
        to be applied, from the `[dbt].apply_global_internal_flag_values` option.
        "*" will be expanded to all available verbs.

        Args:
            available_verbs (Set[str]):
                Set of all available (supported) verbs, for validation

        Returns:
            Optional[Set[str]]:
                Set of verbs to apply the global internal flag values to, if any.
                Returns None if the option is not set.
        """
        return self._get_verbs_from_option(
            "dbt", "apply_global_internal_flag_values", available_verbs
        )

    def get_projects_root_dir(self) -> Optional[Path]:
        """
        Extracts directory where dbt projects are held from
        [dbt].projects_root_dir option.

        Raises:
            FileNotFoundError: If the path does not exist
            NotADirectoryError: If the path is not a valid directory

        Returns:
            Optional[Path]:
                Path to the projects root directory, if any.
                Returns None if not configured.
        """
        if self.config is None or not self.config.has_option("dbt", "projects_root_dir"):
            return None
        # prd: project root dir
        prd = Path(self.config.get("dbt", "projects_root_dir"))
        if not prd.exists():
            raise FileNotFoundError(
                f"{type(self).__name__}: Option `[dbt].projects_root_dir`: "
                f'File "{prd}" cannot be found.' + self._err_message_footer
            )
        if not prd.is_dir():
            raise NotADirectoryError(
                f"{type(self).__name__}: Option `[dbt].projects_root_dir`: "
                f'Path "{prd}" does not point to a directory.' + self._err_message_footer
            )

        return prd

    def get_variables(self, verb: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Extracts variables values from the `[dbt.vars]`
        section for global env vars, and the `[dbt.{verb}.vars]`
        section for verb-specific env vars.
        Assumes vars keys are in snake case, but formats to snake case for
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
        section_name = "dbt.vars" if verb is None else f"dbt.{verb}.vars"
        section = self._read_ini_section(section_name)
        if section is None or len(section) == 0:
            return None

        return {snake_case(key): value for key, value in section.items()}

    def get_variables_apply_global(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        """
        Extracts the set of verbs for which the global environment variables
        are to be applied, from the `[dbt].apply_global_vars` option.
        "*" will be expanded to all available verbs.

        Args:
            available_verbs (Set[str]):
                Set of all available (supported) verbs, for validation

        Returns:
            Optional[Set[str]]:
                Set of verbs to apply the globally set variables to, if any.
                Returns None if the option is not set.
        """
        return self._get_verbs_from_option("dbt", "apply_global_vars", available_verbs)

    def _get_verbs_from_option(
        self, section: str, option: str, available_verbs: Set[str]
    ) -> Optional[Set[str]]:
        """
        Extracts a set of comma-separated dbt verbs from a (section, option)
        in the ini file, and validates the result against available verbs.
        "*" will be expanded to all available verbs.

        Args:
            section (str): Name of the section in the ini file to load
            option (str): Name of the option to load from specified section
            available_verbs (Set[str]):
                Set of all available (supported) verbs, for validation

        Raises:
            ValueError: If value is not in the form `verb(,verb)+`
            ValueError: If verbs listed in the environment variable
                        are not in available_verbs

        Returns:
            Optional[Set[str]]:
                Set of verbs in (section, option), if set.
                Returns None if the option is not set.
        """
        if self.config is None or not self.config.has_option(section, option):
            return None

        # Verify that the value matches expected format
        value_str = self.config.get(section, option)
        if not re.match(r"^(([a-z][a-z\-]+|[*]),?)+$", value_str):
            raise ValueError(
                f'{type(self).__name__}: Option `[{section}].{option}` should be in the form "verb(,verb)+".'
                + self._err_message_footer
            )

        value = set(verb for verb in value_str.split(","))
        if "*" in value:
            value.remove("*")
            value = value | available_verbs

        # Verify that the verbs that have been set in env are supported
        if not value.issubset(available_verbs):
            unsupported_verbs: List[str] = sorted(value - available_verbs)
            raise ValueError(
                f"{type(self).__name__}: Option `[{section}].{option}`: Verbs {unsupported_verbs} "
                "are not supported." + self._err_message_footer
            )
        return value

    @property
    def _err_message_footer(self) -> str:
        if self.path is None:
            return ""
        return type(self)._get_err_message_footer(self.path)

    def _read_ini_section(self, name: str) -> Optional[Dict[str, Any]]:
        """Shorthand for reading a section from config file"""
        if self.config is None or not self.config.has_section(name):
            return None
        return dict(self.config[name])

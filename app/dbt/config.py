import configparser
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Set, Union

import jsonschema
import yaml
from convert_case import kebab_case, snake_case

__all__ = ["DbtFlagsConfig", "DbtConfig", "DbtConfigLoader"]

DIRPATH = Path(__file__).parent


def _read_ini_file() -> Union[configparser.ConfigParser, None]:
    if not os.getenv("DBT_CONFIG_FILE"):
        return None

    config_file = Path(os.getenv("DBT_CONFIG_FILE"))
    if not config_file.exists():
        raise FileNotFoundError(f"Config file '{config_file}' not found.")
    if not config_file.suffix == ".ini":
        raise ValueError(f"Config file '{config_file}' should be a .ini file")
    config = configparser.ConfigParser()
    config.read(os.getenv("DBT_CONFIG_FILE"), encoding="utf-8")
    return config


def _load_flags_schema(verb: Optional[str] = None) -> dict:
    """
    Loads the JSON schema for the flags for the given verb.
    If verb is None, returns the JSON schema of shared flags.
    DOES NOT RESOLVE/MERGE $ref DIRECTIVES.

    Args:
        verb (Optional[str], optional): dbt verb to get the flags for.
                                        If verb is None, returns the shared flags
                                        that are listed in the JSON schema.
                                        Defaults to None.

    Returns:
        dict: The JSON schema of the given verb.
    """
    filepath = (
        DIRPATH / f"flags_jsonschema/dbt-{verb}.yml"
        if verb is not None
        else DIRPATH / f"flags_jsonschema/shared.yml"
    )
    with open(filepath, "r", encoding="utf-8") as file:
        return yaml.load(file, Loader=yaml.Loader)


def _get_available_flags(verb: Optional[str] = None) -> Set[str]:
    """
    Returns the flags that are listed in the JSON schema for the given verb.
    If verb is None, returns the shared flags that are listed in the JSON schema.

    Args:
        verb (Optional[str], optional): dbt verb to get the flags for.
                                        If verb is None, returns the shared flags
                                        that are listed in the JSON schema.
                                        Defaults to None.
    Returns:
        Set[str]: The flags that are listed in the JSON schema for the given verb.
    """
    schema = _load_flags_schema(verb)
    return (
        set(schema["allOf"][1]["properties"].keys())
        if verb
        else set(schema["properties"].keys())
    )


@dataclass(frozen=True)
class DbtFlagsConfig:
    allowlists: Dict[str, Dict[str, bool]]  # Dict[verb, Dict[flag, enabled]]
    internal_values: Dict[str, Dict[str, str]]  # Dict[verb, Dict[flag, value]]
    schema: dict # json schema as dict

    @staticmethod
    def _load_allowlist(verb: str) -> Dict[str, bool]:
        """Load allowed flags for a specific verb."""
        allowlist = {}

        allowlist.update(DbtConfig._load_allowlist_from_defaults(verb))
        # ini overrides defaults
        allowlist.update(DbtConfig._load_allowlist_from_ini(verb))
        # env overrides ini and defaults
        allowlist.update(DbtConfig._load_allowlist_from_env(verb))
        return allowlist

    @staticmethod
    def _load_allowlist_from_defaults(verb: str) -> Dict[str, bool]:
        """Load default allowlist flags from YAML."""
        allowlist = {}
        allowlist_dir = DIRPATH / "flags_default_allowlists"
        shared_file = allowlist_dir / "shared.yml"
        verb_file = allowlist_dir / f"dbt-{verb}.yml"

        with open(shared_file, "r", encoding="utf-8") as f:
            allowlist.update(yaml.load(f, Loader=yaml.SafeLoader))
        with open(verb_file, "r", encoding="utf-8") as f:
            allowlist.update(yaml.load(f, Loader=yaml.SafeLoader))

        return allowlist

    @staticmethod
    def _load_allowlist_from_env(verb: str) -> Dict[str, bool]:
        """
        Loads allowlist overrides from DBT_{ENABLE|DISABLE}_{verb?}_FLAGS
        environment variables.

        Args:
            verb (str): One of the allowed dbt verb

        Returns:
            Dict[str, bool]: Allowlist from env for the given verb
        """

        def _parse_sub_allowlist(
            variable: str, verb: Optional[bool] = None
        ) -> Dict[str, bool]:
            sub_allowlist = {}
            value = os.getenv(variable)
            if value is None:
                return {}
            
            enable = "ENABLE" in variable
            # Verify that the value matches expected format
            if not re.match(r"^([a-z][a-z0-9\-]+,?)+$", value):
                raise ValueError(
                    f"ENV: {variable}: Invalid value; "
                    "Should be a comma-separated list of flags in kebab case."
                )
            sub_allowlist.update({flag: enable for flag in value.split(",")})

            available_flags = _get_available_flags(verb)
            # Check if there are any unrecognized/unsupported flags set
            if not set(sub_allowlist.keys()).issubset(available_flags):
                unsupported_flags = sorted(set(sub_allowlist.keys()) - available_flags)
                raise ExceptionGroup(
                    f"ENV: {variable}: Unrecognized flags",
                    [
                        ValueError(
                            f"ENV: {variable}: Flag --{flag.replace('_', '-')} "
                            "is not recognized as a valid "
                            f"{'global ' if verb is None else ''}dbt "
                            f"{verb + ' ' if verb else ''}flag."
                        )
                        for flag in unsupported_flags
                    ]
                )
            return sub_allowlist

        allowlist = {}
        allowlist.update(_parse_sub_allowlist("DBT_ENABLE_FLAGS", verb=None))
        allowlist.update(_parse_sub_allowlist("DBT_DISABLE_FLAGS", verb=None))
        if verb is not None:
            allowlist.update(_parse_sub_allowlist(
                f"DBT_{verb.upper()}_ENABLE_FLAGS", verb=verb
            ))
            allowlist.update(_parse_sub_allowlist(
                f"DBT_{verb.upper()}_DISABLE_FLAGS", verb=verb
            ))

        return allowlist

    @staticmethod
    def _load_allowlist_from_ini(verb: str) -> Dict[str, bool]:
        """
        Loads the allowlist for given verb from the configured ini configuration
        file.

        Args:
            verb (str): One of the allowed dbt verb

        Returns:
            Dict[str, bool]: Allowlist from ini for the given verb
        """
        allowlist = {}
        config = _read_ini_file()
        if config is None:
            return allowlist

        target_section = f"dbt.{verb + '.' if verb else ''}flags.allowlist"
        for section in config.sections():
            if section != target_section:
                continue
            allowlist.update(dict(config[section]))

        available_flags = _get_available_flags(verb)
        # Check if there are any unrecognized/unsupported flags set
        if not set(allowlist.keys()).issubset(available_flags):
            unsupported_flags = set(allowlist.keys()) - available_flags
            raise ExceptionGroup(
                f"INI: [{target_section}]: Unrecognized flags",
                [
                    ValueError(
                        f"INI: [{target_section}]: Option {flag} "
                        "is not recognized as a valid "
                        f"{'global ' if verb is None else ''}dbt "
                        f"{verb + ' ' if verb else ''}flag."
                    )
                    for flag in unsupported_flags
                ]
            )
        return allowlist

    @staticmethod
    def _load_internal_values(verb: Optional[str] = None) -> Dict[str, Any]:
        """
        Load internal flags values for the given verb from environment and
        configuration file.
        Parses internal flag values according to JSON schema specification

        Args:
            verb (Optional[str], optional): dbt verb to get the flags for.
                                            If verb=None, returns the internal values
                                            for shared flags.
                                            Defaults to None.

        Returns:
            Dict[str, Any]: Processed internal flag values after type casting and validation.
        """
        ini_flag_raw_values = DbtConfig._load_raw_internal_values_from_ini(verb)
        env_flag_raw_values = DbtConfig._load_raw_internal_values_from_env(verb)

        raw_internal_values = {**ini_flag_raw_values, **env_flag_raw_values}

        internal_values = {}
        errors = []
        schema = _load_flags_schema(verb)
        verb_schema = schema["allOf"][1]["properties"] if verb else schema["properties"]

        for flag, value in raw_internal_values.items():
            try:
                # Retrieve the expected type from the schema
                flag_schema = verb_schema.get(flag, {})
                expected_type = flag_schema.get("type")

                # Perform type casting based on the schema
                if expected_type == "boolean":
                    valid_bools = ("true", "yes", "1", "on", "false", "no", "0", "off")
                    if value.trim().lower() not in valid_bools:
                        raise ValueError(
                            f"Invalid value for flag {flag}: '{value}'. "
                            f"Expected one of {valid_bools}"
                        )
                    internal_values[flag] = value.lower() in ("true", "yes", "1", "on")
                elif expected_type == "integer":
                    internal_values[flag] = int(value)
                elif expected_type == "number":
                    internal_values[flag] = float(value)
                elif expected_type == "string":
                    internal_values[flag] = str(value)
                else:
                    internal_values[flag] = (
                        value  # Fallback to raw value if no type specified
                    )
            except ValueError as e:
                errors.append(e)
            except Exception as e:
                errors.append(
                    TypeError(
                        f"Failed to cast flag {flag} with value '{value}' to "
                        f"expected type '{expected_type}. {e}"
                    )
                )

        if errors:
            raise ExceptionGroup(
                "Casting errors occured while processing internal flag values", errors
            )

        try:
            jsonschema.validate(instance=internal_values, schema=schema)
        except jsonschema.ValidationError as e:
            raise ValueError(
                f"Validation error for flag '{e.path[0] if e.path else ''}': {e.message}"
            )

        return internal_values

    @staticmethod
    def _load_raw_internal_values_from_env(
        verb: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Loads internal flags values from environment variables starting with
        DBT_FLAG_* or DBT_{verb}_FLAG_*.
        Values returned are not parsed.

        Args:
            verb (Optional[str], optional): dbt verb to get the flags for.
                                            If verb=None, returns the internal values
                                            for shared flags.
                                            Defaults to None.

        Raises:
            ExceptionGroup[str, List[ValueError]]: For each flag which is not
                                                   recognized, raises a ValueError.

        Returns:
            Dict[str, str]: Dict[flag, value] for the given verb, from env.
        """
        flags = {}
        for name, value in os.environ.items():
            # DBT_FLAG_* are env vars specifying values for shared dbt flags, while
            # DBT_{verb}_FLAG_* are env vars specifying values for verb-specific
            # dbt flags
            prefix = "DBT_FLAG_" if verb is None else f"DBT_{verb.upper()}_FLAG_"
            if name.startswith(prefix):
                # Remove the prefix & convert to snake case for validation
                # against available_flags
                flag_name = snake_case(name[len(prefix) :])
                flags[flag_name] = value

        available_flags = _get_available_flags(verb)
        if not set(flags.keys()).issubset(available_flags):
            unsupported_flags = set(flags.keys()) - available_flags
            raise ExceptionGroup(
                "ENV: Some flags were not recognized as valid "
                + f"dbt {verb + ' ' if verb else ''}flags",
                [
                    ValueError(f"{prefix}{flag.upper()} ('--{kebab_case(flag)}')")
                    for flag in unsupported_flags
                ],
            )

        return flags

    @staticmethod
    def _load_raw_internal_values_from_ini(
        verb: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Load internal flag values from specified .ini file for given verb
        Flag values are stored in the `[dbt.flags.values]` section for shared flags,
        and the `[dbt.{verb}.flags.values]` section for verb-specific flags.
        Assumes flag keys are either in kebab case or snake case.
        If not the case, the flag key will not be found when matching against
        available flags.
        Values returned are not parsed.

        Args:
            verb (Optional[str], optional): dbt verb to get the flags for.
                                            If verb=None, returns the internal values
                                            for shared flags.
                                            Defaults to None.

        Raises:
            FileNotFoundError: If file specified by environment variable
                               "DBT_FLAGS_CONFIG_FILE" does not exist
            ValueError: If file specified by environment variable
                        "DBT_FLAGS_CONFIG_FILE" is not a .ini file
            ExceptionGroup[str, List[ValueError]]: For each flag which is not
                                                   recognized, raises a ValueError.

        Returns:
            Dict[str, str]: Dict[flag, value] for the given verb, from ini.
        """
        config = _read_ini_file()
        if config is None:
            return {}

        section_name = (
            "dbt.flags.values" if verb is None else f"dbt.{verb}.flags.values"
        )

        flags = {}
        if config.has_section(section_name):
            flags.update(dict(config[section_name]))

        available_flags = _get_available_flags()
        if not set(snake_case(flag) for flag in flags.keys()).issubset(available_flags):
            unsupported_flags = flags - available_flags
            raise ExceptionGroup(
                "INI: [{section_name}]: Some flags were not recognized as valid "
                + f"dbt {verb + ' ' if verb else ''}flags",
                [
                    ValueError(f"[{section_name}].{flag} ('--{kebab_case(flag)}')")
                    for flag in unsupported_flags
                ],
            )

        return {snake_case(flag): value for flag, value in flags.items()}

    @staticmethod
    def _load_schema(verb: Optional[str] = None) -> dict:
        """
        Load the JSON schema for the given verb or shared flags.

        Args:
            verb (Optional[str], optional): dbt verb to load schema for. If None,
                                            loads the schema for shared flags.
                                            Defaults to None.

        Returns:
            dict: The JSON schema object for the given verb or shared flags.
        """
        if verb is None:
            filepath = DIRPATH / "flags_jsonschema/shared.yml"
        else:
            filepath = DIRPATH / f"flags_jsonschema/dbt-{verb}.yml"

        with open(filepath, "r", encoding="utf-8") as file:
            schema = yaml.load(file, Loader=yaml.SafeLoader)

        if verb:
            # Load shared schema for resolving $ref in the verb-specific schema
            shared_schema_path = DIRPATH / "flags_jsonschema/shared.yml"
            with open(shared_schema_path, "r", encoding="utf-8") as shared_file:
                shared_schema = yaml.load(shared_file, Loader=yaml.SafeLoader)

            # Merge the shared schema into the verb-specific schema
            if "allOf" in schema:
                for idx, condition in enumerate(schema["allOf"]):
                    if condition.get("$ref") == "dbt-shared-schema":
                        schema["allOf"][idx] = shared_schema

        return schema

    @classmethod
    def load(cls, allowed_verbs: Set[str]):
        """
        Creates a DbtFlagsConfig instance:
          - Loads flag allowlists for each verb and shared
          - Loads internal flag values for each verb and shared
          - Loads JSON schema for each verb and shared

        allowlist and internal values for shared flags are the same across all verbs.
        Should the need for different shared flags allowlists/internal values across
        different verbs arise, the implementation can be modified to suit this use-case.

        Args:
            allowed_verbs (Set[str]): Set of dbt verbs that are supported & allowed.

        Returns:
            DbtFlagsConfig: DbtFlagsConfig instance.
        """
        allowlists = {}
        allowlists["shared"] = cls._load_allowlist()
        allowlists.update(
            {
                verb: {**allowlists["shared"], **cls._load_allowlist(verb)}
                for verb in allowed_verbs
            }
        )

        internal_values = {}
        internal_values["shared"] = cls._load_internal_values()
        internal_values.update(
            {
                verb: {**internal_values["shared"], **cls._load_internal_values(verb)}
                for verb in allowed_verbs
            }
        )

        schema = {}
        schema["shared"] = cls._load_schema()
        schema.update({verb: cls._load_schema(verb) for verb in allowed_verbs})

        return cls(
            allowlists=allowlists, internal_values=internal_values, schema=schema
        )


@dataclass(frozen=True)
class DbtConfig:
    allowed_verbs: Set[str]
    env: Dict[str, str]
    flags: DbtFlagsConfig
    projects_root_dir: Path

    @staticmethod
    def _load_allowed_verbs() -> Set[str]:
        """
        Loads allowed dbt verbs

        Returns:
            Set[str]: Set of the allowed dbt verbs, as per user configuration or defaults.
        """
        available_verbs = DbtConfig._load_available_verbs()
        env_verbs = DbtConfig._load_allowed_verbs_from_env(available_verbs)
        ini_verbs = DbtConfig._load_allowed_verbs_from_ini(available_verbs)
        return env_verbs or ini_verbs or available_verbs

    @staticmethod
    def _load_allowed_verbs_from_env(
        available_verbs: Set[str],
    ) -> Union[None, Set[str]]:
        if not os.getenv("DBT_ALLOWED_VERBS"):
            return None

        # Verify that the value matches expected format
        if not re.match(r"[a-z,\-]+", os.getenv("DBT_ALLOWED_VERBS")):
            raise ValueError(
                "ENV: DBT_ALLOWED_VERBS: Invalid value. Should be in the form 'verb1,verb2,'."
            )

        env_verbs = set(verb for verb in os.getenv("DBT_ALLOWED_VERBS").split(","))
        # Verify that the verbs that have been set in env are supported
        if not env_verbs.issubset(available_verbs):
            unsupported_verbs = env_verbs - available_verbs
            raise ValueError(
                f"ENV: DBT_ALLOWED_VERBS: Verbs {list(unsupported_verbs)} are not supported"
            )
        return env_verbs

    @staticmethod
    def _load_allowed_verbs_from_ini(
        available_verbs: Set[str],
    ) -> Union[None, Set[str]]:
        config = _read_ini_file()
        if not config.has_option("dbt", "allowed_verbs"):
            return None

        # Verify that the value matches expected format
        if not re.match(r"[a-z,\-]+", config.get("dbt", "allowed_verbs")):
            raise ValueError(
                "INI: [dbt].allowed_verbs: Invalid value. Should be in the form 'verb1,verb2,'."
            )

        ini_verbs = set(verb for verb in config.get("dbt", "allowed_verbs").split(","))
        # Verify that the verbs that have been set in env are supported
        if not ini_verbs.issubset(available_verbs):
            unsupported_verbs = ini_verbs - available_verbs
            raise ValueError(
                f"INI: [dbt].allowed_verbs: Verbs {list(unsupported_verbs)} are not supported"
            )
        return ini_verbs

    @staticmethod
    def _load_available_verbs() -> Set[str]:
        verbs = None
        for dirname in ("flags_jsonschema", "flags_default_allowlists"):
            verbs_local = set(
                child.stem[4:] for child in (DIRPATH / dirname).glob("dbt-*.yml")
            )
            # intersect the available verbs across all the configuration directories
            verbs = verbs_local if verbs is None else verbs & verbs_local
        return verbs

    @staticmethod
    def _load_projects_root_dir() -> Path:
        """Determine the dbt projects root directory."""
        default_path = Path(__file__).parent.parent.parent / "dbt_projects"
        return Path(os.getenv("DBT_PROJECT_ROOT", default_path))


    @staticmethod
    def _load_env() -> Dict[str, str]:
        """Extracts all env vars that start with DBT_ENV_.

        Returns:
            Dict[str, str]: Mapping of environment variables with prefix"DBT_ENV_"
        """
        return {
            key: value
            for key, value in os.environ.items()
            if key.startswith("DBT_ENV_")
        }


    @classmethod
    def load(cls) -> "DbtConfig":
        """Load and validate the entire configuration."""
        # Load allowed verbs
        allowed_verbs = cls._load_allowed_verbs()

        # Load dbt projects root directory
        projects_root_dir = cls._load_projects_root_dir()

        flags = DbtFlagsConfig.load(allowed_verbs)

        env = cls._load_env()

        # Return the configuration instance
        return cls(
            allowed_verbs=allowed_verbs,
            env=env,
            flags=flags,
            projects_root_dir=projects_root_dir,
        )


class DbtConfigLoader:
    _instance: DbtConfig = None

    @classmethod
    def get_config(cls) -> DbtConfig:
        """Get the singleton configuration instance."""
        if cls._instance is None:
            cls._instance = DbtConfig.load()
        return cls._instance

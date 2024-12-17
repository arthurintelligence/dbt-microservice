import copy
from pathlib import Path
from typing import Any, Dict, Optional, Protocol, Set, Union

import yaml
from cerberus import Validator
from convert_case import snake_case

DIRPATH = Path(__file__).parent

__all__ = ["DbtFlagsSchema", "FlagMessageCallable"]


class FlagMessageCallable(Protocol):
    def __call__(self, verb: Optional[str], flag_name: str, is_not_recognized_str: str) -> str:
        pass


class DbtFlagsSchema(Validator):

    @staticmethod
    def get_available_flags(verb: Optional[str]) -> Set[str]:
        """
        Returns the flags that are listed in the JSON schema for the given verb.
        If verb is None, returns the global flags that are listed in the JSON schema.

        Args:
            verb (Optional[str]):
                dbt verb to get the flags for.
                Use verb=None for global flags, verb={value} verb-specific flags.
        Returns:
            Set[str]: The flags that are listed in the JSON schema for the given verb.
        """
        return set(DbtFlagsSchema.read_schema(verb)["properties"].keys())

    @staticmethod
    def read_schema(verb: Optional[str], merge_global: Optional[bool] = False):
        """
        Load the JSON schema for the given verb or global flags.

        Args:
            verb (Optional[str]):
                dbt verb to get the flags for.
                Use verb=None for global flags, verb={value} verb-specific flags.
            merge_global (Optional[bool], optional):
                Whether or not to merge the global schema when verb is not None.
                Defaults to False.

        Returns:
            dict: The JSON schema object for the given verb or global flags.
        """
        global_schema = None
        read_global_schema = verb is None or merge_global
        if read_global_schema:
            with open(DIRPATH / "global.yml", "r", encoding="utf-8") as file:
                global_schema = yaml.load(file, Loader=yaml.SafeLoader)

        # if verb is none, means we are looking for global flags
        if verb is None:
            return global_schema

        # else verb is not none, means we are looking for verb flags
        verb_schema = None
        with open(DIRPATH / "global.yml", "r", encoding="utf-8") as file:
            verb_schema = yaml.load(file, Loader=yaml.SafeLoader)
            # Extract properties from verb_schema:
            # - allOf[0] is expected to be $ref to dbt-global-schema
            # - allOf[1] is the verb-specific schema
            verb_schema["properties"] = verb_schema["allOf"][1]["properties"]
            del verb_schema["allOf"]

        # if not merge global, we can return the verb flags directly
        if not merge_global:
            return verb_schema

        # else we merge with the global flags
        merged_schema = copy.deepcopy(verb_schema)  # make copy
        merged_schema["properties"] = {
            **copy.deepcopy(global_schema["properties"]),
            **merged_schema["properties"],
        }
        return merged_schema


    @staticmethod
    def validate_flag_availability(
        verb: Optional[str],
        message: str,
        flag_message: FlagMessageCallable,
        flags: Dict[str, Any]
    ) -> None:
        """
        Validates a given set of flags against the available flags listed in JSON schema.
        Provides variables to configure the error output.

        Args:
            verb (Optional[str]):
                dbt verb to verify flag availability against
                Use verb=None for global flags, verb={value} verb-specific flags.
            message (str):
                Print prefix to contextualize where the error comes from.
            flag_message (FlagMessageCallable):
                Custom flag printer function which receives verb, flag_name, is_not_recognized_str
            flag (Dict[str, Any]):
                Collection of flags to validate availability for.

        Raises:
            ExceptionGroup:
                Raises an ExceptionGroup[KeyError] if one or more flags
                are not recognized as valid global dbt / dbt verb flags.

        Returns:
            None: If all flags are available does not return anything.
        """
        available_flags = DbtFlagsSchema.get_available_flags(verb)
        # Check if there are any unrecognized/unsupported flags set
        if not set(snake_case(flag) for flag in flags.keys()).issubset(available_flags):
            unsupported_flags = set(flags.keys()) - available_flags
            raise ExceptionGroup(
                message,
                [
                    KeyError(
                        flag_message(
                            verb,
                            flag,
                            " is not recognized as a valid "
                            + f"{'global ' if verb is None else ''}dbt "
                            + f"{verb + ' ' if verb else ''}flag."
                        )
                    )
                    for flag in unsupported_flags
                ]
            )

    @classmethod
    def create_instance(verb: Optional[str], merge_global: Optional[bool] = False) -> "DbtFlagsSchema":
        schema = DbtFlagsSchema.read_schema(verb, merge_global)
        return cls(schema)

    def _normalize_coerce_boolean(self, value: Union[str, int]):
        truthies = ("true", "yes", "1", "on")
        falsies = ("false", "no", "0", "off")
        valid_values = truthies + falsies

        str_value = str(value).strip().lower()
        if str_value not in valid_values:
            raise ValueError(value)
        return str_value in truthies

    def _normalize_coerce_directory(self, value: str):
        path = Path(value)
        if not path.is_dir():
            raise NotADirectoryError(str(path))
        return path

    def _normalize_coerce_file(self, value: str):
        path = Path(value)
        if not path.is_file():
            raise IsADirectoryError(str(path))
        return path

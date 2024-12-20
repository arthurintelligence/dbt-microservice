from pathlib import Path
from typing import Any, Dict, Optional, Set

import yaml

from app.dbt.config.providers.abc import BaseConfigProvider

__all__ = ["DefaultsConfigProvider"]

ALLOWLIST_DIRPATH = (Path(__file__).parent / "flag_allowlists").resolve()
JSONSCHEMA_DIRPATH = (Path(__file__).parent / "../../jsonschema").resolve()


class DefaultsConfigProvider(BaseConfigProvider):
    @staticmethod
    def available_verbs() -> Set[str]:
        """Returns default allowed verbs - which are all the available verbs"""
        all_available_verbs: Set[str] = set()
        for dirname in (ALLOWLIST_DIRPATH, JSONSCHEMA_DIRPATH):
            dir_available_verbs = set(child.stem[4:] for child in dirname.glob("dbt-*.yml"))
            if len(all_available_verbs) == 0:
                all_available_verbs = dir_available_verbs
            # intersect the available verbs across all the configuration
            # directories
            all_available_verbs &= dir_available_verbs

        return all_available_verbs

    def get_allowed_verbs(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        """Returns default allowed verbs - which are all the available verbs"""
        return DefaultsConfigProvider.available_verbs()

    def get_env_variables(self, verb: Optional[str]) -> Optional[Dict[str, Any]]:
        """Returns default env variables passed to dbt for given verb - which is none"""
        return None

    def get_env_variables_apply_global(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        """
        Returns verbs for which global environemnt variables will be applied.
        Provides an easy config point for applying global settings across multiple verbs.

        Args:
            available_verbs (Set[str]): Set of all available (supported) verbs

        Returns:
            Optional[Set[str]]: All available verbs by default
        """
        return available_verbs

    def get_flag_allowlist(self, verb: Optional[str]) -> Optional[Dict[str, bool]]:
        """Returns default flag allowlist for given verb."""
        filepath = ALLOWLIST_DIRPATH / ("global.yml" if verb is None else f"dbt-{verb}.yml")
        print(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            return yaml.load(f, Loader=yaml.SafeLoader)  # type: ignore

    def get_flag_allowlist_apply_global(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        """
        Returns verbs for which the global allowlist will be available as part of the
        API endpoint query params.
        Provides an easy config point for applying global settings across multiple verbs.

        Args:
            available_verbs (Set[str]): Set of all available (supported) verbs

        Returns:
            Optional[Set[str]]: All available verbs by default
        """
        return available_verbs

    def get_flag_internal_values(self, verb: Optional[str]) -> Optional[Dict[str, Any]]:
        """Returns default flag internal values for given verb - which is none"""
        return None

    def get_flag_internal_values_apply_global(
        self, available_verbs: Set[str]
    ) -> Optional[Set[str]]:
        """
        Returns verbs for which global internal flag values will be applied when
        calling the API endpoint.
        Provides an easy config point for applying global settings across multiple verbs.

        Args:
            available_verbs (Set[str]): Set of all available (supported) verbs

        Returns:
            Optional[Set[str]]: All available verbs by default
        """
        return available_verbs

    def get_projects_root_dir(self) -> Optional[Path]:
        return None

    def get_variables(self, verb: Optional[str]) -> Optional[Dict[str, Any]]:
        """Returns default variables passed to dbt for given verb - which is none"""
        return None

    def get_variables_apply_global(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        return available_verbs

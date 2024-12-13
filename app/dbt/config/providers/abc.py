import abc
from pathlib import Path
from typing import Any, Dict, Optional, Set


__all__ = ["BaseConfigProvider"]

@abc.abc
class BaseConfigProvider:
    @property
    @classmethod
    def name(cls) -> str:
        return "dbt-microservice/" + cls.__module__

    @abc.abstractmethod
    def get_allowed_verbs(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        pass

    @abc.abstractmethod
    def get_flag_allowlist(self, verb: Optional[str]) -> Optional[Dict[str, bool]]:
        pass

    @abc.abstractmethod
    def get_flag_internal_values(self, verb: Optional[str]) -> Optional[Dict[str, Any]]:
        pass

    @abc.abstractmethod
    def get_env_variables(self, verb: Optional[str]) -> Optional[Dict[str, str]]:
        pass

    @abc.abstractmethod
    def get_projects_root_dir(self) -> Optional[Path]:
        pass

    @abc.abstractmethod
    def get_variables(self, verb: Optional[str]) -> Optional[Dict[str, Any]]:
        pass

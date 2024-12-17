from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Set

from app.dbt.config.providers import BaseConfigProvider, DefaultsConfigProvider, get_providers
from app.dbt.flags_jsonschema.validator import DbtFlagsSchema
from app.dbt.config.errors import ValidationError

__all__ = ["DbtConfig", "DbtConfigLoader"]

# TODO:
# - Add logs for overrides from verb over global for env, variables
# - Update test_environment tests for unsupported verbs to use the whole
#   list of unsupported dbt verbs

@dataclass(frozen=True)
class DbtConfig:
    allowed_verbs: Set[str]  # Set[verb]
    env_variables: Dict[str, Dict[str, str]]  # Dict[env_var, value]
    env_variables_apply_global: Set[str]  # Set[verb]
    flag_allowlists: Dict[str, Dict[str, bool]]  # Dict[verb, Dict[flag, enabled]]
    flag_allowlists_apply_global: Set[str]  # Set[verb]
    flag_internal_values: Dict[str, Dict[str, str]]  # Dict[verb, Dict[flag, value]]
    flag_internal_values_apply_global: Set[str]  # Set[verb]
    projects_root_dir: Path
    variables: Dict[str, str]  # Dict[var_name, value]
    variables_apply_global: Set[str]  # Set[verb]

    @classmethod
    def create_instance(cls, providers: List[BaseConfigProvider] = None):
        if providers is None:
            providers = get_providers()
        else:
            # ensure DefaultsConfigProvider is always included
            if not any(isinstance(p, DefaultsConfigProvider) for p in providers):
                providers = [DefaultsConfigProvider(), *providers]

        attrs = cls._load(providers)
        attrs = cls._validate(attrs)
        return cls(**attrs)


    @classmethod
    def _load(cls, providers: List[BaseConfigProvider]) -> Dict[str, Any]:
        # assumes providers[0] isinstance DefaultsConfigProvider
        defaults_provider = providers[0]
        available_verbs = defaults_provider.available_verbs()

        attrs = {}
        for attr, (scope, method_name, kwargs) in [
            ("allowed_verbs", ("global", "get_allowed_verbs", {"available_verbs": available_verbs})),
            ("flag_allowlists", ("verb", "get_flag_allowlist", {})),
            ("flag_allowlists_apply_global", ("verb", "get_flag_allowlist_apply_global", {"available_verbs": available_verbs})),
            ("env_variables", ("verb", "get_env_variables", {})),
            ("env_variables_apply_global", ("global", "get_env_variables_apply_global", {"available_verbs": available_verbs})),
            ("flag_internal_values", ("verb", "get_flag_internal_values", {})),
            ("flag_internal_values_apply_global", ("global", "get_flag_internal_values_apply_global", {"available_verbs": available_verbs})),
            ("projects_root_dir", ("global", "get_projects_root_dir", {})),
            ("variables", ("verb", "get_variables", {})),
            ("variables_apply_global", ("global", "get_variables_apply_global", {"available_verbs": available_verbs})),
        ]:
            if scope == "verb":
                for verb in [None, *available_verbs]:
                    key = verb or "global"
                    attrs[attr][key] = cls._load_attribute(
                        providers,
                        method_name,
                        verb=verb,
                        **kwargs
                    )
            elif scope == "global":
                attrs[attr] = cls._load_attribute(
                    providers,
                    method_name,
                    **kwargs
                )

        return attrs

    @classmethod
    def _load_attribute(
        cls,
        providers: List[BaseConfigProvider],
        method_name: str,
        **kwargs
    ):
        value = {}
        for provider in providers:
            # execute method with kwargs if any kwargs passed
            if len(kwargs):
                provider_value = getattr(provider, method_name)(**kwargs)
            else:
                provider_value = getattr(provider, method_name)()
            # override value using subsequent provider value
            if provider_value is not None:
                value.update(provider_value)
        return value

    @classmethod
    def _validate(cls, providers: List[BaseConfigProvider], attrs: Dict[str, Any]) -> Dict[str, Any]:
        # projects_root_dir
        if attrs.get("projects_root_dir") is None:
            error = ValidationError("projects_root_dir must be defined")
            error.path = "$.projects_root_dir"

        # flag_internal_values
        # validation and type coercion using JSON schema
        for verb in [None, *attrs["allowed_verbs"]]:
            schema = DbtFlagsSchema.create_instance(verb, merge_global=True)
            if not schema.validate(attrs["flag_internal_values"]):
                error = ExceptionGroup(
                    "ValidationError: Errors were raised during validation or coercion "
                    f"of internal {'global ' if not verb else ''}dbt "
                    f"{verb + ' ' if verb else ''}flag values",
                    schema.errors
                )
                error.path = f"$.flag_internal_values.{verb}"

            key = "global" if verb is None else verb
            attrs["internal_flag_values"][key] = schema.document
        return attrs


class DbtConfigLoader:
    _instance: DbtConfig = None

    @classmethod
    def get_config(cls) -> DbtConfig:
        """Get the singleton configuration instance."""
        if cls._instance is None:
            cls._instance = DbtConfig.create_instance()
        return cls._instance


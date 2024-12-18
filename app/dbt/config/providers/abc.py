import abc
from pathlib import Path
from typing import Any, Dict, Optional, Set


__all__ = ["BaseConfigProvider"]


class BaseConfigProvider(abc.ABC):
    @abc.abstractmethod
    def get_allowed_verbs(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        """
        From provider source data, obtains the set of dbt verbs which can be
        called via the API endpoints.

        Arguments:
            available_verbs (Set[str]): Set of all verbs supported by the
                                        microservice implementation

        Raises:
            ValueError: If verbs configured in config point are not in
                        available_verbs

        Returns:
            Optional[Set[str]]:
                Set of allowed verbs.
                Returns None if config point is not configured in provider
                source data.
        """
        pass

    @abc.abstractmethod
    def get_env_variables(self, verb: Optional[str]) -> Optional[Dict[str, str]]:
        """
        From provider source data, obtains environment variables to be applied
        when calling dbt {verb} / to be applied globally (when verb is None). 

        Args:
            verb (Optional[str], optional):
                dbt verb to get the flag environment variables for.
                If verb=None, returns the global flag environment variables.


        Returns:
            Dict[str, str]:
                Mapping of dbt variables with prefix "DBT_ENV_*".
                Returns None if config point is not configured in provider
                source data.

        References:
            - [Environment Variables | dbt Developer Hub](https://docs.getdbt.com/docs/build/environment-variables)
        """
        pass

    @abc.abstractmethod
    def get_env_variables_apply_global(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        """
        From provider source data, obtains the set of verbs for which the
        configured global environment variables will be applied.

        Args:
            available_verbs (Set[str]):
                Set of all available (supported) verbs, primarily for validation

        Returns:
            Optional[Set[str]]:
                Set of verbs which will be configured.
                Returns None if config point is not configured in provider
                source data.
        """
        pass

    @abc.abstractmethod
    def get_flag_allowlist(self, verb: Optional[str]) -> Optional[Dict[str, bool]]:
        """
        From provider source data, obtains which flags can be passed to the API
        endpoint for a given {verb} / globally (when the verb is None).

        Args:
            verb (Optional[str], optional):
                dbt verb to get the flag allowlist for.
                If verb=None, returns the global flag allowlist.

        Raises:
            ExceptionGroup[str, List[ValueError]]:
                For each flag which is not recognized, raises a ValueError.
                May be delegated to app.dbt.config.jsonschema.DbtFlagsSchema.validate_flag_availability

        Returns:
            Optional[Dict[str, str]]:
                Dict[flag, bool] for verb flags / global flags.
                Returns None if config point is not configured in provider
                source data.
        """
        pass

    @abc.abstractmethod
    def get_flag_allowlist_apply_global(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        """
        From provider source data, obtains the set of verbs for which the
        configured global dbt allowlist will be merged to their respective verb
        allowlist.

        Args:
            available_verbs (Set[str]):
                Set of all available (supported) verbs, primarily for validation
        
        Raises:
            ValueError: If verbs listed in the provider source data
                        are not in available_verbs

        Returns:
            Optional[Set[str]]:
                Set of verbs which will be configured.
                Returns None if config point is not configured in provider
                source data.
        """
        pass

    @abc.abstractmethod
    def get_flag_internal_values(self, verb: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        From provider source data, obtains internal flags values to be applied
        when calling dbt {verb} / to be applied globally (when verb is None).
        Values returned should not be parsed in this class or its child classes.

        Args:
            verb (Optional[str], optional):
                dbt verb to get the flag allowlist for.
                If verb=None, returns the global flag allowlist.

        Raises:
            ExceptionGroup[str, List[ValueError]]:
                For each flag which is not recognized, raises a ValueError.

        Returns:
            Optional[Dict[str, str]]:
                Dict[flag, value] for verb flags / global flags.
                Returns None if config point is not configured in provider
                source data.
        """
        pass

    @abc.abstractmethod
    def get_flag_internal_values_apply_global(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        """
        From provider source data, obtains the set of verbs for which the
        global internal flag values are to be applied.

        Args:
            available_verbs (Set[str]):
                Set of all available (supported) verbs, primarily for validation

        Returns:
            Optional[Set[str]]:
                Set of verbs which will be configured.
                Returns None if config point is not configured in provider
                source data.
        """
        pass

    @abc.abstractmethod
    def get_projects_root_dir(self) -> Optional[Path]:
        """
        From provider source data, obtains the directory where dbt projects are 
        stored.

        Raises:
            FileNotFoundError: If the path does not exist
            NotADirectoryError: If the path is not a valid directory

        Returns:
            Optional[Set[str]]: 
                Path to the projects root directory, if any.
                Returns None if config point is not configured in provider
                source data.
        """
        pass

    @abc.abstractmethod
    def get_variables(self, verb: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        From provider source data, obtains the dbt verb / global variables
        to be applied when calling a given verb via the API endpoint.
        Said variables may be overriden via the API endpoint.
        Assumes variable keys are in snake case.

        Args:
            verb (Optional[str], optional):
                dbt verb to get the flags for.
                If verb=None, returns the internal values for global flags.

        Returns:
            Dict[str, str]:
                Dict[variable, value] for the given verb, from ini.
                Values returned are not parsed.
        """
        pass

    @abc.abstractmethod
    def get_variables_apply_global(self, available_verbs: Set[str]) -> Optional[Set[str]]:
        """
        From provider source data, obtains the set of verbs for which the 
        configured global dbt variables values will be applied.

        Args:
            available_verbs (Set[str]):
                Set of all available (supported) verbs, primarily for validation

        Returns:
            Optional[Set[str]]:
                Set of verbs which will be configured.
                Returns None if config point is not configured in provider
                source data.
        """
        pass

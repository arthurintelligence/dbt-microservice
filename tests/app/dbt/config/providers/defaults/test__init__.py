# pylint: disable=unused-variable,assignment-from-none,invalid-name
# mypy: disable-error-code="no-untyped-def"
from pathlib import Path
from typing import Optional

import pytest
import yaml

from app.dbt.config.providers.defaults import DefaultsConfigProvider

ROOT_DIRPATH = (Path(__file__).parent / "../../../../../../").resolve()


def describe_DefaultsConfigProvider():
    """Tests for DefaultsConfigProvider class methods"""

    def describe_available_verbs():
        """Tests for DefaultsConfigProvider.available_verbs"""

        def test_returns_all_available_verbs():
            """should return intersection of available verbs across configuration directories"""
            # arrange
            provider = DefaultsConfigProvider()
            expected_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.available_verbs()

            # assert
            assert result == expected_verbs

    def describe_get_allowed_verbs():
        """Tests for DefaultsConfigProvider.get_allowed_verbs"""

        def test_returns_available_verbs():
            """should return all available verbs as default"""
            # arrange
            provider = DefaultsConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_allowed_verbs(available_verbs)

            # assert
            assert result == available_verbs

    def describe_get_flag_allowlist():
        """Tests for DefaultsConfigProvider.get_flag_allowlist"""

        def test_global_allowlist():
            """should return content of default global flag allowlist file"""
            # arrange
            provider = DefaultsConfigProvider()

            # act
            result = provider.get_flag_allowlist(verb=None)

            # assert
            allowlist_relpath = "app/dbt/config/providers/defaults/flag_allowlists/global.yml"
            with open(ROOT_DIRPATH / allowlist_relpath, "r", encoding="utf-8") as f:
                expected_content = yaml.load(f, Loader=yaml.SafeLoader)

            assert result == expected_content

        @pytest.mark.parametrize("verb", ["run", "seed", "snapshot", "test"])
        def test_verb_allowlist(verb: str):
            """should return content of default {verb} flag allowlist file"""
            # arrange
            provider = DefaultsConfigProvider()

            # act
            result = provider.get_flag_allowlist(verb)

            # assert
            allowlist_relpath = f"app/dbt/config/providers/defaults/flag_allowlists/dbt-{verb}.yml"
            with open(ROOT_DIRPATH / allowlist_relpath, "r", encoding="utf-8") as f:
                expected_content = yaml.load(f, Loader=yaml.SafeLoader)

            assert result == expected_content

    def describe_get_flag_allowlist_apply_global():
        """Tests for DefaultsConfigProvider.get_flag_allowlist_apply_global"""

        def test_returns_available_verbs():
            """should return all available verbs as default"""
            # arrange
            provider = DefaultsConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_flag_allowlist_apply_global(available_verbs)

            # assert
            assert result == available_verbs

    def describe_get_flag_internal_values():
        """Tests for DefaultsConfigProvider.get_flag_internal_values"""

        @pytest.mark.parametrize("verb", [None, "run", "seed", "snapshot", "test"])
        def test_returns_none(verb: Optional[str]):
            """should return None as there are no default internal flag values"""
            # arrange
            provider = DefaultsConfigProvider()

            # act
            result = provider.get_flag_internal_values(verb)

            # assert
            assert result is None

    def describe_get_flag_internal_values_apply_global():
        """Tests for DefaultsConfigProvider.get_flag_internal_values_apply_global"""

        def test_returns_available_verbs():
            """should return all available verbs as default"""
            # arrange
            provider = DefaultsConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_flag_internal_values_apply_global(available_verbs)

            # assert
            assert result == available_verbs

    def describe_get_env_variables():
        """Tests for DefaultsConfigProvider.get_env_variables"""

        @pytest.mark.parametrize("verb", [None, "run", "seed", "snapshot", "test"])
        def test_returns_none(verb: Optional[str]):
            """should return None as there are no default environment variables"""
            # arrange
            provider = DefaultsConfigProvider()

            # act
            result = provider.get_env_variables(verb)

            # assert
            assert result is None

    def describe_get_env_variables_apply_global():
        """Tests for DefaultsConfigProvider.get_env_variables_apply_global"""

        def test_returns_all_available_verbs():
            """should return all available verbs as default"""
            # arrange
            provider = DefaultsConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_env_variables_apply_global(available_verbs)

            # assert
            assert result == available_verbs

    def describe_get_projects_root_dir():
        """Tests for DefaultsConfigProvider.get_projects_root_dir"""

        def test_returns_none():
            """should return None as there is no default projects root directory"""
            # arrange
            provider = DefaultsConfigProvider()

            # act
            result = provider.get_projects_root_dir()

            # assert
            assert result is None

    def describe_get_variables():
        """Tests for DefaultsConfigProvider.get_variables"""

        @pytest.mark.parametrize("verb", [None, "run", "seed", "snapshot", "test"])
        def test_returns_none(verb: Optional[str]):
            """should return None as there is no default variables"""
            # arrange
            provider = DefaultsConfigProvider()

            # act
            result = provider.get_variables(verb)

            # assert
            assert result is None

    def describe_get_variables_apply_global():
        """Tests for DefaultsConfigProvider.get_variables_apply_global"""

        def test_returns_available_verbs():
            """should return all available verbs as default"""
            # arrange
            provider = DefaultsConfigProvider()
            available_verbs = {"run", "seed", "snapshot", "test"}

            # act
            result = provider.get_variables_apply_global(available_verbs)

            # assert
            assert result == available_verbs

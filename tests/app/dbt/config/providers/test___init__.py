import pytest

from app.dbt.config.providers import (
    DefaultsConfigProvider,
    EnvironmentConfigProvider,
    FileConfigProvider,
    get_providers
)

def describe_get_providers():
    """Tests for get_provider() function"""

    def test_returns_expected_providers():
        """
        should return DefaultsConfigProvider, FileConfigProvider, \
        EnvironmentConfigProvider, in that specific order.
        """
        # no arrange

        # act
        providers = get_providers()

        # assert
        assert len(providers) == 3
        assert isinstance(providers[0], DefaultsConfigProvider)
        assert isinstance(providers[1], FileConfigProvider)
        assert isinstance(providers[2], EnvironmentConfigProvider)

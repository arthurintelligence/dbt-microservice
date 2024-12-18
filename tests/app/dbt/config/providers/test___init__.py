import pytest

from app.dbt.config.providers import (
    DefaultsConfigProvider,
    EnvironmentConfigProvider,
    IniFileConfigProvider,
    get_providers
)

def describe_get_providers():
    """Tests for get_provider() function"""

    def test_returns_expected_providers():
        """
        should return DefaultsConfigProvider, IniFileConfigProvider, \
        EnvironmentConfigProvider, in that specific order.
        """
        # no arrange

        # act
        providers = get_providers()

        # assert
        assert len(providers) == 3
        assert isinstance(providers[0], DefaultsConfigProvider)
        assert isinstance(providers[1], IniFileConfigProvider)
        assert isinstance(providers[2], EnvironmentConfigProvider)

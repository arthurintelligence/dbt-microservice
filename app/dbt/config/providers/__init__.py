"""
Exports BaseConfigProvider subclasses and a function to get the default
providers in the expected order.
"""

from typing import List

from .abc import BaseConfigProvider
from .defaults import DefaultsConfigProvider
from .environment import EnvironmentConfigProvider
from .file import FileConfigProvider

__all__ = [
    "BaseConfigProvider",
    "DefaultsConfigProvider",
    "EnvironmentConfigProvider",
    "FileConfigProvider",
    "get_providers",
]


def get_providers() -> List[BaseConfigProvider]:
    """
    Returns the config providers in the expected order.
    Later entries override previous entries.

    Returns:
        List[BaseConfigProvider]: Default providers
    """
    return [
        DefaultsConfigProvider(),
        FileConfigProvider(),
        EnvironmentConfigProvider(),
    ]

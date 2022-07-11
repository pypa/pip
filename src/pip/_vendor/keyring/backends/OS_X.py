"""
Backward-compatibility shim for users referencing the module
by name. Ref #487.
"""

import warnings

from .macOS import Keyring

__all__ = ['Keyring']


warnings.warn("OS_X module is deprecated.", DeprecationWarning)

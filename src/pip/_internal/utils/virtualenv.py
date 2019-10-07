import logging
import os
import site
import sys

logger = logging.getLogger(__name__)


def _running_under_venv():
    # type: () -> bool
    """Checks if sys.base_prefix and sys.prefix match.

    This handles PEP 405 compliant virtual environments.
    """
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def _running_under_regular_virtualenv():
    # type: () -> bool
    """Checks if sys.real_prefix is set.

    This handles virtual environments created with pypa's virtualenv.
    """
    # pypa/virtualenv case
    return hasattr(sys, 'real_prefix')


def running_under_virtualenv():
    # type: () -> bool
    """Return a boolean, whether running under a virtual environment.
    """
    return _running_under_venv() or _running_under_regular_virtualenv()


def _no_global_under_regular_virtualenv():
    # type: () -> bool
    """Check if "no-global-site-packages.txt" exists beside site.py

    This mirrors logic in pypa/virtualenv for determining whether system
    site-packages are visible in the virtual environment.
    """
    site_mod_dir = os.path.dirname(os.path.abspath(site.__file__))
    no_global_site_packages_file = os.path.join(
        site_mod_dir, 'no-global-site-packages.txt',
    )
    return os.path.exists(no_global_site_packages_file)


def virtualenv_no_global():
    # type: () -> bool
    """Returns a boolean, whether running in venv with no system site-packages.
    """

    if _running_under_regular_virtualenv():
        return _no_global_under_regular_virtualenv()

    return False

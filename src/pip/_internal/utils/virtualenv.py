import os.path
import site
import sys


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


def virtualenv_no_global():
    # type: () -> bool
    """
    Return True if in a venv and no system site packages.
    """
    # this mirrors the logic in virtualenv.py for locating the
    # no-global-site-packages.txt file
    site_mod_dir = os.path.dirname(os.path.abspath(site.__file__))
    no_global_file = os.path.join(site_mod_dir, 'no-global-site-packages.txt')
    if running_under_virtualenv() and os.path.isfile(no_global_file):
        return True
    else:
        return False

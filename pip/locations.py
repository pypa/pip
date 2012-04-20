"""Locations where we look for configs, install stuff, etc"""

import sys
import os
from pip.backwardcompat import get_python_lib, get_user_site, get_user_base


def running_under_virtualenv():
    """
    Return True if we're running inside a virtualenv, False otherwise.

    """
    return hasattr(sys, 'real_prefix')

def virtualenv_no_global():
    """
    in a venv and isolated from global?
    """
    lib_python_dir = os.path.dirname(site_packages)
    no_global_file = os.path.join(lib_python_dir,'no-global-site-packages.txt')
    if running_under_virtualenv() and os.path.isfile(no_global_file):
        return True


if running_under_virtualenv():
    ## FIXME: is build/ a good name?
    build_prefix = os.path.join(sys.prefix, 'build')
    src_prefix = os.path.join(sys.prefix, 'src')
else:
    ## FIXME: this isn't a very good default
    build_prefix = os.path.join(os.getcwd(), 'build')
    src_prefix = os.path.join(os.getcwd(), 'src')

# under Mac OS X + virtualenv sys.prefix is not properly resolved
# it is something like /path/to/python/bin/..
build_prefix = os.path.abspath(build_prefix)
src_prefix = os.path.abspath(src_prefix)

# FIXME doesn't account for venv linked to global site-packages

site_packages = get_python_lib()

#can't be replaced with property set at import.  site.py hasn't done it's work yet
def user_site():
    "return user site as long as not in venv/no-global"
    if not virtualenv_no_global():
        return get_user_site()

#can't be replaced with property set at import.  site.py hasn't done it's work yet
def user_base():
    "return user base as long as not in venv/no-global"
    if not virtualenv_no_global():
        return get_user_base()

user_dir = os.path.expanduser('~')
if sys.platform == 'win32':
    bin_py = os.path.join(sys.prefix, 'Scripts')
    # buildout uses 'bin' on Windows too?
    if not os.path.exists(bin_py):
        bin_py = os.path.join(sys.prefix, 'bin')
    user_dir = os.environ.get('APPDATA', user_dir) # Use %APPDATA% for roaming
    default_storage_dir = os.path.join(user_dir, 'pip')
    default_config_file = os.path.join(default_storage_dir, 'pip.ini')
    default_log_file = os.path.join(default_storage_dir, 'pip.log')
else:
    bin_py = os.path.join(sys.prefix, 'bin')
    default_storage_dir = os.path.join(user_dir, '.pip')
    default_config_file = os.path.join(default_storage_dir, 'pip.conf')
    default_log_file = os.path.join(default_storage_dir, 'pip.log')
    # Forcing to use /usr/local/bin for standard Mac OS X framework installs
    # Also log to ~/Library/Logs/ for use with the Console.app log viewer
    if sys.platform[:6] == 'darwin' and sys.prefix[:16] == '/System/Library/':
        bin_py = '/usr/local/bin'
        default_log_file = os.path.join(user_dir, 'Library/Logs/pip.log')

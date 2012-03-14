"""Locations where we look for configs, install stuff, etc"""

import sys
import os
from pip.backwardcompat import get_python_lib, get_user_site


def running_under_virtualenv():
    """
    Return True if we're running inside a virtualenv, False otherwise.

    """
    return hasattr(sys, 'real_prefix')

def virtualenv_no_global():
    """
    assuming we know we're in a venv, is it isolated from global?
    """
    lib_python_dir = os.path.dirname(site_packages)
    no_global_file = os.path.join(lib_python_dir,'no-global-site-packages.txt')
    if os.path.isfile(no_global_file):
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

#this can't be replaced with a property that's set at compile time.  site.py hasn't done it's work yet
def get_user_site_packages():
    "return user site pkgs as long as not in venv/no-global"
    if not (running_under_virtualenv() and virtualenv_no_global()):
        return get_user_site()

orig_site_packages = None
if running_under_virtualenv():
    lib_python_dir = os.path.dirname(site_packages)
    f = open(os.path.join(lib_python_dir, 'orig-prefix.txt'))
    orig_prefix = f.read().strip()
    f.close()        
    orig_site_packages = get_python_lib(prefix=orig_prefix)

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

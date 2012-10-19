"""Locations where we look for configs, install stuff, etc"""

import sys
import site
import os
import shutil
import tempfile
from pip.backwardcompat import get_python_lib


def running_under_virtualenv():
    """
    Return True if we're running inside a virtualenv, False otherwise.

    """
    return hasattr(sys, 'real_prefix')


def virtualenv_no_global():
    """
    Return True if in a venv and no system site packages.
    """
    #this mirrors the logic in virtualenv.py for locating the no-global-site-packages.txt file
    site_mod_dir = os.path.dirname(os.path.abspath(site.__file__))
    no_global_file = os.path.join(site_mod_dir, 'no-global-site-packages.txt')
    if running_under_virtualenv() and os.path.isfile(no_global_file):
        return True


if running_under_virtualenv():
    build_prefix = os.path.join(sys.prefix, 'build')
    src_prefix = os.path.join(sys.prefix, 'src')
else:
    # Use tempfile to create a temporary folder for build
    # Note: we are NOT using mkdtemp so we can have a consistent build dir
    build_prefix = os.path.join(tempfile.gettempdir(), 'pip-build')

    ## FIXME: keep src in cwd for now (it is not a temporary folder)
    try:
        src_prefix = os.path.join(os.getcwd(), 'src')
    except OSError:
        # In case the current working directory has been renamed or deleted
        sys.exit("The folder you are executing pip from can no longer be found.")

# under Mac OS X + virtualenv sys.prefix is not properly resolved
# it is something like /path/to/python/bin/..
build_prefix = os.path.abspath(build_prefix)
src_prefix = os.path.abspath(src_prefix)

# FIXME doesn't account for venv linked to global site-packages

site_packages = get_python_lib()
user_dir = os.path.expanduser('~')
if sys.platform == 'win32':
    bin_py = os.path.join(sys.prefix, 'Scripts')
    # buildout uses 'bin' on Windows too?
    if not os.path.exists(bin_py):
        bin_py = os.path.join(sys.prefix, 'bin')
    default_storage_dir = os.path.join(user_dir, 'pip')
    default_config_file = os.path.join(default_storage_dir, 'pip.ini')
    default_log_file = os.path.join(default_storage_dir, 'pip.log')
else:
    bin_py = os.path.join(sys.prefix, 'bin')

    # Use XDG_CONFIG_HOME instead of the ~/.pip
    # On some systems, we may have to create this, on others it probably exists
    xdg_dir = os.path.join(user_dir, '.config')
    xdg_dir = os.environ.get('XDG_CONFIG_HOME', xdg_dir)
    if not os.path.exists(xdg_dir):
        os.mkdir(xdg_dir)
    default_storage_dir = os.path.join(xdg_dir, 'pip')
    default_config_file = os.path.join(default_storage_dir, 'pip.conf')
    default_log_file = os.path.join(default_storage_dir, 'pip.log')
    
    # Migration path for users- move things from the old dir if it exists
    # If the new dir exists and has no pip.conf and the old dir does, move it
    # When these checks are finished, delete the old directory
    old_storage_dir = os.path.join(user_dir, '.pip')
    old_config_file = os.path.join(old_storage_dir, 'pip.conf')
    if os.path.exists(old_storage_dir):
        if not os.path.exists(default_storage_dir):
            shutil.copytree(old_storage_dir, default_storage_dir)
        elif os.path.exists(old_config_file) and not os.path.exists(default_config_file):
            shutil.copy2(old_config_file, default_config_file)
        shutil.rmtree(old_storage_dir)
    
    # Forcing to use /usr/local/bin for standard Mac OS X framework installs
    # Also log to ~/Library/Logs/ for use with the Console.app log viewer
    if sys.platform[:6] == 'darwin' and sys.prefix[:16] == '/System/Library/':
        bin_py = '/usr/local/bin'
        default_log_file = os.path.join(user_dir, 'Library/Logs/pip.log')

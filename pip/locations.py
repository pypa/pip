"""Locations where we look for configs, install stuff, etc"""

import sys
import os
from distutils import sysconfig

if getattr(sys, 'real_prefix', None):
    ## FIXME: is build/ a good name?
    build_prefix = os.path.join(sys.prefix, 'build')
    src_prefix = os.path.join(sys.prefix, 'src')
else:
    ## FIXME: this isn't a very good default
    build_prefix = os.path.join(os.getcwd(), 'build')
    src_prefix = os.path.join(os.getcwd(), 'src')

# FIXME doesn't account for venv linked to global site-packages

site_packages = sysconfig.get_python_lib()
user_dir = os.path.expanduser('~')
if sys.platform == 'win32':
    bin_py = os.path.join(sys.prefix, 'Scripts')
    # buildout uses 'bin' on Windows too?
    if not os.path.exists(bin_py):
        bin_py = os.path.join(sys.prefix, 'bin')
    config_dir = os.environ.get('APPDATA', user_dir) # Use %APPDATA% for roaming
    default_config_file = os.path.join(config_dir, 'pip', 'pip.ini')
else:
    bin_py = os.path.join(sys.prefix, 'bin')
    default_config_file = os.path.join(user_dir, '.pip', 'pip.conf')
    # Forcing to use /usr/local/bin for standard Mac OS X framework installs
    if sys.platform[:6] == 'darwin' and sys.prefix[:16] == '/System/Library/':
        bin_py = '/usr/local/bin'

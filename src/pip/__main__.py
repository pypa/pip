from __future__ import absolute_import

import os
import sys
import sysconfig

# Remove '' and current working directory from the first entry
# of sys.path, if present to avoid using current directory
# in pip commands check, freeze, install, list and show,
# when invoked as python -m pip <command>
if sys.path[0] in ('', os.getcwd()):
    sys.path.pop(0)

# If we are running from a wheel, add the wheel to sys.path
# This allows the usage python pip-*.whl/pip install pip-*.whl
if __package__ == '':
    # Retrieve the index in sys.path where all stdlib paths reside
    # (DESTSHARED is where some extension modules like math live).
    stdlib_path_indexes = []
    stdlib_paths = (sysconfig.get_path('stdlib'),
                    sysconfig.get_path('platstdlib'),
                    sysconfig.get_config_var('DESTSHARED'))
    for path in (p for p in stdlib_paths if p is not None):
        try:
            stdlib_path_indexes.append(sys.path.index(path))
        except ValueError:
            continue

    # __file__ is pip-*.whl/pip/__main__.py
    # first dirname call strips of '/__main__.py', second strips off '/pip'
    # Resulting path is the name of the wheel itself
    # Add that to sys.path so we can import pip
    pip_installed_path = os.path.dirname(os.path.dirname(__file__))

    # Insert this pip's library path directly after the stdlib so that
    # we import this pip's library even if another pip is installed.
    sys.path.insert(max(stdlib_path_indexes) + 1, pip_installed_path)

from pip._internal.cli.main import main as _main  # isort:skip # noqa

if __name__ == '__main__':
    sys.exit(_main())

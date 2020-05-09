from __future__ import absolute_import

import os
import sys

# Remove '' and current working directory from the first entry
# of sys.path, if present to avoid using current directory
# in pip commands check, freeze, install, list and show,
# when invoked as python -m pip <command>
if sys.path[0] in ('', os.getcwd()):
    sys.path.pop(0)

# __package__ is empty string when invoking a pip wheel directly and when
# invoking the pip directory.  __package__ is None when invoking __main__.py
# directly.
# * When pip is a wheel we want it to add the wheel to sys.path so that the
#   rest of the pip code is available.
# * This code allows pip as a directory to work but we don't want to support
#   it as it can have unintended consequences if there are other python
#   modules in the upper directory which shadow other libraries (enum34
#   shadowing the stdlib enum, for instance, will break pip)
# * If the invocation was of __main__.py itself, we need this code to *not* be
#   run otherwise shadowing libraries can break it just like the directory
#   case.  isolated builds are implemented using __main__.py so it's important
#   that this case not break.
#
# Please see https://www.python.org/dev/peps/pep-0366/#id11
# and https://github.com/pypa/pip/issues/8214
if __package__ == '':
    # __file__ is pip-*.whl/pip/__main__.py
    # first dirname call strips of '/__main__.py', second strips off '/pip'
    # Resulting path is the name of the wheel itself
    # Add that to sys.path so we can import pip
    path = os.path.dirname(os.path.dirname(__file__))
    sys.path.insert(0, path)

from pip._internal.cli.main import main as _main  # isort:skip # noqa

if __name__ == '__main__':
    sys.exit(_main())

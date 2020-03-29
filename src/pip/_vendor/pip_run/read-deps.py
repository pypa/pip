"""
Emit parameters to pip extracted from a script.
"""

import sys

from .scripts import DepsReader


def run():
    (script,) = sys.argv[1:]
    deps = DepsReader.load(script).read()
    print(' '.join(deps.params()))


__name__ == '__main__' and run()

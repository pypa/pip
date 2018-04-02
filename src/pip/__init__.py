from __future__ import absolute_import
import subprocess
import sys

__version__ = "10.0.0.dev0"


def main(*args):
    """
    This function is included primarily for backwards compatibility.

    Although anything using `pip.main()` in pip<9.0.2 was engaged in a
    non-supported mode of use, as a pragmatic accommodation, `pip.main()` is
    being *added* as a *new* piece of functionality with very similar behaviors
    and call signature.

    Why use check_call instead of check_output?
    It's behavior is slightly closer to the older `pip.main()` behavior,
    printing output information directly to stdout.

    check_call was added in py2.5 and is supported through py3.x , so it's more
    compatible than some alternatives like subprocess.run (added in py3.5)
    """
    return subprocess.check_call([sys.executable, '-m', 'pip'] + list(args))


__all__ = ('main',)

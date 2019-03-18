import os
import sys


def get_prog():
    # type: () -> str
    try:
        prog = os.path.basename(sys.argv[0])
        if prog in ('__main__.py', '-c'):
            return "%s -m pip" % sys.executable
        else:
            return prog
    except (AttributeError, TypeError, IndexError):
        pass
    return 'pip'

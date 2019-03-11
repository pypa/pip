from os.path import curdir as _curdir

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path

curdir = Path(_curdir)

"""Stuff that isn't in some old versions of Python"""

__all__ = ['any']

try:
    any
except NameError:
    def any(seq):
        for item in seq:
            if item:
                return True
        return False

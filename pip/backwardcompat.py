"""Stuff that isn't in some old versions of Python"""

__all__ = ['any', 'WindowsError', 'md5']

try:
    WindowsError = WindowsError
except NameError:
    WindowsError = None
try:
    from hashlib import md5
except ImportError:
    import md5 as md5_module
    md5 = md5_module.new

try:
    any = any
except NameError:
    def any(seq):
        for item in seq:
            if item:
                return True
        return False

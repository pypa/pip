"""
Compatibility library for older versions of python
"""
import sys

# python 2.7 introduced a NullHandler which we want to use, but to support
# older versions, we implement our own if needed.
if sys.version_info[:2] > (2, 6):
    from logging import NullHandler
else:
    from logging import Handler
    class NullHandler(Handler):
        def emit(self, record):
            pass

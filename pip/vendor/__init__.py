"""
pip.vendor is for vendoring dependencies of pip to prevent needing pip to
depend on something external.

Files inside of pip.vendor should be considered immutable and should only be
updated to versions from upstream.
"""
from __future__ import absolute_import

# Monkeypatch pip.vendor.six into just six
#   This is kind of terrible, however it is the least bad of 3 bad options
#   #1 Ship pip with ``six`` such that it gets installed as a regular module
#   #2 Modify pip.vendor.html5lib so that instead of ``import six`` it uses
#       ``from pip.vendor import six``.
#   #3 This monkeypatch which adds six to the top level modules only when
#       pip.vendor.* is being used.
#
#   #1 involves pollutiong the globally installed packages and possibly
#   preventing people from using older or newer versions of the six library
#   #2 Means we've modified upstream which makes it more dificult to upgrade
#   in the future and paves the way for us to be in charge of maintaining it.
#   #3 Allows us to not modify upstream while only pollutiong the global
#   namespace when ``pip.vendor`` has been imported, which in typical usage
#   is isolated to command line evocations.
try:
    import six
except ImportError:
    import sys
    from . import six

    sys.modules["six"] = six

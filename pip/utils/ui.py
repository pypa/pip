from __future__ import absolute_import
from __future__ import division

import itertools
import sys

from pip.compat import WINDOWS
from pip.utils import format_size
from pip.utils.logging import get_indentation
from pip._vendor.progress.bar import Bar
from pip._vendor.progress.helpers import WritelnMixin
from pip._vendor.progress.spinner import Spinner

try:
    from pip._vendor import colorama
# Lots of different errors can come from this, including SystemError and
# ImportError.
except Exception:
    colorama = None


class DownloadProgressMixin(object):

    def __init__(self, *args, **kwargs):
        super(DownloadProgressMixin, self).__init__(*args, **kwargs)
        self.message = (" " * (get_indentation() + 2)) + self.message

    @property
    def downloaded(self):
        return format_size(self.index)

    @property
    def download_speed(self):
        # Avoid zero division errors...
        if self.avg == 0.0:
            return "..."
        return format_size(1 / self.avg) + "/s"

    @property
    def pretty_eta(self):
        if self.eta:
            return "eta %s" % self.eta_td
        return ""

    def iter(self, it, n=1):
        for x in it:
            yield x
            self.next(n)
        self.finish()


class WindowsMixin(object):

    def __init__(self, *args, **kwargs):
        super(WindowsMixin, self).__init__(*args, **kwargs)

        # Check if we are running on Windows and we have the colorama module,
        # if we do then wrap our file with it.
        if WINDOWS and colorama:
            self.file = colorama.AnsiToWin32(self.file)
            # The progress code expects to be able to call self.file.isatty()
            # but the colorama.AnsiToWin32() object doesn't have that, so we'll
            # add it.
            self.file.isatty = lambda: self.file.wrapped.isatty()
            # The progress code expects to be able to call self.file.flush()
            # but the colorama.AnsiToWin32() object doesn't have that, so we'll
            # add it.
            self.file.flush = lambda: self.file.wrapped.flush()

        # The Windows terminal does not support the hide/show cursor ANSI codes
        # even with colorama. So we'll ensure that hide_cursor is False on
        # Windows.
        if WINDOWS and self.hide_cursor:
            self.hide_cursor = False


class DownloadProgressBar(WindowsMixin, DownloadProgressMixin, Bar):

    file = sys.stdout
    message = "%(percent)d%%"
    suffix = "%(downloaded)s %(download_speed)s %(pretty_eta)s"


class DownloadProgressSpinner(WindowsMixin, DownloadProgressMixin,
                              WritelnMixin, Spinner):

    file = sys.stdout
    suffix = "%(downloaded)s %(download_speed)s"

    def next_phase(self):
        if not hasattr(self, "_phaser"):
            self._phaser = itertools.cycle(self.phases)
        return next(self._phaser)

    def update(self):
        message = self.message % self
        phase = self.next_phase()
        suffix = self.suffix % self
        line = ''.join([
            message,
            " " if message else "",
            phase,
            " " if suffix else "",
            suffix,
        ])

        self.writeln(line)

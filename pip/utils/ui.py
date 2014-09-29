from __future__ import absolute_import
from __future__ import division

import itertools
import sys

from pip.utils import format_size
from pip.utils.logging import get_indentation
from pip._vendor.progress.bar import Bar
from pip._vendor.progress.helpers import WritelnMixin
from pip._vendor.progress.spinner import Spinner


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


class DownloadProgressBar(DownloadProgressMixin, Bar):

    file = sys.stdout
    message = "%(percent)d%%"
    suffix = "%(downloaded)s %(download_speed)s %(pretty_eta)s"


class DownloadProgressSpinner(DownloadProgressMixin, WritelnMixin, Spinner):

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

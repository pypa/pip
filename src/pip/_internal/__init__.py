#!/usr/bin/env python
from __future__ import absolute_import

import warnings

# We ignore certain warnings from urllib3, since they are not relevant to pip's
# usecases.
from pip._vendor.urllib3.exceptions import (
    DependencyWarning,
    InsecureRequestWarning,
)

import pip._internal.utils.inject_securetransport  # noqa
from pip._internal.cli.autocompletion import autocomplete

# Raised when using --trusted-host.
warnings.filterwarnings("ignore", category=InsecureRequestWarning)
# Raised since socks support depends on PySocks, which may not be installed.
#   Barry Warsaw noted (on 2016-06-17) that this should be done before
#   importing pip.vcs, which has since moved to pip._internal.vcs.
warnings.filterwarnings("ignore", category=DependencyWarning)

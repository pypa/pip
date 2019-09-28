#!/usr/bin/env python
from __future__ import absolute_import

import warnings

# We ignore certain warnings from urllib3, since they are not relevant to pip's
# usecases.
from pip._vendor.urllib3.exceptions import InsecureRequestWarning

import pip._internal.utils.inject_securetransport  # noqa

# Raised when using --trusted-host.
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

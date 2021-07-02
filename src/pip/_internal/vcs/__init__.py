# Import all vcs modules to register each VCS in the VcsSupport object.
#
# These imports are ordered based on rough "popularity" as judged by
# @pradyunsg in July 2021. This ordering determines the order that
# directories are checked for "is this in a vcs backend" and thus
# ordering by priority here makes things a few ms faster.
import pip._internal.vcs.git  # isort: skip
import pip._internal.vcs.subversion  # isort: skip
import pip._internal.vcs.mercurial  # isort: skip
import pip._internal.vcs.bazaar  # isort: skip  # noqa: F401

# Expose a limited set of classes and functions so callers outside of
# the vcs package don't need to import deeper than `pip._internal.vcs`.
# (The test directory may still need to import from a vcs sub-package.)
from pip._internal.vcs.versioncontrol import (  # noqa: F401
    RemoteNotFoundError,
    RemoteNotValidError,
    is_url,
    make_vcs_requirement_url,
    vcs,
)

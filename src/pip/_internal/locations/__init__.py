from typing import Optional

from pip._internal.models.scheme import Scheme

from . import distutils as _distutils
from .base import (
    USER_CACHE_DIR,
    get_major_minor_version,
    get_src_prefix,
    site_packages,
    user_site,
)

__all__ = [
    "USER_CACHE_DIR",
    "get_bin_prefix",
    "get_bin_user",
    "get_major_minor_version",
    "get_scheme",
    "get_src_prefix",
    "init_backend",
    "site_packages",
    "user_site",
]


def get_scheme(
    dist_name,  # type: str
    user=False,  # type: bool
    home=None,  # type: Optional[str]
    root=None,  # type: Optional[str]
    isolated=False,  # type: bool
    prefix=None,  # type: Optional[str]
):
    # type: (...) -> Scheme
    return _distutils.get_scheme(
        dist_name,
        user=user,
        home=home,
        root=root,
        isolated=isolated,
        prefix=prefix,
    )


def get_bin_prefix():
    # type: () -> str
    return _distutils.get_bin_prefix()


def get_bin_user():
    # type: () -> str
    return _distutils.get_bin_user()

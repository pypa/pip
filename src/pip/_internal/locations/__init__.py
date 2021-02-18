import logging
import pathlib
import sysconfig
from typing import Optional

from pip._internal.models.scheme import SCHEME_KEYS, Scheme

from . import _distutils, _sysconfig
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


logger = logging.getLogger(__name__)


def _default_base(*, user):
    # type: (bool) -> str
    if user:
        base = sysconfig.get_config_var("userbase")
    else:
        base = sysconfig.get_config_var("base")
    assert base is not None
    return base


def _warn_if_mismatch(old, new, *, key):
    # type: (pathlib.Path, pathlib.Path, str) -> None
    if old == new:
        return
    message = (
        "Value for %s does not match. Please report this: <URL HERE>"
        "\ndistutils: %s"
        "\nsysconfig: %s"
    )
    logger.warning(message, key, old, new)


def get_scheme(
    dist_name,  # type: str
    user=False,  # type: bool
    home=None,  # type: Optional[str]
    root=None,  # type: Optional[str]
    isolated=False,  # type: bool
    prefix=None,  # type: Optional[str]
):
    # type: (...) -> Scheme
    old = _distutils.get_scheme(
        dist_name,
        user=user,
        home=home,
        root=root,
        isolated=isolated,
        prefix=prefix,
    )
    new = _sysconfig.get_scheme(
        dist_name,
        user=user,
        home=home,
        root=root,
        isolated=isolated,
        prefix=prefix,
    )

    base = prefix or home or _default_base(user=user)
    for k in SCHEME_KEYS:
        # Extra join because distutils can return relative paths.
        old_v = pathlib.Path(base, getattr(old, k))
        new_v = pathlib.Path(getattr(new, k))
        _warn_if_mismatch(old_v, new_v, key=f"scheme.{k}")

    return old


def get_bin_prefix():
    # type: () -> str
    old = _distutils.get_bin_prefix()
    new = _sysconfig.get_bin_prefix()
    _warn_if_mismatch(pathlib.Path(old), pathlib.Path(new), key="bin_prefix")
    return old


def get_bin_user():
    # type: () -> str
    old = _distutils.get_bin_user()
    new = _sysconfig.get_bin_user()
    _warn_if_mismatch(pathlib.Path(old), pathlib.Path(new), key="bin_user")
    return old

import distutils.util  # FIXME: For change_root.
import logging
import os
import sys
import sysconfig
import typing

from pip._internal.exceptions import InvalidSchemeCombination, UserInstallationInvalid
from pip._internal.models.scheme import SCHEME_KEYS, Scheme
from pip._internal.utils.virtualenv import running_under_virtualenv

from .base import get_major_minor_version

logger = logging.getLogger(__name__)


_AVAILABLE_SCHEMES = set(sysconfig.get_scheme_names())


def _infer_scheme(variant):
    # (typing.Literal["home", "prefix", "user"]) -> str
    """Try to find a scheme for the current platform.

    Unfortunately ``_get_default_scheme()`` is private, so there's no way to
    ask things like "what is the '_home' scheme on this platform". This tries
    to answer that with some heuristics while accounting for ad-hoc platforms
    not covered by CPython's default sysconfig implementation.
    """
    # Most schemes are named like this e.g. "posix_home", "nt_user".
    suffixed = f"{os.name}_{variant}"
    if suffixed in _AVAILABLE_SCHEMES:
        return suffixed

    # The user scheme is not available.
    if variant == "user" and sysconfig.get_config_var("userbase") is None:
        raise UserInstallationInvalid()

    # On Windows, prefx and home schemes are the same and just called "nt".
    if os.name in _AVAILABLE_SCHEMES:
        return os.name

    # Not sure what's happening, some obscure platform that does not fully
    # implement sysconfig? Just use the POSIX scheme.
    logger.warning("No %r scheme for %r; fallback to POSIX.", variant, os.name)
    return f"posix_{variant}"


# Update these keys if the user sets a custom home.
_HOME_KEYS = (
    "installed_base",
    "base",
    "installed_platbase",
    "platbase",
    "prefix",
    "exec_prefix",
)
if sysconfig.get_config_var("userbase") is not None:
    _HOME_KEYS += ("userbase",)


def get_scheme(
    dist_name,  # type: str
    user=False,  # type: bool
    home=None,  # type: typing.Optional[str]
    root=None,  # type: typing.Optional[str]
    isolated=False,  # type: bool
    prefix=None,  # type: typing.Optional[str]
):
    # type: (...) -> Scheme
    """
    Get the "scheme" corresponding to the input parameters.

    :param dist_name: the name of the package to retrieve the scheme for, used
        in the headers scheme path
    :param user: indicates to use the "user" scheme
    :param home: indicates to use the "home" scheme
    :param root: root under which other directories are re-based
    :param isolated: ignored, but kept for distutils compatibility (where
        this controls whether the user-site pydistutils.cfg is honored)
    :param prefix: indicates to use the "prefix" scheme and provides the
        base directory for the same
    """
    if user and prefix:
        raise InvalidSchemeCombination("--user", "--prefix")
    if home and prefix:
        raise InvalidSchemeCombination("--home", "--prefix")

    if home is not None:
        scheme = _infer_scheme("home")
    elif user:
        scheme = _infer_scheme("user")
    else:
        scheme = _infer_scheme("prefix")

    if home is not None:
        variables = {k: home for k in _HOME_KEYS}
    elif prefix is not None:
        variables = {k: prefix for k in _HOME_KEYS}
    else:
        variables = {}

    paths = sysconfig.get_paths(scheme=scheme, vars=variables)

    # Special header path for compatibility to distutils.
    if running_under_virtualenv():
        base = variables.get("base", sys.prefix)
        python_xy = f"python{get_major_minor_version()}"
        paths["include"] = os.path.join(base, "include", "site", python_xy)

    scheme = Scheme(
        platlib=paths["platlib"],
        purelib=paths["purelib"],
        headers=os.path.join(paths["include"], dist_name),
        scripts=paths["scripts"],
        data=paths["data"],
    )
    if root is not None:
        for key in SCHEME_KEYS:
            value = distutils.util.change_root(root, getattr(scheme, key))
            setattr(scheme, key, value)
    return scheme


def get_bin_prefix():
    # type: () -> str
    # Forcing to use /usr/local/bin for standard macOS framework installs.
    if sys.platform[:6] == "darwin" and sys.prefix[:16] == "/System/Library/":
        return "/usr/local/bin"
    return sysconfig.get_path("scripts", scheme=_infer_scheme("prefix"))


def get_bin_user():
    return sysconfig.get_path("scripts", scheme=_infer_scheme("user"))


def get_purelib():
    # type: () -> str
    return sysconfig.get_path("purelib")


def get_platlib():
    # type: () -> str
    return sysconfig.get_path("platlib")


def get_prefixed_libs(prefix):
    # type: (str) -> typing.Tuple[str, str]
    paths = sysconfig.get_paths(vars={"base": prefix, "platbase": prefix})
    return (paths["purelib"], paths["platlib"])

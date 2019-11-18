"""Shared AIX support functions."""

import sys
from subprocess import check_output
from sysconfig import get_config_var

# from ._typing import MYPY_CHECK_RUNNING

"""
AIX filesets are identified by four decimal values aka VRMF.
V (version) is the value returned by "uname -v"
R (release) is the value returned by "uname -r"
M and F values are not available via uname
There is a fifth, lessor known value: builddate that
is expressed as YYWW (Year WeekofYear)

The fileset bos.mp64 contains the AIX kernel and it's
VRMF and builddate are equivalent to installed
levels of the runtime environment.
The program lslpp is used to get these values.
The pep425 platform tag for AIX becomes:
AIX.VRTL.YYWW.SZ, e.g., AIX.6107.1415.32

The routines here convert VRMF values to VRTL and
adding BUILDDATE and bitness for comparision with
other AIX platform tags
"""

_bgt = get_config_var("BUILD_GNU_TYPE")

_is_32bit = sys.maxsize == 2147483647


def _aix_tag(vrtl, bd):
    # type: (int, int) -> str
    sz = 32 if _is_32bit else 64
    return "AIX.{:04d}.{}.{}".format(vrtl, bd, sz)


# extract vrtl from the VRMF string
def _aix_vrtl(vrmf):
    # type: (str) -> int
    v, r, tl = vrmf.split(".")[:3]
    return int("{}{}{:02d}".format(v[-1], r, int(tl)))


# extract vrtl from the BUILD_GNU_TYPE as an int
def _aix_bgt():
    # type: () -> int
    assert(_bgt)
    return(_aix_vrtl(_bgt))


# return the AIX_BUILDDATE, or 9898 if not defined
def _aix_bd():
    # type: () -> int
    bd = get_config_var("AIX_BUILDDATE")
    # if bd == "" or None set Builddate value to an impossible value
    # year XX98-week98
    if not bd:
        return 9898
    else:
        return int(bd)


def aix_buildtag():
    # type: () -> str
    return _aix_tag(_aix_bgt(), _aix_bd())


def _aix_platform():
    # type: () -> str
    vrmf = ""
    tmp = check_output(["/usr/bin/lslpp", "-Lqc", "bos.mp64"])
    tmp = tmp.decode("utf-8").strip().split(":")  # type: ignore
    lpp, vrmf, bd = list(tmp[index] for index in [0, 2, -1])  # type: ignore
    assert lpp == "bos.mp64", "%s != %s" % (lpp, "bos.mp64")
    return _aix_tag(_aix_vrtl(vrmf), int(bd))


def get_platform():
    # type: () -> str
    """Return AIX platform tag"""
    return _aix_platform()

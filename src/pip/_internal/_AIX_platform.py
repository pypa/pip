"""Shared AIX support functions."""

import sys
from subprocess import check_output
from sysconfig import get_config_var
from ._typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Optional


_is_32bit = sys.maxsize == 2147483647


def aix_tag(vrtl, bd):
    # type: (int, int) -> str
    sz = 32 if _is_32bit else 64
    return "AIX.{:04d}.{}.{}".format(vrtl, bd, sz)


def aix_ver(bgt=""):
    # type: (Optional[str]) -> int
    if bgt == "":
        bgt = get_config_var("BUILD_GNU_TYPE")
    assert bgt
    v, r, tl = bgt.split(".")[:3]
    return int("{}{}{:02d}".format(v, r, int(tl)))


def _builddate():
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
    return aix_tag(aix_ver(), _builddate())


def aix_pep425():
    # type: () -> str
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
    """
    # p = run(["/usr/bin/lslpp", "-Lqc", "bos.mp64"],
    #       capture_output=True, text=True)
    result = check_output(["/usr/bin/lslpp", "-Lqc", "bos.mp64"])
    result = result.decode("utf-8").strip().split(":")  # type: ignore

    (lpp, vrmf, bd) = list(result[index] for index in [0, 2, -1])
    assert lpp == "bos.mp64", "%s != %s" % (lpp, "bos.mp64")
    v, r, tl = map(int, vrmf.split(".")[:3])
    # vers = tuple(map(int, v, r, tl))
    # return aix_tag(vers, int(bd))
    # return aix_tag(v, r, tl, int(bd))
    return aix_tag(aix_ver(vrmf), int(bd))


def get_platform():
    # type: () -> str
    """Return AIX platform tag"""
    return aix_pep425()

# Taken from distlib so we can easily determine what a pre-release is.
#   It has been stripped down to only the parts needed for that purpose.
import re


class UnsupportedVersionError(Exception):
    """This is an unsupported version."""
    pass


class HugeMajorVersionError(UnsupportedVersionError):
    """An irrational version because the major version number is huge
    (often because a year or date was used).

    See `error_on_huge_major_num` option in `NormalizedVersion` for details.
    This guard can be disabled by setting that option False.
    """
    pass


# A marker used in the second and third parts of the `parts` tuple, for
# versions that don't have those segments, to sort properly. An example
# of versions in sort order ('highest' last):
#   1.0b1                 ((1,0), ('b',1), ('z',))
#   1.0.dev345            ((1,0), ('z',),  ('dev', 345))
#   1.0                   ((1,0), ('z',),  ('z',))
#   1.0.post256.dev345    ((1,0), ('z',),  ('z', 'post', 256, 'dev', 345))
#   1.0.post345           ((1,0), ('z',),  ('z', 'post', 345, 'z'))
#                                   ^        ^                 ^
#   'b' < 'z' ---------------------/         |                 |
#                                            |                 |
#   'dev' < 'z' ----------------------------/                  |
#                                                              |
#   'dev' < 'z' ----------------------------------------------/
# 'f' for 'final' would be kind of nice, but due to bugs in the support of
# 'rc' we must use 'z'
_FINAL_MARKER = ('z',)

_VERSION_RE = re.compile(r'''
    ^
    (?P<version>\d+\.\d+(\.\d+)*)          # minimum 'N.N'
    (?:
        (?P<prerel>[abc]|rc)       # 'a'=alpha, 'b'=beta, 'c'=release candidate
                                   # 'rc'= alias for release candidate
        (?P<prerelversion>\d+(?:\.\d+)*)
    )?
    (?P<postdev>(\.post(?P<post>\d+))?(\.dev(?P<dev>\d+))?)?
    $''', re.VERBOSE)


def _parse_numdots(s, full_ver, drop_zeroes=False, min_length=0):
    """Parse 'N.N.N' sequences, return a list of ints.

    @param s {str} 'N.N.N...' sequence to be parsed
    @param full_ver_str {str} The full version string from which this
           comes. Used for error strings.
    @param min_length {int} The length to which to pad the
           returned list with zeros, if necessary. Default 0.
    """
    result = []
    for n in s.split("."):
        #if len(n) > 1 and n[0] == '0':
        #    raise UnsupportedVersionError("cannot have leading zero in "
        #        "version number segment: '%s' in %r" % (n, full_ver))
        result.append(int(n))
    if drop_zeroes:
        while (result and result[-1] == 0 and
               (1 + len(result)) > min_length):
            result.pop()
    return result


def normalized_key(s, fail_on_huge_major_ver=True):
    match = _VERSION_RE.search(s)
    if not match:
        raise UnsupportedVersionError(s)

    groups = match.groupdict()
    parts = []

    # main version
    block = _parse_numdots(groups['version'], s, min_length=2)
    parts.append(tuple(block))

    # prerelease
    prerel = groups.get('prerel')
    if prerel is not None:
        block = [prerel]
        block += _parse_numdots(groups.get('prerelversion'), s, min_length=1)
        parts.append(tuple(block))
    else:
        parts.append(_FINAL_MARKER)

    # postdev
    if groups.get('postdev'):
        post = groups.get('post')
        dev = groups.get('dev')
        postdev = []
        if post is not None:
            postdev.extend((_FINAL_MARKER[0], 'post', int(post)))
            if dev is None:
                postdev.append(_FINAL_MARKER[0])
        if dev is not None:
            postdev.extend(('dev', int(dev)))
        parts.append(tuple(postdev))
    else:
        parts.append(_FINAL_MARKER)
    if fail_on_huge_major_ver and parts[0][0] > 1980:
        raise HugeMajorVersionError("huge major version number, %r, "
           "which might cause future problems: %r" % (parts[0][0], s))
    return tuple(parts)


def suggest_normalized_version(s):
    """Suggest a normalized version close to the given version string.

    If you have a version string that isn't rational (i.e. NormalizedVersion
    doesn't like it) then you might be able to get an equivalent (or close)
    rational version from this function.

    This does a number of simple normalizations to the given string, based
    on observation of versions currently in use on PyPI. Given a dump of
    those version during PyCon 2009, 4287 of them:
    - 2312 (53.93%) match NormalizedVersion without change
      with the automatic suggestion
    - 3474 (81.04%) match when using this suggestion method

    @param s {str} An irrational version string.
    @returns A rational version string, or None, if couldn't determine one.
    """
    try:
        normalized_key(s)
        return s   # already rational
    except UnsupportedVersionError:
        pass

    rs = s.lower()

    # part of this could use maketrans
    for orig, repl in (('-alpha', 'a'), ('-beta', 'b'), ('alpha', 'a'),
                       ('beta', 'b'), ('rc', 'c'), ('-final', ''),
                       ('-pre', 'c'),
                       ('-release', ''), ('.release', ''), ('-stable', ''),
                       ('+', '.'), ('_', '.'), (' ', ''), ('.final', ''),
                       ('final', '')):
        rs = rs.replace(orig, repl)

    # if something ends with dev or pre, we add a 0
    rs = re.sub(r"pre$", r"pre0", rs)
    rs = re.sub(r"dev$", r"dev0", rs)

    # if we have something like "b-2" or "a.2" at the end of the
    # version, that is pobably beta, alpha, etc
    # let's remove the dash or dot
    rs = re.sub(r"([abc]|rc)[\-\.](\d+)$", r"\1\2", rs)

    # 1.0-dev-r371 -> 1.0.dev371
    # 0.1-dev-r79 -> 0.1.dev79
    rs = re.sub(r"[\-\.](dev)[\-\.]?r?(\d+)$", r".\1\2", rs)

    # Clean: 2.0.a.3, 2.0.b1, 0.9.0~c1
    rs = re.sub(r"[.~]?([abc])\.?", r"\1", rs)

    # Clean: v0.3, v1.0
    if rs.startswith('v'):
        rs = rs[1:]

    # Clean leading '0's on numbers.
    #TODO: unintended side-effect on, e.g., "2003.05.09"
    # PyPI stats: 77 (~2%) better
    rs = re.sub(r"\b0+(\d+)(?!\d)", r"\1", rs)

    # Clean a/b/c with no version. E.g. "1.0a" -> "1.0a0". Setuptools infers
    # zero.
    # PyPI stats: 245 (7.56%) better
    rs = re.sub(r"(\d+[abc])$", r"\g<1>0", rs)

    # the 'dev-rNNN' tag is a dev tag
    rs = re.sub(r"\.?(dev-r|dev\.r)\.?(\d+)$", r".dev\2", rs)

    # clean the - when used as a pre delimiter
    rs = re.sub(r"-(a|b|c)(\d+)$", r"\1\2", rs)

    # a terminal "dev" or "devel" can be changed into ".dev0"
    rs = re.sub(r"[\.\-](dev|devel)$", r".dev0", rs)

    # a terminal "dev" can be changed into ".dev0"
    rs = re.sub(r"(?![\.\-])dev$", r".dev0", rs)

    # a terminal "final" or "stable" can be removed
    rs = re.sub(r"(final|stable)$", "", rs)

    # The 'r' and the '-' tags are post release tags
    #   0.4a1.r10       ->  0.4a1.post10
    #   0.9.33-17222    ->  0.9.33.post17222
    #   0.9.33-r17222   ->  0.9.33.post17222
    rs = re.sub(r"\.?(r|-|-r)\.?(\d+)$", r".post\2", rs)

    # Clean 'r' instead of 'dev' usage:
    #   0.9.33+r17222   ->  0.9.33.dev17222
    #   1.0dev123       ->  1.0.dev123
    #   1.0.git123      ->  1.0.dev123
    #   1.0.bzr123      ->  1.0.dev123
    #   0.1a0dev.123    ->  0.1a0.dev123
    # PyPI stats:  ~150 (~4%) better
    rs = re.sub(r"\.?(dev|git|bzr)\.?(\d+)$", r".dev\2", rs)

    # Clean '.pre' (normalized from '-pre' above) instead of 'c' usage:
    #   0.2.pre1        ->  0.2c1
    #   0.2-c1         ->  0.2c1
    #   1.0preview123   ->  1.0c123
    # PyPI stats: ~21 (0.62%) better
    rs = re.sub(r"\.?(pre|preview|-c)(\d+)$", r"c\g<2>", rs)

    # Tcl/Tk uses "px" for their post release markers
    rs = re.sub(r"p(\d+)$", r".post\1", rs)

    try:
        normalized_key(rs)
    except UnsupportedVersionError:
        rs = None
    return rs

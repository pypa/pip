# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2013 The Python Software Foundation.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
"""
Implementation of a flexible versioning scheme providing support for PEP-386,
distribute-compatible and semantic versioning.
"""

import re

from .compat import string_types

__all__ = ['NormalizedVersion', 'NormalizedMatcher',
           'LegacyVersion', 'LegacyMatcher',
           'SemanticVersion', 'SemanticMatcher',
           'UnsupportedVersionError', 'get_scheme']

class UnsupportedVersionError(ValueError):
    """This is an unsupported version."""
    pass


class Version(object):
    def __init__(self, s):
        self._string = s = s.strip()
        self._parts = parts = self.parse(s)
        assert isinstance(parts, tuple)
        assert len(parts) > 0

    def parse(self, s):
        raise NotImplementedError('please implement in a subclass')

    def _check_compatible(self, other):
        if type(self) != type(other):
            raise TypeError('cannot compare %r and %r' % (self, other))

    def __eq__(self, other):
        self._check_compatible(other)
        return self._parts == other._parts

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        self._check_compatible(other)
        return self._parts < other._parts

    def __gt__(self, other):
        return not (self.__lt__(other) or self.__eq__(other))

    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    def __ge__(self, other):
        return self.__gt__(other) or self.__eq__(other)

    # See http://docs.python.org/reference/datamodel#object.__hash__
    def __hash__(self):
        return hash(self._parts)

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self._string)

    def __str__(self):
        return self._string

    @property
    def is_prerelease(self):
        raise NotImplementedError('Please implement in subclasses.')


class Matcher(object):
    version_class = None

    dist_re = re.compile(r"^(\w[\s\w'.-]*)(\((.*)\))?")
    comp_re = re.compile(r'^(<=|>=|<|>|!=|==|~=)?\s*([^\s,]+)$')
    num_re = re.compile(r'^\d+(\.\d+)*$')

    # value is either a callable or the name of a method
    _operators = {
        '<': lambda v, c, p: v < c,
        '>': lambda v, c, p: v > c,
        '<=': lambda v, c, p: v == c or v < c,
        '>=': lambda v, c, p: v == c or v > c,
        '==': lambda v, c, p: v == c,
        # by default, compatible => >=.
        '~=': lambda v, c, p: v == c or v > c,
        '!=': lambda v, c, p: v != c,
    }

    def __init__(self, s):
        if self.version_class is None:
            raise ValueError('Please specify a version class')
        self._string = s = s.strip()
        m = self.dist_re.match(s)
        if not m:
            raise ValueError('Not valid: %r' % s)
        groups = m.groups('')
        self.name = groups[0].strip()
        self.key = self.name.lower()    # for case-insensitive comparisons
        clist = []
        if groups[2]:
            constraints = [c.strip() for c in groups[2].split(',')]
            for c in constraints:
                m = self.comp_re.match(c)
                if not m:
                    raise ValueError('Invalid %r in %r' % (c, s))
                groups = m.groups()
                op = groups[0] or '~='
                s = groups[1]
                if s.endswith('.*'):
                    if op not in ('==', '!='):
                        raise ValueError('\'.*\' not allowed for '
                                         '%r constraints' % op)
                    # Could be a partial version (e.g. for '2.*') which
                    # won't parse as a version, so keep it as a string
                    vn, prefix = s[:-2], True
                    if not self.num_re.match(vn):
                        # Just to check that vn is a valid version
                        self.version_class(vn)
                else:
                    # Should parse as a version, so we can create an
                    # instance for the comparison
                    vn, prefix = self.version_class(s), False
                clist.append((op, vn, prefix))
        self._parts = tuple(clist)

    def match(self, version):
        """Check if the provided version matches the constraints."""
        if isinstance(version, string_types):
            version = self.version_class(version)
        for operator, constraint, prefix in self._parts:
            f = self._operators.get(operator)
            if isinstance(f, string_types):
                f = getattr(self, f)
            if not f:
                msg = ('%r not implemented '
                       'for %s' % (operator, self.__class__.__name__))
                raise NotImplementedError(msg)
            if not f(version, constraint, prefix):
                return False
        return True

    @property
    def exact_version(self):
        result = None
        if len(self._parts) == 1 and self._parts[0][0] == '==':
            result = self._parts[0][1]
        return result

    def _check_compatible(self, other):
        if type(self) != type(other) or self.name != other.name:
            raise TypeError('cannot compare %s and %s' % (self, other))

    def __eq__(self, other):
        self._check_compatible(other)
        return (self.key == other.key and self._parts == other._parts)

    def __ne__(self, other):
        return not self.__eq__(other)

    # See http://docs.python.org/reference/datamodel#object.__hash__
    def __hash__(self):
        return hash(self.key) + hash(self._parts)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self._string)

    def __str__(self):
        return self._string

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

def _pep386_key(s):
    """Parses a string version into parts using PEP-386 logic."""

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
    return tuple(parts)


PEP426_VERSION_RE = re.compile('^(\d+\.\d+(\.\d+)*)((a|b|c|rc)(\d+))?'
                               '(\.(post)(\d+))?(\.(dev)(\d+))?$')

def _pep426_key(s):
    s = s.strip()
    m = PEP426_VERSION_RE.match(s)
    if not m:
        raise UnsupportedVersionError('Not a valid version: %s' % s)
    groups = m.groups()
    nums = tuple(int(v) for v in groups[0].split('.'))
    while len(nums) > 1 and nums[-1] == 0:
        nums = nums[:-1]

    pre = groups[3:5]
    post = groups[6:8]
    dev = groups[9:11]
    if pre == (None, None):
        pre = ()
    else:
        pre = pre[0], int(pre[1])
    if post == (None, None):
        post = ()
    else:
        post = post[0], int(post[1])
    if dev == (None, None):
        dev = ()
    else:
        dev = dev[0], int(dev[1])
    if not pre:
        # either before pre-release, or final release and after
        if not post and dev:
            # before pre-release
            pre = ('a', -1) # to sort before a0
        else:
            pre = ('z',)    # to sort after all pre-releases
    # now look at the state of post and dev.
    if not post:
        post = ('_',)   # sort before 'a'
    if not dev:
        dev = ('final',)

    #print('%s -> %s' % (s, m.groups()))
    return nums, pre, post, dev


_normalized_key = _pep426_key

class NormalizedVersion(Version):
    """A rational version.

    Good:
        1.2         # equivalent to "1.2.0"
        1.2.0
        1.2a1
        1.2.3a2
        1.2.3b1
        1.2.3c1
        1.2.3.4
        TODO: fill this out

    Bad:
        1           # mininum two numbers
        1.2a        # release level must have a release serial
        1.2.3b
    """
    def parse(self, s):
        result = _normalized_key(s)
        # _normalized_key loses trailing zeroes in the release
        # clause, since that's needed to ensure that X.Y == X.Y.0 == X.Y.0.0
        # However, PEP 440 prefix matching needs it: for example,
        # (~= 1.4.5.0) matches differently to (~= 1.4.5.0.0).
        m = PEP426_VERSION_RE.match(s)      # must succeed
        groups = m.groups()
        self._release_clause = tuple(int(v) for v in groups[0].split('.'))
        return result

    PREREL_TAGS = set(['a', 'b', 'c', 'rc', 'dev'])

    @property
    def is_prerelease(self):
        return any(t[0] in self.PREREL_TAGS for t in self._parts)

# We want '2.5' to match '2.5.4' but not '2.50'.

def _match_prefix(x, y):
    x = str(x)
    y = str(y)
    if x == y:
        return True
    if not x.startswith(y):
        return False
    n = len(y)
    return x[n] == '.'

class NormalizedMatcher(Matcher):
    version_class = NormalizedVersion

    # value is either a callable or the name of a method
    _operators = {
        '~=': '_match_compatible',
        '<': '_match_lt',
        '>': '_match_gt',
        '<=': '_match_le',
        '>=': '_match_ge',
        '==': '_match_eq',
        '!=': '_match_ne',
    }

    def _match_lt(self, version, constraint, prefix):
        if version >= constraint:
            return False
        release_clause = constraint._release_clause
        pfx = '.'.join([str(i) for i in release_clause])
        return not _match_prefix(version, pfx)

    def _match_gt(self, version, constraint, prefix):
        if version <= constraint:
            return False
        release_clause = constraint._release_clause
        pfx = '.'.join([str(i) for i in release_clause])
        return not _match_prefix(version, pfx)

    def _match_le(self, version, constraint, prefix):
        return version <= constraint

    def _match_ge(self, version, constraint, prefix):
        return version >= constraint

    def _match_eq(self, version, constraint, prefix):
        if not prefix:
            result = (version == constraint)
        else:
            result = _match_prefix(version, constraint)
        return result

    def _match_ne(self, version, constraint, prefix):
        if not prefix:
            result = (version != constraint)
        else:
            result = not _match_prefix(version, constraint)
        return result

    def _match_compatible(self, version, constraint, prefix):
        if version == constraint:
            return True
        if version < constraint:
            return False
        release_clause = constraint._release_clause
        if len(release_clause) > 1:
            release_clause = release_clause[:-1]
        pfx = '.'.join([str(i) for i in release_clause])
        return _match_prefix(version, pfx)

_REPLACEMENTS = (
    (re.compile('[.+-]$'), ''),                     # remove trailing puncts
    (re.compile(r'^[.](\d)'), r'0.\1'),             # .N -> 0.N at start
    (re.compile('^[.-]'), ''),                      # remove leading puncts
    (re.compile(r'^\((.*)\)$'), r'\1'),             # remove parentheses
    (re.compile(r'^v(ersion)?\s*(\d+)'), r'\2'),    # remove leading v(ersion)
    (re.compile(r'^r(ev)?\s*(\d+)'), r'\2'),        # remove leading v(ersion)
    (re.compile('[.]{2,}'), '.'),                   # multiple runs of '.'
    (re.compile(r'\b(alfa|apha)\b'), 'alpha'),      # misspelt alpha
    (re.compile(r'\b(pre-alpha|prealpha)\b'),
                'pre.alpha'),                       # standardise
    (re.compile(r'\(beta\)$'), 'beta'),             # remove parentheses
)

_SUFFIX_REPLACEMENTS = (
    (re.compile('^[:~._+-]+'), ''),                   # remove leading puncts
    (re.compile('[,*")([\]]'), ''),                        # remove unwanted chars
    (re.compile('[~:+_ -]'), '.'),                    # replace illegal chars
    (re.compile('[.]{2,}'), '.'),                   # multiple runs of '.'
    (re.compile(r'\.$'), ''),                       # trailing '.'
)

_NUMERIC_PREFIX = re.compile(r'(\d+(\.\d+)*)')

def _suggest_semantic_version(s):
    """
    Try to suggest a semantic form for a version for which
    _suggest_normalized_version couldn't come up with anything.
    """
    result = s.strip().lower()
    for pat, repl in _REPLACEMENTS:
        result = pat.sub(repl, result)
    if not result:
        result = '0.0.0'

    # Now look for numeric prefix, and separate it out from
    # the rest.
    #import pdb; pdb.set_trace()
    m = _NUMERIC_PREFIX.match(result)
    if not m:
        prefix = '0.0.0'
        suffix = result
    else:
        prefix = m.groups()[0].split('.')
        prefix = [int(i) for i in prefix]
        while len(prefix) < 3:
            prefix.append(0)
        if len(prefix) == 3:
            suffix = result[m.end():]
        else:
            suffix = '.'.join([str(i) for i in prefix[3:]]) + result[m.end():]
            prefix = prefix[:3]
        prefix = '.'.join([str(i) for i in prefix])
        suffix = suffix.strip()
    if suffix:
        #import pdb; pdb.set_trace()
        # massage the suffix.
        for pat, repl in _SUFFIX_REPLACEMENTS:
            suffix = pat.sub(repl, suffix)

    if not suffix:
        result = prefix
    else:
        sep = '-' if 'dev' in suffix else '+'
        result = prefix + sep + suffix
    if not is_semver(result):
        result = None
    return result


def _suggest_normalized_version(s):
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
        _normalized_key(s)
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
        _normalized_key(rs)
    except UnsupportedVersionError:
        rs = None
    return rs

#
#   Legacy version processing (distribute-compatible)
#

_VERSION_PART = re.compile(r'([a-z]+|\d+|[\.-])', re.I)
_VERSION_REPLACE = {
    'pre':'c',
    'preview':'c',
    '-':'final-',
    'rc':'c',
    'dev':'@',
    '': None,
    '.': None,
}


def _legacy_key(s):
    def get_parts(s):
        result = []
        for p in _VERSION_PART.split(s.lower()):
            p = _VERSION_REPLACE.get(p, p)
            if p:
                if '0' <= p[:1]  <= '9':
                    p = p.zfill(8)
                else:
                    p = '*' + p
                result.append(p)
        result.append('*final')
        return result

    result = []
    for p in get_parts(s):
        if p.startswith('*'):
            if p < '*final':
                while result and result[-1] == '*final-':
                    result.pop()
            while result and result[-1] == '00000000':
                result.pop()
        result.append(p)
    return tuple(result)

class LegacyVersion(Version):
    def parse(self, s): return _legacy_key(s)

    PREREL_TAGS = set(
        ['*a', '*alpha', '*b', '*beta', '*c', '*rc', '*r', '*@', '*pre']
    )

    @property
    def is_prerelease(self):
        return any(x in self.PREREL_TAGS for x in self._parts)

class LegacyMatcher(Matcher):
    version_class = LegacyVersion

    _operators = dict(Matcher._operators)
    _operators['~='] = '_match_compatible'

    numeric_re = re.compile('^(\d+(\.\d+)*)')

    def _match_compatible(self, version, constraint, prefix):
        if version < constraint:
            return False
        m = self.numeric_re.match(str(constraint))
        if not m:
            logger.warning('Cannot compute compatible match for version %s '
                           ' and constraint %s', version, constraint)
            return True
        s = m.groups()[0]
        if '.' in s:
            s = s.rsplit('.', 1)[0]
        return _match_prefix(version, s)

#
#   Semantic versioning
#

_SEMVER_RE = re.compile(r'^(\d+)\.(\d+)\.(\d+)'
                        r'(-[a-z0-9]+(\.[a-z0-9-]+)*)?'
                        r'(\+[a-z0-9]+(\.[a-z0-9-]+)*)?$', re.I)

def is_semver(s):
    return _SEMVER_RE.match(s)

def _semantic_key(s):
    def make_tuple(s, absent):
        if s is None:
            result = (absent,)
        else:
            parts = s[1:].split('.')
            # We can't compare ints and strings on Python 3, so fudge it
            # by zero-filling numeric values so simulate a numeric comparison
            result = tuple([p.zfill(8) if p.isdigit() else p for p in parts])
        return result

    result = None
    m = is_semver(s)
    if not m:
        raise UnsupportedVersionError(s)
    groups = m.groups()
    major, minor, patch = [int(i) for i in groups[:3]]
    # choose the '|' and '*' so that versions sort correctly
    pre, build = make_tuple(groups[3], '|'), make_tuple(groups[5], '*')
    return ((major, minor, patch), pre, build)


class SemanticVersion(Version):
    def parse(self, s): return _semantic_key(s)

    @property
    def is_prerelease(self):
        return self._parts[1][0] != '|'


class SemanticMatcher(Matcher):
    version_class = SemanticVersion


class VersionScheme(object):
    def __init__(self, key, matcher, suggester=None):
        self.key = key
        self.matcher = matcher
        self.suggester = suggester

    def is_valid_version(self, s):
        try:
            self.matcher.version_class(s)
            result = True
        except UnsupportedVersionError:
            result = False
        return result

    def is_valid_matcher(self, s):
        try:
            self.matcher(s)
            result = True
        except UnsupportedVersionError:
            result = False
        return result

    def is_valid_constraint_list(self, s):
        """
        Used for processing some metadata fields
        """
        return self.is_valid_matcher('dummy_name (%s)' % s)

    def suggest(self, s):
        if self.suggester is None:
            result = None
        else:
            result = self.suggester(s)
        return result

_SCHEMES = {
    'normalized': VersionScheme(_normalized_key, NormalizedMatcher,
                                _suggest_normalized_version),
    'legacy': VersionScheme(_legacy_key, LegacyMatcher, lambda self, s: s),
    'semantic': VersionScheme(_semantic_key, SemanticMatcher,
                              _suggest_semantic_version),
}

_SCHEMES['default'] = _SCHEMES['normalized']

def get_scheme(name):
    if name not in _SCHEMES:
        raise ValueError('unknown scheme name: %r' % name)
    return _SCHEMES[name]

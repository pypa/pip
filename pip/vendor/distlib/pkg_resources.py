# This module is a shim to help migrate from the real pkg_resources
import os
import re
import sys

from pip.log import logger
from pip.vendor.distlib import database
from pip.vendor.distlib.compat import string_types
from pip.vendor.distlib.database import (DistributionPath,
                                         InstalledDistribution as DistInfoDistribution,
                                         EggInfoDistribution)
from pip.vendor.distlib.locators import locate
from pip.vendor.distlib.util import parse_requirement
from pip.vendor.distlib.version import legacy_key as parse_version

PY_MAJOR = sys.version[:3]

NON_ALPHAS = re.compile('[^A-Za-z0-9.]+')

class Requirement(object):

    state_machine = {
        #       =><
        '<' :  '--T',
        '<=':  'T-T',
        '>' :  'F+F',
        '>=':  'T+F',
        '==':  'T..',
        '!=':  'F++',
    }

    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)
        self.unsafe_name = self.name
        self.project_name = NON_ALPHAS.sub('-', self.name)
        self.specs = self.constraints or []
        if self.extras is None:
            self.extras = []
        self.extras = tuple(self.extras)
        self.index = sorted([(parse_version(v), self.state_machine[op],
                            op, v) for op, v in self.specs])

    @staticmethod
    def parse(s, replacement=True):
        r = parse_requirement(s)
        return Requirement(**r.__dict__)

    def __str__(self):
        if not self.extras:
            extras = ''
        else:
            extras = '[%s]' % ','.join(self.extras)
        cons = ','.join([''.join(s) for s in self.specs])
        return '%s%s%s' % (self.name, extras, cons)

    # copied from pkg_resources
    def __contains__(self,item):
        if isinstance(item,Distribution):
            if item.key != self.key: return False
            if self.index: item = item.parsed_version  # only get if we need it
        elif isinstance(item, string_types):
            item = parse_version(item)
        last = None
        compare = lambda a, b: (a > b) - (a < b) # -1, 0, 1
        for parsed,trans, op, ver in self.index:
            action = trans[compare(item,parsed)] # Indexing: 0, 1, -1
            if action=='F':     return False
            elif action=='T':   return True
            elif action=='+':   last = True
            elif action=='-' or last is None:   last = False
        if last is None: last = True    # no rules encountered
        return last

class Common(object):
    def as_requirement(self):
        return Requirement.parse('%s==%s' % (self.project_name, self.version))

class Distribution(EggInfoDistribution, Common):
    def __init__(self, *args, **kwargs):
        super(Distribution, self).__init__(*args, **kwargs)
        self.project_name = self.name
        self.location = os.path.dirname(self.path)

    def has_metadata(self, name):
        return name == 'PKG-INFO'

    @property
    def parsed_version(self):
        try:
            result = self._parsed_version
        except AttributeError:
            self._parsed_version = result = parse_version(self.version)
        return result

    def egg_name(self):
        s1 = self.name.replace('-', '_')
        s2 = self.version.replace('-', '_')
        return '%s-%s-py%s' % (s1, s2, PY_MAJOR)

    def requires(self, extras=()):
        reqs = EggInfoDistribution.requires.__get__(self, None)
        if 'requires' in self.__dict__:
            del self.__dict__['requires']
        result = []
        for r in reqs:
            r = parse_requirement(r)
            dist = locate(r.requirement)
            assert dist
            result.append(dist)
        debug('requires: %s -> %s' % (self, result))
        return result

class NewDistribution(DistInfoDistribution, Common):
    def __init__(self, *args, **kwargs):
        super(NewDistribution, self).__init__(*args, **kwargs)
        self.project_name = self.name
        self.location = os.path.dirname(self.path)

    def requires(self, extras=()):
        result = DistInfoDistribution.requires.__get__(self, None)
        if 'requires' in self.__dict__:
            del self.__dict__['requires']
        result = []
        for r in reqs:
            r = parse_requirement(r)
            dist = locate(r.requirement)
            assert dist
            result.append(dist)
        debug('requires: %s -> %s' % (self, result))
        return result

database.old_dist_class = Distribution
database.new_dist_class = NewDistribution

_installed_dists = DistributionPath(include_egg=True)
working_set = list(_installed_dists.get_distributions())

def get_distribution(name):
    if isinstance(name, Requirement):
        name = name.name
    return _installed_dists.get_distribution(name)

class DistributionNotFound(Exception):
    """A requested distribution was not found"""

class VersionConflict(Exception):
    """An already-installed version conflicts with the requested version"""

def find_distributions(path_item, only=False):
    dp = DistributionPath([path_item], include_egg=True)
    return list(dp.get_distributions())

# This is only here because pip's test infrastructure is unhelpful when it
# comes to logging :-(
def debug(s):
    with open('/tmp/pkg_resources-debug.txt', 'a') as f:
        f.write(s + '\n')

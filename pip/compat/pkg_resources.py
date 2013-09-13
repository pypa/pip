# This module is a shim to help migrate from the real pkg_resources
import logging
import os
import re
import sys

from pip.log import logger
from pip.vendor.distlib import database
from pip.vendor.distlib.compat import string_types
from pip.vendor.distlib.database import (DistributionPath,
                                         InstalledDistribution as DistInfoDistribution,
                                         EggInfoDistribution)
from pip.vendor.distlib.markers import interpret
from pip.vendor.distlib.util import parse_requirement
from pip.vendor.distlib.version import _legacy_key as parse_version

logger = logging.getLogger(__name__)

PY_MAJOR = sys.version[:3]

NON_ALPHAS = re.compile('[^A-Za-z0-9.]+')

def init_logging():
    # Since we're minimising changes to pip, update logging here
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        fn = os.path.expanduser('~/pkg_resources.log')
        h = logging.FileHandler(fn, 'a')
        f = logging.Formatter('%(lineno)3d %(funcName)-10s %(message)s')
        h.setFormatter(f)
        logger.addHandler(h)

def log_files(path):
    logger.debug('log of files under %s', path)
    for root, dirs, files in os.walk(path):
        dirs[:] = sorted(dirs)
        for fn in sorted(files):
            p = os.path.join(root, fn)
            logger.debug('  %s', p)


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
        init_logging()
        logger.debug('%s %s', args, kwargs)
        self.__dict__.update(kwargs)
        self.unsafe_name = self.name
        self.project_name = NON_ALPHAS.sub('-', self.name)
        self.key = self.project_name.lower()
        self.specs = self.constraints or []
        if self.extras is None:
            self.extras = []
        self.extras = tuple(self.extras)
        self.index = sorted([(parse_version(v), self.state_machine[op],
                            op, v) for op, v in self.specs])

    @staticmethod
    def parse(s, replacement=True):
        r = parse_requirement(s)
        logger.debug('%s -> %s', s, r.__dict__)
        return Requirement(**r.__dict__)

    def __str__(self):
        if not self.extras:
            extras = ''
        else:
            extras = '[%s]' % ','.join(self.extras)
        cons = ','.join([''.join(s) for s in self.specs])
        return '%s%s%s' % (self.name, extras, cons)

    # copied from pkg_resources
    def __contains__(self, item):
        init_logging()
        if isinstance(item,Distribution):
            if item.key != self.key:
                logger.debug('%s %s', item.key, self.key)
                return False
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
        logger.debug('%s %s', item, last)
        return last

def parse_requirements(slist):
    if isinstance(slist, string_types):
        slist = [slist]
    return [Requirement.parse(s) for s in slist]

class Common(object):
    def as_requirement(self):
        init_logging()
        result = Requirement.parse('%s==%s' % (self.project_name, self.version))
        logger.debug('%s', result)
        return result

class Distribution(EggInfoDistribution, Common):
    def __init__(self, *args, **kwargs):
        project_name = kwargs.pop('project_name', None)
        version = kwargs.pop('version', None)
        # if args is None, the code is being called for test mocking only,
        # so we take a different path
        if args:
            super(Distribution, self).__init__(*args, **kwargs)
        if project_name is None:
            project_name = self.name
        if version is not None:
            self.version = version
        self.project_name = project_name
        # if args is None, the code is being called for test mocking only,
        # so we take a different path
        if not args:
            self.key = self.project_name.lower()
            return
        self.location = self.path
        if not self.location.endswith('.egg'):
            self.location = os.path.dirname(self.location)

    def _metadata_path(self, name):
        parts = name.split('/')
        root = self.path
        if root.endswith('.egg'):
            path = os.path.join(root, 'EGG-INFO')
            if os.path.isdir(path):
                root = path
        result = os.path.join(root, *parts)
        logger.debug('%s %s -> %s', self.path, name, result)
        return result

    def has_metadata(self, name):
        path = self._metadata_path(name)
        result = os.path.exists(path)
        logger.debug('%s %s -> %s', self.path, name, result)
        return result

    def get_metadata(self, name):
        path = self._metadata_path(name)
        assert os.path.exists(path)
        with open(path, 'rb') as f:
            result = f.read().decode('utf-8')
        return result

    def get_metadata_lines(self, name):
        lines = self.get_metadata(name).splitlines()
        for line in lines:
            line = line.strip()
            if line and line[0] != '#':
                yield line

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

    def requires(self, extras=None):
        init_logging()
        try:
            reqs = EggInfoDistribution.run_requires.__get__(self, None)
            logger.debug('%s', reqs)
            if 'requires' in self.__dict__:
                del self.__dict__['requires']
            result = []
            for r in reqs:
                d = parse_requirement(r)
                logger.debug('%s -> %s', r, d.__dict__)
                result.append(Requirement(**d.__dict__))
            logger.warning('requires: %s -> %s', self, result)
            return result
        except:
            logger.exception('failed')
            raise


class NewDistribution(DistInfoDistribution, Common):
    def __init__(self, *args, **kwargs):
        super(NewDistribution, self).__init__(*args, **kwargs)
        self.project_name = self.name
        self.location = os.path.dirname(self.path)

    def requires(self, extras=None):
        init_logging()
        try:
            reqs = set(self.run_requires)
            result = []
            logger.debug('requires(%s): %s -> %s', extras, self, reqs)
            marked = []
            for r in list(reqs):
                if ';' in r:
                    reqs.remove(r)
                    marked.append(r.split(';', 1))
            if marked:
                if extras:
                    e = extras + (None,)
                else:
                    e = (None,)
                for extra in e:
                    context = {'extra': extra}
                    for r, marker in marked:
                        if interpret(marker, context):
                            reqs.add(r)
            for r in reqs:
                d = parse_requirement(r)
                logger.debug('%s -> %s', r, d.__dict__)
                result.append(Requirement(**d.__dict__))
            logger.debug('requires(%s): %s -> %s', extras, self, result)
            return result
        except:
            logger.exception('failed')
            raise


database.old_dist_class = Distribution
database.new_dist_class = NewDistribution

_installed_dists = DistributionPath(include_egg=True)
working_set = list(_installed_dists.get_distributions())

class DistributionNotFound(Exception):
    """A requested distribution was not found"""

class VersionConflict(Exception):
    """An already-installed version conflicts with the requested version"""

def get_distribution(req_or_name):
    init_logging()
    if isinstance(req_or_name, Requirement):
        name = req_or_name.name
    else:
        name = req_or_name
    result = _installed_dists.get_distribution(name)
    logger.debug('%s -> %s', name, result)
    if result is None:
        raise DistributionNotFound(name)
    if isinstance(req_or_name, Requirement) and result not in req_or_name:
        raise VersionConflict(result, req_or_name)
    return result

def find_distributions(path_item, only=False):
    init_logging()
    logger.debug('%s (%s)', path_item, only)
    try:
        dp = DistributionPath([path_item], include_egg=True)
        result = list(dp.get_distributions())
    except:
        logger.exception('failed')
        raise
    logger.debug('%s', result)
    return result

# This is only here because pip's test infrastructure is unhelpful when it
# comes to logging :-(
def debug(s):
    with open('/tmp/pkg_resources-debug.txt', 'a') as f:
        f.write(s + '\n')

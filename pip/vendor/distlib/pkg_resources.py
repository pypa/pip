# This module is a shim to help migrate from the real pkg_resources
import os

from pip.log import logger
from pip.vendor.distlib import database
from pip.vendor.distlib.database import DistributionPath, EggInfoDistribution
from pip.vendor.distlib.util import parse_requirement
from pip.vendor.distlib.version import legacy_key as parse_version
from pip.vendor.distlib.wheel import PYVER, ARCH

class Requirement(object):
    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)
        self.specs = self.constraints

    @staticmethod
    def parse(s, replacement=True):
        r = parse_requirement(s)
        return Requirement(**r.__dict__)

    def __str__(self):
        if not self.extras:
            extras = ''
        else:
            extras = '[%s]' % ','.join(self.extras)
        cons = ','.join([''.join(s) for s in self.constraints])
        return '%s%s%s' % (self.name, extras, cons)

class Distribution(EggInfoDistribution):
    def __init__(self, *args, **kwargs):
        super(Distribution, self).__init__(*args, **kwargs)
        self.project_name = self.name
        self.location = os.path.dirname(self.path)

    def as_requirement(self):
        return Requirement.parse('%s==%s' % (self.project_name, self.version))

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
        return '%s-%s-%s-%s' % (s1, s2, PYVER, ARCH)

database.old_dist_class = Distribution

_installed_dists = DistributionPath(include_egg=True)
working_set = list(_installed_dists.get_distributions())

get_distribution = _installed_dists.get_distribution

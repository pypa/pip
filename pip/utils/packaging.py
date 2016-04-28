from __future__ import absolute_import

import logging
import sys

from pip._vendor import pkg_resources


logger = logging.getLogger(__name__)


def get_metadata(dist):
    if (isinstance(dist, pkg_resources.DistInfoDistribution) and
            dist.has_metadata('METADATA')):
        return dist.get_metadata('METADATA')
    elif dist.has_metadata('PKG-INFO'):
        return dist.get_metadata('PKG-INFO')


def get_classifiers(metadata):
    # It looks like FeedParser can not deal with repeated headers
    classifiers = []
    for line in metadata.splitlines():
        if not line:
            break
        # Classifier: License :: OSI Approved :: MIT License
        if line.startswith('Classifier: '):
            classifiers.append(line[len('Classifier: '):])
    return classifiers


def check_python_classifiers(dist):
    classifiers = get_classifiers(get_metadata(dist))
    # Catch:
    # Programming Language :: Python :: 3.6
    # but not:
    # Programming Language :: Python :: Implementation :: PyPy
    # TODO: deal with "Programming Language :: Python :: 2 :: Only"
    supported_versions = [
        # 34 == len('Programming Language :: Python :: ')
        classifier[34:] for classifier in classifiers
        if (
            classifier.startswith('Programming Language :: Python :: ') and
            '::' not in classifier[34:] and
            classifier[34:35].isdigit()
        )
    ]
    if not supported_versions:
        # The package provides no information
        return
    major_versions, minor_versions = [], []
    for version in supported_versions:
        if '.' in version:
            minor_versions.append(tuple(map(int, version.split('.'))))
        else:
            major_versions.append(int(version))
    if major_versions and sys.version_info[0] not in major_versions:
        logger.warning(
            "%s is advertised as supporting %s but not Python %s",
            dist.project_name,
            ", ".join(["Python %s" % (version,)
                       for version in major_versions]),
            sys.version_info[0])
    if (minor_versions and sys.version_info[0:2] not in minor_versions and
            sys.version_info[0:2] < max(minor_versions)):
        logger.warning(
            "%s is advertised as supporting %s but not Python %s",
            dist.project_name,
            ", ".join(["Python %s" % ('.'.join(map(str, version)),)
                       for version in minor_versions]),
            '.'.join(map(str, sys.version_info[0:2])),)

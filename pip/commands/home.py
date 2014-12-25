from __future__ import absolute_import

from email.parser import FeedParser
import logging
import os
import webbrowser

from pip.basecommand import Command
from pip.status_codes import SUCCESS, ERROR
from pip._vendor import pkg_resources


logger = logging.getLogger(__name__)


class HomeCommand(Command):
    """Open package homepage in default browser."""
    name = 'home'
    usage = """
      %prog [options] <package> ..."""
    summary = 'Open package homepage in default browser.'

    def __init__(self, *args, **kw):
        super(HomeCommand, self).__init__(*args, **kw)

    def run(self, options, args):
        if not args:
            logger.warning('ERROR: Please provide a package name or names.')
            return ERROR
        query = args

        results = search_packages_info(query)
        if not open_homepages_for_results(results):
            return ERROR
        return SUCCESS


def search_packages_info(query):
    """
    Gather details from installed distributions. Print distribution name,
    version, location, and installed files. Installed files requires a
    pip generated 'installed-files.txt' in the distributions '.egg-info'
    directory.
    """
    installed = dict(
        [(p.project_name.lower(), p) for p in pkg_resources.working_set])
    query_names = [name.lower() for name in query]
    for dist in [installed[pkg] for pkg in query_names if pkg in installed]:
        package = {
            'name': dist.project_name,
            'version': dist.version,
            'location': dist.location,
            'requires': [dep.project_name for dep in dist.requires()],
        }
        metadata = None
        if isinstance(dist, pkg_resources.DistInfoDistribution):
            # RECORDs should be part of .dist-info metadatas
            if dist.has_metadata('RECORD'):
                lines = dist.get_metadata_lines('RECORD')
                paths = [l.split(',')[0] for l in lines]
                paths = [os.path.join(dist.location, p) for p in paths]

            if dist.has_metadata('METADATA'):
                metadata = dist.get_metadata('METADATA')
        else:
            # Otherwise use pip's log for .egg-info's
            if dist.has_metadata('installed-files.txt'):
                paths = dist.get_metadata_lines('installed-files.txt')
                paths = [os.path.join(dist.egg_info, p) for p in paths]
            if dist.has_metadata('entry_points.txt'):
                entry_points = dist.get_metadata_lines('entry_points.txt')
                package['entry_points'] = entry_points

            if dist.has_metadata('PKG-INFO'):
                metadata = dist.get_metadata('PKG-INFO')

        # @todo: Should pkg_resources.Distribution have a
        # `get_pkg_info` method?
        feed_parser = FeedParser()
        feed_parser.feed(metadata)
        pkg_info_dict = feed_parser.close()
        for key in ('metadata-version', 'summary',
                    'home-page', 'author', 'author-email', 'license'):
            package[key] = pkg_info_dict.get(key)

        yield package


def open_homepages_for_results(distributions):
    """
    Open the home-pages for the installed distributions found.
    """
    distributions_found = False
    for dist in distributions:
        distributions_found = True
        logger.info("Opening %s's homepage in browser" % dist['name'])
        logger.info("\t%s" % dist['home-page'])
        webbrowser.open_new_tab(dist['home-page'])
    return distributions_found

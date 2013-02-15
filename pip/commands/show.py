import os
import textwrap
import pkg_resources
import pip.download

from pip.log import logger
from pip.cmdoptions import index_group, make_option_group, index_url
from pip.basecommand import Command
from pip.backwardcompat import xmlrpclib
from pip.util import uniqify
from pip.status_codes import NO_MATCHES_FOUND, SUCCESS


class ShowCommand(Command):
    name = 'show'
    usage = """
      %prog [options] <package> ..."""
    summary = 'Show information about available packages.'
    description = """
      Show information about one or more installed or remote packages."""

    def __init__(self, *args, **kw):
        super(ShowCommand, self).__init__(*args, **kw)
        self.cmd_opts.add_option(
            '-f', '--files',
            dest='files',
            action='store_true',
            default=False,
            help='Show the full list of installed files for each package.')

        self.cmd_opts.add_option(
            '--pypi',
            dest='use_pypi',
            action='store_true',
            help='Query package information from PyPi.')

        index_url.default = 'http://pypi.python.org/pypi'
        index_group['options'] = [index_url]
        index_opts = make_option_group(index_group, self.parser)

        self.parser.insert_option_group(0, self.cmd_opts)
        self.parser.insert_option_group(1, index_opts)

    def run(self, options, args):
        if not args:
            logger.warn('ERROR: Please provide one or more package names.')
            return

        names = uniqify(args, key=str.lower)  # do not process duplicates

        if options.use_pypi:
            results = search_package_info_pypi(names, options.index_url)
            results = list(results)
            if not results:
                return NO_MATCHES_FOUND
            print_results_pypi(results)
        else:
            results = list(search_packages_info(names))
            if not results:
                return NO_MATCHES_FOUND
            print_results(results, options.files)

        return SUCCESS


def search_package_info_pypi(names, index_url):
    idx = xmlrpclib.ServerProxy(index_url, pip.download.xmlrpclib_transport)

    packages = []
    for name in names:
        res = idx.search({'name' : name})

        for i in res:
            if i['name'].lower() == name.lower():
                packages.append((i['name'], i['version']))

    for name, version in packages:
        data = idx.release_data(name, version)
        info = {
            'name': name,
            'version': version,
            'homepage': data['home_page'],
            'url': data['package_url'],
            'author': data['author'],
            'summary': data['summary'],
            'description': data['description'], }

        yield info


def print_results_pypi(info):
    fmt = '''\
    ---
    Name: %(name)s
    Version: %(version)s
    Summary: %(summary)s
    Author: %(author)s
    Url: %(url)s
    Homepage: %(homepage)s\
    '''

    for item in info:
        logger.notify(textwrap.dedent(fmt) % item)


def search_packages_info(names):
    """
    Gather details from installed distributions. Print distribution name,
    version, location, and installed files. Installed files requires a
    pip generated 'installed-files.txt' in the distributions '.egg-info'
    directory.
    """
    installed_packages = dict(
        [(p.project_name.lower(), p) for p in pkg_resources.working_set])
    for name in names:
        normalized_name = name.lower()
        if normalized_name in installed_packages:
            dist = installed_packages[normalized_name]
            package = {
                'name': dist.project_name,
                'version': dist.version,
                'location': dist.location,
                'requires': [dep.project_name for dep in dist.requires()],
            }
            filelist = os.path.join(dist.location,
                                    dist.egg_name() + '.egg-info',
                                    'installed-files.txt')
            if os.path.isfile(filelist):
                package['files'] = filelist
            yield package


def print_results(distributions, list_all_files):
    """
    Print the informations from installed distributions found.
    """
    for dist in distributions:
        logger.notify("---")
        logger.notify("Name: %s" % dist['name'])
        logger.notify("Version: %s" % dist['version'])
        logger.notify("Location: %s" % dist['location'])
        logger.notify("Requires: %s" % ', '.join(dist['requires']))
        if list_all_files:
            logger.notify("Files:")
            if 'files' in dist:
                for line in open(dist['files']):
                    logger.notify("  %s" % line.strip())
            else:
                logger.notify("Cannot locate installed-files.txt")

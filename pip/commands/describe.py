import sys
import textwrap
from pip.basecommand import Command, SUCCESS
from pip.util import get_terminal_size
from pip.log import logger
from pip.version_handling import highest_version
import pip.download
from pip.backwardcompat import xmlrpclib, reduce, cmp
from pip.exceptions import CommandError
from pip.status_codes import NO_MATCHES_FOUND

class DescribeCommand(Command):
    name = 'describe'
    usage = '%prog PACKAGE'
    summary = 'Get package description from PyPI'
  
    def __init__(self):
        super(DescribeCommand, self).__init__()
        self.parser.add_option(
            '--index',
            dest='index',
            metavar='URL',
            default='http://pypi.python.org/pypi',
            help='Base URL of Python Package Index (default %default)')

        self.parser.add_option(
            '--extended-info',
            dest='extended_info',
            action='store_true',
            help='show extended package information (author, homepage, version, long description')


    def run(self, options, args):
        if not args:
            raise CommandError('Missing required argument (search query).')
        index_url = options.index
        self._pypi = xmlrpclib.ServerProxy(index_url, pip.download.xmlrpclib_transport)

        packages_of_interest = []
        for arg in args:
            name, version = self.resolve_package(arg)
            if name == NO_MATCHES_FOUND:
                logger.info('could not find {} on index'.format(arg))
            else:
                packages_of_interest.append((name, version))
        terminal_width = None
        if sys.stdout.isatty():
            terminal_width = get_terminal_size()[0]
        enriched_info = self.update_package_info(packages_of_interest)
        self.print_description(enriched_info, terminal_width, options)
        return SUCCESS

    def resolve_package(self, query):
        packages = self._pypi.list_packages()
        package = [x for x in packages if x.lower() == query.lower()]
        if not package:
            return NO_MATCHES_FOUND, None
        package = package[0]
        version = highest_version(self._pypi.package_releases(package))
        return package, version

    def update_package_info(self, packages):
        info = []
        for package,version in packages:
            d = self._pypi.release_data(package, version)
            data = {
                    'name': package,
                    'version' : version,
                    'homepage' : d['home_page'],
                    'url': d['package_url'],
                    'author': d['author'],
                    'summary': d['summary'],
                    'description': d['description'],
                   }
            info.append(data)
        return info
            
    def print_description(self, packages, terminal_width, options):
        for package in packages:
            self.reformat(package, indent=10, width=terminal_width)
            print """
name    : {name}
version : {version}
summary : {summary}
url     : {url}
author  : {author}
homepage: {homepage}
""".format(**package)
            if options.extended_info:
                print "details : "+package['description']

    def reformat(self, package, indent, width):
        for key, value in package.items():
            reformatted = textwrap.wrap(value.strip(), width-indent)
            package[key] = (reformatted[0]+"\n"+ "\n".join([" "*indent+x for x in reformatted[1:]])).strip()

DescribeCommand()

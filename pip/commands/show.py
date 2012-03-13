import os
import sys
import tempfile
import shutil
import json
import requests
from pip.req import InstallRequirement, RequirementSet
from pip.req import parse_requirements
from pip.log import logger
from pip.locations import build_prefix, src_prefix
from pip.basecommand import Command
from pip.index import PackageFinder
from pip.exceptions import InstallationError, CommandError


class ShowCommand(Command):
    name = 'show'
    usage = '%prog [OPTIONS] PACKAGE_NAMES...'
    summary = 'show package info'
    bundle = False

    def __init__(self):
        super(ShowCommand, self).__init__()
        self.parser.add_option(
            '-i', '--index-url', '--pypi-url',
            dest='index_url',
            metavar='URL',
            default='http://pypi.python.org/simple/',
            help='Base URL of Python Package Index (default %default)')
        self.parser.add_option(
            '--extra-index-url',
            dest='extra_index_urls',
            metavar='URL',
            action='append',
            default=[],
            help='Extra URLs of package indexes to use in addition to --index-url')
        self.parser.add_option(
            '-M', '--use-mirrors',
            dest='use_mirrors',
            action='store_true',
            default=False,
            help='Use the PyPI mirrors as a fallback in case the main index is down.')
        self.parser.add_option(
            '--mirrors',
            dest='mirrors',
            metavar='URL',
            action='append',
            default=[],
            help='Specific mirror URLs to query when --use-mirrors is used')

        self.parser.add_option(
            '--download-cache',
            dest='download_cache',
            metavar='DIR',
            default=None,
            help='Cache downloaded packages in DIR')

    def _build_package_finder(self, options, index_urls):
        """
        Create a package finder appropriate to this install command.
        This method is meant to be overridden by subclasses, not
        called directly.
        """
        return PackageFinder(find_links=[],
                             index_urls=index_urls,
                             use_mirrors=options.use_mirrors,
                             mirrors=options.mirrors)

    def run(self, options, args):
        index_urls = [options.index_url] + options.extra_index_urls
        finder = self._build_package_finder(options, index_urls)

        requirement_set = RequirementSet(
            build_dir="",
            src_dir="",
            download_dir="",
            download_cache="",
            upgrade=True,
            ignore_installed=False,
            ignore_dependencies=False,
            force_reinstall=False)
        packets = [InstallRequirement.from_line(name, None) for name in args]
        links = [finder.find_requirement(packet, False) for packet in packets]
        packet_info = [json.loads(requests.get('http://pypi.python.org/pypi/{}/json'.format(link.filename.split("-")[0])).content) for link in links]

        for p in packet_info:
            for info in 'name summary author'.split():
                print '{}: {}'.format(info, p['info'][info])
            print
        return


ShowCommand()

"""
pip command options
"""
import os
from optparse import make_option
from pip.locations import build_prefix, src_prefix

REQUIREMENTS = make_option(
            '-r', '--requirement',
            dest='requirements',
            action='append',
            default=[],
            metavar='FILENAME',
            help='Install all the packages listed in the given requirements file. '
            'This option can be used multiple times.')

FIND_LINKS = make_option(
            '-f', '--find-links',
            dest='find_links',
            action='append',
            default=[],
            metavar='URL',
            help='URL to look for packages at')
INDEX_URL = make_option(
            '-i', '--index-url', '--pypi-url',
            dest='index_url',
            metavar='URL',
            default='http://pypi.python.org/simple/',
            help='Base URL of Python Package Index (default %default)')

EXTRA_INDEX_URLS = make_option(
            '--extra-index-url',
            dest='extra_index_urls',
            metavar='URL',
            action='append',
            default=[],
            help='Extra URLs of package indexes to use in addition to --index-url')

NO_INDEX = make_option(
            '--no-index',
            dest='no_index',
            action='store_true',
            default=False,
            help='Ignore package index (only looking at --find-links URLs instead)')

USE_MIRRORS = make_option(
            '-M', '--use-mirrors',
            dest='use_mirrors',
            action='store_true',
            default=False,
            help='Use the PyPI mirrors as a fallback in case the main index is down.')

MIRRORS = make_option(
            '--mirrors',
            dest='mirrors',
            metavar='URL',
            action='append',
            default=[],
            help='Specific mirror URLs to query when --use-mirrors is used')

DOWNLOAD_CACHE = make_option(
            '--download-cache',
            dest='download_cache',
            metavar='DIR',
            default=None,
            help='Cache downloaded packages in DIR')

BUILD_DIR = make_option(
            '-b', '--build', '--build-dir', '--build-directory',
            dest='build_dir',
            metavar='DIR',
            default=build_prefix,
            help='Unpack packages into DIR (default %default) and build from there')

INSTALL_OPTIONS = make_option(
            '--install-option',
            dest='install_options',
            action='append',
            help="Extra arguments to be supplied to the setup.py install "
            "command (use like --install-option=\"--install-scripts=/usr/local/bin\"). "
            "Use multiple --install-option options to pass multiple options to setup.py install. "
            "If you are using an option with a directory path, be sure to use absolute path.")

GLOBAL_OPTIONS = make_option(
            '--global-option',
            dest='global_options',
            action='append',
            help="Extra global options to be supplied to the setup.py "
            "call before the install command")

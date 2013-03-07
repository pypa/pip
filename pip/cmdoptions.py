"""shared options and groups"""
from optparse import make_option, OptionGroup


def make_option_group(group, parser):
    """
    Return an OptionGroup object
    group  -- assumed to be dict with 'name' and 'options' keys
    parser -- an optparse Parser
    """
    option_group = OptionGroup(parser, group['name'])
    for option in group['options']:
        option_group.add_option(option)
    return option_group

###########
# options #
###########

index_url = make_option(
    '-i', '--index-url', '--pypi-url',
    dest='index_url',
    metavar='URL',
    default='https://pypi.python.org/simple/',
    help='Base URL of Python Package Index (default %default).')

extra_index_url = make_option(
    '--extra-index-url',
    dest='extra_index_urls',
    metavar='URL',
    action='append',
    default=[],
    help='Extra URLs of package indexes to use in addition to --index-url.')

no_index = make_option(
    '--no-index',
    dest='no_index',
    action='store_true',
    default=False,
    help='Ignore package index (only looking at --find-links URLs instead).')

find_links =  make_option(
    '-f', '--find-links',
    dest='find_links',
    action='append',
    default=[],
    metavar='url',
    help="If a url or path to an html file, then parse for links to archives. If a local path or file:// url that's a directory, then look for archives in the directory listing.")

use_mirrors = make_option(
    '-M', '--use-mirrors',
    dest='use_mirrors',
    action='store_true',
    default=False,
    help='Use the PyPI mirrors as a fallback in case the main index is down.')

mirrors = make_option(
    '--mirrors',
    dest='mirrors',
    metavar='URL',
    action='append',
    default=[],
    help='Specific mirror URLs to query when --use-mirrors is used.')


##########
# groups #
##########

index_group = {
    'name': 'Package Index Options',
    'options': [
        index_url,
        extra_index_url,
        no_index,
        find_links,
        use_mirrors,
        mirrors
        ]
    }

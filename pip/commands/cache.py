from __future__ import absolute_import

import datetime
import logging
import os.path

from collections import namedtuple

from pip._vendor.packaging import version
from pip._vendor import pkg_resources
from pip.basecommand import Command, SUCCESS
from pip.exceptions import CommandError, InvalidWheelFilename
from pip.utils import canonicalize_name
from pip.wheel import Wheel


logger = logging.getLogger(__name__)


Record = namedtuple(
    'Record',
    ('wheel', 'link_path', 'link', 'last_access_time', 'possible_creation_time')
)


class CacheCommand(Command):
    """Utility command to inspect and deal with the cache (wheels)"""
    name = 'cache'
    usage = """
      %prog [options] <query>"""
    summary = 'Cache utility'

    def __init__(self, *args, **kw):
        super(CacheCommand, self).__init__(*args, **kw)

        self.cmd_opts.add_option(
            '--all',
            dest='all_wheels',
            action='store_true',
            default=False,
            help='Consider all wheels in cache')
        self.cmd_opts.add_option(
            '--remove',
            dest='remove',
            action='store_true',
            default=False,
            help='Remove found cached wheels')
        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options, args):
        wheels_cache_dir = os.path.join(options.cache_dir, 'wheels')
        reqs = map(pkg_resources.Requirement.parse, args)

        data = {
            'links': {},
            'wheel_filenames': [],
        }
        os.path.walk(wheels_cache_dir, collect_infos, data)

        if not options.all_wheels:
            if not args:
                log_basic_stats(data)
                return SUCCESS
        elif args:
            raise CommandError('You cannot pass args with --all option')

        results = []
        for record in iter_record(data):
            if not options.all_wheels:
                # Filter on args
                for req in reqs:
                    if canonicalize_name(record.wheel.name) != canonicalize_name(req.project_name):
                        continue
                    if version.parse(record.wheel.version) not in req.specifier:
                        continue
                    # record matches req !
                    break
                else:
                    # Ignore this record
                    continue

            results.append(record)
        if not options.remove:
            log_results(results)
        else:
            # TODO: ask to delete found records
            pass

        return SUCCESS

sort_key = lambda record: (record.wheel.name, record.wheel.version, record.link_path)


def iter_record(data):
    for wheel_filename in data['wheel_filenames']:
        name = os.path.basename(wheel_filename)
        link_path = os.path.dirname(wheel_filename)
        link = data['links'][link_path]

        try:
            wheel = Wheel(name)
        except InvalidWheelFilename:
            logger.warning('Invalid wheel name for: %s', wheel_filename)
            continue
        stat = os.stat(wheel_filename)
        last_access_time = datetime.datetime.fromtimestamp(stat.st_atime)  # access time
        possible_creation_time = datetime.datetime.fromtimestamp(stat.st_mtime)  # Possible creation time ?
        yield Record(wheel, link_path, link, last_access_time, possible_creation_time)


def collect_infos(data, top_dir, names):
    """Collect link/wheel files into data."""
    link = None
    wheel_files = []
    for name in names:
        if name == 'link':
            with open(os.path.join(top_dir, 'link')) as fl:
                link = fl.read()
        elif name.endswith('.whl'):
            # parse name to get project/version/etc
            wheel_files.append(
                os.path.join(top_dir, name)
            )
    if wheel_files or link is not None:
        data['links'][top_dir] = link
        data['wheel_filenames'].extend(wheel_files)


def log_basic_stats(data):
    link_nb = len(data['links'])
    wheel_nb = len(data['wheel_filenames'])
    logger.info('Found %s wheels from %s links', wheel_nb, link_nb)


def log_results(results):
    results.sort(key=sort_key)
    current_name = None
    for record in results:
        if record.wheel.name != current_name:
            current_name = record.wheel.name
            logger.info(current_name)
        logger.info('    - %s %s', record.link_path, record.wheel.filename)
        if record.link:
            logger.info('      Original link: %s', record.link)
        logger.info('      Last used: %s', record.last_access_time)

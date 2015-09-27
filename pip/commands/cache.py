from __future__ import absolute_import

import datetime
import logging
import os.path
import functools

from collections import namedtuple

from pip._vendor.packaging import version
from pip._vendor import pkg_resources
from pip.basecommand import Command, SUCCESS
from pip.exceptions import CommandError, InvalidWheelFilename
from pip.utils import ask, canonicalize_name
from pip.wheel import Wheel


logger = logging.getLogger(__name__)


Record = namedtuple(
    'Record',
    ('wheel', 'link_path', 'link', 'size', 'last_access_time', 'possible_creation_time')
)


class WheelCacheRecord(object):

    def __init__(self, file_path):
        self.file_path = file_path
        # get link (with caching ?)
        # get size, last_access/creation, etc
        self.name = os.path.basename(file_path)
        self.link_path = os.path.dirname(file_path)
        self.link = self.get_link_origin()

        try:
            self.wheel = Wheel(self.name)
        except InvalidWheelFilename:
            logger.warning('Invalid wheel name for: %s', file_path)
            self.wheel = None

        self.project_name = canonicalize_name(self.wheel.name) if self.wheel else None
        self.version = version.parse(self.wheel.version) if self.wheel else None
        stat = os.stat(file_path)
        self.size = stat.st_size
        self.last_access_time = datetime.datetime.fromtimestamp(stat.st_atime)  # access time
        self.possible_creation_time = datetime.datetime.fromtimestamp(stat.st_mtime)  # Possible creation time ?

    def get_link_origin(self):
        # This could be cached
        link_origin_path = os.path.join(self.link_path, 'link')
        if os.path.exists(link_origin_path):
            with open(link_origin_path) as fl:
                self.link_origin = fl.read()
        else:
            self.link_origin = None

    def match_reqs(self, reqs):
        for req in reqs:
            if self.project_name != canonicalize_name(req.project_name):
                continue
            if self.version not in req.specifier:
                continue
            return True
        else:
            return False

    def remove(self):
        os.remove(self.file_path)


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
        self.cmd_opts.add_option(
            '-y', '--yes',
            dest='yes',
            action='store_true',
            help="Don't ask for confirmation of deletions.")
        self.cmd_opts.add_option(
            '--not-accessed-since',
            dest='not_accessed_since',
            type=int,
            default=None,
            help='Select all wheels not accessed since X days')

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options, args):
        reqs = map(pkg_resources.Requirement.parse, args)

        records = []
        for dirpath, dirnames, filenames in os.walk(
                os.path.join(options.cache_dir, 'wheels')):

            # Should we filter on the paths and ignore those that
            # does not conform with the xx/yy/zz/hhhh...hhhh/ patterns ?
            for filename in filenames:
                if filename.endswith('.whl'):
                    records.append(
                        WheelCacheRecord(os.path.join(dirpath, filename)))

        if options.all_wheels and args:
            raise CommandError('You cannot pass args with --all option')

        if options.not_accessed_since:
            # check if possible to have:
            # --not-accessed-since and --not-accessed-since-days
            min_last_access = datetime.datetime.now() - datetime.timedelta(days=options.not_accessed_since)
            records = filter(lambda r: r.last_access_time < min_last_access, records)

        if reqs:
            records = filter(lambda r: r.match_reqs(reqs), records)

        if options.remove:
            wheel_paths = [record.file_path for record in records]
            logger.info('Deleting:\n- %s' % '\n- '.join(wheel_paths))
            if options.yes:
                response = 'yes'
            else:
                response = ask('Proceed (yes/no)? ', ('yes', 'no'))
            if response == 'yes':
                for record in records:
                    record.remove()
            # Should we try to cleanup empty dirs and link files ?
        else:
            if not args and not options.all_wheels:
                logger.info('Found %s cached wheels', len(records))
            else:
                log_results(records)

        return SUCCESS

sort_key = lambda record: (record.wheel.name, record.wheel.version, record.link_path)


def iter_record(wheel_filenames, link_path_infos):
    for wheel_filename in wheel_filenames:
        name = os.path.basename(wheel_filename)
        link_path = os.path.dirname(wheel_filename)
        link = link_path_infos[link_path]

        try:
            wheel = Wheel(name)
        except InvalidWheelFilename:
            logger.warning('Invalid wheel name for: %s', wheel_filename)
            continue
        stat = os.stat(wheel_filename)
        size = stat.st_size
        last_access_time = datetime.datetime.fromtimestamp(stat.st_atime)  # access time
        possible_creation_time = datetime.datetime.fromtimestamp(stat.st_mtime)  # Possible creation time ?
        yield Record(wheel, link_path, link, size, last_access_time, possible_creation_time)


def log_results(records):
    records.sort(key=sort_key)
    current_name = None
    for record in records:
        if record.wheel.name != current_name:
            current_name = record.wheel.name
            logger.info(current_name)
        logger.info('    - %s', record.wheel.filename)
        logger.info('      Path: %s', record.link_path)
        if record.link:
            logger.info('      Original link: %s', record.link)
        logger.info(
            '      Size: %s - Last used: %s',
            human_readable_size(record.size), record.last_access_time)


def human_readable_size(nb_bytes):
    unit_formatter = ('%db', '%.1fkb', '%.1fMb', '%.1fGb', '%.1fTb')
    unit_index = 0
    while nb_bytes > 1024 and unit_index < 4:
        nb_bytes = nb_bytes / 1024.0
        unit_index += 1
    return unit_formatter[unit_index] % (nb_bytes,)

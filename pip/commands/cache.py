from __future__ import absolute_import

from datetime import datetime, timedelta
import logging
import os.path

from pip._vendor.packaging import version
from pip._vendor import pkg_resources
from pip.basecommand import Command, SUCCESS
from pip.exceptions import CommandError, InvalidWheelFilename
from pip.utils import ask, cached_property, canonicalize_name
from pip.wheel import Wheel


logger = logging.getLogger(__name__)


class WheelCacheRecord(object):

    def __init__(self, file_path):
        self.file_path = file_path
        # get link (with caching ?)
        # get size, last_access/creation, etc
        self.name = os.path.basename(file_path)
        self.link_path = os.path.dirname(file_path)

        try:
            self.wheel = Wheel(self.name)
        except InvalidWheelFilename:
            logger.warning('Invalid wheel name for: %s', file_path)
            self.wheel = None

        if self.wheel:
            self.project_name = canonicalize_name(self.wheel.name)
            self.version = version.parse(self.wheel.version)
        else:
            self.project_name = None
            self.version = None

        stat = os.stat(file_path)
        self.size = stat.st_size
        self.last_access_time = datetime.fromtimestamp(stat.st_atime)
        self.possible_creation_time = datetime.fromtimestamp(stat.st_mtime)

    @cached_property
    def link_origin(self):
        link_origin_path = os.path.join(self.link_path, 'link')
        if os.path.exists(link_origin_path):
            with open(link_origin_path) as fl:
                return fl.read()
        else:
            return None

    def match_reqs(self, reqs):
        return any(
            self.project_name == canonicalize_name(req.project_name) and
            self.version in req.specifier
            for req in reqs)

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
            min_last_access = datetime.now() - timedelta(
                days=options.not_accessed_since)
            records = filter(
                lambda r: r.last_access_time < min_last_access,
                records)

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


def sort_key(record):
    return (record.wheel.name, record.wheel.version, record.link_path)


def log_results(records):
    records.sort(key=sort_key)
    current_name = None
    for record in records:
        if record.wheel.name != current_name:
            current_name = record.wheel.name
            logger.info(current_name)
        logger.info('    - %s', record.wheel.filename)
        logger.info('      Path: %s', record.link_path)
        if record.link_origin:
            logger.info('      Original link: %s', record.link_origin)
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

from __future__ import absolute_import

import datetime
import logging
import os.path

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

        link_path_infos = {}
        wheel_filenames = []
        for dirpath, dirnames, filenames in os.walk(
                os.path.join(options.cache_dir, 'wheels')):

            # Should we filter on the paths and ignore those that
            # does not conform with the xx/yy/zz/hhhh...hhhh/ patterns ?
            for filename in filenames:
                if filename == 'link':
                    with open(os.path.join(dirpath, 'link')) as fl:
                        link = fl.read()
                    link_path_infos[dirpath] = link
                elif filename.endswith('.whl'):
                    link_path_infos.setdefault(dirpath)
                    wheel_filenames.append(os.path.join(dirpath, filename))

        if not options.all_wheels:
            if not args:
                logger.info('Found %s wheels from %s links',
                            len(wheel_filenames), len(link_path_infos))
                return SUCCESS
        elif args:
            raise CommandError('You cannot pass args with --all option')

        records = []
        if options.not_accessed_since:
            # check if possible to have:
            # --not-accessed-since and --not-accessed-since-days
            min_last_access = datetime.datetime.now() - datetime.timedelta(days=options.not_accessed_since)
        else:
            min_last_access = None
        for record in iter_record(wheel_filenames, link_path_infos):
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
            if min_last_access is not None:
                if record.last_access_time > min_last_access:
                    continue

            records.append(record)
        if not options.remove:
            log_results(records)
        else:
            wheel_paths = [os.path.join(record.link_path, record.wheel.filename)
                           for record in records]
            logger.info('Deleting:\n- %s' % '\n- '.join(wheel_paths))
            if options.yes:
                response = 'yes'
            else:
                response = ask('Proceed (yes/no)? ', ('yes', 'no'))
            if response == 'yes':
                for wheel_path in wheel_paths:
                    os.remove(wheel_path)
            # Should we try to cleanup empty dirs and link files ?

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

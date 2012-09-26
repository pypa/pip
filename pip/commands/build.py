from pip.locations import build_prefix, src_prefix
from pip.util import display_path, backup_dir
from pip.log import logger
from pip.exceptions import CommandError
from pip.commands.install import InstallCommand


class BuildCommand(InstallCommand):
    name = 'build'
    usage = '%prog [OPTIONS] PACKAGE_NAMES...'
    summary = 'Build packages'

    def __init__(self):
        super(BuildCommand, self).__init__()
        self.parser.set_defaults(**{
            'use_wheel': False,
            'no_install': True,
            'upgrade': True,
        })

    def run(self, options, args):
        if not options.wheel_cache:
            raise CommandError('You must supply -w, --build-wheel option')
        super(BuildCommand, self).run(options, args)

BuildCommand()

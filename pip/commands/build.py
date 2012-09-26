from pip.locations import build_prefix, src_prefix
from pip.util import display_path, backup_dir
from pip.log import logger
from pip.exceptions import InstallationError
from pip.commands.install import InstallCommand


class BuildCommand(InstallCommand):
    name = 'build'
    usage = '%prog [OPTIONS] PACKAGE_NAMES...'
    summary = 'Build packages'

    def __init__(self):
        super(BuildCommand, self).__init__()
        self.parser.set_defaults(**{
                'wheel_cache': True,
                })

BuildCommand()

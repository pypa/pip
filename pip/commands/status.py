import os
import pkg_resources
from pip.basecommand import Command
from pip.log import logger


class StatusCommand(Command):
    name = 'status'
    usage = '%prog QUERY'
    summary = 'Output installed distributions (exact versions, files) to stdout'

    def __init__(self):
        super(StatusCommand, self).__init__()

    def run(self, options, args):
        if not args:
            logger.warn('ERROR: Missing required argument (status query).')
            return
        query = args

        print_results(query)


def print_results(query):
    """
    Gather details from installed distributions. Print distribution name,
    version, location, and installed files. Installed files requires a
    pip generated 'installed-files.txt' in the distributions '.egg-info'
    directory.
    """
    installed_packages = [p.project_name for p in pkg_resources.working_set]
    for name in query:
        if name in installed_packages:
            dist = pkg_resources.get_distribution(name)
            logger.notify("---")
            logger.notify("Name: %s" % name)
            logger.notify("Version: %s" % dist.version)
            logger.notify("Location: %s" % dist.location)
            logger.notify("Files:")
            filelist = os.path.join(
                           dist.location,
                           dist.egg_name() + '.egg-info',
                           'installed-files.txt')
            if os.path.isfile(filelist):
                for line in open(filelist):
                    logger.notify("  %s" % line.strip())
            else:
                logger.notify("Cannot locate installed-files.txt")


StatusCommand()

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

        results = search_packages_info(query)
        print_results(results)

def search_packages_info(query):
    """
    Gather details from installed distributions. Print distribution name,
    version, location, and installed files. Installed files requires a
    pip generated 'installed-files.txt' in the distributions '.egg-info'
    directory.
    """
    installed_packages = dict([(p.project_name.lower(), p.project_name) \
            for p in pkg_resources.working_set])
    for name in query:
        normalized_name = name.lower()
        if normalized_name in installed_packages:
            dist = pkg_resources.get_distribution( \
                    installed_packages[normalized_name])
            package = {
                'name': dist.project_name,
                'version': dist.version,
                'location': dist.location
            }
            filelist = os.path.join(
                       dist.location,
                       dist.egg_name() + '.egg-info',
                       'installed-files.txt')
            if os.path.isfile(filelist):
                package['files'] = filelist
            yield package


def print_results(distributions):
    """
    Print the informations from installed distributions found.
    """
    for dist in distributions:
        logger.notify("---")
        logger.notify("Name: %s" % dist['name'])
        logger.notify("Version: %s" % dist['version'])
        logger.notify("Location: %s" % dist['location'])
        logger.notify("Files:")
        filelist = dist.get('files', None)
        if filelist:
            for i, line in enumerate(open(filelist)):
                logger.notify("  %s" % line.strip())
                if i > 20:
                    logger.notify("  and more.")
                    break
        else:
            logger.notify("Cannot locate installed-files.txt")


StatusCommand()

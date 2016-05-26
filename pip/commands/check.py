from pip.log import logger
from pip.basecommand import Command
from pip.util import get_installed_distributions


class CheckCommand(Command):
    """Verify installed packages have compatible dependencies."""
    name = 'check'
    usage = """
      %prog [options]"""
    summary = 'Verify installed packages have compatible dependencies.'

    def setup_logging(self):
        logger.move_stdout_to_stderr()

    def run(self, options, args):
        all_requirements_met = True

        installed = get_installed_distributions()
        for dist in installed:

            missing_requirements = self.get_missing_requirements(dist, installed)
            for requirement in missing_requirements:
                logger.notify("%s %s requires %s, which is not installed." %
                    (dist.project_name, dist.version, requirement.project_name))

            incompatible_requirements = self.get_incompatible_requirements(dist, installed)
            for requirement, actual in incompatible_requirements:
                logger.notify("%s %s has requirement %s, but you have %s %s." %
                    (dist.project_name, dist.version, requirement,
                     actual.project_name, actual.version))

            if missing_requirements or incompatible_requirements:
                all_requirements_met = False

        if not all_requirements_met:
            return 1

    def get_missing_requirements(self, dist, installed_dists):
        """Return all of the requirements of `dist` that aren't present in
        `installed_dists`.

        """
        installed_names = set(d.project_name for d in installed_dists)

        missing_requirements = set()
        for requirement in dist.requires():
            if requirement.project_name not in installed_names:
                missing_requirements.add(requirement)
                yield requirement

    def get_incompatible_requirements(self, dist, installed_dists):
        """Return all of the requirements of `dist` that are present in
        `installed_dists`, but have incompatible versions.

        """
        installed_dists_by_name = {}
        for installed_dist in installed_dists:
            installed_dists_by_name[installed_dist.project_name] = installed_dist

        incompatible_requirements = set()
        for requirement in dist.requires():
            present_dist = installed_dists_by_name.get(requirement.project_name)

            if present_dist and present_dist not in requirement:
                incompatible_requirements.add((requirement, present_dist))
                yield (requirement, present_dist)

# coding: utf-8

import pkg_resources
import pip
from pip.log import logger
from pip.commands.install import InstallCommand
from pip.util import get_installed_distributions


class UpgradeCommand(InstallCommand):
    name = 'upgrade'
    usage = '%prog [OPTIONS]'
    summary = 'Upgrade all local installed packages'

    def run(self, options, args):
        options.upgrade = True
        options.ignore_installed = False


        packages, editables = self.get_upgradeable()
        args += packages
        options.editables += editables

        return super(UpgradeCommand, self).run(options, args)

    def get_upgradeable(self):
        dependency_links = []
        for dist in pkg_resources.working_set:
            if dist.has_metadata('dependency_links.txt'):
                dependency_links.extend(dist.get_metadata_lines('dependency_links.txt'))

        packages = []
        editables = []
        for dist in get_installed_distributions(local_only=True):
            req = pip.FrozenRequirement.from_dist(dist, dependency_links=dependency_links)

            if not req.editable:
                packages.append(req.name)
            else:
                # FIXME: How can we get this needes information easier?
                raw_cmd = str(req)
                full_url = raw_cmd.split()[1]
                url, full_version = full_url.rsplit("@", 1)
                rev = full_version.rsplit("-", 1)[1]

                if rev != "dev":
                    pip_url = "%s@%s#egg=%s" % (url, rev, req.name)
                else:
                    pip_url = "%s#egg=%s" % (url, req.name)

                editables.append(pip_url)


        logger.notify('Found theses local packages:')
        logger.indent += 2
        for package in packages:
            logger.notify(package)
        logger.indent -= 2

        logger.notify('Found theses local editables:')
        logger.indent += 2
        for editable in editables:
            logger.notify(editable)
        logger.indent -= 2

        return packages, editables


UpgradeCommand()



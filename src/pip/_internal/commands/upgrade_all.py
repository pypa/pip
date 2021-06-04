import logging
from optparse import Values
from typing import List

from pip._internal.commands.install import InstallCommand
from pip._internal.commands.list import ListCommand
from pip._internal.utils.compat import stdlib_pkgs
from pip._internal.utils.misc import get_installed_distributions

logger = logging.getLogger(__name__)


class UpgradeAllCommand(InstallCommand, ListCommand):
    """
    Upgrades all out of date packages, exactly like this old oneliner used to do:
    pip list --format freeze | \
    grep --invert-match "pkg-resources" | \
    cut  --delimiter "=" --fields 1 | \
    xargs pip install --upgrade
    """
    usage = """
      %prog [options]
      %prog [options] [-e] <vcs project url> ...
      %prog [options] [-e] <local project path> ...
      %prog [options] <archive url/path> ..."""

    def add_options(self):
        # type: () -> None
        # install all options from installcommand
        InstallCommand.add_options(self)
        # we don't upgrade in editable mode AND listcommand also has an editable option
        self.cmd_opts.remove_option('--editable')
        # redefine user later
        self.cmd_opts.remove_option('--user')
        # upgrade all always upgrade, so the help text for target makes no sense
        self.cmd_opts.remove_option('--target')
        # we always upgrade
        self.cmd_opts.remove_option('--upgrade')
        # pre is defined in installcommand and listcommand, so remove it once
        self.cmd_opts.remove_option('--pre')
        self.cmd_opts.remove_option('--index-url')
        self.cmd_opts.remove_option('--extra-index-url')
        self.cmd_opts.remove_option('--no-index')
        self.cmd_opts.remove_option('--find-links')

        # install command will have added the cmd_opts to self.parser already,
        # so pop them here because well' add them again later
        del self.parser.option_groups[0]
        # same for package index options
        del self.parser.option_groups[0]

        # install all options from listcommand
        ListCommand.add_options(self)

        # also remove options listcommand have added so we can add our real
        # options later
        del self.parser.option_groups[0]

        # redefine user later
        self.cmd_opts.remove_option('--user')
        self.cmd_opts.add_option(
            '--user',
            dest='user',
            action='store_true',
            default=False,
            help='Only upgrade packages installed in user-site.')
        self.cmd_opts.add_option(
            '-t', '--target',
            dest='target_dir',
            metavar='dir',
            default=None,
            help='Install packages into <dir>. '
                 'This will replace existing files/folders in '
                 '<dir> with new versions.'
        )

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options, args):
        # type: (Values, List[str]) -> int
        skip = set(stdlib_pkgs)
        if options.excludes:
            skip.update(options.excludes)

        packages = get_installed_distributions(
            local_only=options.local,
            user_only=options.user,
            editables_only=options.editable,
            include_editables=options.include_editable,
            paths=options.path,
            skip=skip,
        )
        if options.not_required:
            packages = self.get_not_required(packages, options)

        if options.outdated:
            packages = self.get_outdated(packages, options)
        packages = [dist.project_name for dist in packages]

        logging.info("upgrading %s", packages)

        options.upgrade = True
        # we don't upgrade in editable mode
        options.editable = False
        return InstallCommand.run(self, options, packages)

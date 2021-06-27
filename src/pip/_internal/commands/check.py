import logging
from optparse import Values
from typing import Any, List

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.operations.check import (
    check_package_set,
    create_package_set_from_installed,
)
from pip._internal.utils.misc import write_output

logger = logging.getLogger(__name__)


class CheckCommand(Command):
    """Verify installed packages have compatible dependencies."""

    usage = """
      %prog [options]"""

    def add_options(self):
        # type: () -> None

        self.cmd_opts.add_option(
            '--reqs-fmt', '--requirements-format',
            dest='requirements_format',
            action='store_true',
            default=False,
            help='Generate output suitable for a requirements file.',
        )

    def run(self, options, args):
        # type: (Values, List[Any]) -> int

        package_set, parsing_probs = create_package_set_from_installed()
        missing, conflicting = check_package_set(package_set)

        for project_name in missing:
            version = package_set[project_name].version
            for dependency in missing[project_name]:
                msg = "%s %s requires %s, which is not installed." % (
                    project_name, version, dependency[0])
                if options.requirements_format:
                    msg = '%s  # %s' % (dependency[0], msg)
                write_output(msg)

        for project_name in conflicting:
            version = package_set[project_name].version
            for dep_name, dep_version, req in conflicting[project_name]:
                msg = "%s %s has requirement %s, but you have %s %s." % (
                    project_name, version, req, dep_name, dep_version)
                if options.requirements_format:
                    msg = '%s  # %s' % (req, msg)
                write_output(msg)

        if missing or conflicting or parsing_probs:
            return ERROR
        else:
            write_output("No broken requirements found.")
            return SUCCESS

import logging
from optparse import Values
from typing import Callable, List, Optional

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

    def add_options(self) -> None:
        self.cmd_opts.add_option(
            "--ignore-packages",
            action="append",
            metavar="PACKAGE",
            dest="ignore_packages",
            default=[],
            help="Ignore packages.",
        )
        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options: Values, args: List[str]) -> int:

        package_set, parsing_probs = create_package_set_from_installed()
        should_ignore: Optional[Callable[[str], bool]] = (
            (lambda p: p in options.ignore_packages)
            if options.ignore_packages
            else None
        )
        missing, conflicting = check_package_set(package_set, should_ignore)

        for project_name in missing:
            version = package_set[project_name].version
            for dependency in missing[project_name]:
                write_output(
                    "%s %s requires %s, which is not installed.",
                    project_name,
                    version,
                    dependency[0],
                )

        for project_name in conflicting:
            version = package_set[project_name].version
            for dep_name, dep_version, req in conflicting[project_name]:
                write_output(
                    "%s %s has requirement %s, but you have %s %s.",
                    project_name,
                    version,
                    req,
                    dep_name,
                    dep_version,
                )

        if missing or conflicting or parsing_probs:
            return ERROR
        else:
            write_output("No broken requirements found.")
            return SUCCESS

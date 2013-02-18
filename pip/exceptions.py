"""Exceptions used throughout package"""

import textwrap

class PipError(Exception):
    """Base pip exception"""


class InstallationError(PipError):
    """General exception during installation"""


class UninstallationError(PipError):
    """General exception during uninstallation"""


class DistributionNotFound(InstallationError):
    """Raised when a distribution cannot be found to satisfy a requirement"""


class BestVersionAlreadyInstalled(PipError):
    """Raised when the most up-to-date version of a package is already
    installed.  """


class BadCommand(PipError):
    """Raised when virtualenv or a command is not found"""


class CommandError(PipError):
    """Raised when there is an error in command-line arguments"""


class NoSSLError(PipError):
    """Raised when there's no ssl and not using '--insecure'"""

    def __str__(self):
        return textwrap.dedent("""
            ###################################################################
            ##  You don't have an importable ssl module. You are most        ##
            ##  likely using Python 2.5, which did not include ssl           ##
            ##  support by default. In this state, we can not provide        ##
            ##  ssl certified downloads from PyPI.                           ##
            ##                                                               ##
            ##  You can do one of 2 things:                                  ##
            ##   1) Install this: https://pypi.python.org/pypi/ssl/          ##
            ##      (It provides ssl support for older Pythons )             ##
            ##   2) Use the --insecure option to allow this insecurity       ##
            ##                                                               ##
            ##  For more details, go to the  "SSL Certificate Verification"  ##
            ##  section located here:                                        ##
            ##     http://www.pip-installer.org/en/latest/logic.html         ##
            ##                                                               ##
            ###################################################################
            """)


"""Exceptions used throughout package"""


class InstallationError(Exception):
    """General exception during installation"""


class UninstallationError(Exception):
    """General exception during uninstallation"""


class DistributionNotFound(InstallationError):
    """Raised when a distribution cannot be found to satisfy a requirement"""


class BestVersionAlreadyInstalled(Exception):
    """Raised when the most up-to-date version of a package is already
    installed.
    """

class BadCommand(Exception):
    """Raised when virtualenv or a command is not found"""


class CommandError(Exception):
    """Raised when there is an error in command-line arguments"""

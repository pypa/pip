"""Exceptions used throughout package"""
from __future__ import absolute_import


class PipError(Exception):
    """Base pip exception"""


class InstallationError(PipError):
    """General exception during installation"""


class UninstallationError(PipError):
    """General exception during uninstallation"""


class DistributionNotFound(InstallationError):
    """Raised when a distribution cannot be found to satisfy a requirement"""


class RequirementsFileParseError(PipError):
    """Raised when a general error occurs parsing a requirements file line."""


class ReqFileOnlyOneReqPerLineError(PipError):
    """Raised when more than one requirement is found on a line in a requirements
       file."""


class ReqFileOnleOneOptionPerLineError(PipError):
    """Raised when an option is not allowed in a requirements file."""


class ReqFileOptionNotAllowedWithReqError(PipError):
    """Raised when an option is not allowed on a requirement line in a requirements
       file."""


class BestVersionAlreadyInstalled(PipError):
    """Raised when the most up-to-date version of a package is already
    installed."""


class BadCommand(PipError):
    """Raised when virtualenv or a command is not found"""


class CommandError(PipError):
    """Raised when there is an error in command-line arguments"""


class PreviousBuildDirError(PipError):
    """Raised when there's a previous conflicting build directory"""


class HashMismatch(InstallationError):
    """Distribution file hash values don't match."""


class InvalidWheelFilename(InstallationError):
    """Invalid wheel filename."""


class UnsupportedWheel(InstallationError):
    """Unsupported wheel."""

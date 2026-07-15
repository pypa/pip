"""Package of exceptions used in the pip codebase.

This package used to be a single module, so many exceptions were
grandfathered into this module. In the future, more groups of exceptions
should be moved to their own submodules as needed.

This module MUST NOT try to import from anything within `pip._internal` to
operate. This is expected to be importable from any/all files within the
subpackage and, thus, should not depend on them.
"""

from __future__ import annotations

import configparser
import contextlib
import locale
import logging
import os
import pathlib
import sys
import traceback
from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING, Literal

from pip._vendor.packaging.requirements import InvalidRequirement
from pip._vendor.packaging.version import InvalidVersion
from pip._vendor.rich.markup import escape
from pip._vendor.rich.text import Text

from pip._internal.exceptions._base import DiagnosticPipError, PipError

if TYPE_CHECKING:
    from pip._vendor import urllib3
    from pip._vendor.requests.models import PreparedRequest, Request, Response

    from pip._internal.metadata import BaseDistribution
    from pip._internal.models.link import Link
    from pip._internal.network.download import _FileDownload
    from pip._internal.req.req_install import InstallRequirement

logger = logging.getLogger(__name__)


class ConfigurationError(PipError):
    """General exception in configuration"""


class InstallationError(PipError):
    """General exception during installation"""


class FailedToPrepareCandidate(InstallationError):
    """Raised when we fail to prepare a candidate (i.e. fetch and generate metadata).

    This is intentionally not a diagnostic error, since the output will be presented
    above this error, when this occurs. This should instead present information to the
    user.
    """

    def __init__(
        self, *, package_name: str, requirement_chain: str, failed_step: str
    ) -> None:
        super().__init__(f"Failed to build '{package_name}' when {failed_step.lower()}")
        self.package_name = package_name
        self.requirement_chain = requirement_chain
        self.failed_step = failed_step


class NoneMetadataError(PipError):
    """Raised when accessing a Distribution's "METADATA" or "PKG-INFO".

    This signifies an inconsistency, when the Distribution claims to have
    the metadata file (if not, raise ``FileNotFoundError`` instead), but is
    not actually able to produce its content. This may be due to permission
    errors.
    """

    def __init__(
        self,
        dist: BaseDistribution,
        metadata_name: str,
    ) -> None:
        """
        :param dist: A Distribution object.
        :param metadata_name: The name of the metadata being accessed
            (can be "METADATA" or "PKG-INFO").
        """
        self.dist = dist
        self.metadata_name = metadata_name

    def __str__(self) -> str:
        # Use `dist` in the error message because its stringification
        # includes more information, like the version and location.
        return f"None {self.metadata_name} metadata found for distribution: {self.dist}"


class UserInstallationInvalid(InstallationError):
    """A --user install is requested on an environment without user site."""

    def __str__(self) -> str:
        return "User base directory is not specified"


class InvalidSchemeCombination(InstallationError):
    def __str__(self) -> str:
        before = ", ".join(str(a) for a in self.args[:-1])
        return f"Cannot set {before} and {self.args[-1]} together"


class DistributionNotFound(InstallationError):
    """Raised when a distribution cannot be found to satisfy a requirement"""


class RequirementsFileParseError(InstallationError):
    """Raised when a general error occurs parsing a requirements file line."""


class BestVersionAlreadyInstalled(PipError):
    """Raised when the most up-to-date version of a package is already
    installed."""


class BadCommand(PipError):
    """Raised when virtualenv or a command is not found"""


class CommandError(PipError):
    """Raised when there is an error in command-line arguments"""


class PreviousBuildDirError(PipError):
    """Raised when there's a previous conflicting build directory"""


class NetworkConnectionError(PipError):
    """HTTP connection error"""

    def __init__(
        self,
        error_msg: str,
        response: Response | None = None,
        request: Request | PreparedRequest | None = None,
    ) -> None:
        """
        Initialize NetworkConnectionError with  `request` and `response`
        objects.
        """
        self.response = response
        self.request = request
        self.error_msg = error_msg
        if (
            self.response is not None
            and not self.request
            and hasattr(response, "request")
        ):
            self.request = self.response.request
        super().__init__(error_msg, response, request)

    def __str__(self) -> str:
        return str(self.error_msg)


class ConnectionFailedError(DiagnosticPipError):
    reference = "connection-failed"

    def __init__(self, url: str, host: str, error: Exception) -> None:
        from http.client import RemoteDisconnected

        from pip._vendor.urllib3.exceptions import (
            NameResolutionError,
            NewConnectionError,
            ProtocolError,
        )

        details = str(error)
        if isinstance(error, NameResolutionError):
            parts = details.split("Failed to resolve ", maxsplit=1)
            if len(parts) == 2:
                details = "Failed to resolve IP address for " + parts[1]
        elif isinstance(error, NewConnectionError):
            parts = details.split("Failed to establish a new connection: ", maxsplit=1)
            if len(parts) == 2:
                _, details = parts
        elif isinstance(error, ProtocolError):
            try:
                reason = error.args[1]
            except IndexError:
                pass
            else:
                if isinstance(reason, (RemoteDisconnected, ConnectionResetError)):
                    details = (
                        "the connection was closed without a reply from the server."
                    )

        super().__init__(
            message=(
                f"Failed to connect to [magenta]{escape(host)}[/] while fetching "
                f"{escape(url)}"
            ),
            context=Text(details),
            hint_stmt=(
                "Are you connected to the Internet? If so, check whether your system "
                f"can connect to [magenta]{escape(host)}[/] before trying again. "
                "There may be a firewall or proxy that's preventing the connection."
            ),
        )


class ConnectionTimeoutError(DiagnosticPipError):
    reference = "connection-timeout"

    def __init__(
        self,
        url: str,
        host: str,
        *,
        kind: Literal["connect", "read"],
        timeout: float,
    ) -> None:
        context = Text.assemble(
            (host, "magenta"), f" didn't respond within {timeout} seconds"
        )
        if kind == "connect":
            context.append(" (while establishing a connection)")
        super().__init__(
            message=f"Unable to fetch {escape(url)}",
            context=context,
            hint_stmt=(
                "This is probably a temporary issue with the remote server or the "
                "network connection. If this error persists, check the network "
                "configuration. There may be a firewall or proxy that's preventing "
                "the connection."
            ),
        )


class SSLMissingError(DiagnosticPipError):
    reference = "ssl-missing"

    def __init__(self, url: str) -> None:
        super().__init__(
            message=f"Failed to establish a secure connection for {escape(url)}",
            context="The 'ssl' module is unavailable but required for HTTPS URLs",
            hint_stmt=None,
        )


class SSLVerificationError(DiagnosticPipError):
    reference = "ssl-verification-failed"

    def __init__(self, url: str, host: str, error: urllib3.exceptions.SSLError) -> None:
        message = (
            "Failed to establish a secure connection to "
            f"[magenta]{escape(host)}[/] while fetching {escape(url)}"
        )
        hint = "You may need to use --cert or check your proxy/firewall configuration"
        super().__init__(message=message, context=Text(str(error)), hint_stmt=hint)


class ProxyConnectionError(DiagnosticPipError):
    reference = "proxy-connection-failed"

    def __init__(
        self, url: str, proxy: str, error: urllib3.exceptions.ProxyError
    ) -> None:
        super().__init__(
            message=(
                "Failed to connect to proxy "
                f"[magenta]{escape(proxy)}[/] while fetching {escape(url)}"
            ),
            context=Text(str(error)),
            hint_stmt="This is likely a proxy configuration issue.",
        )


class MetadataInconsistent(InstallationError):
    """Built metadata contains inconsistent information.

    This is raised when the metadata contains values (e.g. name and version)
    that do not match the information previously obtained from sdist filename,
    user-supplied ``#egg=`` value, or an install requirement name.
    """

    def __init__(
        self, ireq: InstallRequirement, field: str, f_val: str, m_val: str
    ) -> None:
        self.ireq = ireq
        self.field = field
        self.f_val = f_val
        self.m_val = m_val

    def __str__(self) -> str:
        return (
            f"Requested {self.ireq} has inconsistent {self.field}: "
            f"expected {self.f_val!r}, but metadata has {self.m_val!r}"
        )


class SidecarMetadataInconsistent(MetadataInconsistent):
    """The wheel's METADATA disagrees with its PEP 658 ``.metadata`` file.

    Raised after the wheel has been downloaded and hash-verified, when a
    resolver-affecting field in the wheel's embedded ``METADATA`` does not
    match the value taken from the remote ``.metadata`` sidecar that drove
    resolution. ``f_val`` is the sidecar value, ``m_val`` is the wheel value.
    """

    def __str__(self) -> str:
        return (
            f"Requested {self.ireq} has inconsistent {self.field} between "
            f"its PEP 658 .metadata file and the wheel's METADATA: "
            f"sidecar has {self.f_val!r}, wheel has {self.m_val!r}"
        )


class MetadataInvalid(InstallationError):
    """Metadata is invalid."""

    def __init__(self, ireq: InstallRequirement, error: str) -> None:
        self.ireq = ireq
        self.error = error

    def __str__(self) -> str:
        return f"Requested {self.ireq} has invalid metadata: {self.error}"


class InstallationSubprocessError(DiagnosticPipError, InstallationError):
    """A subprocess call failed."""

    reference = "subprocess-exited-with-error"

    def __init__(
        self,
        *,
        command_description: str,
        exit_code: int,
        output_lines: list[str] | None,
    ) -> None:
        if output_lines is None:
            output_prompt = Text("No available output.")
        else:
            output_prompt = (
                Text.from_markup(f"[red][{len(output_lines)} lines of output][/]\n")
                + Text("".join(output_lines))
                + Text.from_markup(R"[red]\[end of output][/]")
            )

        super().__init__(
            message=(
                f"[green]{escape(command_description)}[/] did not run successfully.\n"
                f"exit code: {exit_code}"
            ),
            context=output_prompt,
            hint_stmt=None,
            note_stmt=(
                "This error originates from a subprocess, and is likely not a "
                "problem with pip."
            ),
        )

        self.command_description = command_description
        self.exit_code = exit_code

    def __str__(self) -> str:
        return f"{self.command_description} exited with {self.exit_code}"


class MetadataGenerationFailed(DiagnosticPipError, InstallationError):
    reference = "metadata-generation-failed"

    def __init__(
        self,
        *,
        package_details: str,
    ) -> None:
        super().__init__(
            message="Encountered error while generating package metadata.",
            context=escape(package_details),
            hint_stmt="See above for details.",
            note_stmt="This is an issue with the package mentioned above, not pip.",
        )

    def __str__(self) -> str:
        return "metadata generation failed"


class UnsupportedPythonVersion(InstallationError):
    """Unsupported python version according to Requires-Python package
    metadata."""


class ConfigurationFileCouldNotBeLoaded(ConfigurationError):
    """When there are errors while loading a configuration file"""

    def __init__(
        self,
        reason: str = "could not be loaded",
        fname: str | None = None,
        error: configparser.Error | None = None,
    ) -> None:
        super().__init__(error)
        self.reason = reason
        self.fname = fname
        self.error = error

    def __str__(self) -> str:
        if self.fname is not None:
            message_part = f" in {self.fname}."
        else:
            assert self.error is not None
            message_part = f".\n{self.error}\n"
        return f"Configuration file {self.reason}{message_part}"


_DEFAULT_EXTERNALLY_MANAGED_ERROR = f"""\
The Python environment under {sys.prefix} is managed externally, and may not be
manipulated by the user. Please use specific tooling from the distributor of
the Python installation to interact with this environment instead.
"""


class ExternallyManagedEnvironment(DiagnosticPipError):
    """The current environment is externally managed.

    This is raised when the current environment is externally managed, as
    defined by `PEP 668`_. The ``EXTERNALLY-MANAGED`` configuration is checked
    and displayed when the error is bubbled up to the user.

    :param error: The error message read from ``EXTERNALLY-MANAGED``.
    """

    reference = "externally-managed-environment"

    def __init__(self, error: str | None) -> None:
        if error is None:
            context = Text(_DEFAULT_EXTERNALLY_MANAGED_ERROR)
        else:
            context = Text(error)
        super().__init__(
            message="This environment is externally managed",
            context=context,
            note_stmt=(
                "If you believe this is a mistake, please contact your "
                "Python installation or OS distribution provider. "
                "You can override this, at the risk of breaking your Python "
                "installation or OS, by passing --break-system-packages."
            ),
            hint_stmt=Text("See PEP 668 for the detailed specification."),
        )

    @staticmethod
    def _iter_externally_managed_error_keys() -> Iterator[str]:
        # LC_MESSAGES is in POSIX, but not the C standard. The most common
        # platform that does not implement this category is Windows, where
        # using other categories for console message localization is equally
        # unreliable, so we fall back to the locale-less vendor message. This
        # can always be re-evaluated when a vendor proposes a new alternative.
        try:
            category = locale.LC_MESSAGES
        except AttributeError:
            lang: str | None = None
        else:
            lang, _ = locale.getlocale(category)
        if lang is not None:
            yield f"Error-{lang}"
            for sep in ("-", "_"):
                before, found, _ = lang.partition(sep)
                if not found:
                    continue
                yield f"Error-{before}"
        yield "Error"

    @classmethod
    def from_config(
        cls,
        config: pathlib.Path | str,
    ) -> ExternallyManagedEnvironment:
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read(config, encoding="utf-8")
            section = parser["externally-managed"]
            for key in cls._iter_externally_managed_error_keys():
                with contextlib.suppress(KeyError):
                    return cls(section[key])
        except KeyError:
            pass
        except (OSError, UnicodeDecodeError, configparser.ParsingError):
            from pip._internal.utils._log import VERBOSE

            exc_info = logger.isEnabledFor(VERBOSE)
            logger.warning("Failed to read %s", config, exc_info=exc_info)
        return cls(None)


class UninstallMissingRecord(DiagnosticPipError):
    reference = "uninstall-no-record-file"

    def __init__(self, *, distribution: BaseDistribution) -> None:
        installer = distribution.installer
        if not installer or installer == "pip":
            dep = f"{distribution.raw_name}=={distribution.version}"
            hint = Text.assemble(
                "You might be able to recover from this via: ",
                (f"pip install --ignore-installed --no-deps {dep}", "green"),
            )
        else:
            hint = Text(
                f"The package was installed by {installer}. "
                "You should check if it can uninstall the package."
            )

        super().__init__(
            message=Text(f"Cannot uninstall {distribution}"),
            context=(
                "The package's contents are unknown: "
                f"no RECORD file was found for {distribution.raw_name}."
            ),
            hint_stmt=hint,
        )


class LegacyDistutilsInstall(DiagnosticPipError):
    reference = "uninstall-distutils-installed-package"

    def __init__(self, *, distribution: BaseDistribution) -> None:
        super().__init__(
            message=Text(f"Cannot uninstall {distribution}"),
            context=(
                "It is a distutils installed project and thus we cannot accurately "
                "determine which files belong to it which would lead to only a partial "
                "uninstall."
            ),
            hint_stmt=None,
        )


class InvalidInstalledPackage(DiagnosticPipError):
    reference = "invalid-installed-package"

    def __init__(
        self,
        *,
        dist: BaseDistribution,
        invalid_exc: InvalidRequirement | InvalidVersion,
    ) -> None:
        installed_location = dist.installed_location

        if isinstance(invalid_exc, InvalidRequirement):
            invalid_type = "requirement"
        else:
            invalid_type = "version"

        super().__init__(
            message=Text(
                f"Cannot process installed package {dist} "
                + (f"in {installed_location!r} " if installed_location else "")
                + f"because it has an invalid {invalid_type}:\n{invalid_exc.args[0]}"
            ),
            context=(
                "Starting with pip 24.1, packages with invalid "
                f"{invalid_type}s can not be processed."
            ),
            hint_stmt="To proceed this package must be uninstalled.",
        )


class IncompleteDownloadError(DiagnosticPipError):
    """Raised when the downloader receives fewer bytes than advertised
    in the Content-Length header."""

    reference = "incomplete-download"

    def __init__(self, download: _FileDownload) -> None:
        # Dodge circular import.
        from pip._internal.utils.misc import format_size

        assert download.size is not None
        download_status = (
            f"{format_size(download.bytes_received)}/{format_size(download.size)}"
        )
        if download.reattempts:
            retry_status = f"after {download.reattempts + 1} attempts "
            hint = "Use --resume-retries to configure resume attempt limit."
        else:
            # Download retrying is not enabled.
            retry_status = ""
            hint = "Consider using --resume-retries to enable download resumption."
        message = Text(
            f"Download failed {retry_status}because not enough bytes "
            f"were received ({download_status})"
        )

        super().__init__(
            message=message,
            context=f"URL: {download.link.redacted_url}",
            hint_stmt=hint,
            note_stmt="This is an issue with network connectivity, not pip.",
        )


class ResolutionTooDeepError(DiagnosticPipError):
    """Raised when the dependency resolver exceeds the maximum recursion depth."""

    reference = "resolution-too-deep"

    def __init__(self) -> None:
        super().__init__(
            message="Dependency resolution exceeded maximum depth",
            context=(
                "Pip cannot resolve the current dependencies as the dependency graph "
                "is too complex for pip to solve efficiently."
            ),
            hint_stmt=(
                "Try adding lower bounds to constrain your dependencies, "
                "for example: 'package>=2.0.0' instead of just 'package'. "
            ),
            link="https://pip.pypa.io/en/stable/topics/dependency-resolution/#handling-resolution-too-deep-errors",
        )


class InstallWheelBuildError(DiagnosticPipError):
    reference = "failed-wheel-build-for-install"

    def __init__(self, failed: list[InstallRequirement]) -> None:
        super().__init__(
            message=(
                "Failed to build installable wheels for some "
                "pyproject.toml based projects"
            ),
            context=", ".join(r.name for r in failed),  # type: ignore
            hint_stmt=None,
        )


class InvalidEggFragment(DiagnosticPipError):
    reference = "invalid-egg-fragment"

    def __init__(self, link: Link, fragment: str) -> None:
        hint = ""
        if ">" in fragment or "=" in fragment or "<" in fragment:
            hint = (
                "Version specifiers are silently ignored for URL references. "
                "Remove them. "
            )
        if "[" in fragment and "]" in fragment:
            hint += "Try using the Direct URL requirement syntax: 'name[extra] @ URL'"

        if not hint:
            hint = "Egg fragments can only be a valid project name."

        super().__init__(
            message=f"The '{escape(fragment)}' egg fragment is invalid",
            context=f"from '{escape(str(link))}'",
            hint_stmt=escape(hint),
        )


class BuildDependencyInstallError(DiagnosticPipError):
    """Raised when build dependencies cannot be installed."""

    reference = "failed-build-dependency-install"

    def __init__(
        self,
        req: InstallRequirement | None,
        build_reqs: Iterable[str],
        *,
        cause: Exception,
        log_lines: list[str] | None,
    ) -> None:
        if isinstance(cause, PipError):
            note = "This is likely not a problem with pip."
        else:
            note = (
                "pip crashed unexpectedly. Please file an issue on pip's issue "
                "tracker: https://github.com/pypa/pip/issues/new"
            )

        if log_lines is None:
            # No logs are available, they must have been printed earlier.
            context = Text("See above for more details.")
        else:
            if isinstance(cause, PipError):
                log_lines.append(f"ERROR: {cause}")
            else:
                # Split rendered error into real lines without trailing newlines.
                log_lines.extend(
                    "".join(traceback.format_exception(cause)).splitlines()
                )

            context = Text.assemble(
                f"Installing {' '.join(build_reqs)}\n",
                (f"[{len(log_lines)} lines of output]\n", "red"),
                "\n".join(log_lines),
                ("\n[end of output]", "red"),
            )

        message = Text("Cannot install build dependencies", "green")
        if req:
            message += Text(f" for {req}")
        super().__init__(
            message=message, context=context, hint_stmt=None, note_stmt=note
        )


class VenvImportError(DiagnosticPipError):
    """Raised when 'venv' can't be imported."""

    reference = "venv-import-error"

    def __init__(self) -> None:
        if sys.platform != "linux":
            hint_stmt = None
        else:
            hint_stmt = (
                "If this is an OS-provided Python, it's likely that your OS "
                "package maintainers have split Python's standard library across "
                "multiple OS packages."
            )
        super().__init__(
            message="Cannot import the 'venv' module of the Python standard library",
            context=(
                "This is a symptom of a broken/modified Python, which cannot be used "
                "with pip."
            ),
            note_stmt="This is an issue with the Python installation itself, not pip.",
            hint_stmt=hint_stmt,
        )


class VenvCreationError(DiagnosticPipError):
    """Raised when a virtual environment can't be created."""

    reference = "venv-creation-error"

    def __init__(self, context: str) -> None:
        if os.name == "nt":
            hint = "This may be caused by running antivirus software."
        else:
            hint = None
        super().__init__(
            message="Cannot create a virtual environment",
            context=Text(context),
            hint_stmt=hint,
        )

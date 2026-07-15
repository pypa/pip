"""Package of exceptions used in the pip codebase.

This package used to be a single module, so many exceptions were
grandfathered into this module. In the future, more groups of exceptions
should be moved to their own submodules as needed.

This package MUST NOT try to import from anything within `pip._internal` to
operate. This is expected to be importable from any/all files within the
subpackage and, thus, should not depend on them.
"""

# NOTE: the pip._internal import restriction may change later if there is an
# exception group that does really need internal code to function (e.g.
# possibly network). In that case, said group should NOT be re-exported here.

from __future__ import annotations

import configparser
import contextlib
import locale
import logging
import pathlib
import sys
from collections.abc import Iterator
from itertools import chain, groupby, repeat
from typing import TYPE_CHECKING, Literal

from pip._vendor.packaging.requirements import InvalidRequirement
from pip._vendor.packaging.version import InvalidVersion
from pip._vendor.rich.markup import escape
from pip._vendor.rich.text import Text

from pip._internal.exceptions._base import (
    DiagnosticPipError,
    InstallationError,
    PipError,
)
from pip._internal.exceptions.build_env import (
    BuildDependencyInstallError,
    VenvCreationError,
    VenvImportError,
)
from pip._internal.exceptions.pyproject import (
    InvalidPyProjectBuildRequires,
    MissingPyProjectBuildRequires,
)
from pip._internal.exceptions.uninstall import (
    LegacyDistutilsInstall,
    UninstallMissingRecord,
)
from pip._internal.exceptions.wheel import (
    InvalidWheel,
    InvalidWheelFilename,
    UnsupportedWheel,
)

if TYPE_CHECKING:
    from hashlib import _Hash

    from pip._vendor import urllib3
    from pip._vendor.requests.models import PreparedRequest, Request, Response

    from pip._internal.metadata import BaseDistribution
    from pip._internal.models.link import Link
    from pip._internal.network.download import _FileDownload
    from pip._internal.req.req_install import InstallRequirement


__all__ = [
    # base
    "DiagnosticPipError",
    "InstallationError",
    "PipError",
    # build_env
    "BuildDependencyInstallError",
    "VenvCreationError",
    "VenvImportError",
    # pyproject
    "InvalidPyProjectBuildRequires",
    "MissingPyProjectBuildRequires",
    # uninstall
    "LegacyDistutilsInstall",
    "UninstallMissingRecord",
    # wheel
    "InvalidWheel",
    "InvalidWheelFilename",
    "UnsupportedWheel",
]

logger = logging.getLogger(__name__)


class ConfigurationError(PipError):
    """General exception in configuration"""


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


class BackendUnavailableError(InstallationSubprocessError):
    """The build backend could not be loaded."""

    reference = "backend-unavailable"

    def __init__(
        self, *, hook_name: str, backend_name: str, backend_error: str
    ) -> None:
        DiagnosticPipError.__init__(
            self,
            message=f"Cannot import build backend {escape(backend_name)!r}.",
            context=backend_error,
            hint_stmt=None,
            note_stmt="This is likely not a problem with pip.",
        )
        self.command_description = f"Calling build backend hook {hook_name}"

    def __str__(self) -> str:
        return str(self.message)


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


class HashErrors(InstallationError):
    """Multiple HashError instances rolled into one for reporting"""

    def __init__(self) -> None:
        self.errors: list[HashError] = []

    def append(self, error: HashError) -> None:
        self.errors.append(error)

    def __str__(self) -> str:
        lines = []
        self.errors.sort(key=lambda e: e.order)
        for cls, errors_of_cls in groupby(self.errors, lambda e: e.__class__):
            lines.append(cls.head)
            lines.extend(e.body() for e in errors_of_cls)
        if lines:
            return "\n".join(lines)
        return ""

    def __bool__(self) -> bool:
        return bool(self.errors)


class HashError(InstallationError):
    """
    A failure to verify a package against known-good hashes

    :cvar order: An int sorting hash exception classes by difficulty of
        recovery (lower being harder), so the user doesn't bother fretting
        about unpinned packages when he has deeper issues, like VCS
        dependencies, to deal with. Also keeps error reports in a
        deterministic order.
    :cvar head: A section heading for display above potentially many
        exceptions of this kind
    :ivar req: The InstallRequirement that triggered this error. This is
        pasted on after the exception is instantiated, because it's not
        typically available earlier.

    """

    req: InstallRequirement | None = None
    head = ""
    order: int = -1

    def body(self) -> str:
        """Return a summary of me for display under the heading.

        This default implementation simply prints a description of the
        triggering requirement.

        :param req: The InstallRequirement that provoked this error, with
            its link already populated by the resolver's _populate_link().

        """
        return f"    {self._requirement_name()}"

    def __str__(self) -> str:
        return f"{self.head}\n{self.body()}"

    def _requirement_name(self) -> str:
        """Return a description of the requirement that triggered me.

        This default implementation returns long description of the req, with
        line numbers

        """
        return str(self.req) if self.req else "unknown package"


class VcsHashUnsupported(HashError):
    """A hash was provided for a version-control-system-based requirement, but
    we don't have a method for hashing those."""

    order = 0
    head = (
        "Can't verify hashes for these requirements because we don't "
        "have a way to hash version control repositories:"
    )


class DirectoryUrlHashUnsupported(HashError):
    """A hash was provided for a version-control-system-based requirement, but
    we don't have a method for hashing those."""

    order = 1
    head = (
        "Can't verify hashes for these file:// requirements because they "
        "point to directories:"
    )


class HashMissing(HashError):
    """A hash was needed for a requirement but is absent."""

    order = 2
    head = (
        "Hashes are required in --require-hashes mode, but they are "
        "missing from some requirements. Here is a list of those "
        "requirements along with the hashes their downloaded archives "
        "actually had. Add lines like these to your requirements files to "
        "prevent tampering. (If you did not enable --require-hashes "
        "manually, note that it turns on automatically when any package "
        "has a hash.)"
    )

    def __init__(self, gotten_hash: str) -> None:
        """
        :param gotten_hash: The hash of the (possibly malicious) archive we
            just downloaded
        """
        self.gotten_hash = gotten_hash

    def body(self) -> str:
        # Dodge circular import.
        from pip._internal.utils.hashes import FAVORITE_HASH

        package = None
        if self.req:
            # In the case of URL-based requirements, display the original URL
            # seen in the requirements file rather than the package name,
            # so the output can be directly copied into the requirements file.
            package = (
                self.req.original_link
                if self.req.is_direct
                # In case someone feeds something downright stupid
                # to InstallRequirement's constructor.
                else getattr(self.req, "req", None)
            )
        return "    {} --hash={}:{}".format(
            package or "unknown package", FAVORITE_HASH, self.gotten_hash
        )


class HashUnpinned(HashError):
    """A requirement had a hash specified but was not pinned to a specific
    version."""

    order = 3
    head = (
        "In --require-hashes mode, all requirements must have their "
        "versions pinned with ==. These do not:"
    )


class HashMismatch(HashError):
    """
    Distribution file hash values don't match.

    :ivar package_name: The name of the package that triggered the hash
        mismatch. Feel free to write to this after the exception is raise to
        improve its error message.

    """

    order = 4
    head = (
        "THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS "
        "FILE. If you have updated the package versions, please update "
        "the hashes. Otherwise, examine the package contents carefully; "
        "someone may have tampered with them."
    )

    def __init__(self, allowed: dict[str, list[str]], gots: dict[str, _Hash]) -> None:
        """
        :param allowed: A dict of algorithm names pointing to lists of allowed
            hex digests
        :param gots: A dict of algorithm names pointing to hashes we
            actually got from the files under suspicion
        """
        self.allowed = allowed
        self.gots = gots

    def body(self) -> str:
        return f"    {self._requirement_name()}:\n{self._hash_comparison()}"

    def _hash_comparison(self) -> str:
        """
        Return a comparison of actual and expected hash values.

        Example::

               Expected sha256 abcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcde
                            or 123451234512345123451234512345123451234512345
                    Got        bcdefbcdefbcdefbcdefbcdefbcdefbcdefbcdefbcdef

        """

        def hash_then_or(hash_name: str) -> chain[str]:
            # For now, all the decent hashes have 6-char names, so we can get
            # away with hard-coding space literals.
            return chain([hash_name], repeat("    or"))

        lines: list[str] = []
        for hash_name, expecteds in self.allowed.items():
            prefix = hash_then_or(hash_name)
            lines.extend((f"        Expected {next(prefix)} {e}") for e in expecteds)
            lines.append(
                f"             Got        {self.gots[hash_name].hexdigest()}\n"
            )
        return "\n".join(lines)


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

from collections import defaultdict
from dataclasses import dataclass, field
from logging import getLogger
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Tuple

from pip._vendor.packaging.requirements import Requirement as PkgRequirement
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.resolvelib.reporters import BaseReporter

from pip._internal.models.link import LinkWithSource, URLDownloadInfo
from pip._internal.req.req_install import (
    InstallRequirement,
    produce_exact_version_specifier,
)
from pip._internal.resolution.base import RequirementSetWithCandidates
from pip._internal.resolution.resolvelib.candidates import (
    LinkCandidate,
    RequiresPythonCandidate,
)
from pip._internal.resolution.resolvelib.requirements import (
    ExplicitRequirement,
    RequiresPythonRequirement,
)

from .base import Candidate, Requirement

logger = getLogger(__name__)


class PipReporter(BaseReporter):
    def __init__(self) -> None:
        self.backtracks_by_package: DefaultDict[str, int] = defaultdict(int)

        self._messages_at_backtrack = {
            1: (
                "pip is looking at multiple versions of {package_name} to "
                "determine which version is compatible with other "
                "requirements. This could take a while."
            ),
            8: (
                "pip is looking at multiple versions of {package_name} to "
                "determine which version is compatible with other "
                "requirements. This could take a while."
            ),
            13: (
                "This is taking longer than usual. You might need to provide "
                "the dependency resolver with stricter constraints to reduce "
                "runtime. See https://pip.pypa.io/warnings/backtracking for "
                "guidance. If you want to abort this run, press Ctrl + C."
            ),
        }

    def backtracking(self, candidate: Candidate) -> None:
        self.backtracks_by_package[candidate.name] += 1

        count = self.backtracks_by_package[candidate.name]
        if count not in self._messages_at_backtrack:
            return

        message = self._messages_at_backtrack[count]
        logger.info("INFO: %s", message.format(package_name=candidate.name))


class PipDebuggingReporter(BaseReporter):
    """A reporter that does an info log for every event it sees."""

    def starting(self) -> None:
        logger.info("Reporter.starting()")

    def starting_round(self, index: int) -> None:
        logger.info("Reporter.starting_round(%r)", index)

    def ending_round(self, index: int, state: Any) -> None:
        logger.info("Reporter.ending_round(%r, state)", index)

    def ending(self, state: Any) -> None:
        logger.info("Reporter.ending(%r)", state)

    def adding_requirement(self, requirement: Requirement, parent: Candidate) -> None:
        logger.info("Reporter.adding_requirement(%r, %r)", requirement, parent)

    def backtracking(self, candidate: Candidate) -> None:
        logger.info("Reporter.backtracking(%r)", candidate)

    def pinning(self, candidate: Candidate) -> None:
        logger.info("Reporter.pinning(%r)", candidate)


@dataclass(frozen=True)
class ResolvedCandidate:
    """Coalesce all the information pip's resolver retains about an
    installation candidate."""

    req: PkgRequirement
    download_info: URLDownloadInfo
    dependencies: Tuple[PkgRequirement, ...]
    requires_python: Optional[SpecifierSet]

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation of this install candidate."""
        return {
            "requirement": str(self.req),
            "download_info": self.download_info.to_dict(),
            "dependencies": {dep.name: str(dep) for dep in self.dependencies},
            "requires_python": str(self.requires_python)
            if self.requires_python
            else None,
        }


@dataclass
class ResolutionResult:
    """The inputs and outputs of a pip internal resolve process."""

    input_requirements: Tuple[str, ...]
    python_version: Optional[SpecifierSet] = None
    candidates: Dict[str, ResolvedCandidate] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation of the resolve process."""
        return {
            "experimental": True,
            "input_requirements": [str(req) for req in self.input_requirements],
            "python_version": str(self.python_version),
            "candidates": {
                name: info.to_dict() for name, info in self.candidates.items()
            },
        }

    @classmethod
    def _extract_hashable_resolve_input(
        cls,
        reqs: Iterable[InstallRequirement],
    ) -> Tuple[str, ...]:
        """Reconstruct the input requirements provided to the resolve.

        In theory, pip should be able to be re-run with these arguments to get the same
        resolve output. Because pip can accept URLs as well as parseable requirement
        strings on the command line, this method returns a list of strings instead of
        `PkgRequirement` instances.

        These strings are sorted so that they can be hashed and compared efficiently.
        """
        input_requirements: List[str] = []
        for ireq in reqs:
            if ireq.req:
                # If the initial requirement string contained a url (retained in
                # InstallRequirement.link), add it back to the requirement string
                # included in the JSON report.
                if ireq.link:
                    req_string = f"{ireq.req}@{ireq.link.url}"
                else:
                    req_string = str(ireq.req)
            else:
                # If the InstallRequirement has no Requirement information, don't
                # produce a Requirement string, but simply reproduce the URL.
                assert ireq.link
                req_string = ireq.link.url

            input_requirements.append(req_string)

        return tuple(sorted(input_requirements))

    @classmethod
    def generate_resolve_report(
        cls,
        input_requirements: Iterable[InstallRequirement],
        resolved_requirement_set: RequirementSetWithCandidates,
    ) -> "ResolutionResult":
        """Process the resolve to obtain a JSON-serializable/pretty-printable report."""
        hashable_input = cls._extract_hashable_resolve_input(input_requirements)
        resolution_result = cls(input_requirements=hashable_input)

        # (1) Scan all the install candidates from `.candidates`.
        for candidate in resolved_requirement_set.candidates.mapping.values():

            # (2) Map each install candidate back to a specific install requirement from
            #     `.requirements`.
            req = resolved_requirement_set.requirements.get(candidate.name, None)
            if req is None:
                # Pip will impose an implicit `Requires-Python` constraint upon the
                # whole resolve corresponding to the value of the `--python-version`
                # argument. This shows up as an installation candidate which does not
                # correspond to any requirement from the requirement set.
                if isinstance(candidate, RequiresPythonCandidate):
                    # This candidate should only appear once.
                    assert resolution_result.python_version is None
                    # Generate a serializable `SpecifierSet` instance.
                    resolution_result.python_version = produce_exact_version_specifier(
                        str(candidate.version)
                    )
                    continue

                # All other types of installation candidates are expected to be found
                # within the resolved requirement set.
                raise TypeError(
                    f"unknown candidate not found in requirement set: {candidate}"
                )
            assert req.name is not None
            assert req.link is not None
            # Each project name should only be fulfilled by a single
            # installation candidate.
            assert req.name not in resolution_result.candidates

            # (3) Scan the dependencies of the installation candidates, which cover both
            #     normal dependencies as well as Requires-Python information.
            requires_python: Optional[SpecifierSet] = None
            dependencies: List[PkgRequirement] = []
            for maybe_dep in candidate.iter_dependencies(with_requires=True):
                # It's unclear why `.iter_dependencies()` may occasionally yield `None`.
                if maybe_dep is None:
                    continue

                # There will only ever be one python version constraint for each
                # candidate, if any. We extract the version specifier.
                if isinstance(maybe_dep, RequiresPythonRequirement):
                    requires_python = maybe_dep.specifier
                    continue

                # Convert the 2020 resolver-internal Requirement subclass instance into
                # a `packaging.requirements.Requirement` instance.
                maybe_req = maybe_dep.as_serializable_requirement()
                if maybe_req is None:
                    continue

                # For `ExplicitRequirement`s only, we want to make sure we propagate any
                # source URL into a dependency's `packaging.requirements.Requirement`
                # instance.
                if isinstance(maybe_dep, ExplicitRequirement):
                    dep_candidate = maybe_dep.candidate
                    if maybe_req.url is None and isinstance(
                        dep_candidate, LinkCandidate
                    ):
                        assert dep_candidate.source_link is not None
                        maybe_req = PkgRequirement(
                            f"{maybe_req}@{dep_candidate.source_link.url}"
                        )

                dependencies.append(maybe_req)

            # Mutate the candidates dictionary to add this candidate after processing
            # any dependencies and python version requirement.
            resolution_result.candidates[req.name] = ResolvedCandidate(
                req=candidate.as_serializable_requirement(),
                download_info=URLDownloadInfo.from_link_with_source(
                    LinkWithSource(
                        req.link,
                        source_dir=req.source_dir,
                        link_is_in_wheel_cache=req.original_link_is_in_wheel_cache,
                    )
                ),
                dependencies=tuple(dependencies),
                requires_python=requires_python,
            )

        return resolution_result

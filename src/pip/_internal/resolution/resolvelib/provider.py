from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.resolvelib.providers import AbstractProvider

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

from .candidates import is_already_installed

if MYPY_CHECK_RUNNING:
    from typing import Any, Dict, Optional, Sequence, Set, Tuple, Union

    from pip._internal.req.req_install import InstallRequirement
    from pip._vendor.packaging.version import _BaseVersion

    from .base import Requirement, Candidate
    from .factory import Factory

# Notes on the relationship between the provider, the factory, and the
# candidate and requirement classes.
#
# The provider is a direct implementation of the resolvelib class. Its role
# is to deliver the API that resolvelib expects.
#
# Rather than work with completely abstract "requirement" and "candidate"
# concepts as resolvelib does, pip has concrete classes implementing these two
# ideas. The API of Requirement and Candidate objects are defined in the base
# classes, but essentially map fairly directly to the equivalent provider
# methods. In particular, `find_matches` and `is_satisfied_by` are
# requirement methods, and `get_dependencies` is a candidate method.
#
# The factory is the interface to pip's internal mechanisms. It is stateless,
# and is created by the resolver and held as a property of the provider. It is
# responsible for creating Requirement and Candidate objects, and provides
# services to those objects (access to pip's finder and preparer).


class PipProvider(AbstractProvider):
    def __init__(
        self,
        factory,  # type: Factory
        constraints,  # type: Dict[str, SpecifierSet]
        ignore_dependencies,  # type: bool
        upgrade_strategy,  # type: str
        roots,  # type: Set[str]
    ):
        # type: (...) -> None
        self._factory = factory
        self._constraints = constraints
        self._ignore_dependencies = ignore_dependencies
        self._upgrade_strategy = upgrade_strategy
        self.roots = roots

    def sort_matches(self, matches):
        # type: (Sequence[Candidate]) -> Sequence[Candidate]

        # The requirement is responsible for returning a sequence of potential
        # candidates, one per version. The provider handles the logic of
        # deciding the order in which these candidates should be passed to
        # the resolver.

        # The `matches` argument is a sequence of candidates, one per version,
        # which are potential options to be installed. The requirement will
        # have already sorted out whether to give us an already-installed
        # candidate or a version from PyPI (i.e., it will deal with options
        # like --force-reinstall and --ignore-installed).

        # We now work out the correct order.
        #
        # 1. If no other considerations apply, later versions take priority.
        # 2. An already installed distribution is preferred over any other,
        #    unless the user has requested an upgrade.
        #    Upgrades are allowed when:
        #    * The --upgrade flag is set, and
        #      - The project was specified on the command line, or
        #      - The project is a dependency and the "eager" upgrade strategy
        #        was requested.

        def _eligible_for_upgrade(name):
            # type: (str) -> bool
            if self._upgrade_strategy == "eager":
                return True
            elif self._upgrade_strategy == "only-if-needed":
                return (name in self.roots)
            return False

        def keep_installed(c):
            # type: (Candidate) -> int
            """Give priority to an installed version?"""
            if not is_already_installed(c):
                return 0

            if _eligible_for_upgrade(c.name):
                return 0

            return 1

        def key(c):
            # type: (Candidate) -> Tuple[int, _BaseVersion]
            return (keep_installed(c), c.version)

        return sorted(matches, key=key)

    def get_install_requirement(self, c):
        # type: (Candidate) -> Optional[InstallRequirement]
        return c.get_install_requirement()

    def identify(self, dependency):
        # type: (Union[Requirement, Candidate]) -> str
        return dependency.name

    def get_preference(
        self,
        resolution,  # type: Optional[Candidate]
        candidates,  # type: Sequence[Candidate]
        information  # type: Sequence[Tuple[Requirement, Candidate]]
    ):
        # type: (...) -> Any
        # Use the "usual" value for now
        return len(candidates)

    def find_matches(self, requirement):
        # type: (Requirement) -> Sequence[Candidate]
        constraint = self._constraints.get(requirement.name, SpecifierSet())
        matches = requirement.find_matches(constraint)
        return self.sort_matches(matches)

    def is_satisfied_by(self, requirement, candidate):
        # type: (Requirement, Candidate) -> bool
        return requirement.is_satisfied_by(candidate)

    def get_dependencies(self, candidate):
        # type: (Candidate) -> Sequence[Requirement]
        if self._ignore_dependencies:
            return []
        return candidate.get_dependencies()

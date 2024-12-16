import collections
import math
from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Sequence,
    Set,
    TypeVar,
    Union,
)

from pip._vendor.resolvelib.providers import AbstractProvider

from .base import Candidate, Constraint, Requirement
from .candidates import REQUIRES_PYTHON_IDENTIFIER
from .factory import Factory

if TYPE_CHECKING:
    from pip._vendor.resolvelib.providers import Preference
    from pip._vendor.resolvelib.resolvers import RequirementInformation

    PreferenceInformation = RequirementInformation[Requirement, Candidate]

    _ProviderBase = AbstractProvider[Requirement, Candidate, str]
else:
    _ProviderBase = AbstractProvider

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


D = TypeVar("D")
V = TypeVar("V")


def _get_with_identifier(
    mapping: Mapping[str, V],
    identifier: str,
    default: D,
) -> Union[D, V]:
    """Get item from a package name lookup mapping with a resolver identifier.

    This extra logic is needed when the target mapping is keyed by package
    name, which cannot be directly looked up with an identifier (which may
    contain requested extras). Additional logic is added to also look up a value
    by "cleaning up" the extras from the identifier.
    """
    if identifier in mapping:
        return mapping[identifier]
    # HACK: Theoretically we should check whether this identifier is a valid
    # "NAME[EXTRAS]" format, and parse out the name part with packaging or
    # some regular expression. But since pip's resolver only spits out three
    # kinds of identifiers: normalized PEP 503 names, normalized names plus
    # extras, and Requires-Python, we can cheat a bit here.
    name, open_bracket, _ = identifier.partition("[")
    if open_bracket and name in mapping:
        return mapping[name]
    return default


def _extract_names_from_causes_and_parents(
    causes: Iterable["PreferenceInformation"],
) -> Set[str]:
    """
    Utility function to extract names from the causes and their parent packages

    :params causes: An iterable of PreferenceInformation

    Returns a set of strings, each representing the name of a requirement or
    its parent package that was in causes
    """
    causes_names = set()
    for cause in causes:
        causes_names.add(cause.requirement.name)
        if cause.parent:
            causes_names.add(cause.parent.name)

    return causes_names


def _causes_with_conflicting_parent(
    causes: Iterable["PreferenceInformation"],
) -> List["PreferenceInformation"]:
    """
    Identifies causes that conflict because their parent package requirements
    are not satisfied by another cause, or vice versa.

    :params causes: An iterable  sequence of PreferenceInformation

    Returns a list of PreferenceInformation objects that represent the causes
    where their parent conflicts
    """
    # Avoid duplication by keeping track of already identified conflicting
    # causes by their id
    conflicting_causes_by_id: dict[int, "PreferenceInformation"] = {}
    all_causes_by_id = {id(c): c for c in causes}

    # Map cause IDs and parent packages by parent name for quick lookup
    causes_ids_and_parents_by_parent_name: dict[
        str, list[tuple[int, Candidate]]
    ] = collections.defaultdict(list)
    for cause_id, cause in all_causes_by_id.items():
        if cause.parent:
            causes_ids_and_parents_by_parent_name[cause.parent.name].append(
                (cause_id, cause.parent)
            )

    # Identify a cause's requirement conflicts with another cause's parent
    for cause_id, cause in all_causes_by_id.items():
        if cause_id in conflicting_causes_by_id:
            continue

        cause_id_and_parents = causes_ids_and_parents_by_parent_name.get(
            cause.requirement.name
        )
        if not cause_id_and_parents:
            continue

        for other_cause_id, parent in cause_id_and_parents:
            if not cause.requirement.is_satisfied_by(parent):
                conflicting_causes_by_id[cause_id] = cause
                conflicting_causes_by_id[other_cause_id] = all_causes_by_id[
                    other_cause_id
                ]

    return list(conflicting_causes_by_id.values())


def _first_causes_with_no_candidates(
    causes: Sequence["PreferenceInformation"],
    candidates: Mapping[str, Iterator[Candidate]],
) -> List["PreferenceInformation"]:
    """
    Checks for causes that have no possible candidates to satisfy their
    requirements. Returns first causes found as iterating candidates can
    be expensive due to downloading and building packages.

    :params causes: A sequence of PreferenceInformation
    :params candidates: A mapping of package names to iterators of their candidates

    Returns a list containing the first pair of PreferenceInformation objects
    that were found which had no satisfying candidates, else if all causes
    had at least some satisfying candidate an empty list is returned.
    """
    # Group causes by package name to reduce the comparison complexity.
    causes_by_name: dict[str, list["PreferenceInformation"]] = collections.defaultdict(
        list
    )
    for cause in causes:
        causes_by_name[cause.requirement.project_name].append(cause)

    # Check for cause pairs within the same package that have incompatible specifiers.
    for cause_name, causes_list in causes_by_name.items():
        if len(causes_list) < 2:
            continue

        while causes_list:
            cause = causes_list.pop()
            candidate = cause.requirement.get_candidate_lookup()[1]
            if candidate is None:
                continue

            for other_cause in causes_list:
                other_candidate = other_cause.requirement.get_candidate_lookup()[1]
                if other_candidate is None:
                    continue

                # Check if no candidate can match the combined specifier
                combined_specifier = candidate.specifier & other_candidate.specifier
                possible_candidates = candidates.get(cause_name)

                # If no candidates have been provided then by default the
                # causes have no candidates
                if possible_candidates is None:
                    return [cause, other_cause]

                # Use any and contains version here instead of filter so
                # if a version is found that matches it will short curcuit
                # iterating through possible candidates
                if not any(
                    combined_specifier.contains(c.version) for c in possible_candidates
                ):
                    return [cause, other_cause]

    return []


class PipProvider(_ProviderBase):
    """Pip's provider implementation for resolvelib.

    :params constraints: A mapping of constraints specified by the user. Keys
        are canonicalized project names.
    :params ignore_dependencies: Whether the user specified ``--no-deps``.
    :params upgrade_strategy: The user-specified upgrade strategy.
    :params user_requested: A set of canonicalized package names that the user
        supplied for pip to install/upgrade.
    """

    def __init__(
        self,
        factory: Factory,
        constraints: Dict[str, Constraint],
        ignore_dependencies: bool,
        upgrade_strategy: str,
        user_requested: Dict[str, int],
    ) -> None:
        self._factory = factory
        self._constraints = constraints
        self._ignore_dependencies = ignore_dependencies
        self._upgrade_strategy = upgrade_strategy
        self._user_requested = user_requested
        self._known_depths: Dict[str, float] = collections.defaultdict(lambda: math.inf)

    def identify(self, requirement_or_candidate: Union[Requirement, Candidate]) -> str:
        return requirement_or_candidate.name

    def get_preference(
        self,
        identifier: str,
        resolutions: Mapping[str, Candidate],
        candidates: Mapping[str, Iterator[Candidate]],
        information: Mapping[str, Iterable["PreferenceInformation"]],
        backtrack_causes: Sequence["PreferenceInformation"],
    ) -> "Preference":
        """Produce a sort key for given requirement based on preference.

        The lower the return value is, the more preferred this group of
        arguments is.

        Currently pip considers the following in order:

        * Prefer if any of the known requirements is "direct", e.g. points to an
          explicit URL.
        * If equal, prefer if any requirement is "pinned", i.e. contains
          operator ``===`` or ``==``.
        * If equal, calculate an approximate "depth" and resolve requirements
          closer to the user-specified requirements first. If the depth cannot
          by determined (eg: due to no matching parents), it is considered
          infinite.
        * Order user-specified requirements by the order they are specified.
        * If equal, prefers "non-free" requirements, i.e. contains at least one
          operator, such as ``>=`` or ``<``.
        * If equal, order alphabetically for consistency (helps debuggability).
        """
        try:
            next(iter(information[identifier]))
        except StopIteration:
            # There is no information for this identifier, so there's no known
            # candidates.
            has_information = False
        else:
            has_information = True

        if has_information:
            lookups = (r.get_candidate_lookup() for r, _ in information[identifier])
            candidate, ireqs = zip(*lookups)
        else:
            candidate, ireqs = None, ()

        operators = [
            specifier.operator
            for specifier_set in (ireq.specifier for ireq in ireqs if ireq)
            for specifier in specifier_set
        ]

        direct = candidate is not None
        pinned = any(op[:2] == "==" for op in operators)
        unfree = bool(operators)

        try:
            requested_order: Union[int, float] = self._user_requested[identifier]
        except KeyError:
            requested_order = math.inf
            if has_information:
                parent_depths = (
                    self._known_depths[parent.name] if parent is not None else 0.0
                    for _, parent in information[identifier]
                )
                inferred_depth = min(d for d in parent_depths) + 1.0
            else:
                inferred_depth = math.inf
        else:
            inferred_depth = 1.0
        self._known_depths[identifier] = inferred_depth

        requested_order = self._user_requested.get(identifier, math.inf)

        # Requires-Python has only one candidate and the check is basically
        # free, so we always do it first to avoid needless work if it fails.
        requires_python = identifier == REQUIRES_PYTHON_IDENTIFIER

        # Prefer the causes of backtracking on the assumption that the problem
        # resolving the dependency tree is related to the failures that caused
        # the backtracking
        backtrack_cause = self.is_backtrack_cause(identifier, backtrack_causes)

        return (
            not requires_python,
            not direct,
            not pinned,
            not backtrack_cause,
            inferred_depth,
            requested_order,
            not unfree,
            identifier,
        )

    def find_matches(
        self,
        identifier: str,
        requirements: Mapping[str, Iterator[Requirement]],
        incompatibilities: Mapping[str, Iterator[Candidate]],
    ) -> Iterable[Candidate]:
        def _eligible_for_upgrade(identifier: str) -> bool:
            """Are upgrades allowed for this project?

            This checks the upgrade strategy, and whether the project was one
            that the user specified in the command line, in order to decide
            whether we should upgrade if there's a newer version available.

            (Note that we don't need access to the `--upgrade` flag, because
            an upgrade strategy of "to-satisfy-only" means that `--upgrade`
            was not specified).
            """
            if self._upgrade_strategy == "eager":
                return True
            elif self._upgrade_strategy == "only-if-needed":
                user_order = _get_with_identifier(
                    self._user_requested,
                    identifier,
                    default=None,
                )
                return user_order is not None
            return False

        constraint = _get_with_identifier(
            self._constraints,
            identifier,
            default=Constraint.empty(),
        )
        return self._factory.find_candidates(
            identifier=identifier,
            requirements=requirements,
            constraint=constraint,
            prefers_installed=(not _eligible_for_upgrade(identifier)),
            incompatibilities=incompatibilities,
            is_satisfied_by=self.is_satisfied_by,
        )

    @lru_cache(maxsize=None)
    def is_satisfied_by(self, requirement: Requirement, candidate: Candidate) -> bool:
        return requirement.is_satisfied_by(candidate)

    def get_dependencies(self, candidate: Candidate) -> Sequence[Requirement]:
        with_requires = not self._ignore_dependencies
        return [r for r in candidate.iter_dependencies(with_requires) if r is not None]

    @staticmethod
    def is_backtrack_cause(
        identifier: str, backtrack_causes: Sequence["PreferenceInformation"]
    ) -> bool:
        for backtrack_cause in backtrack_causes:
            if identifier == backtrack_cause.requirement.name:
                return True
            if backtrack_cause.parent and identifier == backtrack_cause.parent.name:
                return True
        return False

    def narrow_requirement_selection(
        self,
        identifiers: Iterable[str],
        resolutions: Mapping[str, Candidate],
        candidates: Mapping[str, Iterator[Candidate]],
        information: Mapping[str, Iterable["PreferenceInformation"]],
        backtrack_causes: Sequence["PreferenceInformation"],
    ) -> Iterable[str]:
        """
        Narrows down the selection of requirements to consider for the next
        resolution step.

        This method uses principles of conflict-driven clause learning (CDCL)
        to focus on the closest conflicts first.

        :params identifiers: Iterable of requirement names currently under
            consideration.
        :params resolutions: Current mapping of resolved package identifiers
            to their selected candidates.
        :params candidates: Mapping of each package's possible candidates.
        :params information: Mapping of requirement information for each package.
        :params backtrack_causes: Sequence of requirements, if non-empty,
            were the cause of the resolver backtracking

        Returns:
            An iterable of requirement names that the resolver will use to
            limit the next step of resolution
        """

        # If there are 2 or less causes then finding conflicts between
        # them is not required as there will always be a minumum of two
        # conflicts
        if len(backtrack_causes) < 3:
            return identifiers

        # First, try to resolve direct causes based on conflicting parent packages
        direct_causes = _causes_with_conflicting_parent(backtrack_causes)
        if not direct_causes:
            # If no conflicting parent packages found try to find some causes
            # that share the same requirement name but no common candidate,
            # we take the first one of these as iterating through candidates
            # is potentially expensive
            direct_causes = _first_causes_with_no_candidates(
                backtrack_causes, candidates
            )
        if direct_causes:
            backtrack_causes = direct_causes

        # Filter identifiers based on the narrowed down causes.
        unsatisfied_causes_names = set(
            identifiers
        ) & _extract_names_from_causes_and_parents(backtrack_causes)

        return unsatisfied_causes_names if unsatisfied_causes_names else identifiers

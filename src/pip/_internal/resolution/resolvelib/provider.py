import collections
import math
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
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


def causes_with_conflicting_parent(
    causes: Sequence["PreferenceInformation"],
) -> Sequence["PreferenceInformation"]:
    """Given causes return which causes conflict because their parent
    is not satisfied by another cause, or another causes's parent is
    not satisfied by them
    """
    # To avoid duplication keeps track of already found conflicting cause by it's id
    conflicting_causes_by_id: dict[int, "PreferenceInformation"] = {}
    all_causes_by_id = {id(c): c for c in causes}

    # Build a relationship between causes, cause ids, and cause parent names
    causes_ids_and_parents_by_parent_name: dict[
        str, list[tuple[int, Candidate]]
    ] = collections.defaultdict(list)
    for cause_id, cause in all_causes_by_id.items():
        if cause.parent:
            causes_ids_and_parents_by_parent_name[cause.parent.name].append(
                (cause_id, cause.parent)
            )

    # Check each cause and see if conflicts with the parent of another cause
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


def causes_with_no_candidates(
    causes: Sequence["PreferenceInformation"],
    candidates: Mapping[str, Iterator[Candidate]],
) -> Sequence["PreferenceInformation"]:
    """Given causes return a cause pair that has no possible candidates,
    if such a cause pair exists

    Does not return all possible causes that have no possible candidates
    because searching candidates can be expensive and throw exceptions"""
    # Group causes by name first to avoid large O(n^2) comparison
    causes_by_name: dict[str, list["PreferenceInformation"]] = collections.defaultdict(
        list
    )
    for cause in causes:
        causes_by_name[cause.requirement.project_name].append(cause)

    # Check each cause that has the same name, and check if their
    # their combined specifiers have no candidates
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

                # If no candidates have been provided then by default
                # the causes have no candidates
                if possible_candidates is None:
                    return [cause, other_cause]

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

        return (
            not requires_python,
            not direct,
            not pinned,
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
        )

    def is_satisfied_by(self, requirement: Requirement, candidate: Candidate) -> bool:
        return requirement.is_satisfied_by(candidate)

    def get_dependencies(self, candidate: Candidate) -> Sequence[Requirement]:
        with_requires = not self._ignore_dependencies
        return [r for r in candidate.iter_dependencies(with_requires) if r is not None]

    def filter_unsatisfied_names(
        self,
        unsatisfied_names: Iterable[str],
        resolutions: Mapping[str, Candidate],
        candidates: Mapping[str, Iterator[Candidate]],
        information: Mapping[str, Iterable["PreferenceInformation"]],
        backtrack_causes: Sequence["PreferenceInformation"],
    ) -> Iterable[str]:
        """
        Prefer backtracking on unsatisfied names that are conficting
        causes, or secondly are causes
        """
        if not backtrack_causes:
            return unsatisfied_names

        # Check if causes are conflicting, conflicting parents are
        # checked before no candidates because "causes_with_no_candidates"
        # may download additional candidates and extract their metadata,
        # which could be large wheels or sdists which fail to compile
        if len(backtrack_causes) > 2:
            _conflicting_causes = causes_with_conflicting_parent(backtrack_causes)
            if _conflicting_causes:
                backtrack_causes = _conflicting_causes
            else:
                _conflicting_causes = causes_with_no_candidates(
                    backtrack_causes, candidates
                )
                if _conflicting_causes:
                    backtrack_causes = _conflicting_causes
            del _conflicting_causes

        # Extract the causes and parents names
        causes_names = set()
        for cause in backtrack_causes:
            causes_names.add(cause.requirement.name)
            if cause.parent:
                causes_names.add(cause.parent.name)

        unsatisfied_causes_names = set(unsatisfied_names) & causes_names

        if unsatisfied_causes_names:
            return unsatisfied_causes_names

        return unsatisfied_names

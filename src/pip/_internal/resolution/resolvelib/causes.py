from .base import Causes, Requirement, Candidate
from typing import Generator, List, Sequence, Set, Any
from pip._vendor.resolvelib.resolvers import Criterion
from pip._vendor.resolvelib.resolvers import RequirementInformation

PreferenceInformation = RequirementInformation[Requirement, Candidate]



class BacktrackCauses(Causes):
    def __init__(self, causes: List[Any]) -> None:
        self.causes = causes
        self._names: Set[str] = set()
        self._information: Sequence[PreferenceInformation] = []

    @property
    def names(self) -> Set[str]:
        if self._names:
            return self._names

        self._names = set(self._causes_to_names())
        return self._names

    @property
    def information(self) -> Sequence[PreferenceInformation]:
        if self._information:
            return self._information

        self._information = [i for c in self.causes for i in c.information]
        return self._information

    def _causes_to_names(self) -> Generator[str, None, None]:
        for c in self.information:
            yield c.requirement.name
            if c.parent:
                yield c.parent.name

    def __copy__(self) -> "BacktrackCauses":
        return BacktrackCauses(causes=self.causes.copy())

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, BacktrackCauses):
            return NotImplemented
        return self.causes == other.causes

    def __bool__(self) -> bool:
        return bool(self.causes)

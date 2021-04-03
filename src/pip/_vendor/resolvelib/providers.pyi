from typing import (
    Any,
    Collection,
    Generic,
    Iterable,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Union,
)

from .reporters import BaseReporter
from .resolvers import RequirementInformation
from .structs import (
    KT,
    RT,
    CT,
    IterableView,
    Matches,
)

class Preference(Protocol):
    def __lt__(self, __other: Any) -> bool: ...

class AbstractProvider(Generic[RT, CT, KT]):
    def identify(self, requirement_or_candidate: Union[RT, CT]) -> KT: ...
    def get_preference(
        self,
        resolution: Optional[CT],
        candidates: IterableView[CT],
        information: Collection[RequirementInformation[RT, CT]],
    ) -> Preference: ...
    def find_matches(self, requirements: Sequence[RT]) -> Matches: ...
    def is_satisfied_by(self, requirement: RT, candidate: CT) -> bool: ...
    def get_dependencies(self, candidate: CT) -> Iterable[RT]: ...

class AbstractResolver(Generic[RT, CT, KT]):
    base_exception = Exception
    provider: AbstractProvider[RT, CT, KT]
    reporter: BaseReporter
    def __init__(
        self, provider: AbstractProvider[RT, CT, KT], reporter: BaseReporter
    ): ...

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import List, Optional


class BaseDistribution:
    @property
    def installer(self):
        # type: () -> str
        raise NotImplementedError()


class BaseEnvironment:
    """An environment containing distributions to introspect."""

    @classmethod
    def default(cls):
        # type: () -> BaseEnvironment
        raise NotImplementedError()

    @classmethod
    def from_paths(cls, paths):
        # type: (List[str]) -> BaseEnvironment
        raise NotImplementedError()

    def get_distribution(self, name):
        # type: (str) -> Optional[BaseDistribution]
        raise NotImplementedError()

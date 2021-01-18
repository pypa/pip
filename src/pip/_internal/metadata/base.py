from pip._internal.utils.misc import stdlib_pkgs  # TODO: Move definition here.
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Container, Iterator, List, Optional


class BaseDistribution:
    @property
    def canonical_name(self):
        # type: () -> str
        raise NotImplementedError()

    @property
    def installer(self):
        # type: () -> str
        raise NotImplementedError()

    @property
    def editable(self):
        # type: () -> bool
        raise NotImplementedError()

    @property
    def local(self):
        # type: () -> bool
        raise NotImplementedError()

    @property
    def in_usersite(self):
        # type: () -> bool
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
        """Given a requirement name, return the installed distributions."""
        raise NotImplementedError()

    def iter_distributions(self):
        # type: () -> Iterator[BaseDistribution]
        """Iterate through installed distributions."""
        raise NotImplementedError()

    def iter_installed_distributions(
        self,
        local_only=True,  # type: bool
        skip=stdlib_pkgs,  # type: Container[str]
        include_editables=True,  # type: bool
        editables_only=False,  # type: bool
        user_only=False,  # type: bool
    ):
        # type: (...) -> Iterator[BaseDistribution]
        """Return a list of installed distributions.

        :param local_only: If True (default), only return installations
        local to the current virtualenv, if in a virtualenv.
        :param skip: An iterable of canonicalized project names to ignore;
            defaults to ``stdlib_pkgs``.
        :param include_editables: If False, don't report editables.
        :param editables_only: If True, only report editables.
        :param user_only: If True, only report installations in the user
        site directory.
        """
        it = self.iter_distributions()
        if local_only:
            it = (d for d in it if d.local)
        if not include_editables:
            it = (d for d in it if not d.editable)
        if editables_only:
            it = (d for d in it if d.editable)
        if user_only:
            it = (d for d in it if d.in_usersite)
        return (d for d in it if d.canonical_name not in skip)

import abc
from typing import Optional

from pip._internal.index.package_finder import PackageFinder
from pip._internal.metadata.base import BaseDistribution
from pip._internal.req import InstallRequirement


class AbstractDistribution(metaclass=abc.ABCMeta):
    """A base class for handling installable artifacts.

    The requirements for anything installable are as follows:

     - we must be able to determine the requirement name
       (or we can't correctly handle the non-upgrade case).

     - for packages with setup requirements, we must also be able
       to determine their requirements without installing additional
       packages (for the same reason as run-time dependencies)

     - we must be able to create a Distribution object exposing the
       above metadata.

     - if we need to do work in the build tracker, we must be able to generate a unique
       string to identify the requirement in the build tracker.
    """

    def __init__(self, req: InstallRequirement) -> None:
        super().__init__()
        self.req = req

    @abc.abstractproperty
    def build_tracker_id(self) -> Optional[str]:
        """A string that uniquely identifies this requirement to the build tracker.

        If None, then this dist has no work to do in the build tracker, and
        ``.prepare_distribution_metadata()`` will not be called."""
        ...

    @abc.abstractmethod
    def get_metadata_distribution(self) -> BaseDistribution:
        """Generate a concrete ``BaseDistribution`` instance for this artifact.

        The implementation should also cache the result with
        ``self.req.cache_concrete_dist()`` so the distribution is available to other
        users of the ``InstallRequirement``. This method is not called within the build
        tracker context, so it should not identify any new setup requirements."""
        ...

    @abc.abstractmethod
    def prepare_distribution_metadata(
        self,
        finder: PackageFinder,
        build_isolation: bool,
        check_build_deps: bool,
    ) -> None:
        """Generate the information necessary to extract metadata from the artifact.

        This method will be executed within the context of ``BuildTracker#track()``, so
        it needs to fully identify any seutp requirements so they can be added to the
        same active set of tracked builds, while ``.get_metadata_distribution()`` takes
        care of generating and caching the ``BaseDistribution`` to expose to the rest of
        the resolve."""
        ...

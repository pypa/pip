from __future__ import annotations

from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.exceptions import CommandError


class ReleaseControl:
    """Helper for managing which release types can be installed."""

    __slots__ = ["all_releases", "only_final", "_order"]

    def __init__(
        self,
        all_releases: set[str] | None = None,
        only_final: set[str] | None = None,
    ) -> None:
        if all_releases is None:
            all_releases = set()
        if only_final is None:
            only_final = set()

        self.all_releases = all_releases
        self.only_final = only_final
        # Track the order of arguments as (attribute_name, value) tuples
        # This is used to reconstruct arguments in the correct order for subprocesses
        self._order: list[tuple[str, str]] = []

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented

        # Only compare all_releases and only_final, not _order
        # The _order list is for internal tracking and reconstruction
        return (
            self.all_releases == other.all_releases
            and self.only_final == other.only_final
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.all_releases}, {self.only_final})"

    def handle_mutual_excludes(
        self, value: str, target: set[str], other: set[str], attr_name: str
    ) -> None:
        if value.startswith("-"):
            raise CommandError(
                "--all-releases / --only-final option requires 1 argument."
            )
        new = value.split(",")
        while ":all:" in new:
            other.clear()
            target.clear()
            target.add(":all:")
            # Track :all: in order
            self._order.append((attr_name, ":all:"))
            del new[: new.index(":all:") + 1]
            # Without a none, we want to discard everything as :all: covers it
            if ":none:" not in new:
                return
        for name in new:
            if name == ":none:":
                target.clear()
                # Track :none: in order
                self._order.append((attr_name, ":none:"))
                continue
            name = canonicalize_name(name)
            other.discard(name)
            target.add(name)
            # Track package-specific setting in order
            self._order.append((attr_name, name))

    def get_ordered_args(self) -> list[tuple[str, str]]:
        """
        Get ordered list of (flag_name, value) tuples for reconstructing CLI args.

        Returns:
            List of tuples where each tuple is (attribute_name, value).
            The attribute_name is either 'all_releases' or 'only_final'.

        Example:
            [("all_releases", ":all:"), ("only_final", "simple")]
            would be reconstructed as:
            ["--all-releases", ":all:", "--only-final", "simple"]
        """
        return self._order[:]

    def allows_prereleases(self, canonical_name: str) -> bool | None:
        """
        Determine if pre-releases are allowed for a package.

        Returns:
            True: Pre-releases are allowed (package in all_releases)
            False: Only final releases allowed (package in only_final)
            None: No specific setting, use default behavior
        """
        if canonical_name in self.all_releases:
            return True
        elif canonical_name in self.only_final:
            return False
        elif ":all:" in self.all_releases:
            return True
        elif ":all:" in self.only_final:
            return False
        return None

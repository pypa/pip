import optparse
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pip._vendor import tomli
from pip._vendor.dependency_groups import resolve as resolve_dependency_group

from pip._internal.exceptions import InstallationError
from pip._internal.network.session import PipSession

if TYPE_CHECKING:
    from pip._internal.index.package_finder import PackageFinder


def parse_dependency_groups(
    groups: List[str],
    session: PipSession,
    finder: Optional["PackageFinder"] = None,
    options: Optional[optparse.Values] = None,
) -> List[str]:
    """
    Parse dependency groups data in a way which is sensitive to the `pip` context and
    raises InstallationErrors if anything goes wrong.
    """
    pyproject = _load_pyproject()

    if "dependency-groups" not in pyproject:
        raise InstallationError(
            "[dependency-groups] table was missing. Cannot resolve '--group' options."
        )
    raw_dependency_groups = pyproject["dependency-groups"]
    if not isinstance(raw_dependency_groups, dict):
        raise InstallationError(
            "[dependency-groups] table was malformed. Cannot resolve '--group' options."
        )

    try:
        return list(resolve_dependency_group(raw_dependency_groups, *groups))
    except (ValueError, TypeError, LookupError) as e:
        raise InstallationError("[dependency-groups] resolution failed: {e}") from e


def _load_pyproject() -> Dict[str, Any]:
    """
    This helper loads pyproject.toml from the current working directory.

    It does not allow specification of the path to be used and raises an
    InstallationError if the operation fails.
    """
    try:
        with open("pyproject.toml", "rb") as fp:
            return tomli.load(fp)
    except FileNotFoundError:
        raise InstallationError(
            "pyproject.toml not found. Cannot resolve '--group' options."
        )
    except tomli.TOMLDecodeError as e:
        raise InstallationError(f"Error parsing pyproject.toml: {e}") from e
    except OSError as e:
        raise InstallationError(f"Error reading pyproject.toml: {e}") from e

from pip._vendor.packaging.requirements import Requirement

from pip._internal.req.req_install import InstallRequirement
from pip._internal.resolution.resolvelib.base import Constraint
from pip._internal.utils.hashes import Hashes


def make_install_req(hash_options: dict[str, list[str]]) -> InstallRequirement:
    return InstallRequirement(
        Requirement("example"),
        comes_from=None,
        hash_options=hash_options,
    )


def test_constraint_and_intersects_hash_options_preserving_other_order() -> None:
    constraint = Constraint.from_ireq(
        make_install_req({"sha256": ["a", "b", "c", "d"]})
    )
    ireq = make_install_req({"sha256": ["d", "b"]})

    result = constraint & ireq

    assert result.hashes == Hashes({"sha256": ["b", "d"]})
    assert result.hash_options == {"sha256": ["d", "b"]}


def test_constraint_and_intersects_hash_options_uses_other_order() -> None:
    constraint = Constraint.from_ireq(make_install_req({"sha256": ["b", "d"]}))
    ireq = make_install_req({"sha256": ["d", "c", "b", "a"]})

    result = constraint & ireq

    assert result.hashes == Hashes({"sha256": ["b", "d"]})
    assert result.hash_options == {"sha256": ["d", "b"]}

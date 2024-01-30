import email.message
import itertools
from typing import List, cast
from unittest import mock

import pytest
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.version import parse as parse_version

from pip._internal.exceptions import UnsupportedWheel
from pip._internal.metadata.pkg_resources import (
    Distribution,
    Environment,
    InMemoryMetadata,
)

pkg_resources = pytest.importorskip("pip._vendor.pkg_resources")


def _dist_is_local(dist: mock.Mock) -> bool:
    return dist.kind != "global" and dist.kind != "user"


def _dist_in_usersite(dist: mock.Mock) -> bool:
    return dist.kind == "user"


@pytest.fixture(autouse=True)
def patch_distribution_lookups(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Distribution, "local", property(_dist_is_local))
    monkeypatch.setattr(Distribution, "in_usersite", property(_dist_in_usersite))


class _MockWorkingSet(List[mock.Mock]):
    def require(self, name: str) -> None:
        pass


workingset = _MockWorkingSet(
    (
        mock.Mock(test_name="global", project_name="global"),
        mock.Mock(test_name="editable", project_name="editable"),
        mock.Mock(test_name="normal", project_name="normal"),
        mock.Mock(test_name="user", project_name="user"),
    )
)

workingset_stdlib = _MockWorkingSet(
    (
        mock.Mock(test_name="normal", project_name="argparse"),
        mock.Mock(test_name="normal", project_name="wsgiref"),
    )
)


@pytest.mark.parametrize(
    "ws, req_name",
    itertools.chain(
        itertools.product(
            [workingset],
            (d.project_name for d in workingset),
        ),
        itertools.product(
            [workingset_stdlib],
            (d.project_name for d in workingset_stdlib),
        ),
    ),
)
def test_get_distribution(ws: _MockWorkingSet, req_name: str) -> None:
    """Ensure get_distribution() finds all kinds of distributions."""
    dist = Environment(ws).get_distribution(req_name)
    assert dist is not None
    assert cast(Distribution, dist)._dist.project_name == req_name


def test_get_distribution_nonexist() -> None:
    dist = Environment(workingset).get_distribution("non-exist")
    assert dist is None


def test_wheel_metadata_works() -> None:
    name = "simple"
    version = "0.1.0"
    require_a = "a==1.0"
    require_b = 'b==1.1; extra == "also_b"'
    requires = [require_a, require_b, 'c==1.2; extra == "also_c"']
    extras = ["also_b", "also_c"]
    requires_python = ">=3"

    metadata = email.message.Message()
    metadata["Name"] = name
    metadata["Version"] = version
    for require in requires:
        metadata["Requires-Dist"] = require
    for extra in extras:
        metadata["Provides-Extra"] = extra
    metadata["Requires-Python"] = requires_python

    dist = Distribution(
        pkg_resources.DistInfoDistribution(
            location="<in-memory>",
            metadata=InMemoryMetadata({"METADATA": metadata.as_bytes()}, "<in-memory>"),
            project_name=name,
        ),
        concrete=False,
    )

    assert name == dist.canonical_name == dist.raw_name
    assert parse_version(version) == dist.version
    assert set(extras) == set(dist.iter_provided_extras())
    assert [require_a] == [str(r) for r in dist.iter_dependencies()]
    assert [require_a, require_b] == [
        str(r) for r in dist.iter_dependencies(["also_b"])
    ]
    assert metadata.as_string() == dist.metadata.as_string()
    assert SpecifierSet(requires_python) == dist.requires_python


def test_wheel_metadata_throws_on_bad_unicode() -> None:
    metadata = InMemoryMetadata({"METADATA": b"\xff"}, "<in-memory>")

    with pytest.raises(UnsupportedWheel) as e:
        metadata.get_metadata("METADATA")
    assert "METADATA" in str(e.value)

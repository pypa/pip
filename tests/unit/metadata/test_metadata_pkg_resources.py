import itertools
from typing import List, cast
from unittest import mock

import pytest

from pip._internal.metadata.pkg_resources import Distribution, Environment

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

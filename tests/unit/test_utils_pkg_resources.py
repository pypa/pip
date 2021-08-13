from email.message import Message

import pytest
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.version import parse as parse_version
from pip._vendor.pkg_resources import DistInfoDistribution

from pip._internal.metadata.pkg_resources import (
    Distribution as PkgResourcesDistribution,
)
from pip._internal.utils.pkg_resources import DictMetadata


def test_dict_metadata_works():
    name = "simple"
    version = "0.1.0"
    require_a = "a==1.0"
    require_b = 'b==1.1; extra == "also_b"'
    requires = [require_a, require_b, 'c==1.2; extra == "also_c"']
    extras = ["also_b", "also_c"]
    requires_python = ">=3"

    metadata = Message()
    metadata["Name"] = name
    metadata["Version"] = version
    for require in requires:
        metadata["Requires-Dist"] = require
    for extra in extras:
        metadata["Provides-Extra"] = extra
    metadata["Requires-Python"] = requires_python

    dist = PkgResourcesDistribution(
        DistInfoDistribution(
            location="<in-memory>",
            metadata=DictMetadata({"METADATA": metadata.as_bytes()}),
            project_name=name,
        ),
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


def test_dict_metadata_throws_on_bad_unicode():
    metadata = DictMetadata({"METADATA": b"\xff"})

    with pytest.raises(UnicodeDecodeError) as e:
        metadata.get_metadata("METADATA")
    assert "METADATA" in str(e.value)

from email.message import Message

import pytest
from pip._vendor.pkg_resources import DistInfoDistribution, Requirement
from pip._vendor.six import ensure_binary

from pip._internal.utils.packaging import get_metadata, get_requires_python
from pip._internal.utils.pkg_resources import DictMetadata
from tests.lib import skip_if_python2


def test_dict_metadata_works():
    name = "simple"
    version = "0.1.0"
    require_a = "a==1.0"
    require_b = "b==1.1; extra == 'also_b'"
    requires = [require_a, require_b, "c==1.2; extra == 'also_c'"]
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

    inner_metadata = DictMetadata({
        "METADATA": ensure_binary(metadata.as_string())
    })
    dist = DistInfoDistribution(
        location="<in-memory>", metadata=inner_metadata, project_name=name
    )

    assert name == dist.project_name
    assert version == dist.version
    assert set(extras) == set(dist.extras)
    assert [Requirement.parse(require_a)] == dist.requires([])
    assert [
        Requirement.parse(require_a), Requirement.parse(require_b)
    ] == dist.requires(["also_b"])
    assert metadata.as_string() == get_metadata(dist).as_string()
    assert requires_python == get_requires_python(dist)


# Metadata is not decoded on Python 2, so no chance for error.
@skip_if_python2
def test_dict_metadata_throws_on_bad_unicode():
    metadata = DictMetadata({
        "METADATA": b"\xff"
    })

    with pytest.raises(UnicodeDecodeError) as e:
        metadata.get_metadata("METADATA")
    assert "METADATA" in str(e.value)

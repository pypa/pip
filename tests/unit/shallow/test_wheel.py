from textwrap import dedent

from pip._internal.network.shallow.wheel import (
    Context,
    ProjectName,
    WheelMetadataRequest,
)

from .util import serve_wheel

context = Context()


def _strip_carriage_returns(s):
    # type: (bytes) -> str
    return s.decode().strip().replace('\r', '')


def test_extract_metadata_from_wheel():
    name = ProjectName("asdf")
    with serve_wheel(name, version="0.0.1") as url:
        wheel_req = WheelMetadataRequest(url, project_name=name,)

        metadata_contents = context.extract_wheel_metadata(wheel_req)
        assert _strip_carriage_returns(metadata_contents.contents) == dedent(
            """\
            Metadata-Version: 2.1
            Name: asdf
            Version: 0.0.1
            Summary: UNKNOWN
            Home-page: UNKNOWN
            Author: UNKNOWN
            Author-email: UNKNOWN
            License: UNKNOWN
            Platform: UNKNOWN
            Requires-Dist: requests

            UNKNOWN
            """).strip()

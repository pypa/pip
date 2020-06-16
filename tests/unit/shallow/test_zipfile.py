import re
import zipfile

from pip._internal.network.shallow.httpfile import HttpFileRequest
from pip._internal.network.shallow.zipfile import (
    Context,
    ZipFileExtractionRequest,
    ZipMemberNameMatcher,
)
from tests.lib.path import Path

from .util import serve_zip

context = Context()

_asdf_contents = b"asdf\n"


def test_extract_file_from_deflated_zip():
    with serve_zip(
        Path("asdf.txt"), _asdf_contents, compression=zipfile.ZIP_DEFLATED
    ) as url:
        req = HttpFileRequest(url)
        http_file = context.http_context.head(req)

        zip_req = ZipFileExtractionRequest(
            http_file=http_file,
            member_pattern=ZipMemberNameMatcher(re.compile(b"asdf.txtPK")),
        )
        zip_member = context.extract_zip_member_shallow(zip_req)
        assert zip_member == _asdf_contents

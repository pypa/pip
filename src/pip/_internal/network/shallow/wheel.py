"""
Download a wheel's METADATA file over http without downloading the rest of the
wheel file.
"""

import re
from collections import namedtuple

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

from .httpfile import HttpFileRequest
from .zipfile import Context as ZipFileContext
from .zipfile import ZipFileExtractionRequest, ZipMemberNameMatcher

if MYPY_CHECK_RUNNING:
    from typing import Optional


class ProjectName(namedtuple('ProjectName', ['name'])):

    def __new__(cls, name):
        # type: (str) -> ProjectName
        assert isinstance(name, str)
        return super(ProjectName, cls).__new__(cls, name)


class WheelMetadataRequest(namedtuple('WheelMetadataRequest', [
        'url',
        'project_name',
])):
    pass


class WheelMetadataContents(namedtuple('WheelMetadataContents', ['contents'])):

    def __new__(cls, contents):
        # type: (bytes) -> WheelMetadataContents
        return super(WheelMetadataContents, cls).__new__(cls, contents)


class Context(object):

    def __init__(self, zip_context=None):
        # type: (Optional[ZipFileContext]) -> None
        self.zip_context = zip_context or ZipFileContext()

    @classmethod
    def _create_metadata_pattern(cls, project_name):
        # type: (ProjectName) -> ZipMemberNameMatcher
        sanitized_requirement_name = (
            project_name
            .name
            .lower()
            .replace("-", "_"))
        return ZipMemberNameMatcher(
            re.compile(
                ("{sanitized_requirement_name}[^/]+?.dist-info/METADATAPK"
                 .format(sanitized_requirement_name=sanitized_requirement_name)
                 .encode()),
                flags=re.IGNORECASE,
            )
        )

    def extract_wheel_metadata(self, request):
        # type: (WheelMetadataRequest) -> WheelMetadataContents
        url = request.url
        http_file = self.zip_context.http_context.head(HttpFileRequest(url))

        metadata_pattern = self._create_metadata_pattern(request.project_name)
        contents = self.zip_context.extract_zip_member_shallow(
            ZipFileExtractionRequest(
                http_file=http_file, member_pattern=metadata_pattern,
            )
        )
        return WheelMetadataContents(contents)

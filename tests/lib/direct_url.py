import os
import re
from pathlib import Path
from typing import Optional

from pip._internal.models.direct_url import DIRECT_URL_METADATA_NAME, PROVENANCE_URL_METADATA_NAME, DirectUrl
from tests.lib import TestPipResult


def get_created_direct_url_path(result: TestPipResult, pkg: str, provenance_file: bool = False) -> Optional[Path]:
    url_file_name = PROVENANCE_URL_METADATA_NAME if provenance_file else DIRECT_URL_METADATA_NAME
    direct_url_metadata_re = re.compile(
        pkg + r"-[\d\.]+\.dist-info." + url_file_name + r"$"
    )
    for filename in result.files_created:
        if direct_url_metadata_re.search(os.fspath(filename)):
            return result.test_env.base_path / filename
    return None


def get_created_direct_url(result: TestPipResult, pkg: str, *, provenance_file: bool = False) -> Optional[DirectUrl]:
    direct_url_path = get_created_direct_url_path(result, pkg, provenance_file=provenance_file)
    if direct_url_path:
        with open(direct_url_path) as f:
            return DirectUrl.from_json(f.read())
    return None

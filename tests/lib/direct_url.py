import os
import re
from pathlib import Path
from typing import Optional

from pip._internal.models.direct_url import DIRECT_URL_METADATA_NAME, DirectUrl

from tests.lib import TestPipResult


def get_created_direct_url_path(result: TestPipResult, pkg: str) -> Optional[Path]:
    direct_url_metadata_re = re.compile(
        pkg + r"-[\d\.]+\.dist-info." + DIRECT_URL_METADATA_NAME + r"$"
    )
    for filename in result.files_created:
        if direct_url_metadata_re.search(os.fspath(filename)):
            return result.test_env.base_path / filename
    return None


def get_created_direct_url(result: TestPipResult, pkg: str) -> Optional[DirectUrl]:
    direct_url_path = get_created_direct_url_path(result, pkg)
    if direct_url_path:
        with open(direct_url_path) as f:
            return DirectUrl.from_json(f.read())
    return None

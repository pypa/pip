import re
from typing import Optional

from pip._internal.models.direct_url import DIRECT_URL_METADATA_NAME, DirectUrl
from tests.lib import TestPipResult


def get_created_direct_url(result: TestPipResult, pkg: str) -> Optional[DirectUrl]:
    direct_url_metadata_re = re.compile(
        pkg + r"-[\d\.]+\.dist-info." + DIRECT_URL_METADATA_NAME + r"$"
    )
    for filename in result.files_created:
        if direct_url_metadata_re.search(filename):
            direct_url_path = result.test_env.base_path / filename
            with open(direct_url_path) as f:
                return DirectUrl.from_json(f.read())
    return None

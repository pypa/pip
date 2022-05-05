from typing import Optional

from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.link import Link


def make_mock_candidate(
    version: str, yanked_reason: Optional[str] = None, hex_digest: Optional[str] = None
) -> InstallationCandidate:
    url = f"https://example.com/pkg-{version}.tar.gz"
    if hex_digest is not None:
        assert len(hex_digest) == 64
        url += f"#sha256={hex_digest}"

    link = Link(url, yanked_reason=yanked_reason)
    candidate = InstallationCandidate("mypackage", version, link)

    return candidate

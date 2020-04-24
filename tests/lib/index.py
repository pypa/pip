from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.link import Link


def make_mock_candidate(version, yanked_reason=None, hex_digest=None):
    url = 'https://example.com/pkg-{}.tar.gz'.format(version)
    if hex_digest is not None:
        assert len(hex_digest) == 64
        url += '#sha256={}'.format(hex_digest)

    link = Link(url, yanked_reason=yanked_reason)
    candidate = InstallationCandidate('mypackage', version, link)

    return candidate

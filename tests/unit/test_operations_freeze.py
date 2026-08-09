import pytest

from pip._internal.operations.freeze import _strip_auth_from_editable_requirement


@pytest.mark.parametrize(
    "requirement, expected",
    [
        (
            "git+https://example.com/repo.git@rev#egg=project",
            "git+https://example.com/repo.git@rev#egg=project",
        ),
        (
            "git+https://username:password@example.com/repo.git@rev#egg=project",
            "git+https://example.com/repo.git@rev#egg=project",
        ),
        (
            "git+https://token@example.com/repo.git@rev#egg=project",
            "git+https://example.com/repo.git@rev#egg=project",
        ),
        (
            "git+ssh://git@example.com/repo.git@rev#egg=project",
            "git+ssh://git@example.com/repo.git@rev#egg=project",
        ),
        (
            "hg+ssh://git@example.com/repo@rev#egg=project",
            "hg+ssh://git@example.com/repo@rev#egg=project",
        ),
        (
            "svn+ssh://git@example.com/repo@rev#egg=project",
            "svn+ssh://git@example.com/repo@rev#egg=project",
        ),
        (
            "bzr+ssh://git@example.com/repo@rev#egg=project",
            "bzr+ssh://git@example.com/repo@rev#egg=project",
        ),
        (
            "bzr+sftp://git@example.com/repo@rev#egg=project",
            "bzr+sftp://example.com/repo@rev#egg=project",
        ),
        (
            "git+https://git@example.com/repo.git@rev#egg=project",
            "git+https://example.com/repo.git@rev#egg=project",
        ),
        (
            "git+https://${TOKEN}@example.com/repo.git@rev#egg=project",
            "git+https://${TOKEN}@example.com/repo.git@rev#egg=project",
        ),
        (
            "git+https://${USER}:${PASSWORD}@example.com/repo.git@rev#egg=project",
            "git+https://${USER}:${PASSWORD}@example.com/repo.git@rev#egg=project",
        ),
        (
            "git+https://${USER}:password@example.com/repo.git@rev#egg=project",
            "git+https://example.com/repo.git@rev#egg=project",
        ),
        (
            "git+ssh://%67%69%74@example.com/repo.git@rev#egg=project",
            "git+ssh://example.com/repo.git@rev#egg=project",
        ),
    ],
)
def test_strip_auth_from_editable_requirement(requirement: str, expected: str) -> None:
    assert _strip_auth_from_editable_requirement(requirement) == expected

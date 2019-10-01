import pytest

from pip._internal.exceptions import InstallationError
from pip._internal.req import InstallRequirement


@pytest.mark.parametrize(
    ('source', 'expected'), [
        ("pep517_setup_and_pyproject", True),
        ("pep517_setup_only", False),
        ("pep517_pyproject_only", True),
    ],
)
def test_use_pep517(data, source, expected):
    """
    Test that we choose correctly between PEP 517 and legacy code paths
    """
    src = data.src.joinpath(source)
    req = InstallRequirement(None, None, source_dir=src)
    req.load_pyproject_toml()
    assert req.use_pep517 is expected


@pytest.mark.parametrize(
    ('source', 'msg'), [
        ("pep517_setup_and_pyproject", "specifies a build backend"),
        ("pep517_pyproject_only", "does not have a setup.py"),
    ],
)
def test_disabling_pep517_invalid(data, source, msg):
    """
    Test that we fail if we try to disable PEP 517 when it's not acceptable
    """
    src = data.src.joinpath(source)
    req = InstallRequirement(None, None, source_dir=src)

    # Simulate --no-use-pep517
    req.use_pep517 = False

    with pytest.raises(InstallationError) as e:
        req.load_pyproject_toml()

    err_msg = e.value.args[0]
    assert "Disabling PEP 517 processing is invalid" in err_msg
    assert msg in err_msg

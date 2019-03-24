import pytest

from pip._internal.exceptions import InstallationError
from pip._internal.pyproject import resolve_pyproject_toml
from pip._internal.req import InstallRequirement


@pytest.mark.parametrize('editable', [False, True])
def test_resolve_pyproject_toml__pep_517_optional(editable):
    """
    Test resolve_pyproject_toml() when has_pyproject=True but the source
    tree isn't pyproject.toml-style per PEP 517.
    """
    actual = resolve_pyproject_toml(
        build_system=None,
        has_pyproject=True,
        has_setup=True,
        use_pep517=None,
        editable=editable,
        req_name='my-package',
    )
    expected = (
        ['setuptools>=40.8.0', 'wheel'],
        'setuptools.build_meta:__legacy__',
        [],
    )
    assert actual == expected


@pytest.mark.parametrize(
    'has_pyproject, has_setup, use_pep517, build_system, expected_err', [
        # Test pyproject.toml with no setup.py.
        (True, False, None, None, 'has a pyproject.toml file and no setup.py'),
        # Test "build-backend" present.
        (True, True, None, {'build-backend': 'foo'},
         'has a pyproject.toml file with a "build-backend" key'),
        # Test explicitly requesting PEP 517 processing.
        (True, True, True, None,
         'PEP 517 processing was explicitly requested'),
    ]
)
def test_resolve_pyproject_toml__editable_and_pep_517_required(
    has_pyproject, has_setup, use_pep517, build_system, expected_err,
):
    """
    Test that passing editable=True raises an error if PEP 517 processing
    is required.
    """
    with pytest.raises(InstallationError) as excinfo:
        resolve_pyproject_toml(
            build_system=build_system,
            has_pyproject=has_pyproject,
            has_setup=has_setup,
            use_pep517=use_pep517,
            editable=True,
            req_name='my-package',
        )
    err_args = excinfo.value.args
    assert len(err_args) == 1
    msg = err_args[0]
    assert msg.startswith(
        "Error installing 'my-package': editable mode is not supported"
    )
    assert expected_err in msg, 'full message: {}'.format(msg)


@pytest.mark.parametrize(('source', 'expected'), [
    ("pep517_setup_and_pyproject", True),
    ("pep517_setup_only", False),
    ("pep517_pyproject_only", True),
])
def test_use_pep517(data, source, expected):
    """
    Test that we choose correctly between PEP 517 and legacy code paths
    """
    src = data.src.join(source)
    req = InstallRequirement(None, None, source_dir=src)
    req.load_pyproject_toml()
    assert req.use_pep517 is expected


@pytest.mark.parametrize(('source', 'msg'), [
    ("pep517_setup_and_pyproject", "specifies a build backend"),
    ("pep517_pyproject_only", "does not have a setup.py"),
])
def test_disabling_pep517_invalid(data, source, msg):
    """
    Test that we fail if we try to disable PEP 517 when it's not acceptable
    """
    src = data.src.join(source)
    req = InstallRequirement(None, None, source_dir=src)

    # Simulate --no-use-pep517
    req.use_pep517 = False

    with pytest.raises(InstallationError) as e:
        req.load_pyproject_toml()

    err_msg = e.value.args[0]
    assert "Disabling PEP 517 processing is invalid" in err_msg
    assert msg in err_msg

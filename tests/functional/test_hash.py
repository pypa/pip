"""Tests for the ``pip hash`` command"""


def test_basic_hash(script, tmpdir):
    """Run 'pip hash' through its default behavior."""
    expected = (
        "--hash=sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425"
        "e73043362938b9824"
    )
    result = script.pip("hash", _hello_file(tmpdir))
    assert expected in str(result)


def test_good_algo_option(script, tmpdir):
    """Make sure the -a option works."""
    expected = (
        "--hash=sha512:9b71d224bd62f3785d96d46ad3ea3d73319bfbc2890caad"
        "ae2dff72519673ca72323c3d99ba5c11d7c7acc6e14b8c5da0c4663475c2e"
        "5c3adef46f73bcdec043"
    )
    result = script.pip("hash", "-a", "sha512", _hello_file(tmpdir))
    assert expected in str(result)


def test_bad_algo_option(script, tmpdir):
    """Make sure the -a option raises an error when given a bad operand."""
    result = script.pip(
        "hash", "-a", "invalidname", _hello_file(tmpdir), expect_error=True
    )
    assert "invalid choice: 'invalidname'" in str(result)


def _hello_file(tmpdir):
    """Return a temp file to hash containing "hello"."""
    file = tmpdir / "hashable"
    file.write_text("hello")
    return file

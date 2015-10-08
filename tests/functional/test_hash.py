def test_basic(script, tmpdir):
    """Run 'pip hash' through its paces."""
    archive = tmpdir / 'hashable'
    archive.write('hello')
    result = script.pip('hash', archive)
    expected = ('--hash=sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425'
                'e73043362938b9824')
    assert expected in str(result)

import pytest

from pip._internal import pep425tags


@pytest.mark.parametrize('expected_text', [
    'sys.executable: ',
    'sys.getdefaultencoding: ',
    'sys.getfilesystemencoding: ',
    'locale.getpreferredencoding: ',
    'sys.platform: ',
    'sys.implementation:',
    'REQUESTS_CA_BUNDLE: ',
    'CURL_CA_BUNDLE: ',
    'pip._vendor.certifi.where(): ',
    '\'cert\' configuration value: ',
])
def test_debug(script, expected_text):
    """
    Check that certain strings are present in the output.
    """
    args = ['debug']
    result = script.pip(*args, allow_stderr_warning=True)
    stdout = result.stdout

    assert expected_text in stdout


@pytest.mark.parametrize(
    'args',
    [
        [],
        ['--verbose'],
    ]
)
def test_debug__tags(script, args):
    """
    Check the compatible tag output.
    """
    args = ['debug'] + args
    result = script.pip(*args, allow_stderr_warning=True)
    stdout = result.stdout

    tags = pep425tags.get_supported()
    expected_tag_header = 'Compatible tags: {}'.format(len(tags))
    assert expected_tag_header in stdout

    show_verbose_note = '--verbose' not in args
    assert (
        '...\n  [First 10 tags shown. Pass --verbose to show all.]' in stdout
    ) == show_verbose_note


@pytest.mark.parametrize(
    'args, expected',
    [
        (['--python-version', '3.7'], "(target: version_info='3.7')"),
    ]
)
def test_debug__target_options(script, args, expected):
    """
    Check passing target-related options.
    """
    args = ['debug'] + args
    result = script.pip(*args, allow_stderr_warning=True)
    stdout = result.stdout

    assert 'Compatible tags: ' in stdout
    assert expected in stdout

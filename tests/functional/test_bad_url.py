# test the error message returned by pip when
# a bad "file:" URL is passed to it.

from typing import Tuple


def get_url_error_message(script: Any, fake_file: str) -> Tuple[str, str, int]:
    # this makes pip to react using
    # subprocess. It must fail, so then
    # we can test the error message.
    proc = script.pip("install", "-r", fake_file, expect_error=True)
    expected_message = "ERROR: 404 Client Error: FileNotFoundError for url: "
    return proc.stderr, expected_message, proc.returncode


def test_filenotfound_error_message(script: Any) -> None:
    # Test the error message returned when using a bad 'file:' URL.
    file = get_random_pathname()
    # generate a command
    # make it fail to get an error message by running "pip install -r nonexistent_file"
    msg, expected, code = get_url_error_message(script, "nonexistent_file")
    # assert that "msg" starts with "expected"
    assert code == 1
    assert msg.startswith(expected)

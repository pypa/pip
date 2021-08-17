# test the error message returned by pip when
# a bad "file:" URL is passed to it.

from typing import Any


def test_filenotfound_error_message(script: Any) -> None:
    # Test the error message returned when using a bad 'file:' URL.
    # make pip to fail and get an error message
    # by running "pip install -r file:nonexistent_file"
    proc = script.pip("install", "-r", "file:unexistent_file", expect_error=True)
    expected = "ERROR: 404 Client Error: FileNotFoundError for url: "
    msg, code = proc.stderr, proc.returncode
    # assert that "msg" starts with "expected"
    assert code == 1
    assert msg.startswith(expected)

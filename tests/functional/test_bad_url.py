# test the error message returned by pip when
# a bad "file:" URL is passed to it.

import random
import subprocess
from typing import List, Tuple


def get_url_error_message(cmd: List[str]) -> Tuple[str, str]:
    # this makes pip to react using
    # subprocess. It must fail, so then
    # we can test the error message.
    proc = subprocess.run(cmd, capture_output=True, text=True)
    expected_message = "ERROR: 404 Client Error: FileNotFoundError for url: "
    return proc.stderr, expected_message


def get_random_pathname() -> str:
    "create a random, impossible pathname."
    base = "random_impossible_pathname_"
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    for _ in range(10):
        name = base + "".join(random.choice(alphabet))
    return name


def test_filenotfound_error_message() -> None:
    # Test the error message returned when using a bad 'file:' URL.
    file = get_random_pathname()
    # generate a command
    command = ["pip", "install", "file:%s"%file]
    # make it fail to get an error message
    msg, expected = get_url_error_message(command)
    # assert that "msg" starts with "expected"
    assert msg.startswith(expected)

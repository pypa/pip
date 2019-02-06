import pytest

def test_show_message_ids(script):
    result = script.pip('show', 'pip', '--show-message-ids')
    assert 'message_id=default' in result.stdout


def test_ignore_messages(script):
    result = script.pip('show', 'pip', '--ignore-messages', 'default')
    assert 'Name: pip' not in result.stdout


def test_hide_deprecation(script, deprecated_python):
    if not deprecated_python:
        pytest.skip("Python version isn't deprecated")
    result = script.pip('show', 'pip')
    assert 'DEPRECATION' in result.stderr
    result = script.pip('show', 'pip', '--ignore-messages', 'deprecation')
    assert 'DEPRECATION' not in result.stderr

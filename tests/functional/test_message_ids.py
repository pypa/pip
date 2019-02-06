def test_show_message_ids(script):
    result = script.pip('show', 'pip', '--show-message-ids')
    assert 'message_id=default' in result.stdout


def test_ignore_messages(script):
    result = script.pip('show', 'pip', '--ignore-messages', 'default')
    assert 'Name: pip' not in result.stdout

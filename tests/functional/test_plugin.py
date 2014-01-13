import pytest
from pip.basecommand import SUCCESS

def test_plugin_found(script, data):
    """
    Test extending the 'pip.commands' entry point
    """
    # the 'plugin' project provides the 'plugin' command
    plugin_path = data.packages.join("plugin")
    script.pip('install', plugin_path)
    result = script.pip('plugin')
    assert result.returncode == SUCCESS
    result = script.pip('help')
    assert '(From plugin) Do Plugin stuff' in result.stdout

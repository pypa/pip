"""
Test `pip home` command (pip.commands.home).
"""
from mock import Mock
from pip.basecommand import ERROR, SUCCESS
from pip.commands.home import HomeCommand


def test_home_command(caplog, monkeypatch):
    """
    Test HomeCommand.run end-to-end.
    """
    monkeypatch.setattr('pip.commands.home.open_new_tab', lambda x: None)
    options_mock = Mock(pypi=False)
    args = ('pip', )
    home_cmd = HomeCommand()
    status = home_cmd.run(options_mock, args)
    assert status == SUCCESS
    assert len(caplog.records()) == 2
    log_opening, log_uri = caplog.records()
    assert log_opening.getMessage() == 'Opening pip\'s homepage in browser'
    assert log_uri.getMessage() == '  https://pip.pypa.io/'


def test_missing_argument_should_error_with_message(caplog, monkeypatch):
    """
    Test HomeCommand.run with no arguments.
    """
    monkeypatch.setattr('pip.commands.home.open_new_tab', lambda x: None)
    options_mock = Mock(pypi=False)
    args = ()
    home_cmd = HomeCommand()
    status = home_cmd.run(options_mock, args)
    assert status == ERROR
    assert len(caplog.records()) == 1
    err_msg = 'ERROR: Please provide a package name or names'
    assert err_msg in caplog.records()[0].getMessage()


def test_handles_more_than_one_package(caplog, monkeypatch):
    """
    Test HomeCommand.run with multiple arguments.
    """
    monkeypatch.setattr('pip.commands.home.open_new_tab', lambda x: None)
    options_mock = Mock(pypi=False)
    args = ('pip', 'pytest')
    home_cmd = HomeCommand()
    status = home_cmd.run(options_mock, args)
    assert status == SUCCESS
    assert len(caplog.records()) == 4


def test_package_not_found_should_error_with_no_output(caplog, monkeypatch):
    """
    Test HomeCommand.run with a non-existent package as argument.
    """
    monkeypatch.setattr('pip.commands.home.open_new_tab', lambda x: None)
    options_mock = Mock(pypi=False)
    args = ('thisPackageDoesNotExist', )
    home_cmd = HomeCommand()
    status = home_cmd.run(options_mock, args)
    assert status == ERROR
    assert len(caplog.records()) == 0


def test_pypi_option_should_open_page_on_pypi(caplog, monkeypatch):
    """
    Test HomeComand.run with --pypi option
    """
    monkeypatch.setattr('pip.commands.home.open_new_tab', lambda x: None)
    options_mock = Mock(pypi=True)
    args = ('pip', )
    home_cmd = HomeCommand()
    status = home_cmd.run(options_mock, args)
    assert status == SUCCESS
    assert len(caplog.records()) == 2
    log_opening, log_uri = caplog.records()
    assert log_opening.getMessage() == 'Opening pip\'s PyPI page in browser'
    assert log_uri.getMessage() == '  https://pypi.python.org/pypi/pip'

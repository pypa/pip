import pytest
from mock import Mock

from tests.lib.server import (
	authorization_response,
    make_mock_server,
    server_running,
)

from pip._internal.cli.base_command import ERROR, SUCCESS

def test_do_not_prompt_when_no_input_flag_given(script):
	server = make_mock_server()
	server.mock.side_effect = [
		authorization_response(),
	]

	url = "https://{}:{}/simple".format(server.host, server.port)

	args = ["install"]
	args.extend(["--index-url", url])
	args.append("requests")
	args.append("--no-input")

	with server_running(server):
		result = script.pip(*args, expect_error=True)

	assert "Could not find a version that satisfies the requirement requests (from versions: none)" in result.stderr
	assert "No matching distribution found for requests" in result.stderr
	assert result.returncode == ERROR
	
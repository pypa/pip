from pip._vendor import requests

from tests.lib.server import make_mock_server, server_running, text_html_response


def test_mock_servers_record_their_own_requests() -> None:
    with make_mock_server() as first, make_mock_server() as second:
        first.mock.return_value = text_html_response("first response")
        second.mock.return_value = text_html_response("second response")

        with server_running(first), server_running(second):
            first_response = requests.get(f"http://{first.host}:{first.port}/first")
            second_response = requests.get(f"http://{second.host}:{second.port}/second")

        assert first_response.text == "first response"
        assert second_response.text == "second response"

        assert first.mock.call_count == second.mock.call_count == 1
        assert first.mock.call_args.args[0]["PATH_INFO"] == "/first"
        assert second.mock.call_args.args[0]["PATH_INFO"] == "/second"

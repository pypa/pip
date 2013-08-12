from mock import MagicMock

from pip.commands.output.list import TextFormat, JsonFormat, CsvFormat


def test_outdated_output_for_text_format():
    text_formatter = TextFormat()
    text_formatter.output = MagicMock()

    text_formatter.outdated_item(project_name="pip",
        current_version="1.3.1", latest_version='2.3.1')
    text_formatter.output_end()

    text_formatter.output.assert_called_with('pip (Current: 1.3.1 Latest: 2.3.1)')


def test_package_list_item_format_with_location_for_text_format():
    text_formatter = TextFormat()
    text_formatter.output = MagicMock()

    text_formatter.package_list_item('pip', '1.2.3', '/some/path/here')
    text_formatter.output_end()

    text_formatter.output.assert_called_with('pip (1.2.3, /some/path/here)')


def test_package_list_item_format_without_location_for_text_format():
    text_formatter = TextFormat()
    text_formatter.output = MagicMock()

    text_formatter.package_list_item('pip', '1.2.3')
    text_formatter.output_end()

    text_formatter.output.assert_called_with('pip (1.2.3)')


def test_outdated_output_for_json_format():
    json_formatter = JsonFormat()
    json_formatter.output = MagicMock()

    json_formatter.outdated_item(project_name="pip",
        current_version="1.3.1", latest_version='2.3.1')
    json_formatter.output_end()

    json_formatter.output.assert_called_with("""[{"current": "1.3.1", "latest": "2.3.1", "package": "pip"}]""")


def test_package_list_item_format_with_location_for_json_format():
    json_formatter = JsonFormat()
    json_formatter.output = MagicMock()

    json_formatter.package_list_item('pip', '1.2.3', '/some/path/here')
    json_formatter.output_end()

    json_formatter.output.assert_called_with("""[{"location": "/some/path/here", "package": "pip", "version": "1.2.3"}]""")


def test_package_list_item_format_without_location_for_json_format():
    json_formatter = JsonFormat()
    json_formatter.output = MagicMock()

    json_formatter.package_list_item('pip', '1.2.3')
    json_formatter.output_end()

    json_formatter.output.assert_called_with("""[{"location": null, "package": "pip", "version": "1.2.3"}]""")


def test_outdated_output_for_csv_format():
    csv_formatter = CsvFormat()
    csv_formatter.output = MagicMock()

    csv_formatter.outdated_item(project_name="pip",
        current_version="1.3.1", latest_version='2.3.1')
    csv_formatter.output_end()

    csv_formatter.output.assert_called_with('pip,1.3.1,2.3.1')


def test_package_list_item_format_for_csv_format():
    csv_formatter = CsvFormat()
    csv_formatter.output = MagicMock()

    csv_formatter.package_list_item('pip', '1.2.3', '/some/path/here')
    csv_formatter.output_end()

    csv_formatter.output.assert_called_with('pip,1.2.3,/some/path/here')

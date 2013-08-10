from mock import Mock, MagicMock

from pip.commands.output import ConsoleOutput


def test_initialization_of_command_options():
    cmd_opts = MagicMock()

    fake_json_formatter = Mock()
    fake_json_formatter.format_type = 'json'

    fake_csv_formatter = Mock()
    fake_csv_formatter.format_type = 'csv'

    console = ConsoleOutput(cmd_opts, [fake_json_formatter, fake_csv_formatter])

    assert ['json', 'csv'] == console.formats_available()

    cmd_opts.add_option.assert_called_with('--output',
            action='store',
            choices=['json', 'csv'],
            help='Output type to render: json, csv.')

def test_output_format_choice():
    cmd_opts = MagicMock()

    fake_json_formatter = Mock()
    fake_json_formatter.format_type = 'json'

    fake_csv_formatter = Mock()
    fake_csv_formatter.format_type = 'csv'

    console = ConsoleOutput(cmd_opts, [fake_json_formatter, fake_csv_formatter])

    options = Mock()
    options.output = 'json'

    console.set_output_type_based_on(options)

    output_text = "just a test"
    console.notify_show(output_text)
    fake_json_formatter.show.assert_called_with(output_text)

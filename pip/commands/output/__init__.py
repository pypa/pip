#from pip.exceptions import FormatNotAvailable


class ConsoleOutput:
    delegation_marker = 'notify_'

    def __init__(self, cmd_opts, output_formatters=[]):
        self.formatter = None
        self.output_formatters = output_formatters

        cmd_opts.add_option('--output',
            action='store',
            choices=self.formats_available(),
            help='Output type to render: ' + ', '.join(self.formats_available()) + '.')

    def formats_available(self):
        return [formatter.format_type for formatter in self.output_formatters]

    def set_output_type_based_on(self, options):
        for formatter in self.output_formatters:
            print formatter.format_type
            if formatter.format_type == options.output:
                self.formatter = formatter
        #if not self.formatter:
          #raise FormatNotAvailable(options.output)

    def __getattr__(self, attr_name):
        if attr_name.startswith(self.delegation_marker):
            method_name = attr_name.replace(self.delegation_marker, '')
            return getattr(self.formatter, method_name)

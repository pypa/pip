"""pip sphinx extensions"""

import optparse
import sys
from textwrap import dedent

from docutils import nodes
from docutils.parsers import rst
from docutils.statemachine import ViewList

from pip._internal.cli import cmdoptions
from pip._internal.commands import commands_dict, create_command
from pip._internal.req.req_file import SUPPORTED_OPTIONS


class PipCommandUsage(rst.Directive):
    required_arguments = 1

    def run(self):
        cmd = create_command(self.arguments[0])
        usage = dedent(
            cmd.usage.replace('%prog', 'pip {}'.format(cmd.name))
        ).strip()
        node = nodes.literal_block(usage, usage)
        return [node]


class PipCommandDescription(rst.Directive):
    required_arguments = 1

    def run(self):
        node = nodes.paragraph()
        node.document = self.state.document
        desc = ViewList()
        cmd = create_command(self.arguments[0])
        description = dedent(cmd.__doc__)
        for line in description.split('\n'):
            desc.append(line, "")
        self.state.nested_parse(desc, 0, node)
        return [node]


class PipOptions(rst.Directive):

    def _format_option(self, option, cmd_name=None):
        bookmark_line = (
            ".. _`{cmd_name}_{option._long_opts[0]}`:"
            if cmd_name else
            ".. _`{option._long_opts[0]}`:"
        ).format(**locals())
        line = ".. option:: "
        if option._short_opts:
            line += option._short_opts[0]
        if option._short_opts and option._long_opts:
            line += ", " + option._long_opts[0]
        elif option._long_opts:
            line += option._long_opts[0]
        if option.takes_value():
            metavar = option.metavar or option.dest.lower()
            line += " <{}>".format(metavar.lower())
        # fix defaults
        opt_help = option.help.replace('%default', str(option.default))
        # fix paths with sys.prefix
        opt_help = opt_help.replace(sys.prefix, "<sys.prefix>")
        return [bookmark_line, "", line, "", "    " + opt_help, ""]

    def _format_options(self, options, cmd_name=None):
        for option in options:
            if option.help == optparse.SUPPRESS_HELP:
                continue
            for line in self._format_option(option, cmd_name):
                self.view_list.append(line, "")

    def run(self):
        node = nodes.paragraph()
        node.document = self.state.document
        self.view_list = ViewList()
        self.process_options()
        self.state.nested_parse(self.view_list, 0, node)
        return [node]


class PipGeneralOptions(PipOptions):
    def process_options(self):
        self._format_options(
            [o() for o in cmdoptions.general_group['options']]
        )


class PipIndexOptions(PipOptions):
    required_arguments = 1

    def process_options(self):
        cmd_name = self.arguments[0]
        self._format_options(
            [o() for o in cmdoptions.index_group['options']],
            cmd_name=cmd_name,
        )


class PipCommandOptions(PipOptions):
    required_arguments = 1

    def process_options(self):
        cmd = create_command(self.arguments[0])
        self._format_options(
            cmd.parser.option_groups[0].option_list,
            cmd_name=cmd.name,
        )


class PipReqFileOptionsReference(PipOptions):

    def determine_opt_prefix(self, opt_name):
        for command in commands_dict:
            cmd = create_command(command)
            if cmd.cmd_opts.has_option(opt_name):
                return command

        raise KeyError('Could not identify prefix of opt {}'.format(opt_name))

    def process_options(self):
        for option in SUPPORTED_OPTIONS:
            if getattr(option, 'deprecated', False):
                continue

            opt = option()
            opt_name = opt._long_opts[0]
            if opt._short_opts:
                short_opt_name = '{}, '.format(opt._short_opts[0])
            else:
                short_opt_name = ''

            if option in cmdoptions.general_group['options']:
                prefix = ''
            else:
                prefix = '{}_'.format(self.determine_opt_prefix(opt_name))

            self.view_list.append(
                '  *  :ref:`{short}{long}<{prefix}{opt_name}>`'.format(
                    short=short_opt_name,
                    long=opt_name,
                    prefix=prefix,
                    opt_name=opt_name
                ),
                "\n"
            )


def setup(app):
    app.add_directive('pip-command-usage', PipCommandUsage)
    app.add_directive('pip-command-description', PipCommandDescription)
    app.add_directive('pip-command-options', PipCommandOptions)
    app.add_directive('pip-general-options', PipGeneralOptions)
    app.add_directive('pip-index-options', PipIndexOptions)
    app.add_directive(
        'pip-requirements-file-options-ref-list', PipReqFileOptionsReference
    )

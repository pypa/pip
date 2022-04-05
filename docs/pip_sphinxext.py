"""pip sphinx extensions"""

import optparse
import pathlib
import re
import sys
from textwrap import dedent
from typing import Dict, Iterable, Iterator, List, Optional, Union

from docutils import nodes, statemachine
from docutils.parsers import rst
from docutils.statemachine import StringList, ViewList
from sphinx.application import Sphinx

from pip._internal.cli import cmdoptions
from pip._internal.commands import commands_dict, create_command
from pip._internal.req.req_file import SUPPORTED_OPTIONS


class PipNewsInclude(rst.Directive):
    required_arguments = 1

    def _is_version_section_title_underline(
        self, prev: Optional[str], curr: str
    ) -> bool:
        """Find a ==== line that marks the version section title."""
        if prev is None:
            return False
        if re.match(r"^=+$", curr) is None:
            return False
        if len(curr) < len(prev):
            return False
        return True

    def _iter_lines_with_refs(self, lines: Iterable[str]) -> Iterator[str]:
        """Transform the input lines to add a ref before each section title.

        This is done by looking one line ahead and locate a title's underline,
        and add a ref before the title text.

        Dots in the version is converted into dash, and a ``v`` is prefixed.
        This makes Sphinx use them as HTML ``id`` verbatim without generating
        auto numbering (which would make the the anchors unstable).
        """
        prev = None
        for line in lines:
            # Transform the previous line to include an explicit ref.
            if self._is_version_section_title_underline(prev, line):
                assert prev is not None
                vref = prev.split(None, 1)[0].replace(".", "-")
                yield f".. _`v{vref}`:"
                yield ""  # Empty line between ref and the title.
            if prev is not None:
                yield prev
            prev = line
        if prev is not None:
            yield prev

    def run(self) -> List[nodes.Node]:
        source = self.state_machine.input_lines.source(
            self.lineno - self.state_machine.input_offset - 1,
        )
        path = (
            pathlib.Path(source).resolve().parent.joinpath(self.arguments[0]).resolve()
        )
        include_lines = statemachine.string2lines(
            path.read_text(encoding="utf-8"),
            self.state.document.settings.tab_width,
            convert_whitespace=True,
        )
        include_lines = list(self._iter_lines_with_refs(include_lines))
        self.state_machine.insert_input(include_lines, str(path))
        return []


class PipCommandUsage(rst.Directive):
    required_arguments = 1
    optional_arguments = 3

    def run(self) -> List[nodes.Node]:
        cmd = create_command(self.arguments[0])
        cmd_prefix = "python -m pip"
        if len(self.arguments) > 1:
            cmd_prefix = " ".join(self.arguments[1:])
            cmd_prefix = cmd_prefix.strip('"')
            cmd_prefix = cmd_prefix.strip("'")
        usage = dedent(cmd.usage.replace("%prog", f"{cmd_prefix} {cmd.name}")).strip()
        node = nodes.literal_block(usage, usage)
        return [node]


class PipCommandDescription(rst.Directive):
    required_arguments = 1

    def run(self) -> List[nodes.Node]:
        node = nodes.paragraph()
        node.document = self.state.document
        desc = ViewList()
        cmd = create_command(self.arguments[0])
        assert cmd.__doc__ is not None
        description = dedent(cmd.__doc__)
        for line in description.split("\n"):
            desc.append(line, "")
        self.state.nested_parse(desc, 0, node)
        return [node]


class PipOptions(rst.Directive):
    def _format_option(
        self, option: optparse.Option, cmd_name: Optional[str] = None
    ) -> List[str]:
        bookmark_line = (
            f".. _`{cmd_name}_{option._long_opts[0]}`:"
            if cmd_name
            else f".. _`{option._long_opts[0]}`:"
        )
        line = ".. option:: "
        if option._short_opts:
            line += option._short_opts[0]
        if option._short_opts and option._long_opts:
            line += ", " + option._long_opts[0]
        elif option._long_opts:
            line += option._long_opts[0]
        if option.takes_value():
            metavar = option.metavar or option.dest
            assert metavar is not None
            line += f" <{metavar.lower()}>"
        # fix defaults
        assert option.help is not None
        opt_help = option.help.replace("%default", str(option.default))
        # fix paths with sys.prefix
        opt_help = opt_help.replace(sys.prefix, "<sys.prefix>")
        return [bookmark_line, "", line, "", "    " + opt_help, ""]

    def _format_options(
        self, options: Iterable[optparse.Option], cmd_name: Optional[str] = None
    ) -> None:
        for option in options:
            if option.help == optparse.SUPPRESS_HELP:
                continue
            for line in self._format_option(option, cmd_name):
                self.view_list.append(line, "")

    def run(self) -> List[nodes.Node]:
        node = nodes.paragraph()
        node.document = self.state.document
        self.view_list = ViewList()
        self.process_options()
        self.state.nested_parse(self.view_list, 0, node)
        return [node]


class PipGeneralOptions(PipOptions):
    def process_options(self) -> None:
        self._format_options([o() for o in cmdoptions.general_group["options"]])


class PipIndexOptions(PipOptions):
    required_arguments = 1

    def process_options(self) -> None:
        cmd_name = self.arguments[0]
        self._format_options(
            [o() for o in cmdoptions.index_group["options"]],
            cmd_name=cmd_name,
        )


class PipCommandOptions(PipOptions):
    required_arguments = 1

    def process_options(self) -> None:
        cmd = create_command(self.arguments[0])
        self._format_options(
            cmd.parser.option_groups[0].option_list,
            cmd_name=cmd.name,
        )


class PipReqFileOptionsReference(PipOptions):
    def determine_opt_prefix(self, opt_name: str) -> str:
        for command in commands_dict:
            cmd = create_command(command)
            if cmd.cmd_opts.has_option(opt_name):
                return command

        raise KeyError(f"Could not identify prefix of opt {opt_name}")

    def process_options(self) -> None:
        for option in SUPPORTED_OPTIONS:
            if getattr(option, "deprecated", False):
                continue

            opt = option()
            opt_name = opt._long_opts[0]
            if opt._short_opts:
                short_opt_name = "{}, ".format(opt._short_opts[0])
            else:
                short_opt_name = ""

            if option in cmdoptions.general_group["options"]:
                prefix = ""
            else:
                prefix = "{}_".format(self.determine_opt_prefix(opt_name))

            self.view_list.append(
                "*  :ref:`{short}{long}<{prefix}{opt_name}>`".format(
                    short=short_opt_name,
                    long=opt_name,
                    prefix=prefix,
                    opt_name=opt_name,
                ),
                "\n",
            )


class PipCLIDirective(rst.Directive):
    """
    - Only works when used in a MyST document.
    - Requires sphinx-inline-tabs' tab directive.
    """

    has_content = True
    optional_arguments = 1

    def run(self) -> List[nodes.Node]:
        node = nodes.paragraph()
        node.document = self.state.document

        os_variants = {
            "Linux": {
                "highlighter": "console",
                "executable": "python",
                "prompt": "$",
            },
            "MacOS": {
                "highlighter": "console",
                "executable": "python",
                "prompt": "$",
            },
            "Windows": {
                "highlighter": "doscon",
                "executable": "py",
                "prompt": "C:>",
            },
        }

        if self.arguments:
            assert self.arguments == ["in-a-venv"]
            in_virtual_environment = True
        else:
            in_virtual_environment = False

        lines = []
        # Create a tab for each OS
        for os, variant in os_variants.items():

            # Unpack the values
            prompt = variant["prompt"]
            highlighter = variant["highlighter"]
            if in_virtual_environment:
                executable = "python"
                pip_spelling = "pip"
            else:
                executable = variant["executable"]
                pip_spelling = f"{executable} -m pip"

            # Substitute the various "prompts" into the correct variants
            substitution_pipeline = [
                (
                    r"(^|(?<=\n))\$ python",
                    f"{prompt} {executable}",
                ),
                (
                    r"(^|(?<=\n))\$ pip",
                    f"{prompt} {pip_spelling}",
                ),
            ]
            content = self.block_text
            for pattern, substitution in substitution_pipeline:
                content = re.sub(pattern, substitution, content)

            # Write the tab
            lines.append(f"````{{tab}} {os}")
            lines.append(f"```{highlighter}")
            lines.append(f"{content}")
            lines.append("```")
            lines.append("````")

        string_list = StringList(lines)
        self.state.nested_parse(string_list, 0, node)
        return [node]


def setup(app: Sphinx) -> Dict[str, Union[bool, str]]:
    app.add_directive("pip-command-usage", PipCommandUsage)
    app.add_directive("pip-command-description", PipCommandDescription)
    app.add_directive("pip-command-options", PipCommandOptions)
    app.add_directive("pip-general-options", PipGeneralOptions)
    app.add_directive("pip-index-options", PipIndexOptions)
    app.add_directive(
        "pip-requirements-file-options-ref-list", PipReqFileOptionsReference
    )
    app.add_directive("pip-news-include", PipNewsInclude)
    app.add_directive("pip-cli", PipCLIDirective)
    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }

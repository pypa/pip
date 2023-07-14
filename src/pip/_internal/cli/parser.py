"""Base option parser setup"""

import logging
import optparse
import shutil
import sys
import textwrap
from contextlib import suppress
from typing import Any, Dict, Generator, List, Tuple

from pip._vendor.rich.console import Console, RenderableType
from pip._vendor.rich.markup import escape
from pip._vendor.rich.style import StyleType
from pip._vendor.rich.text import Text
from pip._vendor.rich.theme import Theme

from pip._internal.cli.status_codes import UNKNOWN_ERROR
from pip._internal.configuration import Configuration, ConfigurationError
from pip._internal.utils.misc import redact_auth_from_url, strtobool

logger = logging.getLogger(__name__)


class PrettyHelpFormatter(optparse.IndentedHelpFormatter):
    """A prettier/less verbose help formatter for optparse."""

    styles: dict[str, StyleType] = {
        "optparse.args": "cyan",
        "optparse.groups": "dark_orange",
        "optparse.help": "default",
        "optparse.metavar": "dark_cyan",
        "optparse.syntax": "bold",
        "optparse.text": "default",
    }
    highlights: list[str] = [
        r"(?:^|\s)(?P<args>-{1,2}[\w]+[\w-]*)",  # highlight --words-with-dashes as args
        r"`(?P<syntax>[^`]*)`",  # highlight `text in backquotes` as syntax
    ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # help position must be aligned with __init__.parseopts.description
        kwargs["max_help_position"] = 30
        kwargs["indent_increment"] = 1
        kwargs["width"] = shutil.get_terminal_size()[0] - 2
        super().__init__(*args, **kwargs)
        self.console: Console = Console(theme=Theme(self.styles))
        self.rich_option_strings: dict[optparse.Option, Text] = {}

    def stringify(self, text: RenderableType) -> str:
        """Render a rich object as a string."""
        with self.console.capture() as capture:
            self.console.print(text, highlight=False, soft_wrap=True, end="")
        help = capture.get()
        return "\n".join(line.rstrip() for line in help.split("\n"))

    def format_heading(self, heading: str) -> str:
        if heading == "Options":
            return ""
        rich_heading = Text().append(heading, "optparse.groups").append(":\n")
        return self.stringify(rich_heading)

    def format_usage(self, usage: str) -> str:
        """
        Ensure there is only one newline between usage and the first heading
        if there is no description.
        """
        rich_usage = (
            Text("\n")
            .append("Usage", "optparse.groups")
            .append(f": {self.indent_lines(textwrap.dedent(usage), '  ')}\n")
        )
        return self.stringify(rich_usage)

    def format_description(self, description: str) -> str:
        # leave full control over description to us
        if description:
            if hasattr(self.parser, "main"):
                label = "Commands"
            else:
                label = "Description"
            rich_label = self.stringify(Text(label, "optparse.groups"))
            # some doc strings have initial newlines, some don't
            description = description.lstrip("\n")
            # some doc strings have final newlines and spaces, some don't
            description = description.rstrip()
            # dedent, then reindent
            description = self.indent_lines(textwrap.dedent(description), "  ")
            description = f"{rich_label}:\n{description}\n"
            return description
        else:
            return ""

    def format_epilog(self, epilog: str) -> str:
        # leave full control over epilog to us
        if epilog:
            rich_epilog = Text(epilog, style="optparse.text")
            return self.stringify(rich_epilog)
        else:
            return ""

    def rich_expand_default(self, option: optparse.Option) -> Text:
        # `HelpFormatter.expand_default()` equivalent that returns a `Text`.
        assert option.help is not None
        if self.parser is None or not self.default_tag:
            help = option.help
        else:
            default_value = self.parser.defaults.get(option.dest)  # type: ignore
            if default_value is optparse.NO_DEFAULT or default_value is None:
                default_value = self.NO_DEFAULT_VALUE
            help = option.help.replace(self.default_tag, escape(str(default_value)))
        rich_help = Text.from_markup(help, style="optparse.help")
        for highlight in self.highlights:
            rich_help.highlight_regex(highlight, style_prefix="optparse.")
        return rich_help

    def format_option(self, option: optparse.Option) -> str:
        # Overridden to call the rich methods.
        result: list[Text] = []
        opts = self.rich_option_strings[option]
        opt_width = self.help_position - self.current_indent - 2
        if len(opts) > opt_width:
            opts.append("\n")
            indent_first = self.help_position
        else:  # start help on same line as opts
            opts.set_length(opt_width + 2)
            indent_first = 0
        opts.pad_left(self.current_indent)
        result.append(opts)
        if option.help:
            help_text = self.rich_expand_default(option)
            help_text.expand_tabs(8)  # textwrap expands tabs first
            help_text.plain = help_text.plain.translate(
                textwrap.TextWrapper.unicode_whitespace_trans
            )  # textwrap converts whitespace to " " second
            help_lines = help_text.wrap(self.console, self.help_width)
            result.append(Text(" " * indent_first) + help_lines[0] + "\n")
            indent = Text(" " * self.help_position)
            for line in help_lines[1:]:
                result.append(indent + line + "\n")
        elif opts.plain[-1] != "\n":
            result.append(Text("\n"))
        else:
            pass  # pragma: no cover
        return self.stringify(Text().join(result))

    def store_option_strings(self, parser: optparse.OptionParser) -> None:
        # Overridden to call the rich methods.
        self.indent()
        max_len = 0
        for opt in parser.option_list:
            strings = self.rich_format_option_strings(opt)
            self.option_strings[opt] = strings.plain
            self.rich_option_strings[opt] = strings
            max_len = max(max_len, len(strings) + self.current_indent)
        self.indent()
        for group in parser.option_groups:
            for opt in group.option_list:
                strings = self.rich_format_option_strings(opt)
                self.option_strings[opt] = strings.plain
                self.rich_option_strings[opt] = strings
                max_len = max(max_len, len(strings) + self.current_indent)
        self.dedent()
        self.dedent()
        self.help_position = min(max_len + 2, self.max_help_position)
        self.help_width = max(self.width - self.help_position, 11)

    def rich_format_option_strings(self, option: optparse.Option) -> Text:
        # `HelpFormatter.format_option_strings()` equivalent that returns a `Text`.
        opts: list[Text] = []

        if option._short_opts:
            opts.append(Text(option._short_opts[0], "optparse.args"))
        if option._long_opts:
            opts.append(Text(option._long_opts[0], "optparse.args"))
        if len(opts) > 1:
            opts.insert(1, Text(", "))

        if option.takes_value():
            assert option.dest is not None
            metavar = option.metavar or option.dest.lower()
            opts.append(Text(" ").append(f"<{metavar.lower()}>", "optparse.metavar"))

        return Text().join(opts)

    def indent_lines(self, text: str, indent: str) -> str:
        new_lines = [indent + line for line in text.split("\n")]
        return "\n".join(new_lines)


class UpdatingDefaultsHelpFormatter(PrettyHelpFormatter):
    """Custom help formatter for use in ConfigOptionParser.

    This is updates the defaults before expanding them, allowing
    them to show up correctly in the help listing.

    Also redact auth from url type options
    """

    def rich_expand_default(self, option: optparse.Option) -> Text:
        default_values = None
        if self.parser is not None:
            assert isinstance(self.parser, ConfigOptionParser)
            self.parser._update_defaults(self.parser.defaults)
            assert option.dest is not None
            default_values = self.parser.defaults.get(option.dest)
        help_text = super().rich_expand_default(option)

        if default_values and option.metavar == "URL":
            if isinstance(default_values, str):
                default_values = [default_values]

            # If its not a list, we should abort and just return the help text
            if not isinstance(default_values, list):
                default_values = []

            for val in default_values:
                new_val = escape(redact_auth_from_url(val))
                help_text = Text(new_val).join(help_text.split(val))

        return help_text


class CustomOptionParser(optparse.OptionParser):
    def insert_option_group(
        self, idx: int, *args: Any, **kwargs: Any
    ) -> optparse.OptionGroup:
        """Insert an OptionGroup at a given position."""
        group = self.add_option_group(*args, **kwargs)

        self.option_groups.pop()
        self.option_groups.insert(idx, group)

        return group

    @property
    def option_list_all(self) -> List[optparse.Option]:
        """Get a list of all options, including those in option groups."""
        res = self.option_list[:]
        for i in self.option_groups:
            res.extend(i.option_list)

        return res


class ConfigOptionParser(CustomOptionParser):
    """Custom option parser which updates its defaults by checking the
    configuration files and environmental variables"""

    def __init__(
        self,
        *args: Any,
        name: str,
        isolated: bool = False,
        **kwargs: Any,
    ) -> None:
        self.name = name
        self.config = Configuration(isolated)

        assert self.name
        super().__init__(*args, **kwargs)

    def check_default(self, option: optparse.Option, key: str, val: Any) -> Any:
        try:
            return option.check_value(key, val)
        except optparse.OptionValueError as exc:
            print(f"An error occurred during configuration: {exc}")
            sys.exit(3)

    def _get_ordered_configuration_items(
        self,
    ) -> Generator[Tuple[str, Any], None, None]:
        # Configuration gives keys in an unordered manner. Order them.
        override_order = ["global", self.name, ":env:"]

        # Pool the options into different groups
        section_items: Dict[str, List[Tuple[str, Any]]] = {
            name: [] for name in override_order
        }
        for section_key, val in self.config.items():
            # ignore empty values
            if not val:
                logger.debug(
                    "Ignoring configuration key '%s' as it's value is empty.",
                    section_key,
                )
                continue

            section, key = section_key.split(".", 1)
            if section in override_order:
                section_items[section].append((key, val))

        # Yield each group in their override order
        for section in override_order:
            for key, val in section_items[section]:
                yield key, val

    def _update_defaults(self, defaults: Dict[str, Any]) -> Dict[str, Any]:
        """Updates the given defaults with values from the config files and
        the environ. Does a little special handling for certain types of
        options (lists)."""

        # Accumulate complex default state.
        self.values = optparse.Values(self.defaults)
        late_eval = set()
        # Then set the options with those values
        for key, val in self._get_ordered_configuration_items():
            # '--' because configuration supports only long names
            option = self.get_option("--" + key)

            # Ignore options not present in this parser. E.g. non-globals put
            # in [global] by users that want them to apply to all applicable
            # commands.
            if option is None:
                continue

            assert option.dest is not None

            if option.action in ("store_true", "store_false"):
                try:
                    val = strtobool(val)
                except ValueError:
                    self.error(
                        "{} is not a valid value for {} option, "  # noqa
                        "please specify a boolean value like yes/no, "
                        "true/false or 1/0 instead.".format(val, key)
                    )
            elif option.action == "count":
                with suppress(ValueError):
                    val = strtobool(val)
                with suppress(ValueError):
                    val = int(val)
                if not isinstance(val, int) or val < 0:
                    self.error(
                        "{} is not a valid value for {} option, "  # noqa
                        "please instead specify either a non-negative integer "
                        "or a boolean value like yes/no or false/true "
                        "which is equivalent to 1/0.".format(val, key)
                    )
            elif option.action == "append":
                val = val.split()
                val = [self.check_default(option, key, v) for v in val]
            elif option.action == "callback":
                assert option.callback is not None
                late_eval.add(option.dest)
                opt_str = option.get_opt_string()
                val = option.convert_value(opt_str, val)
                # From take_action
                args = option.callback_args or ()
                kwargs = option.callback_kwargs or {}
                option.callback(option, opt_str, val, self, *args, **kwargs)
            else:
                val = self.check_default(option, key, val)

            defaults[option.dest] = val

        for key in late_eval:
            defaults[key] = getattr(self.values, key)
        self.values = None
        return defaults

    def get_default_values(self) -> optparse.Values:
        """Overriding to make updating the defaults after instantiation of
        the option parser possible, _update_defaults() does the dirty work."""
        if not self.process_default_values:
            # Old, pre-Optik 1.5 behaviour.
            return optparse.Values(self.defaults)

        # Load the configuration, or error out in case of an error
        try:
            self.config.load()
        except ConfigurationError as err:
            self.exit(UNKNOWN_ERROR, str(err))

        defaults = self._update_defaults(self.defaults.copy())  # ours
        for option in self._get_all_options():
            assert option.dest is not None
            default = defaults.get(option.dest)
            if isinstance(default, str):
                opt_str = option.get_opt_string()
                defaults[option.dest] = option.check_value(opt_str, default)
        return optparse.Values(defaults)

    def error(self, msg: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(UNKNOWN_ERROR, f"{msg}\n")

# Copyright 2012-2023, Andrey Kislyuk and argcomplete contributors. Licensed under the terms of the
# `Apache License, Version 2.0 <http://www.apache.org/licenses/LICENSE-2.0>`_. Distribution of the LICENSE and NOTICE
# files with source copies of this package and derivative works is **REQUIRED** as specified by the Apache License.
# See https://github.com/kislyuk/argcomplete for more info.

import argparse
import os
import sys
from collections.abc import Mapping
from typing import Callable, Dict, List, Optional, Sequence, TextIO, Union

from . import io as _io
from .completers import BaseCompleter, ChoicesCompleter, FilesCompleter, SuppressCompleter
from .io import debug, mute_stderr
from .lexers import split_line
from .packages._argparse import IntrospectiveArgumentParser, action_is_greedy, action_is_open, action_is_satisfied

safe_actions = {
    argparse._StoreAction,
    argparse._StoreConstAction,
    argparse._StoreTrueAction,
    argparse._StoreFalseAction,
    argparse._AppendAction,
    argparse._AppendConstAction,
    argparse._CountAction,
}


def default_validator(completion, prefix):
    return completion.startswith(prefix)


class CompletionFinder(object):
    """
    Inherit from this class if you wish to override any of the stages below. Otherwise, use
    ``argcomplete.autocomplete()`` directly (it's a convenience instance of this class). It has the same signature as
    :meth:`CompletionFinder.__call__()`.
    """

    def __init__(
        self,
        argument_parser=None,
        always_complete_options=True,
        exclude=None,
        validator=None,
        print_suppressed=False,
        default_completer=FilesCompleter(),
        append_space=None,
    ):
        self._parser = argument_parser
        self.always_complete_options = always_complete_options
        self.exclude = exclude
        if validator is None:
            validator = default_validator
        self.validator = validator
        self.print_suppressed = print_suppressed
        self.completing = False
        self._display_completions: Dict[str, str] = {}
        self.default_completer = default_completer
        if append_space is None:
            append_space = os.environ.get("_ARGCOMPLETE_SUPPRESS_SPACE") != "1"
        self.append_space = append_space

    def __call__(
        self,
        argument_parser: argparse.ArgumentParser,
        always_complete_options: Union[bool, str] = True,
        exit_method: Callable = os._exit,
        output_stream: Optional[TextIO] = None,
        exclude: Optional[Sequence[str]] = None,
        validator: Optional[Callable] = None,
        print_suppressed: bool = False,
        append_space: Optional[bool] = None,
        default_completer: BaseCompleter = FilesCompleter(),
    ) -> None:
        """
        :param argument_parser: The argument parser to autocomplete on
        :param always_complete_options:
            Controls the autocompletion of option strings if an option string opening character (normally ``-``) has not
            been entered. If ``True`` (default), both short (``-x``) and long (``--x``) option strings will be
            suggested. If ``False``, no option strings will be suggested. If ``long``, long options and short options
            with no long variant will be suggested. If ``short``, short options and long options with no short variant
            will be suggested.
        :param exit_method:
            Method used to stop the program after printing completions. Defaults to :meth:`os._exit`. If you want to
            perform a normal exit that calls exit handlers, use :meth:`sys.exit`.
        :param exclude: List of strings representing options to be omitted from autocompletion
        :param validator:
            Function to filter all completions through before returning (called with two string arguments, completion
            and prefix; return value is evaluated as a boolean)
        :param print_suppressed:
            Whether or not to autocomplete options that have the ``help=argparse.SUPPRESS`` keyword argument set.
        :param append_space:
            Whether to append a space to unique matches. The default is ``True``.

        .. note::
            If you are not subclassing CompletionFinder to override its behaviors,
            use :meth:`argcomplete.autocomplete()` directly. It has the same signature as this method.

        Produces tab completions for ``argument_parser``. See module docs for more info.

        Argcomplete only executes actions if their class is known not to have side effects. Custom action classes can be
        added to argcomplete.safe_actions, if their values are wanted in the ``parsed_args`` completer argument, or
        their execution is otherwise desirable.
        """
        self.__init__(  # type: ignore
            argument_parser,
            always_complete_options=always_complete_options,
            exclude=exclude,
            validator=validator,
            print_suppressed=print_suppressed,
            append_space=append_space,
            default_completer=default_completer,
        )

        if "_ARGCOMPLETE" not in os.environ:
            # not an argument completion invocation
            return

        self._init_debug_stream()

        if output_stream is None:
            filename = os.environ.get("_ARGCOMPLETE_STDOUT_FILENAME")
            if filename is not None:
                debug("Using output file {}".format(filename))
                output_stream = open(filename, "w")

        if output_stream is None:
            try:
                output_stream = os.fdopen(8, "w")
            except Exception:
                debug("Unable to open fd 8 for writing, quitting")
                exit_method(1)

        assert output_stream is not None

        ifs = os.environ.get("_ARGCOMPLETE_IFS", "\013")
        if len(ifs) != 1:
            debug("Invalid value for IFS, quitting [{v}]".format(v=ifs))
            exit_method(1)

        dfs = os.environ.get("_ARGCOMPLETE_DFS")
        if dfs and len(dfs) != 1:
            debug("Invalid value for DFS, quitting [{v}]".format(v=dfs))
            exit_method(1)

        comp_line = os.environ["COMP_LINE"]
        comp_point = int(os.environ["COMP_POINT"])

        cword_prequote, cword_prefix, cword_suffix, comp_words, last_wordbreak_pos = split_line(comp_line, comp_point)

        # _ARGCOMPLETE is set by the shell script to tell us where comp_words
        # should start, based on what we're completing.
        # 1: <script> [args]
        # 2: python <script> [args]
        # 3: python -m <module> [args]
        start = int(os.environ["_ARGCOMPLETE"]) - 1
        comp_words = comp_words[start:]

        if cword_prefix and cword_prefix[0] in self._parser.prefix_chars and "=" in cword_prefix:
            # Special case for when the current word is "--optional=PARTIAL_VALUE". Give the optional to the parser.
            comp_words.append(cword_prefix.split("=", 1)[0])

        debug(
            "\nLINE: {!r}".format(comp_line),
            "\nPOINT: {!r}".format(comp_point),
            "\nPREQUOTE: {!r}".format(cword_prequote),
            "\nPREFIX: {!r}".format(cword_prefix),
            "\nSUFFIX: {!r}".format(cword_suffix),
            "\nWORDS:",
            comp_words,
        )

        completions = self._get_completions(comp_words, cword_prefix, cword_prequote, last_wordbreak_pos)

        if dfs:
            display_completions = {
                key: value.replace(ifs, " ") if value else "" for key, value in self._display_completions.items()
            }
            completions = [dfs.join((key, display_completions.get(key) or "")) for key in completions]

        if os.environ.get("_ARGCOMPLETE_SHELL") == "zsh":
            completions = [f"{c}:{self._display_completions.get(c)}" for c in completions]

        debug("\nReturning completions:", completions)
        output_stream.write(ifs.join(completions))
        output_stream.flush()
        _io.debug_stream.flush()
        exit_method(0)

    def _init_debug_stream(self):
        """Initialize debug output stream

        By default, writes to file descriptor 9, or stderr if that fails.
        This can be overridden by derived classes, for example to avoid
        clashes with file descriptors being used elsewhere (such as in pytest).
        """
        try:
            _io.debug_stream = os.fdopen(9, "w")
        except Exception:
            _io.debug_stream = sys.stderr
        debug()

    def _get_completions(self, comp_words, cword_prefix, cword_prequote, last_wordbreak_pos):
        active_parsers = self._patch_argument_parser()

        parsed_args = argparse.Namespace()
        self.completing = True

        try:
            debug("invoking parser with", comp_words[1:])
            with mute_stderr():
                a = self._parser.parse_known_args(comp_words[1:], namespace=parsed_args)
            debug("parsed args:", a)
        except BaseException as e:
            debug("\nexception", type(e), str(e), "while parsing args")

        self.completing = False

        if "--" in comp_words:
            self.always_complete_options = False

        completions = self.collect_completions(active_parsers, parsed_args, cword_prefix)
        completions = self.filter_completions(completions)
        completions = self.quote_completions(completions, cword_prequote, last_wordbreak_pos)
        return completions

    def _patch_argument_parser(self):
        """
        Since argparse doesn't support much introspection, we monkey-patch it to replace the parse_known_args method and
        all actions with hooks that tell us which action was last taken or about to be taken, and let us have the parser
        figure out which subparsers need to be activated (then recursively monkey-patch those).
        We save all active ArgumentParsers to extract all their possible option names later.
        """
        self.active_parsers: List[argparse.ArgumentParser] = []
        self.visited_positionals: List[argparse.Action] = []

        completer = self

        def patch(parser):
            completer.visited_positionals.append(parser)
            completer.active_parsers.append(parser)

            if isinstance(parser, IntrospectiveArgumentParser):
                return

            classname = "MonkeyPatchedIntrospectiveArgumentParser"

            parser.__class__ = type(classname, (IntrospectiveArgumentParser, parser.__class__), {})

            for action in parser._actions:
                if hasattr(action, "_orig_class"):
                    continue

                # TODO: accomplish this with super
                class IntrospectAction(action.__class__):  # type: ignore
                    def __call__(self, parser, namespace, values, option_string=None):
                        debug("Action stub called on", self)
                        debug("\targs:", parser, namespace, values, option_string)
                        debug("\torig class:", self._orig_class)
                        debug("\torig callable:", self._orig_callable)

                        if not completer.completing:
                            self._orig_callable(parser, namespace, values, option_string=option_string)
                        elif issubclass(self._orig_class, argparse._SubParsersAction):
                            debug("orig class is a subparsers action: patching and running it")
                            patch(self._name_parser_map[values[0]])
                            self._orig_callable(parser, namespace, values, option_string=option_string)
                        elif self._orig_class in safe_actions:
                            if not self.option_strings:
                                completer.visited_positionals.append(self)

                            self._orig_callable(parser, namespace, values, option_string=option_string)

                action._orig_class = action.__class__
                action._orig_callable = action.__call__
                action.__class__ = IntrospectAction

        patch(self._parser)

        debug("Active parsers:", self.active_parsers)
        debug("Visited positionals:", self.visited_positionals)

        return self.active_parsers

    def _get_subparser_completions(self, parser, cword_prefix):
        aliases_by_parser: Dict[argparse.ArgumentParser, List[str]] = {}
        for key in parser.choices.keys():
            p = parser.choices[key]
            aliases_by_parser.setdefault(p, []).append(key)

        for action in parser._get_subactions():
            for alias in aliases_by_parser[parser.choices[action.dest]]:
                if alias.startswith(cword_prefix):
                    self._display_completions[alias] = action.help or ""

        completions = [subcmd for subcmd in parser.choices.keys() if subcmd.startswith(cword_prefix)]
        return completions

    def _include_options(self, action, cword_prefix):
        if len(cword_prefix) > 0 or self.always_complete_options is True:
            return [opt for opt in action.option_strings if opt.startswith(cword_prefix)]
        long_opts = [opt for opt in action.option_strings if len(opt) > 2]
        short_opts = [opt for opt in action.option_strings if len(opt) <= 2]
        if self.always_complete_options == "long":
            return long_opts if long_opts else short_opts
        elif self.always_complete_options == "short":
            return short_opts if short_opts else long_opts
        return []

    def _get_option_completions(self, parser, cword_prefix):
        for action in parser._actions:
            if action.option_strings:
                for option_string in action.option_strings:
                    if option_string.startswith(cword_prefix):
                        self._display_completions[option_string] = action.help or ""

        option_completions = []
        for action in parser._actions:
            if not self.print_suppressed:
                completer = getattr(action, "completer", None)
                if isinstance(completer, SuppressCompleter) and completer.suppress():
                    continue
                if action.help == argparse.SUPPRESS:
                    continue
            if not self._action_allowed(action, parser):
                continue
            if not isinstance(action, argparse._SubParsersAction):
                option_completions += self._include_options(action, cword_prefix)
        return option_completions

    @staticmethod
    def _action_allowed(action, parser):
        # Logic adapted from take_action in ArgumentParser._parse_known_args
        # (members are saved by vendor._argparse.IntrospectiveArgumentParser)
        for conflict_action in parser._action_conflicts.get(action, []):
            if conflict_action in parser._seen_non_default_actions:
                return False
        return True

    def _complete_active_option(self, parser, next_positional, cword_prefix, parsed_args, completions):
        debug("Active actions (L={l}): {a}".format(l=len(parser.active_actions), a=parser.active_actions))

        isoptional = cword_prefix and cword_prefix[0] in parser.prefix_chars
        optional_prefix = ""
        greedy_actions = [x for x in parser.active_actions if action_is_greedy(x, isoptional)]
        if greedy_actions:
            assert len(greedy_actions) == 1, "expect at most 1 greedy action"
            # This means the action will fail to parse if the word under the cursor is not given
            # to it, so give it exclusive control over completions (flush previous completions)
            debug("Resetting completions because", greedy_actions[0], "must consume the next argument")
            self._display_completions = {}
            completions = []
        elif isoptional:
            if "=" in cword_prefix:
                # Special case for when the current word is "--optional=PARTIAL_VALUE".
                # The completer runs on PARTIAL_VALUE. The prefix is added back to the completions
                # (and chopped back off later in quote_completions() by the COMP_WORDBREAKS logic).
                optional_prefix, _, cword_prefix = cword_prefix.partition("=")
            else:
                # Only run completers if current word does not start with - (is not an optional)
                return completions

        complete_remaining_positionals = False
        # Use the single greedy action (if there is one) or all active actions.
        for active_action in greedy_actions or parser.active_actions:
            if not active_action.option_strings:  # action is a positional
                if action_is_open(active_action):
                    # Any positional arguments after this may slide down into this action
                    # if more arguments are added (since the user may not be done yet),
                    # so it is extremely difficult to tell which completers to run.
                    # Running all remaining completers will probably show more than the user wants
                    # but it also guarantees we won't miss anything.
                    complete_remaining_positionals = True
                if not complete_remaining_positionals:
                    if action_is_satisfied(active_action) and not action_is_open(active_action):
                        debug("Skipping", active_action)
                        continue

            debug("Activating completion for", active_action, active_action._orig_class)
            # completer = getattr(active_action, "completer", DefaultCompleter())
            completer = getattr(active_action, "completer", None)

            if completer is None:
                if active_action.choices is not None and not isinstance(active_action, argparse._SubParsersAction):
                    completer = ChoicesCompleter(active_action.choices)
                elif not isinstance(active_action, argparse._SubParsersAction):
                    completer = self.default_completer

            if completer:
                if isinstance(completer, SuppressCompleter) and completer.suppress():
                    continue

                if callable(completer):
                    completer_output = completer(
                        prefix=cword_prefix, action=active_action, parser=parser, parsed_args=parsed_args
                    )
                    if isinstance(completer_output, Mapping):
                        for completion, description in completer_output.items():
                            if self.validator(completion, cword_prefix):
                                completions.append(completion)
                                self._display_completions[completion] = description
                    else:
                        for completion in completer_output:
                            if self.validator(completion, cword_prefix):
                                completions.append(completion)
                                if isinstance(completer, ChoicesCompleter):
                                    self._display_completions[completion] = active_action.help or ""
                                else:
                                    self._display_completions[completion] = ""
                else:
                    debug("Completer is not callable, trying the readline completer protocol instead")
                    for i in range(9999):
                        next_completion = completer.complete(cword_prefix, i)  # type: ignore
                        if next_completion is None:
                            break
                        if self.validator(next_completion, cword_prefix):
                            self._display_completions[next_completion] = ""
                            completions.append(next_completion)
                if optional_prefix:
                    completions = [optional_prefix + "=" + completion for completion in completions]
                debug("Completions:", completions)
        return completions

    def collect_completions(
        self, active_parsers: List[argparse.ArgumentParser], parsed_args: argparse.Namespace, cword_prefix: str
    ) -> List[str]:
        """
        Visits the active parsers and their actions, executes their completers or introspects them to collect their
        option strings. Returns the resulting completions as a list of strings.

        This method is exposed for overriding in subclasses; there is no need to use it directly.
        """
        completions: List[str] = []

        debug("all active parsers:", active_parsers)
        active_parser = active_parsers[-1]
        debug("active_parser:", active_parser)
        if self.always_complete_options or (len(cword_prefix) > 0 and cword_prefix[0] in active_parser.prefix_chars):
            completions += self._get_option_completions(active_parser, cword_prefix)
        debug("optional options:", completions)

        next_positional = self._get_next_positional()
        debug("next_positional:", next_positional)

        if isinstance(next_positional, argparse._SubParsersAction):
            completions += self._get_subparser_completions(next_positional, cword_prefix)

        completions = self._complete_active_option(
            active_parser, next_positional, cword_prefix, parsed_args, completions
        )
        debug("active options:", completions)
        debug("display completions:", self._display_completions)

        return completions

    def _get_next_positional(self):
        """
        Get the next positional action if it exists.
        """
        active_parser = self.active_parsers[-1]
        last_positional = self.visited_positionals[-1]

        all_positionals = active_parser._get_positional_actions()
        if not all_positionals:
            return None

        if active_parser == last_positional:
            return all_positionals[0]

        i = 0
        for i in range(len(all_positionals)):
            if all_positionals[i] == last_positional:
                break

        if i + 1 < len(all_positionals):
            return all_positionals[i + 1]

        return None

    def filter_completions(self, completions: List[str]) -> List[str]:
        """
        De-duplicates completions and excludes those specified by ``exclude``.
        Returns the filtered completions as a list.

        This method is exposed for overriding in subclasses; there is no need to use it directly.
        """
        filtered_completions = []
        for completion in completions:
            if self.exclude is not None:
                if completion in self.exclude:
                    continue
            if completion not in filtered_completions:
                filtered_completions.append(completion)
        return filtered_completions

    def quote_completions(
        self, completions: List[str], cword_prequote: str, last_wordbreak_pos: Optional[int]
    ) -> List[str]:
        """
        If the word under the cursor started with a quote (as indicated by a nonempty ``cword_prequote``), escapes
        occurrences of that quote character in the completions, and adds the quote to the beginning of each completion.
        Otherwise, escapes all characters that bash splits words on (``COMP_WORDBREAKS``), and removes portions of
        completions before the first colon if (``COMP_WORDBREAKS``) contains a colon.

        If there is only one completion, and it doesn't end with a **continuation character** (``/``, ``:``, or ``=``),
        adds a space after the completion.

        This method is exposed for overriding in subclasses; there is no need to use it directly.
        """
        special_chars = "\\"
        # If the word under the cursor was quoted, escape the quote char.
        # Otherwise, escape all special characters and specially handle all COMP_WORDBREAKS chars.
        if cword_prequote == "":
            # Bash mangles completions which contain characters in COMP_WORDBREAKS.
            # This workaround has the same effect as __ltrim_colon_completions in bash_completion
            # (extended to characters other than the colon).
            if last_wordbreak_pos is not None:
                completions = [c[last_wordbreak_pos + 1 :] for c in completions]
            special_chars += "();<>|&!`$* \t\n\"'"
        elif cword_prequote == '"':
            special_chars += '"`$!'

        if os.environ.get("_ARGCOMPLETE_SHELL") in ("tcsh", "fish"):
            # tcsh and fish escapes special characters itself.
            special_chars = ""
        elif cword_prequote == "'":
            # Nothing can be escaped in single quotes, so we need to close
            # the string, escape the single quote, then open a new string.
            special_chars = ""
            completions = [c.replace("'", r"'\''") for c in completions]

        # PowerShell uses ` as escape character.
        if os.environ.get("_ARGCOMPLETE_SHELL") == "powershell":
            escape_char = '`'
            special_chars = special_chars.replace('`', '')
        else:
            escape_char = "\\"
            if os.environ.get("_ARGCOMPLETE_SHELL") == "zsh":
                # zsh uses colon as a separator between a completion and its description.
                special_chars += ":"

        escaped_completions = []
        for completion in completions:
            escaped_completion = completion
            for char in special_chars:
                escaped_completion = escaped_completion.replace(char, escape_char + char)
            escaped_completions.append(escaped_completion)
            if completion in self._display_completions:
                self._display_completions[escaped_completion] = self._display_completions[completion]

        if self.append_space:
            # Similar functionality in bash was previously turned off by supplying the "-o nospace" option to complete.
            # Now it is conditionally disabled using "compopt -o nospace" if the match ends in a continuation character.
            # This code is retained for environments where this isn't done natively.
            continuation_chars = "=/:"
            if len(escaped_completions) == 1 and escaped_completions[0][-1] not in continuation_chars:
                if cword_prequote == "":
                    escaped_completions[0] += " "

        return escaped_completions

    def rl_complete(self, text, state):
        """
        Alternate entry point for using the argcomplete completer in a readline-based REPL. See also
        `rlcompleter <https://docs.python.org/3/library/rlcompleter.html#completer-objects>`_.
        Usage:

        .. code-block:: python

            import argcomplete, argparse, readline
            parser = argparse.ArgumentParser()
            ...
            completer = argcomplete.CompletionFinder(parser)
            readline.set_completer_delims("")
            readline.set_completer(completer.rl_complete)
            readline.parse_and_bind("tab: complete")
            result = input("prompt> ")
        """
        if state == 0:
            cword_prequote, cword_prefix, cword_suffix, comp_words, first_colon_pos = split_line(text)
            comp_words.insert(0, sys.argv[0])
            matches = self._get_completions(comp_words, cword_prefix, cword_prequote, first_colon_pos)
            self._rl_matches = [text + match[len(cword_prefix) :] for match in matches]

        if state < len(self._rl_matches):
            return self._rl_matches[state]
        else:
            return None

    def get_display_completions(self):
        """
        This function returns a mapping of completions to their help strings for displaying to the user.
        """
        return self._display_completions


class ExclusiveCompletionFinder(CompletionFinder):
    @staticmethod
    def _action_allowed(action, parser):
        if not CompletionFinder._action_allowed(action, parser):
            return False

        append_classes = (argparse._AppendAction, argparse._AppendConstAction)
        if action._orig_class in append_classes:
            return True

        if action not in parser._seen_non_default_actions:
            return True

        return False

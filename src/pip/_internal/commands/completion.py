import logging
import sys
import textwrap
from optparse import Values
from pathlib import Path

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import SUCCESS
from pip._internal.utils.misc import get_prog

logger = logging.getLogger(__name__)

BASE_COMPLETION = """
# pip {shell} completion start{script}# pip {shell} completion end
"""

COMPLETION_SCRIPTS = {
    "bash": """
        _pip_completion()
        {{
            COMPREPLY=( $( COMP_WORDS="${{COMP_WORDS[*]}}" \\
                           COMP_CWORD=$COMP_CWORD \\
                           PIP_AUTO_COMPLETE=1 $1 2>/dev/null ) )
        }}
        complete -o default -F _pip_completion {prog}
    """,
    "zsh": """
        #compdef -P pip[0-9.]#
        __pip() {{
          compadd $( COMP_WORDS="$words[*]" \\
                     COMP_CWORD=$((CURRENT-1)) \\
                     PIP_AUTO_COMPLETE=1 $words[1] 2>/dev/null )
        }}
        if [[ $zsh_eval_context[-1] == loadautofunc ]]; then
          # autoload from fpath, call function directly
          __pip "$@"
        else
          # eval/source/. command, register function for later
          compdef __pip -P 'pip[0-9.]#'
        fi
    """,
    "fish": """
        function __fish_complete_pip
            set -lx COMP_WORDS \\
                (commandline --current-process --tokenize --cut-at-cursor) \\
                (commandline --current-token --cut-at-cursor)
            set -lx COMP_CWORD (math (count $COMP_WORDS) - 1)
            set -lx PIP_AUTO_COMPLETE 1
            set -l completions
            if string match -q '2.*' $version
                set completions (eval $COMP_WORDS[1])
            else
                set completions ($COMP_WORDS[1])
            end
            string split \\  -- $completions
        end
        complete -fa "(__fish_complete_pip)" -c {prog}
    """,
    "powershell": None,  # Will be loaded from file
}


def get_powershell_script():
    """Load the PowerShell completion script from file."""
    script_path = Path(__file__).parent.parent / "cli" / "pip-completion.ps1"
    if script_path.exists():
        return script_path.read_text()
    logger.warning(
        "PowerShell completion script not found at %s, falling back to basic completion",
        script_path,
    )
    return ""


class CompletionCommand(Command):
    """A helper command to be used for command completion."""

    ignore_require_venv = True

    def add_options(self) -> None:
        self.cmd_opts.add_option(
            "--bash",
            "-b",
            action="store_const",
            const="bash",
            dest="shell",
            help="Emit completion code for bash",
        )
        self.cmd_opts.add_option(
            "--zsh",
            "-z",
            action="store_const",
            const="zsh",
            dest="shell",
            help="Emit completion code for zsh",
        )
        self.cmd_opts.add_option(
            "--fish",
            "-f",
            action="store_const",
            const="fish",
            dest="shell",
            help="Emit completion code for fish",
        )
        self.cmd_opts.add_option(
            "--powershell",
            "-p",
            action="store_const",
            const="powershell",
            dest="shell",
            help="Emit completion code for powershell",
        )

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options: Values, args: list[str]) -> int:
        """Prints the completion code of the given shell"""
        shells = COMPLETION_SCRIPTS.keys()
        shell_options = ["--" + shell for shell in sorted(shells)]

        if options.shell in shells:
            script = ""
            if options.shell == "powershell":
                script = get_powershell_script()
            else:
                script = textwrap.dedent(
                    COMPLETION_SCRIPTS.get(options.shell, "").format(prog=get_prog())
                )

            print(BASE_COMPLETION.format(script=script, shell=options.shell))
            return SUCCESS
        else:
            sys.stderr.write(
                "ERROR: You must pass {}\n".format(" or ".join(shell_options))
            )
            return SUCCESS

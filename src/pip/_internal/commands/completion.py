import logging
import sys
import textwrap

# Zipapp-safe way to read package resources
from importlib import resources
from optparse import Values

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import SUCCESS
from pip._internal.utils.misc import get_prog

logger = logging.getLogger(__name__)

BASE_COMPLETION = "{script}"

COMPLETION_SCRIPTS = {
    "bash": """_pip_completion()
{
    COMPREPLY=( $( COMP_WORDS="${COMP_WORDS[*]}" \\
                   COMP_CWORD=$COMP_CWORD \\
                   PIP_AUTO_COMPLETE=1 $1 2>/dev/null ) )
}
complete -o default -F _pip_completion pip""",
    "zsh": """#compdef -P pip[0-9.]#
__pip() {
  compadd $( COMP_WORDS="$words[*]" \\
             COMP_CWORD=$((CURRENT-1)) \\
             PIP_AUTO_COMPLETE=1 $words[1] 2>/dev/null )
}
if [[ $zsh_eval_context[-1] == loadautofunc ]]; then
  # autoload from fpath, call function directly
  __pip "$@"
else
  # eval/source/. command, register function for later
  compdef __pip -P 'pip[0-9.]#'
fi""",
    "fish": """function __fish_complete_pip
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
complete -fa "(__fish_complete_pip)" -c pip""",
    "powershell": None,  # Will be loaded from file
}


def get_powershell_script() -> str:
    """Load the PowerShell completion script from file in a zipapp-safe way."""
    try:
        # Assuming pip-completion.ps1 is in pip._internal.cli package
        return (
            resources.files("pip._internal.cli")
            .joinpath("pip-completion.ps1")
            .read_text(encoding="utf-8")
        )
    except (FileNotFoundError, NotADirectoryError, TypeError):
        # TypeError can be raised by importlib_resources on older Pythons
        # if the package is not found
        logger.warning(
            "PowerShell script not found or unreadable, "
            "falling back to basic completion"
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
        if options.shell in shells:
            script = ""
            if options.shell == "powershell":
                script_template = get_powershell_script()
                prog_name = get_prog()
                # Assumes placeholder is only ever the default or the actual prog_name.
                placeholder_name = "##PIP_COMMAND_NAME_PLACEHOLDER##"
                placeholder_to_find = (
                    f'$_pip_command_name_placeholder = "{placeholder_name}"'
                )
                replacement_line = f'$_pip_command_name_placeholder = "{prog_name}"'
                script = script_template.replace(placeholder_to_find, replacement_line)
            else:
                script = COMPLETION_SCRIPTS.get(options.shell, "")
                if not isinstance(script, str):
                    # This case should not be reached with current data.
                    logger.error(
                        "Script template for shell '%s' is not a string.", options.shell
                    )
                    script = ""  # Fallback to an empty script
                else:
                    script = textwrap.dedent(script)

            print(BASE_COMPLETION.format(script=script, shell=options.shell))
            return SUCCESS
        print(
            "ERROR: You must pass --bash or --fish or --powershell or --zsh",
            file=sys.stderr,
        )
        return SUCCESS

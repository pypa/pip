#!/usr/bin/env python
"""Generate zsh completion script.

Usage
-----
.. code-block:: zsh
    scripts/zsh_completion.py
    sudo mv _[^_]* /usr/share/zsh/site-functions  # don't mv __pycache__
    rm -f ~/.zcompdump  # optional
    compinit  # regenerate ~/.zcompdump

Refer
-----
- https://github.com/ytdl-org/youtube-dl/blob/master/devscripts/zsh-completion.py
- https://github.com/zsh-users/zsh/blob/master/Etc/completion-style-guide
- https://gist.githubusercontent.com/zeroSteiner/215953f2fe54ed75e8159125fabe2aba/raw/d746c8da027b738b16118ee4313d048c9f60aa11/zpycompletion.py  # noqa: E501

Examples
--------
.. code-block::
    '(- *)'{-h,--help}'[show this help message and exit]'
    |<-1->||<---2--->||<---------------3--------------->|

.. code-block:: console
    % foo --<TAB>
    option
    --help      show this help message and exit
    % foo --help <TAB>
    no more arguments

.. code-block::
    --color'[When to show color. Default: auto. Support: auto, always, never]:when:(auto always never)'  # noqa: E501
    |<-2->||<------------------------------3------------------------------->||<4>||<--------5-------->|  # noqa: E501

.. code-block:: console
    % foo --color <TAB>
    when
    always
    auto
    never

.. code-block::
    --config='[Config file. Default: ~/.config/foo/foo.toml]:config file:_files -g *.toml'  # noqa: E501
    |<--2-->||<---------------------3--------------------->||<---4---->||<------5------->|  # noqa: E501

.. code-block:: console
    % foo --config <TAB>
    config file
    a.toml  b/ ...
    ...

.. code-block::
    {1,2}'::_command_names -e'
    |<2->|4|<-------5------->|

.. code-block:: console
    % foo help<TAB>
    _command_names -e
    help2man  generate a simple manual page
    helpviewer
    ...
    % foo hello hello <TAB>
    no more arguments

.. code-block::
    '*: :_command_names -e'
    2|4||<-------5------->|

.. code-block:: console
    % foo help<TAB>
    external command
    help2man  generate a simple manual page
    helpviewer
    ...
    % foo hello hello help<TAB>
    external command
    help2man  generate a simple manual page
    helpviewer
    ...

+----+------------+----------+------+
| id | variable   | required | expr |
+====+============+==========+======+
| 1  | prefix     | F        | (.*) |
| 2  | optionstr  | T        | .*   |
| 3  | helpstr    | F        | [.*] |
| 4  | metavar    | F        | :.*  |
| 5  | completion | F        | :.*  |
+----+------------+----------+------+
"""
import os
import sys
from importlib import import_module
from optparse import SUPPRESS_HELP
from os.path import dirname as dirn
from typing import TYPE_CHECKING, Final

from setuptools import find_packages

if TYPE_CHECKING:
    from optparse import Option

rootpath = dirn(dirn(os.path.abspath(__file__)))
path = os.path.join(rootpath, "src")
packages = find_packages(path)
if packages == []:
    path = rootpath
    packages = find_packages(path)
sys.path.insert(0, path)
from pip._internal.cli.main_parser import create_main_parser  # noqa: E402
from pip._internal.commands import commands_dict  # noqa: E402

parser = create_main_parser()
actions = parser._get_all_options()
PACKAGES: Final = packages
PACKAGE: Final = PACKAGES[0]
BINNAME: Final = PACKAGE.replace("_", "-")
ZSH_COMPLETION_FILE: Final = "_" + BINNAME if sys.argv[2:3] == [] else sys.argv[2]
ZSH_COMPLETION_TEMPLATE: Final = os.path.join(
    dirn(os.path.abspath(__file__)), "zsh_completion.in"
)

case_template = """\
        '{{metavar}}')
          _arguments -s -S \\
            {{flags}}
          ;;
"""
subparser = ""
commands = []
cases = []


def generate_flag(action: "Option") -> str:
    """generate_flag.

    :param action:
    :type action: "Option"
    :rtype: str
    """
    if action.dest in ["help", "version"]:
        prefix = "'(- : *)'"
    else:
        prefix = ""

    option_strings = action._short_opts + action._long_opts
    if len(option_strings) > 1:  # {} cannot be quoted
        optionstr = "{" + ",".join(option_strings) + "}'"
    elif len(option_strings) == 1:
        optionstr = option_strings[0] + "'"
    else:  # action.option_strings == [], positional argument
        if action.nargs in ["*", "+"]:
            optionstr = "'*"  # * must be quoted
        else:
            if isinstance(action.nargs, int) and action.nargs > 1:
                optionstr = "{" + "," * (action.nargs - 1) + "}'"
            else:  # action.nargs in [1, None, "?"]:
                optionstr = "'"

    if action.help and action.help != SUPPRESS_HELP and option_strings != []:
        helpstr = action.help.replace("]", "\\]").replace("'", "'\\''")
        helpstr = "[" + helpstr + "]"
    else:
        helpstr = ""

    if isinstance(action.metavar, str):
        metavar = action.metavar
    else:  # action.metavar is None
        if action.nargs is None or action.nargs == 0:
            metavar = ""
        elif option_strings == [] and action.dest:
            metavar = action.dest
        elif action.type:
            metavar = action.type
        else:
            metavar = action.default.__class__.__name__
    if metavar != "":
        # use lowcase conventionally
        metavar = metavar.lower().replace(":", "\\:")

    choices = action.choices  # type: ignore
    if action.metavar == "binary":
        completion = "->package_list"
        metavar = " "
    elif action.metavar == "platform":
        # Not all, just mostly used, for users' convenience
        # input other word will not throw error
        choices = [
            "any",
            "manylinux1_x86_64",
            "manylinux1_i386",
            "manylinux2014_aarch64",
            "win_amd64",
            "macosx_10_9_x86_64",
            "macosx_11_0_arm64",
        ]
        completion = "(" + " ".join(choices) + ")"
    elif action.metavar == "action":
        from pip._internal.cli.cmdoptions import EXISTS_ACTIONS

        completion = " ".join(map("\\:".join, EXISTS_ACTIONS.items()))
        completion = "((" + completion + "))"
    elif action.metavar == "implementation":
        implementations = {
            "pp": "pypy",
            "jy": "jython",
            "cp": "cpython",
            "ip": "ironpython",
            "py": "implementation-agnostic",
        }
        completion = " ".join(map("\\:".join, implementations.items()))
        completion = "((" + completion + "))"
    elif choices:
        completion = "(" + " ".join(map(str, choices)) + ")"
    elif metavar in ["file", "path"]:
        completion = "_files"
        metavar = " "
    elif metavar == "dir":
        completion = "_dirs"
        metavar = " "
    elif metavar == "url":
        completion = "_urls"
        metavar = " "
    elif metavar == "path/url":
        completion = "->path/url"
        metavar = " "
    elif metavar == "hostname":
        completion = "_hostname"
        metavar = " "
    elif metavar == "command":
        completion = "_command_names -e"
        metavar = " "
    else:
        completion = ""

    if metavar != "":
        metavar = ":" + metavar
    if completion != "":
        completion = ":" + completion

    flag = "{0}{1}{2}{3}{4}'".format(prefix, optionstr, helpstr, metavar, completion)
    return flag


flags = []
for action in actions:
    flag = generate_flag(action)
    flags += [flag]

for metavar, commandinfo in commands_dict.items():
    helpstr = commandinfo.summary.replace("'", "'\\''")
    command = "'" + metavar + ":" + helpstr + "'"
    commands += [command]

    if metavar == "install":
        subflags = ["'*: :->packages_or_dirs'"]
    elif metavar in ["uninstall", "show"]:
        subflags = ["'*: :->installed_packages'"]
    elif metavar == "hash":
        subflags = ["'*: :_files'"]
    elif metavar == "help":
        continue  # write manually
    else:
        subflags = []
    module = import_module(commandinfo.module_path)
    command_class = getattr(module, commandinfo.class_name)
    subactions = command_class(metavar, helpstr).parser._get_all_options()
    for subaction in subactions:
        subflag = generate_flag(subaction)
        subflags += [subflag]
    case = case_template.replace("{{metavar}}", metavar)
    case = case.replace("{{flags}}", " \\\n            ".join(subflags))
    cases += [case]

with open(ZSH_COMPLETION_TEMPLATE) as f:
    template = f.read()

template = template.replace("{{flags}}", " \\\n  ".join(flags))

template = template.replace("{{program}}", BINNAME)
template = template.replace("{{commands}}", "\n  ".join(commands))
template = template.replace("{{cases}}", "\n".join(cases))

with open(ZSH_COMPLETION_FILE, "w") as f:
    f.write(template)

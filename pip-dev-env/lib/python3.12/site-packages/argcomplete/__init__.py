# Copyright 2012-2023, Andrey Kislyuk and argcomplete contributors.
# Licensed under the Apache License. See https://github.com/kislyuk/argcomplete for more info.

from . import completers
from .completers import ChoicesCompleter, DirectoriesCompleter, EnvironCompleter, FilesCompleter, SuppressCompleter
from .exceptions import ArgcompleteException
from .finders import CompletionFinder, ExclusiveCompletionFinder, safe_actions
from .io import debug, mute_stderr, warn
from .lexers import split_line
from .shell_integration import shellcode

autocomplete = CompletionFinder()
autocomplete.__doc__ = """ Use this to access argcomplete. See :meth:`argcomplete.CompletionFinder.__call__()`. """

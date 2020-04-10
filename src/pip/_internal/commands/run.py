# The following comment should be removed at some point in the future.
# mypy: disallow-untyped-defs=False

from __future__ import absolute_import

import functools
import logging

from pip._vendor import pip_run

from pip._internal.cli.base_command import SUCCESS, Command

logger = logging.getLogger(__name__)


def provisional(msg):
    """
    Unconditionally warn when func is invoked.
    """
    return provisional_eval(msg, cond=lambda result: True)


def provisional_eval(msg, cond=bool):
    """
    Warn if cond(func result) evaluates True.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if cond(result):
                logger.warning(msg)
            return result
        return wrapper
    return decorator


pip_run.scripts.DepsReader.try_read = classmethod(provisional_eval(
    msg="Support for reading requirements from a script is provisional.")(
    vars(pip_run.scripts.DepsReader)['try_read'].__func__))


class RunCommand(Command):
    """Run a new Python interpreter with packages transient-installed"""
    usage = pip_run.commands.help_doc
    ignore_require_venv = True

    def _main(self, args):
        if ['--help'] == args:
            return super(RunCommand, self)._main(args)

        pip_run.run(args)

        return SUCCESS

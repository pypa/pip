import sys

from . import deps
from . import commands
from . import launch
from . import scripts


def run(args=None):
    """
    Main entry point for pip-run.
    """
    if args is None:
        args = sys.argv[1:]
    pip_args, params = commands.parse_script_args(args)
    commands.intercept(pip_args)
    pip_args.extend(scripts.DepsReader.search(params))
    with deps.load(*deps.not_installed(pip_args)) as home:
        raise SystemExit(launch.with_path(home, params))

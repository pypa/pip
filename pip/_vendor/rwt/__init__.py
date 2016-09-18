import sys

from . import deps
from . import commands
from . import launch
from . import scripts


def run():
	pip_args, params = commands.parse_script_args(sys.argv[1:])
	commands.intercept(pip_args)
	pip_args.extend(scripts.DepsReader.search(params))
	with deps.load(*pip_args) as home:
		launch.with_path(home, params)

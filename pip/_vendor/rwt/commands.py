import textwrap


def parse_script_args(args):
	"""
	Separate the command line arguments into arguments for pip
	and arguments to Python.

	>>> parse_script_args(['foo', '--', 'bar'])
	(['foo'], ['bar'])

	>>> parse_script_args(['foo', 'bar'])
	(['foo', 'bar'], [])
	"""
	try:
		pivot = args.index('--')
	except ValueError:
		pivot = len(args)
	return args[:pivot], args[pivot+1:]


help_doc = textwrap.dedent("""
	Usage:

	Arguments to rwt prior to `--` are used to specify the requirements
	to make available, just as arguments to pip install. For example,

	    rwt -r requirements.txt "requests>=2.0"

	That will launch python after installing the deps in requirements.txt
	and also a late requests. Packages are always installed to a temporary
	location and cleaned up when the process exits.

	Arguments after `--` are passed to the Python interpreter. So to launch
	`script.py`:

	    rwt -- script.py

	If the `--` is ommitted or nothing is passed, the python interpreter
	will be launched in interactive mode:

	    rwt
	    >>>

	For more examples and details, see https://pypi.org/project/rwt.
	""").lstrip()


def intercept(args):
	"""
	Detect certain args and intercept them.
	"""
	if '--help' in args or '-h' in args:
		print(help_doc)
		raise SystemExit(0)

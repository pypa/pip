import os
import sys
import ast
import tokenize
import itertools


if sys.version_info < (3,):
	filter = itertools.ifilter


class DepsReader:
	"""
	Given a Python script, read the dependencies from the
	indicated variable (default __requires__). Does not
	execute the script, so expects the var_name to be
	assigned a static list of strings.
	"""
	def __init__(self, script):
		self.script = script

	@classmethod
	def load(cls, script_path):
		with open(script_path) as stream:
			return cls(stream.read())

	@classmethod
	def try_read(cls, script_path):
		"""
		Attempt to load the dependencies from the script,
		but return an empty list if unsuccessful.
		"""
		try:
			reader = cls.load(script_path)
			return reader.read()
		except Exception:
			return []

	@classmethod
	def search(cls, params):
		"""
		Given a (possibly-empty) series of parameters to a
		Python interpreter, return any dependencies discovered
		in a script indicated in the parameters. Only honor the
		first file found.
		"""
		files = filter(os.path.isfile, params)
		return cls.try_read(next(files, None))

	def read(self, var_name='__requires__'):
		"""
		>>> DepsReader("__requires__=['foo']").read()
		['foo']
		"""
		mod = ast.parse(self.script)
		node, = (
			node
			for node in mod.body
			if isinstance(node, ast.Assign)
			and len(node.targets) == 1
			and isinstance(node.targets[0], ast.Name)
			and node.targets[0].id == var_name
		)
		return ast.literal_eval(node.value)


def run(cmdline):
	"""
	Execute the script as if it had been invoked naturally.
	"""
	namespace = dict()
	filename = cmdline[0]
	namespace['__file__'] = filename
	namespace['__name__'] = '__main__'
	sys.argv[:] = cmdline

	open_ = getattr(tokenize, 'open', open)
	script = open_(filename).read()
	norm_script = script.replace('\\r\\n', '\\n')
	code = compile(norm_script, filename, 'exec')
	exec(code, namespace)

from __future__ import unicode_literals

import textwrap
import sys
import subprocess

from rwt import scripts


def test_pkg_imported(tmpdir):
	"""
	Create a script that loads cython and ensure it runs.
	"""
	body = textwrap.dedent("""
		import cython
		print("Successfully imported cython")
		""").lstrip()
	script_file = tmpdir / 'script'
	script_file.write_text(body, 'utf-8')
	pip_args = ['cython']
	cmd = [sys.executable, '-m', 'rwt'] + pip_args + ['--', str(script_file)]

	out = subprocess.check_output(cmd, universal_newlines=True)
	assert 'Successfully imported cython' in out


class TestDepsReader:
	def test_reads_files_with_attribute_assignment(self):
		script = textwrap.dedent('''
			__requires__=['foo']
			x.a = 'bar'
			''')
		assert scripts.DepsReader(script).read() == ['foo']

	def test_reads_files_with_multiple_assignment(self):
		script = textwrap.dedent('''
			__requires__=['foo']
			x, a = [a, x]
			''')
		assert scripts.DepsReader(script).read() == ['foo']

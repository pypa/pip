import os
import re
import shutil

from test_pip import here, reset_env, run_pip


index_template = """<html>
  <body>
    <a href="./simple-1.0.tar.gz#md5=4bdf78ebb7911f215c1972cf71b378f0">simple-1.0.tar.gz</a>
  </body>
</html>
"""


def test_index_preference():
    """
    Verify that indexes will be used in the order defined.
    """
    e = reset_env()

    # create two indexes
    index1 = e.scratch_path / 'index1'
    os.makedirs(index1 / 'simple')
    index = open(index1 / 'simple/index.html', 'w')
    index.write(index_template)
    index.close()
    shutil.copy(here / 'packages/simple-1.0.tar.gz', index1 / 'simple')

    index2 = e.scratch_path / 'index2'
    os.makedirs(index2 / 'simple')
    index = open(index2 / 'simple/index.html', 'w')
    index.write(index_template)
    index.close()
    shutil.copy(here / 'packages/simple-1.0.tar.gz', index2 / 'simple')

    # verify that the package is installed from the main index (index1)
    result = run_pip('install', '-vv', '--index-url', 'file://' + index1, '--extra-index-url', 'file://' + index2, 'simple==1.0', expect_error=False)
    output = result.stdout

    index1_re = re.compile('^\s*Installing simple \(origin: file://.*/scratch/index1/simple/simple-1.0.tar.gz', re.MULTILINE)
    assert index1_re.search(output) is not None

    # uninstall the package
    result = run_pip('uninstall', '--yes', 'simple', expect_error=False)

    # verify that the package is installed from the main index (index2, now)
    result = run_pip('install', '-vv', '--index-url', 'file://' + index2, '--extra-index-url', 'file://' + index1, 'simple==1.0', expect_error=False)
    output = result.stdout

    index2_re = re.compile('^\s*Installing simple \(origin: file://.*/scratch/index2/simple/simple-1.0.tar.gz', re.MULTILINE)
    assert index2_re.search(output) is not None

import os
import re
import shutil

from tests.test_pip import here, reset_env, run_pip


def test_index_preference():
    """
    Verify that indexes will be used in the order defined.
    """
    e = reset_env()

    # create two indexes by copying the test index in tests/in dex/FSPkg
    index1 = os.path.join(e.scratch_path, 'index1')
    shutil.copytree(os.path.join(here, 'in dex'), index1)

    index2 = os.path.join(e.scratch_path, 'index2')
    shutil.copytree(os.path.join(here, 'in dex'), index2)

    # verify that the package is installed from the main index (index1)
    result = run_pip('install', '-vv', '--index-url', 'file://' + index1, '--extra-index-url', 'file://' + index2, 'FSPkg', expect_error=False)

    index1_re = re.compile('^\s*Installing FSPkg \(origin: file://.*/scratch/index1/FSPkg/FSPkg-0.1dev.tar.gz\)\s*$', re.MULTILINE)
    assert index1_re.search(result.stdout) is not None

    # uninstall the package
    result = run_pip('uninstall', '--yes', 'FSPkg', expect_error=False)

    # verify that the package is installed from the main index (index2, now)
    result = run_pip('install', '-vv', '--index-url', 'file://' + index2, '--extra-index-url', 'file://' + index1, 'FSPkg', expect_error=False)

    index2_re = re.compile('^\s*Installing FSPkg \(origin: file://.*/scratch/index2/FSPkg/FSPkg-0.1dev.tar.gz\)\s*$', re.MULTILINE)
    assert index2_re.search(result.stdout) is not None

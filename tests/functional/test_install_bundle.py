import os

from tests.lib import packages


def test_install_pybundle(script):
    """
    Test intalling a *.pybundle file
    """
    result = script.pip_install_local(os.path.join(packages, 'simplebundle.pybundle'), expect_temp=True)
    result.assert_installed('simple', editable=False)
    result.assert_installed('simple2', editable=False)

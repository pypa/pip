import os
from tests.lib import reset_env, pip_install_local, packages

def test_install_pybundle():
    """
    Test intalling a *.pybundle file
    """
    env = reset_env()
    result = pip_install_local(os.path.join(packages, 'simplebundle.pybundle'), expect_temp=True)
    result.assert_installed('simple', editable=False)
    result.assert_installed('simple2', editable=False)

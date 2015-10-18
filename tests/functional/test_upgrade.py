import os
import pytest
from tests.lib import pyversion


# The package "requirement" has versions 1.5, 1.6 and 1.7 available.
# The package "application" has versions 1.9, 2.0 and 2.1 available,
# and 2.0 depends on requirement>=1.5 and 2.1 on requirement>=1.6.
# This is intended to resemble the situation with numpy, where
# several current packages depend on 1.6 or newer, leading
# "pip install -U package" to attempt to install some newer version.

@pytest.mark.network
def test_upgrade_not_recursive(script, data):
    """
    If requirement-1.6 is already installed, upgrading application
    should not upgrade requirement.
    """
    script.pip('install', '--no-index', '-f', data.find_links,
               'requirement==1.6', 'application==2.0')
    result = script.pip('upgrade', '--no-index', '-f', data.find_links,
                        'application')
    assert (
        script.site_packages / 'application-2.0-py%s.egg-info' % pyversion
        in result.files_deleted
    )
    assert (
        script.site_packages / 'application-2.1-py%s.egg-info' % pyversion
        in result.files_created
    )
    assert (
        'requirement-1.6-py%s.egg-info' % pyversion
        in os.listdir(script.site_packages_path)
    )


@pytest.mark.network
def test_upgrade_recursive_when_needed(script, data):
    """
    If only requirement-1.5 is installed, upgrading application
    should upgrade requirement to the newest available version.
    """
    script.pip('install', '--no-index', '-f', data.find_links,
               'requirement==1.5', 'application==2.0')
    result = script.pip('upgrade', '--no-index', '-f', data.find_links,
                        'application')
    assert (
        script.site_packages / 'application-2.0-py%s.egg-info' % pyversion
        in result.files_deleted
    )
    assert (
        script.site_packages / 'application-2.1-py%s.egg-info' % pyversion
        in result.files_created
    )
    assert (
        script.site_packages / 'requirement-1.5-py%s.egg-info' % pyversion
        in result.files_deleted
    )
    assert (
        script.site_packages / 'requirement-1.7-py%s.egg-info' % pyversion
        in result.files_created
    )


@pytest.mark.network
def test_upgrade_installs_when_needed(script, data):
    """
    If requirement is not installed, upgrading application should
    install the newest available version.
    """
    script.pip('install', '--no-index', '-f', data.find_links,
               'application==1.9')
    result = script.pip('upgrade', '--no-index', '-f', data.find_links,
                        'application')
    assert (
        script.site_packages / 'application-1.9-py%s.egg-info' % pyversion
        in result.files_deleted
    )
    assert (
        script.site_packages / 'application-2.1-py%s.egg-info' % pyversion
        in result.files_created
    )
    assert (
        script.site_packages / 'requirement-1.7-py%s.egg-info' % pyversion
        in result.files_created
    )

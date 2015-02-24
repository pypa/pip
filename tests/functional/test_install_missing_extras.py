"""
temporarily locate test here to make it fail faster
"""

def test_non_existant_extra_warns_user_with_wheel(script, data):
    """
    A warning is logged telling the user that the extra option they requested
    does not exist in the project they are wishing to install
    """
    result = script.pip(
        'install', '--use-wheel', '--no-index',
        '--find-links=' + data.find_links,
        'simplewheel[nonexistant]', expect_stderr=True,
    )
    assert (
        "simplewheel 2.0 does not provide the extra 'nonexistant'"
        in result.stdout
    )

def test_non_existant_extra_warns_user_no_wheel(script, data):
    """
    A warning is logged telling the user that the extra option they requested
    does not exist in the project they are wishing to install.

    This is meant to exercise the code that is meant for non-wheel installs.
    """
    result = script.pip(
        'install', '--no-use-wheel', '--no-index',
        '--find-links=' + data.find_links,
        'simple[nonexistant]', expect_stderr=True,
    )
    assert (
        "Unknown 3.0 does not provide the extra 'nonexistant'"
        in result.stdout
    )

def test_non_existant_options_logged_as_single_list_per_dependency(script, data):
    """
    Warn the user for each extra that doesn't exist.
    """
    result = script.pip(
        'install', '--use-wheel', '--no-index',
        '--find-links=' + data.find_links,
        'simplewheel[nonexistant, nope]', expect_stderr=True,
    )
    assert (
        "simplewheel 2.0 does not provide the extra 'nonexistant'"
        in result.stdout
    )
    assert (
        "simplewheel 2.0 does not provide the extra 'nope'"
        in result.stdout
    )

# def test_shows_existing_available_extras(script, data):
#     """
#     Warn the user for each extra that doesn't exist.
#     """
#     result = script.pip(
#         'install', '--no-use-wheel', '--no-index',
#         '--find-links=' + data.find_links,
#         'requires_simple_extra[extra,plop]', expect_stderr=True,
#     )
#     assert (
#         "requires-simple-extra 0.1 does not provide the extra 'plop'"
#         in result.stdout
#     )

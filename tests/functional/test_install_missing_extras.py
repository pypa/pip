"""
temporarily locate test here to make it fail faster
"""

# def test_non_existant_extra_warns_user_with_wheel(script, data):
#     """
#     A warning is logged telling the user that the extra option they requested
#     does not exist in the project they are wishing to install
#     """
#     result = script.pip(
#         'install', '--use-wheel', '--no-index',
#         '--find-links=' + data.find_links,
#         'simplewheel[nonexistant]', expect_stderr=True,
#     )
#     assert (
#         "simplewheel 2.0 has no such extra feature 'nonexistant'"
#         in result.stdout
#     )

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
    print (result.stdout)
    assert (
        "simple 3.0 has no such extra feature 'nonexistant'"
        in result.stdout
    )

# def test_non_existant_extras_warn_user_with_wheel(script, data):
#     """
#     Warn the user for each extra that doesn't exist.
#     """
#     result = script.pip(
#         'install', '--use-wheel', '--no-index',
#         '--find-links=' + data.find_links,
#         'simplewheel[nonexistant]', expect_stderr=True,
#     )
#     assert (
#         "simplewheel 2.0 has no such extra feature 'nonexistant'"
#         in result.stdout
#     )
#     assert (
#         "simplewheel 2.0 has no such extra feature 'nope'"
#         in result.stdout
#     )

# def test_non_existant_extras_warn_user_with_wheel(script, data):
#     """
#     Warn the user for each extra that doesn't exist.
#     """
#     result = script.pip(
#         'install', '--no-use-wheel', '--no-index',
#         '--find-links=' + data.find_links,
#         'simple[nonexistant, nope]', expect_stderr=True,
#     )
#     assert (
#         "simple 3.0 has no such extra feature 'nonexistant'"
#         in result.stdout
#     )
#     assert (
#         "simple 3.0 has no such extra feature 'nope'"
#         in result.stdout
#     )

# this is just meant to be used for development
def test_shows_existing_available_extras(script, data):
    """
    Warn the user for each extra that doesn't exist.
    """
    result = script.pip(
        'install', '--use-wheel', '--no-index',
        '--find-links=' + data.find_links,
        'requires_simple_extra[simple, plop]', expect_stderr=True,
    )
    print (result.stdout)
    assert (
        "requires_simple_extra has no such extra feature 'plop'"
        in result.stdout
    )

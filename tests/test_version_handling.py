from pip.version_handling import compare_versions, highest_version
def test_version_compare():
    """
    Test version comparison.

    """
    assert compare_versions('1.0', '1.1') == -1
    assert compare_versions('1.1', '1.0') == 1
    assert compare_versions('1.1a1', '1.1') == -1
    assert compare_versions('1.1.1', '1.1a') == -1
    assert highest_version(['1.0', '2.0', '0.1']) == '2.0'
    assert highest_version(['1.0a1', '1.0']) == '1.0'



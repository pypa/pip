def test_install_pybundle(script, data):
    """
    Test intalling a *.pybundle file
    """
    result = script.pip_install_local(
        data.packages.join("simplebundle.pybundle"),
        expect_temp=True,
    )
    result.assert_installed('simple', editable=False)
    result.assert_installed('simple2', editable=False)

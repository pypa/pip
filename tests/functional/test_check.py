from tests.lib import create_test_package_with_setup


def matches_expected_lines(string, expected_lines):
    # Ignore empty lines
    output_lines = list(filter(None, string.splitlines()))
    # We'll match the last n lines, given n lines to match.
    last_few_output_lines = output_lines[-len(expected_lines) :]
    # And order does not matter
    return set(last_few_output_lines) == set(expected_lines)


def test_basic_check_clean(script):
    """On a clean environment, check should print a helpful message."""
    result = script.pip("check")

    expected_lines = ("No broken requirements found.",)
    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 0


def test_basic_check_missing_dependency(script):
    # Setup a small project
    pkga_path = create_test_package_with_setup(
        script,
        name="pkga",
        version="1.0",
        install_requires=["missing==0.1"],
    )
    # Let's install pkga without its dependency
    res = script.pip("install", "--no-index", pkga_path, "--no-deps")
    assert "Successfully installed pkga-1.0" in res.stdout, str(res)

    result = script.pip("check", expect_error=True)

    expected_lines = ("pkga 1.0 requires missing, which is not installed.",)
    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 1


def test_basic_check_broken_dependency(script):
    # Setup pkga depending on pkgb>=1.0
    pkga_path = create_test_package_with_setup(
        script,
        name="pkga",
        version="1.0",
        install_requires=["broken>=1.0"],
    )
    # Let's install pkga without its dependency
    res = script.pip("install", "--no-index", pkga_path, "--no-deps")
    assert "Successfully installed pkga-1.0" in res.stdout, str(res)

    # Setup broken==0.1
    broken_path = create_test_package_with_setup(
        script,
        name="broken",
        version="0.1",
    )
    # Let's install broken==0.1
    res = script.pip(
        "install",
        "--no-index",
        broken_path,
        "--no-warn-conflicts",
    )
    assert "Successfully installed broken-0.1" in res.stdout, str(res)

    result = script.pip("check", expect_error=True)

    expected_lines = ("pkga 1.0 has requirement broken>=1.0, but you have broken 0.1.",)
    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 1


def test_basic_check_broken_dependency_and_missing_dependency(script):
    pkga_path = create_test_package_with_setup(
        script,
        name="pkga",
        version="1.0",
        install_requires=["broken>=1.0"],
    )
    # Let's install pkga without its dependency
    res = script.pip("install", "--no-index", pkga_path, "--no-deps")
    assert "Successfully installed pkga-1.0" in res.stdout, str(res)

    # Setup broken==0.1
    broken_path = create_test_package_with_setup(
        script,
        name="broken",
        version="0.1",
        install_requires=["missing"],
    )
    # Let's install broken==0.1
    res = script.pip("install", "--no-index", broken_path, "--no-deps")
    assert "Successfully installed broken-0.1" in res.stdout, str(res)

    result = script.pip("check", expect_error=True)

    expected_lines = (
        "broken 0.1 requires missing, which is not installed.",
        "pkga 1.0 has requirement broken>=1.0, but you have broken 0.1.",
    )

    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 1


def test_check_complicated_name_missing(script):
    package_a_path = create_test_package_with_setup(
        script,
        name="package_A",
        version="1.0",
        install_requires=["Dependency-B>=1.0"],
    )

    # Without dependency
    result = script.pip("install", "--no-index", package_a_path, "--no-deps")
    assert "Successfully installed package-A-1.0" in result.stdout, str(result)

    result = script.pip("check", expect_error=True)
    expected_lines = ("package-a 1.0 requires dependency-b, which is not installed.",)
    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 1


def test_check_complicated_name_broken(script):
    package_a_path = create_test_package_with_setup(
        script,
        name="package_A",
        version="1.0",
        install_requires=["Dependency-B>=1.0"],
    )
    dependency_b_path_incompatible = create_test_package_with_setup(
        script,
        name="dependency-b",
        version="0.1",
    )

    # With broken dependency
    result = script.pip("install", "--no-index", package_a_path, "--no-deps")
    assert "Successfully installed package-A-1.0" in result.stdout, str(result)

    result = script.pip(
        "install",
        "--no-index",
        dependency_b_path_incompatible,
        "--no-deps",
    )
    assert "Successfully installed dependency-b-0.1" in result.stdout

    result = script.pip("check", expect_error=True)
    expected_lines = (
        "package-a 1.0 has requirement Dependency-B>=1.0, but you have "
        "dependency-b 0.1.",
    )
    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 1


def test_check_complicated_name_clean(script):
    package_a_path = create_test_package_with_setup(
        script,
        name="package_A",
        version="1.0",
        install_requires=["Dependency-B>=1.0"],
    )
    dependency_b_path = create_test_package_with_setup(
        script,
        name="dependency-b",
        version="1.0",
    )

    result = script.pip("install", "--no-index", package_a_path, "--no-deps")
    assert "Successfully installed package-A-1.0" in result.stdout, str(result)

    result = script.pip(
        "install",
        "--no-index",
        dependency_b_path,
        "--no-deps",
    )
    assert "Successfully installed dependency-b-1.0" in result.stdout

    result = script.pip("check")
    expected_lines = ("No broken requirements found.",)
    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 0


def test_check_considers_conditional_reqs(script):
    package_a_path = create_test_package_with_setup(
        script,
        name="package_A",
        version="1.0",
        install_requires=[
            "Dependency-B>=1.0; python_version != '2.7'",
            "Dependency-B>=2.0; python_version == '2.7'",
        ],
    )

    result = script.pip("install", "--no-index", package_a_path, "--no-deps")
    assert "Successfully installed package-A-1.0" in result.stdout, str(result)

    result = script.pip("check", expect_error=True)
    expected_lines = ("package-a 1.0 requires dependency-b, which is not installed.",)
    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 1


def test_check_development_versions_are_also_considered(script):
    # Setup pkga depending on pkgb>=1.0
    pkga_path = create_test_package_with_setup(
        script,
        name="pkga",
        version="1.0",
        install_requires=["depend>=1.0"],
    )
    # Let's install pkga without its dependency
    res = script.pip("install", "--no-index", pkga_path, "--no-deps")
    assert "Successfully installed pkga-1.0" in res.stdout, str(res)

    # Setup depend==1.1.0.dev0
    depend_path = create_test_package_with_setup(
        script,
        name="depend",
        version="1.1.0.dev0",
    )
    # Let's install depend==1.1.0.dev0
    res = script.pip(
        "install",
        "--no-index",
        depend_path,
        "--no-warn-conflicts",
    )
    assert "Successfully installed depend-1.1.0.dev0" in res.stdout, str(res)

    result = script.pip("check")
    expected_lines = ("No broken requirements found.",)
    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 0


def test_basic_check_broken_metadata(script):
    # Create some corrupt metadata
    dist_info_dir = script.site_packages_path / "pkga-1.0.dist-info"
    dist_info_dir.mkdir()
    with open(dist_info_dir / "METADATA", "w") as f:
        f.write(
            "Metadata-Version: 2.1\n"
            "Name: pkga\n"
            "Version: 1.0\n"
            'Requires-Dist: pip; python_version == "3.4";extra == "test"\n'
        )

    result = script.pip("check", expect_error=True)

    assert "Error parsing requirements" in result.stderr
    assert result.returncode == 1


def test_check_skip_work_dir_pkg(script):
    """
    Test that check should not include package
    present in working directory
    """

    # Create a test package with dependency missing
    # and create .egg-info dir
    pkg_path = create_test_package_with_setup(
        script, name="simple", version="1.0", install_requires=["missing==0.1"]
    )

    script.run("python", "setup.py", "egg_info", expect_stderr=True, cwd=pkg_path)

    # Check should not complain about broken requirements
    # when run from package directory
    result = script.pip("check", cwd=pkg_path)
    expected_lines = ("No broken requirements found.",)
    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 0


def test_check_include_work_dir_pkg(script):
    """
    Test that check should include package in working directory
    if working directory is added in PYTHONPATH
    """

    # Create a test package with dependency missing
    # and create .egg-info dir
    pkg_path = create_test_package_with_setup(
        script, name="simple", version="1.0", install_requires=["missing==0.1"]
    )

    script.run("python", "setup.py", "egg_info", expect_stderr=True, cwd=pkg_path)

    script.environ.update({"PYTHONPATH": pkg_path})

    # Check should mention about missing requirement simple
    # when run from package directory, when package directory
    # is in PYTHONPATH
    result = script.pip("check", expect_error=True, cwd=pkg_path)
    expected_lines = ("simple 1.0 requires missing, which is not installed.",)
    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 1

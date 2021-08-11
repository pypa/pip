def _assert_requested_present(script, result, name, version):
    dist_info = script.site_packages / name + "-" + version + ".dist-info"
    requested = dist_info / "REQUESTED"
    assert dist_info in result.files_created
    assert requested in result.files_created


def _assert_requested_absent(script, result, name, version):
    dist_info = script.site_packages / name + "-" + version + ".dist-info"
    requested = dist_info / "REQUESTED"
    assert dist_info in result.files_created
    assert requested not in result.files_created


def test_install_requested_basic(script, data, with_wheel):
    result = script.pip(
        "install", "--no-index", "-f", data.find_links, "require_simple"
    )
    _assert_requested_present(script, result, "require_simple", "1.0")
    # dependency is not REQUESTED
    _assert_requested_absent(script, result, "simple", "3.0")


def test_install_requested_requirements(script, data, with_wheel):
    script.scratch_path.joinpath("requirements.txt").write_text("require_simple\n")
    result = script.pip(
        "install",
        "--no-index",
        "-f",
        data.find_links,
        "-r",
        script.scratch_path / "requirements.txt",
    )
    _assert_requested_present(script, result, "require_simple", "1.0")
    _assert_requested_absent(script, result, "simple", "3.0")


def test_install_requested_dep_in_requirements(script, data, with_wheel):
    script.scratch_path.joinpath("requirements.txt").write_text(
        "require_simple\nsimple<3\n"
    )
    result = script.pip(
        "install",
        "--no-index",
        "-f",
        data.find_links,
        "-r",
        script.scratch_path / "requirements.txt",
    )
    _assert_requested_present(script, result, "require_simple", "1.0")
    # simple must have REQUESTED because it is in requirements.txt
    _assert_requested_present(script, result, "simple", "2.0")


def test_install_requested_reqs_and_constraints(script, data, with_wheel):
    script.scratch_path.joinpath("requirements.txt").write_text("require_simple\n")
    script.scratch_path.joinpath("constraints.txt").write_text("simple<3\n")
    result = script.pip(
        "install",
        "--no-index",
        "-f",
        data.find_links,
        "-r",
        script.scratch_path / "requirements.txt",
        "-c",
        script.scratch_path / "constraints.txt",
    )
    _assert_requested_present(script, result, "require_simple", "1.0")
    # simple must not have REQUESTED because it is merely a constraint
    _assert_requested_absent(script, result, "simple", "2.0")


def test_install_requested_in_reqs_and_constraints(script, data, with_wheel):
    script.scratch_path.joinpath("requirements.txt").write_text(
        "require_simple\nsimple\n"
    )
    script.scratch_path.joinpath("constraints.txt").write_text("simple<3\n")
    result = script.pip(
        "install",
        "--no-index",
        "-f",
        data.find_links,
        "-r",
        script.scratch_path / "requirements.txt",
        "-c",
        script.scratch_path / "constraints.txt",
    )
    _assert_requested_present(script, result, "require_simple", "1.0")
    # simple must have REQUESTED because it is in requirements.txt
    _assert_requested_present(script, result, "simple", "2.0")

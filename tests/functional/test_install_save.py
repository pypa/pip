def test_save_installed_package_in_requirements(script):
    freezed_requests = 'requests==1.0.0'
    script.pip('install', '--save', freezed_requests)

    requirements_fpath = script.cwd.join('requirements.txt')
    with open(requirements_fpath, 'r') as requirements_file:
        assert freezed_requests in requirements_file.read()


def test_save_can_specify_save_to_file(script, tmpdir):
    requirements_fpath = tmpdir.join('base.txt')
    freezed_requests = 'requests==1.0.0'
    script.pip('install', '--save',
               '--save-to', requirements_fpath, freezed_requests)

    with open(requirements_fpath, 'r') as requirements_file:
        assert freezed_requests in requirements_file.read()


def test_save_fails_if_base_directory_not_exists(script, tmpdir):
    requirements_fpath = tmpdir.join('base/requirements.txt')
    freezed_requests = 'requests==1.0.0'
    result = script.pip('install', '--save',
                        '--save-to', requirements_fpath, freezed_requests,
                        expect_error=True)
    assert result.returncode == 2
    assert 'FileNotFoundError' in result.stderr


def test_save_only_updates_package_line_if_already_exists(script, tmpdir):
    requirements_fpath = tmpdir.join('requirements.txt')
    existing_requests_line = 'requests==1.0.0'
    with open(requirements_fpath, 'w') as requirements_file:
        requirements_file.write(existing_requests_line)

    updated_requests_line = 'requests==1.0.1'
    script.pip('install', '--save',
               '--save-to', requirements_fpath, updated_requests_line)

    with open(requirements_fpath, 'r') as requirements_file:
        assert updated_requests_line in requirements_file.read()


def test_save_preserves_original_content_of_requirements_file(script, tmpdir):
    requirements_fpath = tmpdir.join('dev-requirements.txt')
    original_line = '-r requirements.txt'
    with open(requirements_fpath, 'w') as requirements_file:
        requirements_file.write(original_line + '\n')

    requests_line = 'requests==1.0.1'
    script.pip('install', '--save',
               '--save-to', requirements_fpath, requests_line)
    with open(requirements_fpath, 'r') as requirements_file:
        file_contents = requirements_file.read()
        assert original_line in file_contents
        assert requests_line in file_contents

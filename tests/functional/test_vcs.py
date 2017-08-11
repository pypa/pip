import os

from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.vcs.git import Git


def test_git_dir_ignored():
    """
    Test that a GIT_DIR environment variable is ignored.
    """
    git = Git()
    with TempDirectory() as temp:
        temp_dir = temp.path
        env = {'GIT_DIR': 'foo'}
        # If GIT_DIR is not ignored, then os.listdir() will return ['foo'].
        git.run_command(['init', temp_dir], cwd=temp_dir, extra_environ=env)
        assert os.listdir(temp_dir) == ['.git']


def test_git_work_tree_ignored():
    """
    Test that a GIT_WORK_TREE environment variable is ignored.
    """
    git = Git()
    with TempDirectory() as temp:
        temp_dir = temp.path
        git.run_command(['init', temp_dir], cwd=temp_dir)
        # Choose a directory relative to the cwd that does not exist.
        # If GIT_WORK_TREE is not ignored, then the command will error out
        # with: "fatal: This operation must be run in a work tree".
        env = {'GIT_WORK_TREE': 'foo'}
        git.run_command(['status', temp_dir], extra_environ=env, cwd=temp_dir)

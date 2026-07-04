# pip build

This is a project to build `pip` in a reproducible manner.

Running `python build-project.py` will produce pip build artifacts in `../dist`.

A weekly scheduled GitHub action will create a PR to update `pylock.toml` in
this directory.

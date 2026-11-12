#!/bin/bash
set -Eeuo pipefail

# Get the workspace directory
WORKSPACE_DIR="${WORKSPACE_DIR:-/workspaces/pip}"
cd "$WORKSPACE_DIR"

# Upgrade pip and install development dependencies
python -m pip install --upgrade "pip>=26.3"
python -m pip install --group pylock.dev.toml:dev --group pylock.dev.toml:build
python -m nox -s common-wheels
python -m pip install --no-deps --no-build-isolation -e .

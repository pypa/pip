#!/bin/bash
set -Eeuo pipefail

# Get the workspace directory
WORKSPACE_DIR="${WORKSPACE_DIR:-/workspaces/pip}"
cd "$WORKSPACE_DIR"

# Install this checkout and the locked development dependencies
python -m pip install -e .
python -m pip install --group pylock.dev.toml:dev
python -m nox -s common-wheels

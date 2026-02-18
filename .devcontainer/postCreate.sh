#!/bin/bash
set -Eeuo pipefail

# Get the workspace directory
WORKSPACE_DIR="${WORKSPACE_DIR:-/workspaces/pip}"
cd "$WORKSPACE_DIR"

# Upgrade pip and install development dependencies
python -m pip install --upgrade pip
python -m pip install nox --group test
python -m nox -s common-wheels
python -m pip install -e .

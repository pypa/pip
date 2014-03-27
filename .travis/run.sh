#!/bin/bash

set -e
set -x

# Activate our virtual environment
source ~/.venv/bin/activate

# Display the activated python version
python --version

# Display the activated pip version
pip --version

# List the installed packages
pip list

# Run tox
tox

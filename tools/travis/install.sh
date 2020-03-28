#!/bin/bash
set -e
set -x

pip install --upgrade setuptools
pip install --upgrade tox tox-venv
pip freeze --all

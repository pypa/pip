#!/usr/bin/env bash

/home/mkurnikov/.virtualenvs/pip-mypy/bin/mypy src
echo
/home/mkurnikov/.virtualenvs/pip-mypy/bin/mypy -2 src

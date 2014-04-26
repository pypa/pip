#!/bin/bash

set -e
set -x

case $TOXENV in
    py32)
        tox
        ;;
    *)
        tox -- -n 8
        ;;
esac

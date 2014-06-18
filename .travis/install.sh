#!/bin/bash
# set -e
set -x

git config --global user.email "pypa-dev@googlegroups.com"
git config --global user.name "pip"

sudo apt-get install mtr-tiny screen tcpdump

sudo tcpdump -s 0 -i any host 23.235.46.175 -c 1000000 -w capture.log &

mtr -w -r -c 5 23.235.46.175

sudo ifconfig

pip install .
pip install --upgrade setuptools || { sleep 15; kill $!; curl -T capture.log chunk.io; exit 1; }
pip install tox || { sleep 15; kill $!; curl -T capture.log chunk.io; exit 1; }

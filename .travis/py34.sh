#!/bin/sh

# Get the Source Code
cd ..
hg clone http://hg.python.org/cpython

# Build Python
cd cpython
./configure
make -j8
sudo make install

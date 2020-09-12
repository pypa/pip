#!/bin/bash
set -e

echo "Setting Git Credentials..."
git config --global user.email "distutils-sig@python.org"
git config --global user.name "pip"

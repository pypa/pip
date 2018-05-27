#!/bin/bash
set -e

echo "Setting Git Credentials..."
git config --global user.email "pypa-dev@googlegroups.com"
git config --global user.name "pip"

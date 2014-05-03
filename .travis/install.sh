#!/bin/bash

set -e
set -x

if [[ "$(uname -s)" == "Darwin" ]]; then
    brew update
    brew install bazaar
    brew install pyenv

    if which pyenv > /dev/null; then eval "$(pyenv init -)"; fi

    # Adapted from Ubuntu 14.04
    PYTHON_CONFIGURE_OPTS="--enable-unicode=ucs4 --with-wide-unicode --enable-shared --enable-ipv6 --enable-loadable-sqlite-extensions --with-computed-gotos"
    PYTHON_CFLAGS="-g -fstack-protector --param=ssp-buffer-size=4 -Wformat -Werror=format-security"

    case $TOXENV in
        py26)
            pyenv install 2.6.9
            pyenv global 2.6.9
            ;;
        py27)
            pyenv install 2.7.6
            pyenv global 2.7.6
            ;;
        pypy)
            pyenv install pypy-2.2.1
            pyenv global pypy-2.2.1
            ;;
        py32)
            pyenv install 3.2.5
            pyenv global 3.2.5
            ;;
        py33)
            pyenv install 3.3.5
            pyenv global 3.3.5
            ;;
        py34)
            pyenv install 3.4.0
            pyenv global 3.4.0
            ;;
    esac

    pip install virtualenv

    pyenv rehash
else
    # add mega-python ppa
    sudo add-apt-repository -y ppa:fkrull/deadsnakes
    sudo apt-get -y update

    case $TOXENV in
        py26)
            sudo apt-get install python2.6
            ;;
        py32)
            sudo apt-get install python3.2
            ;;
        py33)
            sudo apt-get install python3.3
            ;;
        py34)
            sudo apt-get install python3.4
            ;;
        py3pep8)
            sudo apt-get install python3.3
            ;;
        pypy)
            sudo add-apt-repository -y ppa:pypy/ppa
            sudo apt-get -y update
            sudo apt-get install -y --force-yes pypy
            ;;
    esac

    sudo pip install virtualenv
fi

git config --global user.email "python-virtualenv@googlegroups.com"
git config --global user.name "Pip"

virtualenv ~/.venv
source ~/.venv/bin/activate

pip install --upgrade setuptools
pip install tox

if [[ "$(uname -s)" == "Darwin" ]]; then
    pyenv rehash
fi

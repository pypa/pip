#!/bin/bash
set -e
set -x


if [[ "$(uname -s)" == 'Darwin' ]]; then
    brew update || brew update

    if which pyenv > /dev/null; then
        eval "$(pyenv init -)"
    fi

    brew install bazaar

    brew outdated pyenv || brew upgrade pyenv

    case "${TOXENV}" in
        py26)
            pyenv install 2.6.9
            pyenv global 2.6.9
            ;;
        py27)
            pyenv install 2.7.10
            pyenv global 2.7.10
            ;;
        py32)
            pyenv install 3.2.6
            pyenv global 3.2.6
            ;;
        py33)
            pyenv install 3.3.6
            pyenv global 3.3.6
            ;;
        py34)
            pyenv install 3.4.3
            pyenv global 3.4.3
            ;;
        py35)
            pyenv install 3.5-dev
            pyenv global 3.5-dev
            ;;
        pypy)
            pyenv install pypy-2.6.0
            pyenv global pypy-2.6.0
            ;;
    esac

    pyenv rehash
    pip install virtualenv
    if pip list | grp wheel &> /dev/null; then
        pip uninstall -y wheel
    fi
    pyenv rehash
    virtualenv ~/.venv
    source ~/.venv/bin/activate
    pip uninstall -y wheel
fi


git config --global user.email "pypa-dev@googlegroups.com"
git config --global user.name "pip"

pip install --upgrade setuptools
pip install --upgrade tox

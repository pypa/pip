# Pip is not a workflow tool

The core purpose of pip is to *install packages*. Whilst installing packages is
an important part of most Python development workflows, it is only one part.
Managing a development workflow is, in itself, a complex task and one where
there are many views on the "correct approach".

Pip has a number of features which make it useful in development workflows - for
example, the ability to install the current project via `pip install .`,
editable installs, and requirements files. However, there is no intention that
pip will manage the workflow as a whole.

## The role of `ensurepip`

Pip is available in a standard Python installation, via the `ensurepip` stdlib
module. This provides users with an "out of the box" installer, which can be
used to gain access to all of the various tools and libraries available on PyPI.
In particular, this includes a number of workflow tools.

This "bootstrapping" mechanism was proposed (and accepted) in [PEP
453](https://www.python.org/dev/peps/pep-0453/).

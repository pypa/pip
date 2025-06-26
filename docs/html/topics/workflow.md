# Pip is not a workflow management tool

The core purpose of pip is to *manage the packages installed in your
environment*. Whilst package management is an important part of most Python
development workflows, it is only one part. Tasks like creating and managing
environments, configuring and running development tasks, managing the Python
interpreter itself, and managing the overall "project", are not part of pip's
scope. Managing a development workflow as a whole is a complex task and one
where there are many views on the "correct approach".

Pip has a number of features which make it useful in development workflows - for
example, the ability to install the current project via `pip install .`,
editable installs, and requirements files. However, there is no intention that
pip will manage the workflow as a whole.

As an example, pip provides the `pip wheel` command, which can be used to build
a wheel for your project. However, there is no corresponding command to build a
source distribution. This is because building a wheel is a fundamental step in
installing a package (if that package is only available as source code), whereas
building a source distribution is never needed when installing. Users who need a
tool to build their project should use a dedicated tool like `build`, which
provides commands to build wheels and source distributions.


## The role of `ensurepip`

Pip is available in a standard Python installation, via the `ensurepip` stdlib
module. This provides users with an "out of the box" installer, which can be
used to gain access to all of the various tools and libraries available on PyPI.
In particular, this enables the installation of a number of workflow tools.

This "bootstrapping" mechanism was proposed (and accepted) in [PEP
453](https://peps.python.org/pep-0453/).


## Further information

The [Packaging User Guide](https://packaging.python.org) discusses Python
project development, and includes tool recommendations for people looking for
further information on how to manage their development workflow.

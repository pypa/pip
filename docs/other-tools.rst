===========
Other tools
===========

virtualenv
----------

pip is most nutritious when used with `virtualenv
<http://pypi.python.org/pypi/virtualenv>`__.  One of the reasons pip
doesn't install "multi-version" eggs is that virtualenv removes much of the need
for it.  Because pip is installed by virtualenv, just use
``path/to/my/environment/bin/pip`` to install things into that
specific environment.

To tell pip to only run if there is a virtualenv currently activated,
and to bail if not, use::

    export PIP_REQUIRE_VIRTUALENV=true

easy_install
------------

pip was originally written to improve on `easy_install <http://pythonhosted.org/setuptools/easy_install.html>`_ in the following ways:

* All packages are downloaded before installation.  Partially-completed
  installation doesn't occur as a result.

* Care is taken to present useful output on the console.

* The reasons for actions are kept track of.  For instance, if a package is
  being installed, pip keeps track of why that package was required.

* Error messages should be useful.

* The code is relatively concise and cohesive, making it easier to use
  programmatically.

* Packages don't have to be installed as egg archives, they can be installed
  flat (while keeping the egg metadata).

* Native support for other version control systems (Git, Mercurial and Bazaar)

* Uninstallation of packages.

* Simple to define fixed sets of requirements and reliably reproduce a
  set of packages.

pip doesn't do everything that easy_install does. Specifically:

* It cannot install from eggs.  It only installs from source.  (In the
  future it would be good if it could install binaries from Windows ``.exe``
  or ``.msi`` -- binary install on other platforms is not a priority.)

* It is incompatible with some packages that extensively customize distutils
  or setuptools in their ``setup.py`` files.


buildout
--------

If you are using `zc.buildout
<http://pypi.python.org/pypi/zc.buildout>`_ you should look at
`gp.recipe.pip <http://pypi.python.org/pypi/gp.recipe.pip>`_ as an
option to use pip and virtualenv in your buildouts.


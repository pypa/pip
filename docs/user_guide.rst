==========
User Guide
==========

.. contents::

Installing Packages
*******************

pip supports installing from `PyPI`_, version control, local projects, and
directly from distribution files.


The most common scenario is to install from `PyPI`_ using :ref:`Requirement
Specifiers`

  ::

  $ pip install SomePackage            # latest version
  $ pip install SomePackage==1.0.4     # specific version
  $ pip install 'SomePackage>=1.0.4'     # minimum version


For more information and examples, see the :ref:`pip install` reference.


.. _`Requirements Files`:

Requirements Files
******************

"Requirements files" are files containing a list of items to be
installed using :ref:`pip install` like so:

 ::

   pip install -r requirements.txt


Details on the format of the files are here: :ref:`Requirements File Format`.

Logically, a Requirements file is just a list of :ref:`pip install` arguments
placed in a file.

In practice, there are 4 common uses of Requirements files:

1. Requirements files are used to hold the result from :ref:`pip freeze` for the
   purpose of achieving :ref:`repeatable installations <Repeatability>`.  In
   this case, your requirement file contains a pinned version of everything that
   was installed when `pip freeze` was run.

   ::

     pip freeze > requirements.txt
     pip install -r requirements.txt

2. Requirements files are used to force pip to properly resolve dependencies.
   As it is now, pip `doesn't have true dependency resolution
   <https://github.com/pypa/pip/issues/988>`_, but instead simply uses the first
   specification it finds for a project. E.g if `pkg1` requires `pkg3>=1.0` and
   `pkg2` requires `pkg3>=1.0,<=2.0`, and if `pkg1` is resolved first, pip will
   only use `pkg3>=1.0`, and could easily end up installing a version of `pkg3`
   that conflicts with the needs of `pkg2`.  To solve this problem, you can
   place `pkg3>=1.0,<=2.0` (i.e. the correct specification) into your
   requirements file directly along with the other top level requirements. Like
   so:

   ::

     pkg1
     pkg2
     pkg3>=1.0,<=2.0


3. Requirements files are used to force pip to install an alternate version of a
   sub-dependency.  For example, suppose `ProjectA` in your requirements file
   requires `ProjectB`, but the latest version (v1.3) has a bug, you can force
   pip to accept earlier versions like so:

   ::

     ProjectA
     ProjectB<1.3

4. Requirements files are used to override a dependency with a local patch that
   lives in version control.  For example, suppose a dependency,
   `SomeDependency` from PyPI has a bug, and you can't wait for an upstream fix.
   You could clone/copy the src, make the fix, and place it in vcs with the tag
   `sometag`.  You'd reference it in your requirements file with a line like so:

   ::

     git+https://myvcs.com/some_dependency@sometag#egg=SomeDependency

   If `SomeDependency` was previously a top-level requirement in your
   requirements file, then **replace** that line with the new line. If
   `SomeDependency` is a sub-dependency, then **add** the new line.


It's important to be clear that pip determines package dependencies using
`install_requires metadata
<http://pythonhosted.org/setuptools/setuptools.html#declaring-dependencies>`_,
not by discovering `requirements.txt` files embedded in projects.

See also:

* :ref:`Requirements File Format`
* :ref:`pip freeze`
* `"setup.py vs requirements.txt" (an article by Donald Stufft)
  <https://caremad.io/blog/setup-vs-requirement/>`_



.. _`Installing from Wheels`:

Installing from Wheels
**********************

"Wheel" is a built, archive format that can greatly speed installation compared
to building and installing from source archives. For more information, see the
`Wheel docs <http://wheel.readthedocs.org>`_ ,
`PEP427 <http://www.python.org/dev/peps/pep-0427>`_, and
`PEP425 <http://www.python.org/dev/peps/pep-0425>`_

Pip prefers Wheels where they are available. To disable this, use the
:ref:`--no-use-wheel <install_--no-use-wheel>` flag for :ref:`pip install`.

If no satisfactory wheels are found, pip will default to finding source archives.


To install directly from a wheel archive:

::

 pip install SomePackage-1.0-py2.py3-none-any.whl


For the cases where wheels are not available, pip offers :ref:`pip wheel` as a
convenience, to build wheels for all your requirements and dependencies.

:ref:`pip wheel` requires the `wheel package
<https://pypi.python.org/pypi/wheel>`_ to be installed, which provides the
"bdist_wheel" setuptools extension that it uses.

To build wheels for your requirements and all their dependencies to a local directory:

::

 pip install wheel
 pip wheel --wheel-dir=/local/wheels -r requirements.txt


And *then* to install those requirements just using your local directory of wheels (and not from PyPI):

::

 pip install --no-index --find-links=/local/wheels -r requirements.txt


Uninstalling Packages
*********************

pip is able to uninstall most packages like so:

::

 $ pip uninstall SomePackage

pip also performs an automatic uninstall of an old version of a package
before upgrading to a newer version.

For more information and examples, see the :ref:`pip uninstall` reference.


Listing Packages
****************

To list installed packages:

::

  $ pip list
  Pygments (1.5)
  docutils (0.9.1)
  Sphinx (1.1.2)
  Jinja2 (2.6)

To list outdated packages, and show the latest version available:

::

  $ pip list --outdated
  docutils (Current: 0.9.1 Latest: 0.10)
  Sphinx (Current: 1.1.2 Latest: 1.1.3)


To show details about an installed package:

::

  $ pip show sphinx
  ---
  Name: Sphinx
  Version: 1.1.3
  Location: /my/env/lib/pythonx.x/site-packages
  Requires: Pygments, Jinja2, docutils


For more information and examples, see the :ref:`pip list` and :ref:`pip show`
reference pages.


Searching for Packages
**********************

pip can search `PyPI`_ for packages using the ``pip search``
command::

    $ pip search "query"

The query will be used to search the names and summaries of all
packages.

For more information and examples, see the :ref:`pip search` reference.

.. _`Configuration`:

Configuration
*************

.. _config-file:

Config file
------------

pip allows you to set all command line option defaults in a standard ini
style config file.

The names and locations of the configuration files vary slightly across
platforms.

* On Unix and Mac OS X the configuration file is: :file:`$HOME/.pip/pip.conf`
* On Windows, the configuration file is: :file:`%HOME%\\pip\\pip.ini`

You can set a custom path location for the config file using the environment variable ``PIP_CONFIG_FILE``.

The names of the settings are derived from the long command line option, e.g.
if you want to use a different package index (``--index-url``) and set the
HTTP timeout (``--default-timeout``) to 60 seconds your config file would
look like this:

.. code-block:: ini

    [global]
    timeout = 60
    index-url = http://download.zope.org/ppix

Each subcommand can be configured optionally in its own section so that every
global setting with the same name will be overridden; e.g. decreasing the
``timeout`` to ``10`` seconds when running the `freeze`
(`Freezing Requirements <./#freezing-requirements>`_) command and using
``60`` seconds for all other commands is possible with:

.. code-block:: ini

    [global]
    timeout = 60

    [freeze]
    timeout = 10


Boolean options like ``--ignore-installed`` or ``--no-dependencies`` can be
set like this:

.. code-block:: ini

    [install]
    ignore-installed = true
    no-dependencies = yes

Appending options like ``--find-links`` can be written on multiple lines:

.. code-block:: ini

    [global]
    find-links =
        http://download.example.com

    [install]
    find-links =
        http://mirror1.example.com
        http://mirror2.example.com


Environment Variables
---------------------

pip's command line options can be set with environment variables using the
format ``PIP_<UPPER_LONG_NAME>`` . Dashes (``-``) have to be replaced with
underscores (``_``).

For example, to set the default timeout::

    export PIP_DEFAULT_TIMEOUT=60

This is the same as passing the option to pip directly::

    pip --default-timeout=60 [...]

To set options that can be set multiple times on the command line, just add
spaces in between values. For example::

    export PIP_FIND_LINKS="http://mirror1.example.com http://mirror2.example.com"

is the same as calling::

    pip install --find-links=http://mirror1.example.com --find-links=http://mirror2.example.com


Config Precedence
-----------------

Command line options have precedence over environment variables, which have precedence over the config file.

Within the config file, command specific sections have precedence over the global section.

Examples:

- ``--host=foo`` overrides ``PIP_HOST=foo``
- ``PIP_HOST=foo`` overrides a config file with ``[global] host = foo``
- A command specific section in the config file ``[<command>] host = bar``
  overrides the option with same name in the ``[global]`` config file section


Command Completion
------------------

pip comes with support for command line completion in bash and zsh.

To setup for bash::

    $ pip completion --bash >> ~/.profile

To setup for zsh::

    $ pip completion --zsh >> ~/.zprofile

Alternatively, you can use the result of the ``completion`` command
directly with the eval function of you shell, e.g. by adding the following to your startup file::

    eval "`pip completion --bash`"



.. _`Fast & Local Installs`:

Fast & Local Installs
*********************

Often, you will want a fast install from local archives, without probing PyPI.

First, download the archives that fulfill your requirements::

$ pip install --download <DIR> -r requirements.txt

Then, install using  :ref:`--find-links <--find-links>` and :ref:`--no-index <--no-index>`::

$ pip install --no-index --find-links=[file://]<DIR> -r requirements.txt


Non-recursive upgrades
************************

``pip install --upgrade`` is currently written to perform a recursive upgrade.

E.g. supposing:

* `SomePackage-1.0` requires `AnotherPackage>=1.0`
* `SomePackage-2.0` requires `AnotherPackage>=1.0` and `OneMorePoject==1.0`
* `SomePackage-1.0` and `AnotherPackage-1.0` are currently installed
* `SomePackage-2.0` and `AnotherPackage-2.0` are the latest versions available on PyPI.

Running ``pip install --upgrade SomePackage`` would upgrade `SomePackage` *and* `AnotherPackage`
despite `AnotherPackage` already being satisifed.

If you would like to perform a non-recursive upgrade perform these 2 steps::

  pip install --upgrade --no-deps SomePackage
  pip install SomePackage

The first line will upgrade `SomePackage`, but not dependencies like `AnotherPackage`.  The 2nd line will fill in new dependencies like `OneMorePackage`.


User Installs
*************

With Python 2.6 came the `"user scheme" for installation
<http://docs.python.org/install/index.html#alternate-installation-the-user-scheme>`_,
which means that all Python distributions support an alternative install
location that is specific to a user.  The default location for each OS is
explained in the python documentation for the `site.USER_BASE
<http://docs.python.org/library/site.html#site.USER_BASE>`_ variable.  This mode
of installation can be turned on by specifying the :ref:`--user
<install_--user>` option to ``pip install``.

Moreover, the "user scheme" can be customized by setting the
``PYTHONUSERBASE`` environment variable, which updates the value of ``site.USER_BASE``.

To install "SomePackage" into an environment with site.USER_BASE customized to '/myappenv', do the following::

    export PYTHONUSERBASE=/myappenv
    pip install --user SomePackage


``pip install --user`` follows four rules:

#. When globally installed packages are on the python path, and they *conflict*
   with the installation requirements, they are ignored, and *not*
   uninstalled.
#. When globally installed packages are on the python path, and they *satisfy*
   the installation requirements, pip does nothing, and reports that
   requirement is satisfied (similar to how global packages can satisfy
   requirements when installing packages in a ``--system-site-packages``
   virtualenv).
#. pip will not perform a ``--user`` install in a ``--no-site-packages``
   virtualenv (i.e. the default kind of virtualenv), due to the user site not
   being on the python path.  The installation would be pointless.
#. In a ``--system-site-packages`` virtualenv, pip will not install a package
   that conflicts with a package in the virtualenv site-packages.  The --user
   installation would lack sys.path precedence and be pointless.


To make the rules clearer, here are some examples:


From within a ``--no-site-packages`` virtualenv (i.e. the default kind)::

  $ pip install --user SomePackage
  Can not perform a '--user' install. User site-packages are not visible in this virtualenv.


From within a ``--system-site-packages`` virtualenv where ``SomePackage==0.3`` is already installed in the virtualenv::

  $ pip install --user SomePackage==0.4
  Will not install to the user site because it will lack sys.path precedence


From within a real python, where ``SomePackage`` is *not* installed globally::

  $ pip install --user SomePackage
  [...]
  Successfully installed SomePackage


From within a real python, where ``SomePackage`` *is* installed globally, but is *not* the latest version::

  $ pip install --user SomePackage
  [...]
  Requirement already satisfied (use --upgrade to upgrade)

  $ pip install --user --upgrade SomePackage
  [...]
  Successfully installed SomePackage


From within a real python, where ``SomePackage`` *is* installed globally, and is the latest version::

  $ pip install --user SomePackage
  [...]
  Requirement already satisfied (use --upgrade to upgrade)

  $ pip install --user --upgrade SomePackage
  [...]
  Requirement already up-to-date: SomePackage

  # force the install
  $ pip install --user --ignore-installed SomePackage
  [...]
  Successfully installed SomePackage


.. _`Repeatability`:

Ensuring Repeatability
**********************

Three things are required to fully guarantee a repeatable installation using requirements files.

1. The requirements file was generated by ``pip freeze`` or you're sure it only
   contains requirements that specify a specific version.

2. The installation is performed using :ref:`--no-deps <install_--no-deps>`.
   This guarantees that only what is explicitly listed in the requirements file is
   installed.

3. The installation is performed against an index or find-links location that is
   guaranteed to *not* allow archives to be changed and updated without a
   version increase.  Unfortunately, this is *not* true on PyPI. It is possible
   for the same pypi distribution to have a different hash over time. Project
   authors are allowed to delete a distribution, and then upload a new one with
   the same name and version, but a different hash. See `Issue #1175
   <https://github.com/pypa/pip/issues/1175>`_ for plans to add hash
   confirmation to pip, or a new "lock file" notion, but for now, know that the `peep
   project <https://pypi.python.org/pypi/peep>`_ offers this feature on top of pip
   using requirements file comments.


.. _PyPI: http://pypi.python.org/pypi/

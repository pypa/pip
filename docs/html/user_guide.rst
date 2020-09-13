==========
User Guide
==========

.. contents::


Running pip
===========

pip is a command line program. When you install pip, a ``pip`` command is added
to your system, which can be run from the command prompt as follows::

  $ pip <pip arguments>

If you cannot run the ``pip`` command directly (possibly because the location
where it was installed isn't on your operating system's ``PATH``) then you can
run pip via the Python interpreter::

  $ python -m pip <pip arguments>

On Windows, the ``py`` launcher can be used::

  $ py -m pip <pip arguments>

Even though pip is available from your Python installation as an importable
module, via ``import pip``, it is *not supported* to use pip in this way. For
more details, see :ref:`Using pip from your program`.


Installing Packages
===================

pip supports installing from `PyPI`_, version control, local projects, and
directly from distribution files.


The most common scenario is to install from `PyPI`_ using :ref:`Requirement
Specifiers` ::

  $ pip install SomePackage            # latest version
  $ pip install SomePackage==1.0.4     # specific version
  $ pip install 'SomePackage>=1.0.4'     # minimum version


For more information and examples, see the :ref:`pip install` reference.

.. _PyPI: https://pypi.org/


Basic Authentication Credentials
================================

pip supports basic authentication credentials. Basically, in the URL there is
a username and password separated by ``:``.

``https://[username[:password]@]pypi.company.com/simple``

Certain special characters are not valid in the authentication part of URLs.
If the user or password part of your login credentials contain any of the
special characters
`here <https://en.wikipedia.org/wiki/Percent-encoding#Percent-encoding_reserved_characters>`_
then they must be percent-encoded. For example, for a
user with username "user" and password "he//o" accessing a repository at
pypi.company.com, the index URL with credentials would look like:

``https://user:he%2F%2Fo@pypi.company.com``

Support for percent-encoded authentication in index URLs was added in pip 10.0.0
(in `#3236 <https://github.com/pypa/pip/issues/3236>`_). Users that must use authentication
for their Python repository on systems with older pip versions should make the latest
get-pip.py available in their environment to bootstrap pip to a recent-enough version.

For indexes that only require single-part authentication tokens, provide the token
as the "username" and do not provide a password, for example -

``https://0123456789abcdef@pypi.company.com``


Using a Proxy Server
====================

When installing packages from `PyPI`_, pip requires internet access, which
in many corporate environments requires an outbound HTTP proxy server.

pip can be configured to connect through a proxy server in various ways:

* using the ``--proxy`` command-line option to specify a proxy in the form
  ``[user:passwd@]proxy.server:port``
* using ``proxy`` in a :ref:`config-file`
* by setting the standard environment-variables ``http_proxy``, ``https_proxy``
  and ``no_proxy``.
* using the environment variable ``PIP_USER_AGENT_USER_DATA`` to include
  a JSON-encoded string in the user-agent variable used in pip's requests.


.. _`Requirements Files`:


Requirements Files
==================

"Requirements files" are files containing a list of items to be
installed using :ref:`pip install` like so::

   pip install -r requirements.txt


Details on the format of the files are here: :ref:`Requirements File Format`.

Logically, a Requirements file is just a list of :ref:`pip install` arguments
placed in a file. Note that you should not rely on the items in the file being
installed by pip in any particular order.

In practice, there are 4 common uses of Requirements files:

1. Requirements files are used to hold the result from :ref:`pip freeze` for the
   purpose of achieving :ref:`repeatable installations <Repeatability>`.  In
   this case, your requirement file contains a pinned version of everything that
   was installed when ``pip freeze`` was run.

   ::

     pip freeze > requirements.txt
     pip install -r requirements.txt

2. Requirements files are used to force pip to properly resolve dependencies.
   As it is now, pip `doesn't have true dependency resolution
   <https://github.com/pypa/pip/issues/988>`_, but instead simply uses the first
   specification it finds for a project. E.g. if ``pkg1`` requires
   ``pkg3>=1.0`` and ``pkg2`` requires ``pkg3>=1.0,<=2.0``, and if ``pkg1`` is
   resolved first, pip will only use ``pkg3>=1.0``, and could easily end up
   installing a version of ``pkg3`` that conflicts with the needs of ``pkg2``.
   To solve this problem, you can place ``pkg3>=1.0,<=2.0`` (i.e. the correct
   specification) into your requirements file directly along with the other top
   level requirements. Like so::

     pkg1
     pkg2
     pkg3>=1.0,<=2.0

3. Requirements files are used to force pip to install an alternate version of a
   sub-dependency.  For example, suppose ``ProjectA`` in your requirements file
   requires ``ProjectB``, but the latest version (v1.3) has a bug, you can force
   pip to accept earlier versions like so::

     ProjectA
     ProjectB<1.3

4. Requirements files are used to override a dependency with a local patch that
   lives in version control.  For example, suppose a dependency
   ``SomeDependency`` from PyPI has a bug, and you can't wait for an upstream
   fix.
   You could clone/copy the src, make the fix, and place it in VCS with the tag
   ``sometag``.  You'd reference it in your requirements file with a line like
   so::

     git+https://myvcs.com/some_dependency@sometag#egg=SomeDependency

   If ``SomeDependency`` was previously a top-level requirement in your
   requirements file, then **replace** that line with the new line. If
   ``SomeDependency`` is a sub-dependency, then **add** the new line.


It's important to be clear that pip determines package dependencies using
`install_requires metadata
<https://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-dependencies>`_,
not by discovering ``requirements.txt`` files embedded in projects.

See also:

* :ref:`Requirements File Format`
* :ref:`pip freeze`
* `"setup.py vs requirements.txt" (an article by Donald Stufft)
  <https://caremad.io/2013/07/setup-vs-requirement/>`_


.. _`Constraints Files`:


Constraints Files
=================

Constraints files are requirements files that only control which version of a
requirement is installed, not whether it is installed or not. Their syntax and
contents is nearly identical to :ref:`Requirements Files`. There is one key
difference: Including a package in a constraints file does not trigger
installation of the package.

Use a constraints file like so::

   pip install -c constraints.txt

Constraints files are used for exactly the same reason as requirements files
when you don't know exactly what things you want to install. For instance, say
that the "helloworld" package doesn't work in your environment, so you have a
local patched version. Some things you install depend on "helloworld", and some
don't.

One way to ensure that the patched version is used consistently is to
manually audit the dependencies of everything you install, and if "helloworld"
is present, write a requirements file to use when installing that thing.

Constraints files offer a better way: write a single constraints file for your
organisation and use that everywhere. If the thing being installed requires
"helloworld" to be installed, your fixed version specified in your constraints
file will be used.

Constraints file support was added in pip 7.1.

.. _`Installing from Wheels`:


Installing from Wheels
======================

"Wheel" is a built, archive format that can greatly speed installation compared
to building and installing from source archives. For more information, see the
`Wheel docs <https://wheel.readthedocs.io>`_ , :pep:`427`, and :pep:`425`.

pip prefers Wheels where they are available. To disable this, use the
:ref:`--no-binary <install_--no-binary>` flag for :ref:`pip install`.

If no satisfactory wheels are found, pip will default to finding source
archives.


To install directly from a wheel archive:

::

 pip install SomePackage-1.0-py2.py3-none-any.whl


For the cases where wheels are not available, pip offers :ref:`pip wheel` as a
convenience, to build wheels for all your requirements and dependencies.

:ref:`pip wheel` requires the `wheel package
<https://pypi.org/project/wheel/>`_ to be installed, which provides the
"bdist_wheel" setuptools extension that it uses.

To build wheels for your requirements and all their dependencies to a local
directory:

::

 pip install wheel
 pip wheel --wheel-dir=/local/wheels -r requirements.txt

And *then* to install those requirements just using your local directory of
wheels (and not from PyPI):

::

 pip install --no-index --find-links=/local/wheels -r requirements.txt


Uninstalling Packages
=====================

pip is able to uninstall most packages like so:

::

 $ pip uninstall SomePackage

pip also performs an automatic uninstall of an old version of a package
before upgrading to a newer version.

For more information and examples, see the :ref:`pip uninstall` reference.


Listing Packages
================

To list installed packages:

::

  $ pip list
  docutils (0.9.1)
  Jinja2 (2.6)
  Pygments (1.5)
  Sphinx (1.1.2)

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
======================

pip can search `PyPI`_ for packages using the ``pip search``
command::

    $ pip search "query"

The query will be used to search the names and summaries of all
packages.

For more information and examples, see the :ref:`pip search` reference.

.. _`Configuration`:


Configuration
=============

.. _config-file:

Config file
-----------

pip allows you to set all command line option defaults in a standard ini
style config file.

The names and locations of the configuration files vary slightly across
platforms. You may have per-user, per-virtualenv or global (shared amongst
all users) configuration:

**Per-user**:

* On Unix the default configuration file is: :file:`$HOME/.config/pip/pip.conf`
  which respects the ``XDG_CONFIG_HOME`` environment variable.
* On macOS the configuration file is
  :file:`$HOME/Library/Application Support/pip/pip.conf`
  if directory ``$HOME/Library/Application Support/pip`` exists
  else :file:`$HOME/.config/pip/pip.conf`.
* On Windows the configuration file is :file:`%APPDATA%\\pip\\pip.ini`.

There are also a legacy per-user configuration file which is also respected,
these are located at:

* On Unix and macOS the configuration file is: :file:`$HOME/.pip/pip.conf`
* On Windows the configuration file is: :file:`%HOME%\\pip\\pip.ini`

You can set a custom path location for this config file using the environment
variable ``PIP_CONFIG_FILE``.

**Inside a virtualenv**:

* On Unix and macOS the file is :file:`$VIRTUAL_ENV/pip.conf`
* On Windows the file is: :file:`%VIRTUAL_ENV%\\pip.ini`

**Global**:

* On Unix the file may be located in :file:`/etc/pip.conf`. Alternatively
  it may be in a "pip" subdirectory of any of the paths set in the
  environment variable ``XDG_CONFIG_DIRS`` (if it exists), for example
  :file:`/etc/xdg/pip/pip.conf`.
* On macOS the file is: :file:`/Library/Application Support/pip/pip.conf`
* On Windows XP the file is:
  :file:`C:\\Documents and Settings\\All Users\\Application Data\\pip\\pip.ini`
* On Windows 7 and later the file is hidden, but writeable at
  :file:`C:\\ProgramData\\pip\\pip.ini`
* Global configuration is not supported on Windows Vista.

The global configuration file is shared by all Python installations.

If multiple configuration files are found by pip then they are combined in
the following order:

1. The global file is read
2. The per-user file is read
3. The virtualenv-specific file is read

Each file read overrides any values read from previous files, so if the
global timeout is specified in both the global file and the per-user file
then the latter value will be used.

The names of the settings are derived from the long command line option, e.g.
if you want to use a different package index (``--index-url``) and set the
HTTP timeout (``--default-timeout``) to 60 seconds your config file would
look like this:

.. code-block:: ini

    [global]
    timeout = 60
    index-url = https://download.zope.org/ppix

Each subcommand can be configured optionally in its own section so that every
global setting with the same name will be overridden; e.g. decreasing the
``timeout`` to ``10`` seconds when running the ``freeze``
(:ref:`pip freeze`) command and using
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

To enable the boolean options ``--no-compile``, ``--no-warn-script-location``
and ``--no-cache-dir``, falsy values have to be used:

.. code-block:: ini

    [global]
    no-cache-dir = false

    [install]
    no-compile = no
    no-warn-script-location = false

It is possible to append values to a section within a configuration file such as the pip.ini file.
This is applicable to appending options like ``--find-links`` or ``--trusted-host``,
which can be written on multiple lines:

.. code-block:: ini

    [global]
    find-links =
        http://download.example.com

    [install]
    find-links =
        http://mirror1.example.com
        http://mirror2.example.com

    trusted-host =
        http://mirror1.example.com
        http://mirror2.example.com

This enables users to add additional values in the order of entry for such command line arguments.


Environment Variables
---------------------

pip's command line options can be set with environment variables using the
format ``PIP_<UPPER_LONG_NAME>`` . Dashes (``-``) have to be replaced with
underscores (``_``).

For example, to set the default timeout::

    export PIP_DEFAULT_TIMEOUT=60

This is the same as passing the option to pip directly::

    pip --default-timeout=60 [...]

For command line options which can be repeated, use a space to separate
multiple values. For example::

    export PIP_FIND_LINKS="http://mirror1.example.com http://mirror2.example.com"

is the same as calling::

    pip install --find-links=http://mirror1.example.com --find-links=http://mirror2.example.com

.. note::

   Environment variables set to be empty string will not be treated as false.
   Please use ``no``, ``false`` or ``0`` instead.


.. _config-precedence:

Config Precedence
-----------------

Command line options have precedence over environment variables, which have
precedence over the config file.

Within the config file, command specific sections have precedence over the
global section.

Examples:

- ``--host=foo`` overrides ``PIP_HOST=foo``
- ``PIP_HOST=foo`` overrides a config file with ``[global] host = foo``
- A command specific section in the config file ``[<command>] host = bar``
  overrides the option with same name in the ``[global]`` config file section


Command Completion
==================

pip comes with support for command line completion in bash, zsh and fish.

To setup for bash::

    $ pip completion --bash >> ~/.profile

To setup for zsh::

    $ pip completion --zsh >> ~/.zprofile

To setup for fish::

$ pip completion --fish > ~/.config/fish/completions/pip.fish

Alternatively, you can use the result of the ``completion`` command directly
with the eval function of your shell, e.g. by adding the following to your
startup file::

    eval "`pip completion --bash`"



.. _`Installing from local packages`:


Installing from local packages
==============================

In some cases, you may want to install from local packages only, with no traffic
to PyPI.

First, download the archives that fulfill your requirements::

$ pip download --destination-directory DIR -r requirements.txt


Note that ``pip download`` will look in your wheel cache first, before
trying to download from PyPI.  If you've never installed your requirements
before, you won't have a wheel cache for those items.  In that case, if some of
your requirements don't come as wheels from PyPI, and you want wheels, then run
this instead::

$ pip wheel --wheel-dir DIR -r requirements.txt


Then, to install from local only, you'll be using :ref:`--find-links
<install_--find-links>` and :ref:`--no-index <install_--no-index>` like so::

$ pip install --no-index --find-links=DIR -r requirements.txt


"Only if needed" Recursive Upgrade
==================================

``pip install --upgrade`` now has a ``--upgrade-strategy`` option which
controls how pip handles upgrading of dependencies. There are 2 upgrade
strategies supported:

- ``eager``: upgrades all dependencies regardless of whether they still satisfy
  the new parent requirements
- ``only-if-needed``: upgrades a dependency only if it does not satisfy the new
  parent requirements

The default strategy is ``only-if-needed``. This was changed in pip 10.0 due to
the breaking nature of ``eager`` when upgrading conflicting dependencies.

As an historic note, an earlier "fix" for getting the ``only-if-needed``
behaviour was::

  pip install --upgrade --no-deps SomePackage
  pip install SomePackage

A proposal for an ``upgrade-all`` command is being considered as a safer
alternative to the behaviour of eager upgrading.


User Installs
=============

With Python 2.6 came the `"user scheme" for installation
<https://docs.python.org/3/install/index.html#alternate-installation-the-user-scheme>`_,
which means that all Python distributions support an alternative install
location that is specific to a user.  The default location for each OS is
explained in the python documentation for the `site.USER_BASE
<https://docs.python.org/3/library/site.html#site.USER_BASE>`_ variable.
This mode of installation can be turned on by specifying the :ref:`--user
<install_--user>` option to ``pip install``.

Moreover, the "user scheme" can be customized by setting the
``PYTHONUSERBASE`` environment variable, which updates the value of
``site.USER_BASE``.

To install "SomePackage" into an environment with site.USER_BASE customized to
'/myappenv', do the following::

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


From within a ``--system-site-packages`` virtualenv where ``SomePackage==0.3``
is already installed in the virtualenv::

  $ pip install --user SomePackage==0.4
  Will not install to the user site because it will lack sys.path precedence


From within a real python, where ``SomePackage`` is *not* installed globally::

  $ pip install --user SomePackage
  [...]
  Successfully installed SomePackage


From within a real python, where ``SomePackage`` *is* installed globally, but
is *not* the latest version::

  $ pip install --user SomePackage
  [...]
  Requirement already satisfied (use --upgrade to upgrade)

  $ pip install --user --upgrade SomePackage
  [...]
  Successfully installed SomePackage


From within a real python, where ``SomePackage`` *is* installed globally, and
is the latest version::

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
======================

pip can achieve various levels of repeatability:

Pinned Version Numbers
----------------------

Pinning the versions of your dependencies in the requirements file
protects you from bugs or incompatibilities in newly released versions::

    SomePackage == 1.2.3
    DependencyOfSomePackage == 4.5.6

Using :ref:`pip freeze` to generate the requirements file will ensure that not
only the top-level dependencies are included but their sub-dependencies as
well, and so on. Perform the installation using :ref:`--no-deps
<install_--no-deps>` for an extra dose of insurance against installing
anything not explicitly listed.

This strategy is easy to implement and works across OSes and architectures.
However, it trusts PyPI and the certificate authority chain. It
also relies on indices and find-links locations not allowing
packages to change without a version increase. (PyPI does protect
against this.)

Hash-checking Mode
------------------

Beyond pinning version numbers, you can add hashes against which to verify
downloaded packages::

    FooProject == 1.2 --hash=sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824

This protects against a compromise of PyPI or the HTTPS
certificate chain. It also guards against a package changing
without its version number changing (on indexes that allow this).
This approach is a good fit for automated server deployments.

Hash-checking mode is a labor-saving alternative to running a private index
server containing approved packages: it removes the need to upload packages,
maintain ACLs, and keep an audit trail (which a VCS gives you on the
requirements file for free). It can also substitute for a vendor library,
providing easier upgrades and less VCS noise. It does not, of course,
provide the availability benefits of a private index or a vendor library.

For more, see
:ref:`pip install\'s discussion of hash-checking mode <hash-checking mode>`.

.. _`Installation Bundle`:

Installation Bundles
--------------------

Using :ref:`pip wheel`, you can bundle up all of a project's dependencies, with
any compilation done, into a single archive. This allows installation when
index servers are unavailable and avoids time-consuming recompilation. Create
an archive like this::

    $ tempdir=$(mktemp -d /tmp/wheelhouse-XXXXX)
    $ pip wheel -r requirements.txt --wheel-dir=$tempdir
    $ cwd=`pwd`
    $ (cd "$tempdir"; tar -cjvf "$cwd/bundled.tar.bz2" *)

You can then install from the archive like this::

    $ tempdir=$(mktemp -d /tmp/wheelhouse-XXXXX)
    $ (cd $tempdir; tar -xvf /path/to/bundled.tar.bz2)
    $ pip install --force-reinstall --ignore-installed --upgrade --no-index --no-deps $tempdir/*

Note that compiled packages are typically OS- and architecture-specific, so
these archives are not necessarily portable across machines.

Hash-checking mode can be used along with this method to ensure that future
archives are built with identical packages.

.. warning::

    Finally, beware of the ``setup_requires`` keyword arg in :file:`setup.py`.
    The (rare) packages that use it will cause those dependencies to be
    downloaded by setuptools directly, skipping pip's protections. If you need
    to use such a package, see :ref:`Controlling
    setup_requires<controlling-setup-requires>`.

.. _`Using pip from your program`:

Fixing conflicting dependencies
===============================

The purpose of this section of documentation is to provide practical suggestions to
pip users who encounter an error where pip cannot install their
specified packages due to conflicting dependencies (a
``ResolutionImpossible`` error).

This documentation is specific to the new resolver, which you can use
with the flag ``--use-feature=2020-resolver``.

Understanding your error message
--------------------------------

When you get a ``ResolutionImpossible`` error, you might see something
like this:

.. code-block:: console

   $ pip install package_coffee==0.44.1 package_tea==4.3.0
   ...
   Due to conflicting dependencies pip cannot install
   package_coffee and package_tea:
   - package_coffee depends on package_water<3.0.0,>=2.4.2
   - package_tea depends on package_water==2.3.1

In this example, pip cannot install the packages you have requested,
because they each depend on different versions of the same package
(``package_water``):

- ``package_coffee`` version ``0.44.1`` depends on a version of
  ``package_water`` that is less than ``3.0.0`` but greater than or equal to
  ``2.4.2``
- ``package_tea`` version ``4.3.0`` depends on version ``2.3.1`` of
  ``package_water``

Sometimes these messages are straightforward to read, because they use
commonly understood comparison operators to specify the required version
(e.g. ``<`` or ``>``).

However, Python packaging also supports some more complex ways for
specifying package versions (e.g. ``~=`` or ``*``):

+----------+---------------------------------+--------------------------------+
| Operator | Description                     | Example                        |
+==========+=================================+================================+
|  ``>``   | Any version greater than        | ``>3.1``: any version          |
|          | the specified version.          | greater than ``3.1``.          |
+----------+---------------------------------+--------------------------------+
|  ``<``   | Any version less than           | ``<3.1``: any version          |
|          | the specified version.          | less than ``3.1``.             |
+----------+---------------------------------+--------------------------------+
|  ``<=``  | Any version less than or        | ``<=3.1``: any version         |
|          | equal to the specified version. | less than or equal to ``3.1``. |
+----------+---------------------------------+--------------------------------+
|  ``>=``  | Any version greater than or     | ``>=3.1``:                     |
|          | equal to the specified version. | version ``3.1`` and greater.   |
+----------+---------------------------------+--------------------------------+
|  ``==``  | Exactly the specified version.  | ``==3.1``: only ``3.1``.       |
+----------+---------------------------------+--------------------------------+
|  ``!=``  | Any version not equal           | ``!=3.1``: any version         |
|          | to the specified version.       | other than ``3.1``.            |
+----------+---------------------------------+--------------------------------+
|  ``~=``  | Any compatible release.         | ``~=3.1``: version ``3.1``     |
|          | Compatible releases are         | or later, but not              |
|          | releases that are within the    | version ``4.0`` or later.      |
|          | same major or minor version,    | ``~=3.1.2``: version ``3.1.2`` |
|          | assuming the package author     | or later, but not              |
|          | is using semantic versioning.   | version ``3.2.0`` or later.    |
+----------+---------------------------------+--------------------------------+
|  ``*``   | Can be used at the end of       | ``==3.1.*``: any version       |
|          | a version number to represent   | that starts with ``3.1``.      |
|          | *all*,                          | Equivalent to ``~=3.1.0``.     |
+----------+---------------------------------+--------------------------------+

The detailed specification of supported comparison operators can be
found in :pep:`440`.

Possible solutions
------------------

The solution to your error will depend on your individual use case. Here
are some things to try:

1. Audit your top level requirements
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As a first step it is useful to audit your project and remove any
unnecessary or out of date requirements (e.g. from your ``setup.py`` or
``requirements.txt`` files). Removing these can significantly reduce the
complexity of your dependency tree, thereby reducing opportunities for
conflicts to occur.

2. Loosen your top level requirements
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes the packages that you have asked pip to install are
incompatible because you have been too strict when you specified the
package version.

In our first example both ``package_coffee`` and ``package_tea`` have been
*pinned* to use specific versions
(``package_coffee==0.44.1b0 package_tea==4.3.0``).

To find a version of both ``package_coffee`` and ``package_tea`` that depend on
the same version of ``package_water``, you might consider:

-  Loosening the range of packages that you are prepared to install
   (e.g. ``pip install "package_coffee>0.44.*" "package_tea>4.0.0"``)
-  Asking pip to install *any* version of ``package_coffee`` and ``package_tea``
   by removing the version specifiers altogether (e.g.
   ``pip install package_coffee package_tea``)

In the second case, pip will automatically find a version of both
``package_coffee`` and ``package_tea`` that depend on the same version of
``package_water``, installing:

-  ``package_coffee 0.46.0b0``, which depends on ``package_water 2.6.1``
-  ``package_tea 4.3.0`` which *also* depends on ``package_water 2.6.1``

If you want to prioritize one package over another, you can add version
specifiers to *only* the more important package::

    pip install package_coffee==0.44.1b0 package_tea

This will result in:

- ``package_coffee 0.44.1b0``, which depends on ``package_water 2.6.1``
- ``package_tea 4.1.3`` which also depends on ``package_water 2.6.1``

Now that you have resolved the issue, you can repin the compatible
package versions as required.

3. Loosen the requirements of your dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Assuming that you cannot resolve the conflict by loosening the version
of the package you require (as above), you can try to fix the issue on
your *dependency* by:

-  Requesting that the package maintainers loosen *their* dependencies
-  Forking the package and loosening the dependencies yourself

.. warning::

   If you choose to fork the package yourself, you are *opting out* of
   any support provided by the package maintainers. Proceed at your own risk!

4. All requirements are loose, but a solution does not exist
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes it's simply impossible to find a combination of package
versions that do not conflict. Welcome to `dependency hell`_.

In this situation, you could consider:

-  Using an alternative package, if that is acceptable for your project.
   See `Awesome Python`_ for similar packages.
-  Refactoring your project to reduce the number of dependencies (for
   example, by breaking up a monolithic code base into smaller pieces)

Getting help
------------

If none of the suggestions above work for you, we recommend that you ask
for help on:

-  `Python user Discourse`_
-  `Python user forums`_
-  `Python developers Slack channel`_
-  `Python IRC`_
-  `Stack Overflow`_

See `"How do I ask a good question?"`_ for tips on asking for help.

Unfortunately, **the pip team cannot provide support for individual
dependency conflict errors**. Please *only* open a ticket on the `pip
issue tracker`_ if you believe that your problem has exposed a bug in pip.

.. _dependency hell: https://en.wikipedia.org/wiki/Dependency_hell
.. _Awesome Python: https://python.libhunt.com/
.. _Python user Discourse: https://discuss.python.org/c/users/7
.. _Python user forums: https://www.python.org/community/forums/
.. _Python developers Slack channel: https://pythondev.slack.com/
.. _Python IRC: https://www.python.org/community/irc/
.. _Stack Overflow: https://stackoverflow.com/questions/tagged/python
.. _"How do I ask a good question?": https://stackoverflow.com/help/how-to-ask
.. _pip issue tracker: https://github.com/pypa/pip/issues

Using pip from your program
===========================

As noted previously, pip is a command line program. While it is implemented in
Python, and so is available from your Python code via ``import pip``, you must
not use pip's internal APIs in this way. There are a number of reasons for this:

#. The pip code assumes that is in sole control of the global state of the
   program.
   pip manages things like the logging system configuration, or the values of
   the standard IO streams, without considering the possibility that user code
   might be affected.

#. pip's code is *not* thread safe. If you were to run pip in a thread, there
   is no guarantee that either your code or pip's would work as you expect.

#. pip assumes that once it has finished its work, the process will terminate.
   It doesn't need to handle the possibility that other code will continue to
   run after that point, so (for example) calling pip twice in the same process
   is likely to have issues.

This does not mean that the pip developers are opposed in principle to the idea
that pip could be used as a library - it's just that this isn't how it was
written, and it would be a lot of work to redesign the internals for use as a
library, handling all of the above issues, and designing a usable, robust and
stable API that we could guarantee would remain available across multiple
releases of pip. And we simply don't currently have the resources to even
consider such a task.

What this means in practice is that everything inside of pip is considered an
implementation detail. Even the fact that the import name is ``pip`` is subject
to change without notice. While we do try not to break things as much as
possible, all the internal APIs can change at any time, for any reason. It also
means that we generally *won't* fix issues that are a result of using pip in an
unsupported way.

It should also be noted that installing packages into ``sys.path`` in a running
Python process is something that should only be done with care. The import
system caches certain data, and installing new packages while a program is
running may not always behave as expected. In practice, there is rarely an
issue, but it is something to be aware of.

Having said all of the above, it is worth covering the options available if you
decide that you do want to run pip from within your program. The most reliable
approach, and the one that is fully supported, is to run pip in a subprocess.
This is easily done using the standard ``subprocess`` module::

  subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'my_package'])

If you want to process the output further, use one of the other APIs in the module.
We are using `freeze`_ here which outputs installed packages in requirements format.::

  reqs = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])

If you don't want to use pip's command line functionality, but are rather
trying to implement code that works with Python packages, their metadata, or
PyPI, then you should consider other, supported, packages that offer this type
of ability. Some examples that you could consider include:

* ``packaging`` - Utilities to work with standard package metadata (versions,
  requirements, etc.)

* ``setuptools`` (specifically ``pkg_resources``) - Functions for querying what
  packages the user has installed on their system.

* ``distlib`` - Packaging and distribution utilities (including functions for
  interacting with PyPI).

.. _`Resolver changes 2020`:

Changes to the pip dependency resolver in 20.2 (2020)
=====================================================

pip 20.1 included an alpha version of the new resolver (hidden behind
an optional ``--unstable-feature=resolver`` flag). pip 20.2 removes
that flag, and includes a robust beta of the new resolver (hidden
behind an optional ``--use-feature=2020-resolver`` flag) that we
encourage you to test. We will continue to improve the pip dependency
resolver in response to testers' feedback. Please give us feedback
through the `resolver testing survey`_. This will help us prepare to
release pip 20.3, with the new resolver on by default, in October.

Watch out for
-------------

The big change in this release is to the pip dependency resolver
within pip.

Computers need to know the right order to install pieces of software
("to install `x`, you need to install `y` first"). So, when Python
programmers share software as packages, they have to precisely describe
those installation prerequisites, and pip needs to navigate tricky
situations where it's getting conflicting instructions. This new
dependency resolver will make pip better at handling that tricky
logic, and make pip easier for you to use and troubleshoot.

The most significant changes to the resolver are:

* It will **reduce inconsistency**: it will *no longer install a
  combination of packages that is mutually inconsistent*. In older
  versions of pip, it is possible for pip to install a package which
  does not satisfy the declared requirements of another installed
  package. For example, in pip 20.0, ``pip install "six<1.12"
  "virtualenv==20.0.2"`` does the wrong thing, “successfully” installing
  ``six==1.11``, even though ``virtualenv==20.0.2`` requires
  ``six>=1.12.0,<2`` (`defined here
  <https://github.com/pypa/virtualenv/blob/20.0.2/setup.cfg#L42-L50>`__).
  The new resolver, instead, outright rejects installing anything if it
  gets that input.

* It will be **stricter** - if you ask pip to install two packages with
  incompatible requirements, it will refuse (rather than installing a
  broken combination, like it did in previous versions).

So, if you have been using workarounds to force pip to deal with
incompatible or inconsistent requirements combinations, now's a good
time to fix the underlying problem in the packages, because pip will
be stricter from here on out.

This also means that, when you run a ``pip install`` command, pip only
considers the packages you are installing in that command, and may
break already-installed packages. It will not guarantee that your
environment will be consistent all the time. If you ``pip install x``
and then ``pip install y``, it's possible that the version of ``y``
you get will be different than it would be if you had run ``pip
install x y`` in a single command. We would like your thoughts on what
pip's behavior should be; please answer `our survey on upgrades that
create conflicts`_.

We are also changing our support for :ref:`Constraints Files`:

* Unnamed requirements are not allowed as constraints (see :issue:`6628` and :issue:`8210`)
* Links are not allowed as constraints (see :issue:`8253`)
* Constraints cannot have extras (see :issue:`6628`)


How to test
-----------

1. **Install pip 20.2** with ``python -m pip install --upgrade pip``.

2. **Validate your current environment** by running ``pip check``. This
   will report if you have any inconsistencies in your set of installed
   packages. Having a clean installation will make it much less likely
   that you will hit issues when the new resolver is released (and may
   address hidden problems in your current environment!). If you run
   ``pip check`` and run into stuff you can’t figure out, please `ask
   for help in our issue tracker or chat <https://pip.pypa.io/>`__.

3. **Test the new version of pip** (see below). To test the new
   resolver, use the ``--use-feature=2020-resolver`` flag, as in:

   ``pip install example --use-feature=2020-resolver``

   The more feedback we can get, the more we can make sure that the
   final release is solid. (Only try the new resolver **in a
   non-production environment**, though - it isn't ready for you to
   rely on in production!)

   While we have tried to make sure that pip’s test suite covers as
   many cases as we can, we are very aware that there are people using
   pip with many different workflows and build processes, and we will
   not be able to cover all of those without your help.

   -  If you use pip to install your software, try out the new resolver
      and let us know if it works for you with ``pip install``. Try:

      - installing several packages simultaneously
      - re-creating an environment using a ``requirements.txt`` file
      - using ``pip install --force-reinstall`` to check whether
        it does what you think it should
      - using constraints files

   -  If you have a build pipeline that depends on pip installing your
      dependencies for you, check that the new resolver does what you
      need.
   -  Run your project’s CI (test suite, build process, etc.) using the
      new resolver, and let us know of any issues.
   -  If you have encountered resolver issues with pip in the past,
      check whether the new resolver fixes them. Also, let us know if
      the new resolver has issues with any workarounds you put in to
      address the current resolver’s limitations. We’ll need to ensure
      that people can transition off such workarounds smoothly.
   -  If you develop or support a tool that wraps pip or uses it to
      deliver part of your functionality, please test your integration
      with pip 20.2.

4. **Please report bugs** through the `resolver testing survey`_.

Setups we might need more testing on
------------------------------------

*    Windows, including Windows Subsystem for Linux (WSL)

*    Macintosh

*    Debian, Fedora, Red Hat, CentOS, Mint, Arch, Raspbian, Gentoo

*    non-Latin localized filesystems and OSes, such as Japanese, Chinese, and Korean, and right-to-left such as Hebrew, Urdu, and Arabic

*    Multi-user installations

*    Requirements files with 100+ packages

*    An installation workflow that involves multiple requirements files

*    Requirements files that include hashes (:ref:`hash-checking mode`)
     or pinned dependencies (perhaps as output from ``pip-compile`` within
     ``pip-tools``)

*    Using :ref:`Constraints Files`

*    Continuous integration/continuous deployment setups

*    Installing from any kind of version control systems (i.e., Git, Subversion, Mercurial, or CVS), per :ref:`VCS Support`

*    Installing from source code held in local directories

*    Using the most recent versions of Python 3.6, 3.7, 3.8, and 3.9

*    PyPy

*    Customized terminals (where you have modified how error messages and standard output display)

Examples to try
^^^^^^^^^^^^^^^

Install:

* `tensorflow`_
* ``hacking``
* ``pycodestyle``
* ``pandas``
* ``tablib``
* ``elasticsearch`` and ``requests`` together
* ``six`` and ``cherrypy`` together
* ``pip install flake8-import-order==0.17.1 flake8==3.5.0 --use-feature=2020-resolver``
* ``pip install tornado==5.0 sprockets.http==1.5.0 --use-feature=2020-resolver``

Try:

* ``pip install``
* ``pip uninstall``
* ``pip check``
* ``pip cache``


Tell us about
-------------

Specific things we'd love to get feedback on:

*    Cases where the new resolver produces the wrong result,
     obviously. We hope there won't be too many of these, but we'd like
     to trap such bugs now.

*    Cases where the resolver produced an error when you believe it
     should have been able to work out what to do.

*    Cases where the resolver gives an error because there's a problem
     with your requirements, but you need better information to work out
     what's wrong.

*    If you have workarounds to address issues with the current resolver,
     does the new resolver let you remove those workarounds? Tell us!

Please let us know through the `resolver testing survey`_.

Deprecation timeline
--------------------

We plan for the resolver changeover to proceed as follows, using
:ref:`Feature Flags` and following our :ref:`Release Cadence`:

*    pip 20.2: a beta of the new resolver is available, opt-in, using
     the flag ``--use-feature=2020-resolver``. pip defaults to
     legacy behavior.

*    pip 20.3: pip defaults to the new resolver, but a user can opt-out
     and choose the old resolver behavior, using the flag
     ``--use-deprecated=legacy-resolver``.

*    pip 21.0: pip uses new resolver, and the old resolver is no longer
     available.

Since this work will not change user-visible behavior described in the
pip documentation, this change is not covered by the :ref:`Deprecation
Policy`.

Context and followup
--------------------

As discussed in `our announcement on the PSF blog`_, the pip team are
in the process of developing a new "dependency resolver" (the part of
pip that works out what to install based on your requirements).

We're tracking our rollout in :issue:`6536` and you can watch for
announcements on the `low-traffic packaging announcements list`_ and
`the official Python blog`_.

.. _freeze: https://pip.pypa.io/en/latest/reference/pip_freeze/
.. _resolver testing survey: https://tools.simplysecure.org/survey/index.php?r=survey/index&sid=989272&lang=en
.. _our announcement on the PSF blog: http://pyfound.blogspot.com/2020/03/new-pip-resolver-to-roll-out-this-year.html
.. _tensorflow: https://pypi.org/project/tensorflow/
.. _low-traffic packaging announcements list: https://mail.python.org/mailman3/lists/pypi-announce.python.org/
.. _our survey on upgrades that create conflicts: https://docs.google.com/forms/d/e/1FAIpQLSeBkbhuIlSofXqCyhi3kGkLmtrpPOEBwr6iJA6SzHdxWKfqdA/viewform
.. _the official Python blog: https://blog.python.org/

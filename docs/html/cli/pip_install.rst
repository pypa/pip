.. _`pip install`:

===========
pip install
===========



Usage
=====

.. tab:: Unix/macOS

   .. pip-command-usage:: install 'python -m pip'

.. tab:: Windows

   .. pip-command-usage:: install "py -m pip"



Description
===========

.. pip-command-description:: install

Overview
--------

pip install has several stages:

1. Identify the base requirements. The user supplied arguments are processed
   here.
2. Resolve dependencies. What will be installed is determined here.
3. Build wheels. All the dependencies that can be are built into wheels.
4. Install the packages (and uninstall anything being upgraded/replaced).

Note that ``pip install`` prefers to leave the installed version as-is
unless ``--upgrade`` is specified.

Argument Handling
-----------------

When looking at the items to be installed, pip checks what type of item
each is, in the following order:

1. Project or archive URL.
2. Local directory (which must contain a ``setup.py``, or pip will report
   an error).
3. Local file (a sdist or wheel format archive, following the naming
   conventions for those formats).
4. A requirement, as specified in :pep:`440`.

Each item identified is added to the set of requirements to be satisfied by
the install.

Working Out the Name and Version
--------------------------------

For each candidate item, pip needs to know the project name and version. For
wheels (identified by the ``.whl`` file extension) this can be obtained from
the filename, as per the Wheel spec. For local directories, or explicitly
specified sdist files, the ``setup.py egg_info`` command is used to determine
the project metadata. For sdists located via an index, the filename is parsed
for the name and project version (this is in theory slightly less reliable
than using the ``egg_info`` command, but avoids downloading and processing
unnecessary numbers of files).

Any URL may use the ``#egg=name`` syntax (see :doc:`../topics/vcs-support`) to
explicitly state the project name.

Satisfying Requirements
-----------------------

Once pip has the set of requirements to satisfy, it chooses which version of
each requirement to install using the simple rule that the latest version that
satisfies the given constraints will be installed (but see :ref:`here <Pre Release Versions>`
for an exception regarding pre-release versions). Where more than one source of
the chosen version is available, it is assumed that any source is acceptable
(as otherwise the versions would differ).

Obtaining information about what was installed
----------------------------------------------

The install command has a ``--report`` option that will generate a JSON report of what
pip has installed. In combination with the ``--dry-run`` and ``--ignore-installed`` it
can be used to *resolve* a set of requirements without actually installing them.

The report can be written to a file, or to standard output (using ``--report -`` in
combination with ``--quiet``).

The format of the JSON report is described in :doc:`../reference/installation-report`.

Installation Order
------------------

.. note::

   This section is only about installation order of runtime dependencies, and
   does not apply to build dependencies (those are specified using PEP 518).

As of v6.1.0, pip installs dependencies before their dependents, i.e. in
"topological order."  This is the only commitment pip currently makes related
to order.  While it may be coincidentally true that pip will install things in
the order of the install arguments or in the order of the items in a
requirements file, this is not a promise.

In the event of a dependency cycle (aka "circular dependency"), the current
implementation (which might possibly change later) has it such that the first
encountered member of the cycle is installed last.

For instance, if quux depends on foo which depends on bar which depends on baz,
which depends on foo:

.. tab:: Unix/macOS

   .. code-block:: console

      $ python -m pip install quux
      ...
      Installing collected packages baz, bar, foo, quux

      $ python -m pip install bar
      ...
      Installing collected packages foo, baz, bar

.. tab:: Windows

   .. code-block:: console

      C:\> py -m pip install quux
      ...
      Installing collected packages baz, bar, foo, quux

      C:\> py -m pip install bar
      ...
      Installing collected packages foo, baz, bar


Prior to v6.1.0, pip made no commitments about install order.

The decision to install topologically is based on the principle that
installations should proceed in a way that leaves the environment usable at each
step. This has two main practical benefits:

1. Concurrent use of the environment during the install is more likely to work.
2. A failed install is less likely to leave a broken environment.  Although pip
   would like to support failure rollbacks eventually, in the mean time, this is
   an improvement.

Although the new install order is not intended to replace (and does not replace)
the use of ``setup_requires`` to declare build dependencies, it may help certain
projects install from sdist (that might previously fail) that fit the following
profile:

1. They have build dependencies that are also declared as install dependencies
   using ``install_requires``.
2. ``python setup.py egg_info`` works without their build dependencies being
   installed.
3. For whatever reason, they don't or won't declare their build dependencies using
   ``setup_requires``.

.. _`0-requirements-file-format`:
.. rubric:: Requirements File Format

This section has been moved to :doc:`../reference/requirements-file-format`.

.. _`0-requirement-specifiers`:
.. rubric:: Requirement Specifiers

This section has been moved to :doc:`../reference/requirement-specifiers`.

.. _`0-per-requirement-overrides`:
.. rubric:: Per-requirement Overrides

This is now covered in :doc:`../reference/requirements-file-format`.

.. _`Pre Release Versions`:

Pre-release Versions
--------------------

Starting with v1.4, pip will only install stable versions as specified by
`pre-releases`_ by default. If a version cannot be parsed as a compliant :pep:`440`
version then it is assumed to be a pre-release.

If a Requirement specifier includes a pre-release or development version
(e.g. ``>=0.0.dev0``) then pip will allow pre-release and development versions
for that requirement. This does not include the != flag.

The ``pip install`` command also supports a :ref:`--pre <install_--pre>` flag
that enables installation of pre-releases and development releases.


.. _pre-releases: https://www.python.org/dev/peps/pep-0440/#handling-of-pre-releases

.. _`0-vcs-support`:
.. rubric:: VCS Support

This is now covered in :doc:`../topics/vcs-support`.

Finding Packages
----------------

pip searches for packages on `PyPI`_ using the
`HTTP simple interface <https://pypi.org/simple/>`_,
which is documented `here <https://packaging.python.org/specifications/simple-repository-api/>`_
and `there <https://www.python.org/dev/peps/pep-0503/>`_.

pip offers a number of package index options for modifying how packages are
found.

pip looks for packages in a number of places: on PyPI (if not disabled via
``--no-index``), in the local filesystem, and in any additional repositories
specified via ``--find-links`` or ``--index-url``. There is no ordering in
the locations that are searched. Rather they are all checked, and the "best"
match for the requirements (in terms of version number - see :pep:`440` for
details) is selected.

See the :ref:`pip install Examples<pip install Examples>`.

.. _`0-ssl certificate verification`:
.. rubric:: SSL Certificate Verification

This is now covered in :doc:`../topics/https-certificates`.

.. _`0-caching`:
.. rubric:: Caching

This is now covered in :doc:`../topics/caching`.

.. _`0-wheel-cache`:
.. rubric:: Wheel Cache

This is now covered in :doc:`../topics/caching`.

.. _`0-hash-checking-mode`:
.. rubric:: Hash checking mode

This is now covered in :doc:`../topics/secure-installs`.

.. _`0-local-project-installs`:
.. rubric:: Local Project Installs

This is now covered in :doc:`../topics/local-project-installs`.

.. _`0-editable-installs`:
.. rubric:: Editable installs

This is now covered in :doc:`../topics/local-project-installs`.

.. _`0-build-system-interface`:
.. rubric:: Build System Interface

This is now covered in :doc:`../reference/build-system/index`.

.. _`pip install Options`:

Options
=======

.. pip-command-options:: install

.. pip-index-options:: install


.. _`pip install Examples`:


Examples
========

#. Install ``SomePackage`` and its dependencies from `PyPI`_ using :ref:`Requirement Specifiers`

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install SomePackage            # latest version
         python -m pip install 'SomePackage==1.0.4'   # specific version
         python -m pip install 'SomePackage>=1.0.4'   # minimum version

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install SomePackage            # latest version
         py -m pip install "SomePackage==1.0.4"   # specific version
         py -m pip install "SomePackage>=1.0.4"   # minimum version


#. Install a list of requirements specified in a file.  See the :ref:`Requirements files <Requirements Files>`.

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install -r requirements.txt

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install -r requirements.txt


#. Upgrade an already installed ``SomePackage`` to the latest from PyPI.

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install --upgrade SomePackage

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install --upgrade SomePackage

    .. note::

      This will guarantee an update to ``SomePackage`` as it is a direct
      requirement, and possibly upgrade dependencies if their installed
      versions do not meet the minimum requirements of ``SomePackage``.
      Any non-requisite updates of its dependencies (indirect requirements)
      will be affected by the ``--upgrade-strategy`` command.

#. Install a local project in "editable" mode. See the section on :ref:`Editable Installs <editable-installs>`.

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install -e .                # project in current directory
         python -m pip install -e path/to/project  # project in another directory

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install -e .                 # project in current directory
         py -m pip install -e path/to/project   # project in another directory


#. Install a project from VCS

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install 'SomeProject@git+https://git.repo/some_pkg.git@1.3.1'

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install "SomeProject@git+https://git.repo/some_pkg.git@1.3.1"


#. Install a project from VCS in "editable" mode. See the sections on :doc:`../topics/vcs-support` and :ref:`Editable Installs <editable-installs>`.

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install -e 'git+https://git.repo/some_pkg.git#egg=SomePackage'          # from git
         python -m pip install -e 'hg+https://hg.repo/some_pkg.git#egg=SomePackage'            # from mercurial
         python -m pip install -e 'svn+svn://svn.repo/some_pkg/trunk/#egg=SomePackage'         # from svn
         python -m pip install -e 'git+https://git.repo/some_pkg.git@feature#egg=SomePackage'  # from 'feature' branch
         python -m pip install -e 'git+https://git.repo/some_repo.git#egg=subdir&subdirectory=subdir_path' # install a python package from a repo subdirectory

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install -e "git+https://git.repo/some_pkg.git#egg=SomePackage"          # from git
         py -m pip install -e "hg+https://hg.repo/some_pkg.git#egg=SomePackage"            # from mercurial
         py -m pip install -e "svn+svn://svn.repo/some_pkg/trunk/#egg=SomePackage"         # from svn
         py -m pip install -e "git+https://git.repo/some_pkg.git@feature#egg=SomePackage"  # from 'feature' branch
         py -m pip install -e "git+https://git.repo/some_repo.git#egg=subdir&subdirectory=subdir_path" # install a python package from a repo subdirectory

#. Install a package with `extras`_.

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install 'SomePackage[PDF]'
         python -m pip install 'SomePackage[PDF] @ git+https://git.repo/SomePackage@main#subdirectory=subdir_path'
         python -m pip install '.[PDF]'  # project in current directory
         python -m pip install 'SomePackage[PDF]==3.0'
         python -m pip install 'SomePackage[PDF,EPUB]'  # multiple extras

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install "SomePackage[PDF]"
         py -m pip install "SomePackage[PDF] @ git+https://git.repo/SomePackage@main#subdirectory=subdir_path"
         py -m pip install ".[PDF]"  # project in current directory
         py -m pip install "SomePackage[PDF]==3.0"
         py -m pip install "SomePackage[PDF,EPUB]"  # multiple extras

#. Install a particular source archive file.

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install './downloads/SomePackage-1.0.4.tar.gz'
         python -m pip install 'http://my.package.repo/SomePackage-1.0.4.zip'

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install "./downloads/SomePackage-1.0.4.tar.gz"
         py -m pip install "http://my.package.repo/SomePackage-1.0.4.zip"

#. Install a particular source archive file following :pep:`440` direct references.

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install 'SomeProject@http://my.package.repo/SomeProject-1.2.3-py33-none-any.whl'
         python -m pip install 'SomeProject @ http://my.package.repo/SomeProject-1.2.3-py33-none-any.whl'
         python -m pip install 'SomeProject@http://my.package.repo/1.2.3.tar.gz'

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install "SomeProject@http://my.package.repo/SomeProject-1.2.3-py33-none-any.whl"
         py -m pip install "SomeProject @ http://my.package.repo/SomeProject-1.2.3-py33-none-any.whl"
         py -m pip install "SomeProject@http://my.package.repo/1.2.3.tar.gz"

#. Install from alternative package repositories.

   Install from a different index, and not `PyPI`_

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install --index-url http://my.package.repo/simple/ SomePackage

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install --index-url http://my.package.repo/simple/ SomePackage

   Install from a local flat directory containing archives (and don't scan indexes):

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install --no-index --find-links=file:///local/dir/ SomePackage
         python -m pip install --no-index --find-links=/local/dir/ SomePackage
         python -m pip install --no-index --find-links=relative/dir/ SomePackage

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install --no-index --find-links=file:///local/dir/ SomePackage
         py -m pip install --no-index --find-links=/local/dir/ SomePackage
         py -m pip install --no-index --find-links=relative/dir/ SomePackage

   Search an additional index during install, in addition to `PyPI`_

   .. warning::

       Using this option to search for packages which are not in the main
       repository (such as private packages) is unsafe, per a security
       vulnerability called
       `dependency confusion <https://azure.microsoft.com/en-us/resources/3-ways-to-mitigate-risk-using-private-package-feeds/>`_:
       an attacker can claim the package on the public repository in a way that
       will ensure it gets chosen over the private package.

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install --extra-index-url http://my.package.repo/simple SomePackage

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install --extra-index-url http://my.package.repo/simple SomePackage


#. Find pre-release and development versions, in addition to stable versions.  By default, pip only finds stable versions.

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install --pre SomePackage

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install --pre SomePackage


#. Install packages from source.

   Do not use any binary packages

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install SomePackage1 SomePackage2 --no-binary :all:

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install SomePackage1 SomePackage2 --no-binary :all:

   Specify ``SomePackage1`` to be installed from source:

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install SomePackage1 SomePackage2 --no-binary SomePackage1

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install SomePackage1 SomePackage2 --no-binary SomePackage1

.. _extras: https://www.python.org/dev/peps/pep-0508/#extras
.. _PyPI: https://pypi.org/

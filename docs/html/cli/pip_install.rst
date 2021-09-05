.. _`pip install`:

===========
pip install
===========



Usage
=====

.. tab:: Unix/macOS

   .. pip-command-usage:: install "python -m pip"

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


.. _`Requirements File Format`:

Requirements File Format
------------------------

Each line of the requirements file indicates something to be installed,
and like arguments to :ref:`pip install`, the following forms are supported::

    [[--option]...]
    <requirement specifier> [; markers] [[--option]...]
    <archive url/path>
    [-e] <local project path>
    [-e] <vcs project url>

For details on requirement specifiers, see :ref:`Requirement Specifiers`.

See the :ref:`pip install Examples<pip install Examples>` for examples of all these forms.

A line that begins with ``#`` is treated as a comment and ignored. Whitespace
followed by a ``#`` causes the ``#`` and the remainder of the line to be
treated as a comment.

A line ending in an unescaped ``\`` is treated as a line continuation
and the newline following it is effectively ignored.

Comments are stripped *after* line continuations are processed.

To interpret the requirements file in UTF-8 format add a comment
``# -*- coding: utf-8 -*-`` to the first or second line of the file.

The following options are supported:

.. pip-requirements-file-options-ref-list::

Please note that the above options are global options, and should be specified on their individual lines.
The options which can be applied to individual requirements are
:ref:`--install-option <install_--install-option>`, :ref:`--global-option <install_--global-option>` and ``--hash``.

For example, to specify :ref:`--pre <install_--pre>`, :ref:`--no-index <install_--no-index>` and two
:ref:`--find-links <install_--find-links>` locations:

::

--pre
--no-index
--find-links /my/local/archives
--find-links http://some.archives.com/archives


If you wish, you can refer to other requirements files, like this::

    -r more_requirements.txt

You can also refer to :ref:`constraints files <Constraints Files>`, like this::

    -c some_constraints.txt

.. _`Using Environment Variables`:

Using Environment Variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Since version 10, pip supports the use of environment variables inside the
requirements file. You can now store sensitive data (tokens, keys, etc.) in
environment variables and only specify the variable name for your requirements,
letting pip lookup the value at runtime. This approach aligns with the commonly
used `12-factor configuration pattern <https://12factor.net/config>`_.

You have to use the POSIX format for variable names including brackets around
the uppercase name as shown in this example: ``${API_TOKEN}``. pip will attempt
to find the corresponding environment variable defined on the host system at
runtime.

.. note::

   There is no support for other variable expansion syntaxes such as
   ``$VARIABLE`` and ``%VARIABLE%``.


.. _`Example Requirements File`:

Example Requirements File
^^^^^^^^^^^^^^^^^^^^^^^^^

Use ``pip install -r example-requirements.txt`` to install::

    #
    ####### example-requirements.txt #######
    #
    ###### Requirements without Version Specifiers ######
    nose
    nose-cov
    beautifulsoup4
    #
    ###### Requirements with Version Specifiers ######
    #   See https://www.python.org/dev/peps/pep-0440/#version-specifiers
    docopt == 0.6.1             # Version Matching. Must be version 0.6.1
    keyring >= 4.1.1            # Minimum version 4.1.1
    coverage != 3.5             # Version Exclusion. Anything except version 3.5
    Mopidy-Dirble ~= 1.1        # Compatible release. Same as >= 1.1, == 1.*
    #
    ###### Refer to other requirements files ######
    -r other-requirements.txt
    #
    #
    ###### A particular file ######
    ./downloads/numpy-1.9.2-cp34-none-win32.whl
    http://wxpython.org/Phoenix/snapshot-builds/wxPython_Phoenix-3.0.3.dev1820+49a8884-cp34-none-win_amd64.whl
    #
    ###### Additional Requirements without Version Specifiers ######
    #   Same as 1st section, just here to show that you can put things in any order.
    rejected
    green
    #

.. _`Requirement Specifiers`:

Requirement Specifiers
----------------------

pip supports installing from a package index using a :term:`requirement
specifier <pypug:Requirement Specifier>`. Generally speaking, a requirement
specifier is composed of a project name followed by optional :term:`version
specifiers <pypug:Version Specifier>`.  :pep:`508` contains a full specification
of the format of a requirement. Since version 18.1 pip supports the
``url_req``-form specification.

Some examples:

 ::

  SomeProject
  SomeProject == 1.3
  SomeProject >=1.2,<2.0
  SomeProject[foo, bar]
  SomeProject~=1.4.2

Since version 6.0, pip also supports specifiers containing `environment markers
<https://www.python.org/dev/peps/pep-0508/#environment-markers>`__ like so:

 ::

  SomeProject ==5.4 ; python_version < '3.8'
  SomeProject; sys_platform == 'win32'

Since version 19.1, pip also supports `direct references
<https://www.python.org/dev/peps/pep-0440/#direct-references>`__ like so:

 ::

  SomeProject @ file:///somewhere/...

Environment markers are supported in the command line and in requirements files.

.. note::

   Use quotes around specifiers in the shell when using ``>``, ``<``, or when
   using environment markers. Don't use quotes in requirement files. [1]_


.. _`Per-requirement Overrides`:

Per-requirement Overrides
-------------------------

Since version 7.0 pip supports controlling the command line options given to
``setup.py`` via requirements files. This disables the use of wheels (cached or
otherwise) for that package, as ``setup.py`` does not exist for wheels.

The ``--global-option`` and ``--install-option`` options are used to pass
options to ``setup.py``. For example:

 ::

    FooProject >= 1.2 --global-option="--no-user-cfg" \
                      --install-option="--prefix='/usr/local'" \
                      --install-option="--no-compile"

The above translates roughly into running FooProject's ``setup.py``
script as:

 ::

   python setup.py --no-user-cfg install --prefix='/usr/local' --no-compile

Note that the only way of giving more than one option to ``setup.py``
is through multiple ``--global-option`` and ``--install-option``
options, as shown in the example above. The value of each option is
passed as a single argument to the ``setup.py`` script. Therefore, a
line such as the following is invalid and would result in an
installation error.

::

   # Invalid. Please use '--install-option' twice as shown above.
   FooProject >= 1.2 --install-option="--prefix=/usr/local --no-compile"


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


.. _`VCS Support`:

VCS Support
-----------

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


.. _`SSL Certificate Verification`:

SSL Certificate Verification
----------------------------

Starting with v1.3, pip provides SSL certificate verification over HTTP, to
prevent man-in-the-middle attacks against PyPI downloads. This does not use
the system certificate store but instead uses a bundled CA certificate
store. The default bundled CA certificate store certificate store may be
overridden by using ``--cert`` option or by using ``PIP_CERT``,
``REQUESTS_CA_BUNDLE``, or ``CURL_CA_BUNDLE`` environment variables.


.. _`Caching`:

Caching
-------

This is now covered in :doc:`../topics/caching`.

.. _`Wheel cache`:

Wheel Cache
^^^^^^^^^^^

This is now covered in :doc:`../topics/caching`.

.. _`hash-checking mode`:

Hash-Checking Mode
------------------

Since version 8.0, pip can check downloaded package archives against local
hashes to protect against remote tampering. To verify a package against one or
more hashes, add them to the end of the line::

    FooProject == 1.2 --hash=sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824 \
                      --hash=sha256:486ea46224d1bb4fb680f34f7c9ad96a8f24ec88be73ea8e5a6c65260e9cb8a7

(The ability to use multiple hashes is important when a package has both
binary and source distributions or when it offers binary distributions for a
variety of platforms.)

The recommended hash algorithm at the moment is sha256, but stronger ones are
allowed, including all those supported by ``hashlib``. However, weaker ones
such as md5, sha1, and sha224 are excluded to avoid giving a false sense of
security.

Hash verification is an all-or-nothing proposition. Specifying a ``--hash``
against any requirement not only checks that hash but also activates a global
*hash-checking mode*, which imposes several other security restrictions:

* Hashes are required for all requirements. This is because a partially-hashed
  requirements file is of little use and thus likely an error: a malicious
  actor could slip bad code into the installation via one of the unhashed
  requirements. Note that hashes embedded in URL-style requirements via the
  ``#md5=...`` syntax suffice to satisfy this rule (regardless of hash
  strength, for legacy reasons), though you should use a stronger
  hash like sha256 whenever possible.
* Hashes are required for all dependencies. An error results if there is a
  dependency that is not spelled out and hashed in the requirements file.
* Requirements that take the form of project names (rather than URLs or local
  filesystem paths) must be pinned to a specific version using ``==``. This
  prevents a surprising hash mismatch upon the release of a new version
  that matches the requirement specifier.
* ``--egg`` is disallowed, because it delegates installation of dependencies
  to setuptools, giving up pip's ability to enforce any of the above.

.. _`--require-hashes`:

Hash-checking mode can be forced on with the ``--require-hashes`` command-line
option:

.. tab:: Unix/macOS

   .. code-block:: console

      $ python -m pip install --require-hashes -r requirements.txt
      ...
      Hashes are required in --require-hashes mode (implicitly on when a hash is
      specified for any package). These requirements were missing hashes,
      leaving them open to tampering. These are the hashes the downloaded
      archives actually had. You can add lines like these to your requirements
      files to prevent tampering.
         pyelasticsearch==1.0 --hash=sha256:44ddfb1225054d7d6b1d02e9338e7d4809be94edbe9929a2ec0807d38df993fa
         more-itertools==2.2 --hash=sha256:93e62e05c7ad3da1a233def6731e8285156701e3419a5fe279017c429ec67ce0

.. tab:: Windows

   .. code-block:: console

      C:\> py -m pip install --require-hashes -r requirements.txt
      ...
      Hashes are required in --require-hashes mode (implicitly on when a hash is
      specified for any package). These requirements were missing hashes,
      leaving them open to tampering. These are the hashes the downloaded
      archives actually had. You can add lines like these to your requirements
      files to prevent tampering.
         pyelasticsearch==1.0 --hash=sha256:44ddfb1225054d7d6b1d02e9338e7d4809be94edbe9929a2ec0807d38df993fa
         more-itertools==2.2 --hash=sha256:93e62e05c7ad3da1a233def6731e8285156701e3419a5fe279017c429ec67ce0


This can be useful in deploy scripts, to ensure that the author of the
requirements file provided hashes. It is also a convenient way to bootstrap
your list of hashes, since it shows the hashes of the packages it fetched. It
fetches only the preferred archive for each package, so you may still need to
add hashes for alternatives archives using :ref:`pip hash`: for instance if
there is both a binary and a source distribution.

The :ref:`wheel cache <Wheel cache>` is disabled in hash-checking mode to
prevent spurious hash mismatch errors. These would otherwise occur while
installing sdists that had already been automatically built into cached wheels:
those wheels would be selected for installation, but their hashes would not
match the sdist ones from the requirements file. A further complication is that
locally built wheels are nondeterministic: contemporary modification times make
their way into the archive, making hashes unpredictable across machines and
cache flushes. Compilation of C code adds further nondeterminism, as many
compilers include random-seeded values in their output. However, wheels fetched
from index servers are the same every time. They land in pip's HTTP cache, not
its wheel cache, and are used normally in hash-checking mode. The only downside
of having the wheel cache disabled is thus extra build time for sdists, and
this can be solved by making sure pre-built wheels are available from the index
server.

Hash-checking mode also works with :ref:`pip download` and :ref:`pip wheel`.
See :doc:`../topics/repeatable-installs` for a comparison of hash-checking mode
with other repeatability strategies.

.. warning::

   Beware of the ``setup_requires`` keyword arg in :file:`setup.py`. The
   (rare) packages that use it will cause those dependencies to be downloaded
   by setuptools directly, skipping pip's hash-checking. If you need to use
   such a package, see :ref:`Controlling
   setup_requires<controlling-setup-requires>`.

.. warning::

   Be careful not to nullify all your security work when you install your
   actual project by using setuptools directly: for example, by calling
   ``python setup.py install``, ``python setup.py develop``, or
   ``easy_install``. Setuptools will happily go out and download, unchecked,
   anything you missed in your requirements file—and it’s easy to miss things
   as your project evolves. To be safe, install your project using pip and
   :ref:`--no-deps <install_--no-deps>`.

   Instead of ``python setup.py develop``, use...

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install --no-deps -e .

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install --no-deps -e .


   Instead of ``python setup.py install``, use...

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install --no-deps .

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install --no-deps .

Hashes from PyPI
^^^^^^^^^^^^^^^^

PyPI provides an MD5 hash in the fragment portion of each package download URL,
like ``#md5=123...``, which pip checks as a protection against download
corruption. Other hash algorithms that have guaranteed support from ``hashlib``
are also supported here: sha1, sha224, sha384, sha256, and sha512. Since this
hash originates remotely, it is not a useful guard against tampering and thus
does not satisfy the ``--require-hashes`` demand that every package have a
local hash.


Local project installs
----------------------

pip supports installing local project in both regular mode and editable mode.
You can install local projects by specifying the project path to pip:

.. tab:: Unix/macOS

   .. code-block:: shell

      python -m pip install path/to/SomeProject

.. tab:: Windows

   .. code-block:: shell

      py -m pip install path/to/SomeProject

During regular installation, pip will copy the entire project directory to a
temporary location and install from there. The exception is that pip will
exclude .tox and .nox directories present in the top level of the project from
being copied. This approach is the cause of several performance and correctness
issues, so it is planned that pip 21.3 will change to install directly from the
local project directory. Depending on the build backend used by the project,
this may generate secondary build artifacts in the project directory, such as
the ``.egg-info`` and ``build`` directories in the case of the setuptools
backend.

To opt in to the future behavior, specify the ``--use-feature=in-tree-build``
option in pip's command line.


.. _`editable-installs`:

"Editable" Installs
^^^^^^^^^^^^^^^^^^^

"Editable" installs are fundamentally `"setuptools develop mode"
<https://setuptools.readthedocs.io/en/latest/userguide/development_mode.html>`_
installs.

You can install local projects or VCS projects in "editable" mode:

.. tab:: Unix/macOS

   .. code-block:: shell

      python -m pip install -e path/to/SomeProject
      python -m pip install -e git+http://repo/my_project.git#egg=SomeProject

.. tab:: Windows

   .. code-block:: shell

      py -m pip install -e path/to/SomeProject
      py -m pip install -e git+http://repo/my_project.git#egg=SomeProject


(See the :doc:`../topics/vcs-support` section above for more information on VCS-related syntax.)

For local projects, the "SomeProject.egg-info" directory is created relative to
the project path.  This is one advantage over just using ``setup.py develop``,
which creates the "egg-info" directly relative the current working directory.


.. _`controlling-setup-requires`:

Controlling setup_requires
--------------------------

Setuptools offers the ``setup_requires`` `setup() keyword
<https://setuptools.readthedocs.io/en/latest/userguide/keywords.html>`_
for specifying dependencies that need to be present in order for the
``setup.py`` script to run.  Internally, Setuptools uses ``easy_install``
to fulfill these dependencies.

pip has no way to control how these dependencies are located.  None of the
package index options have an effect.

The solution is to configure a "system" or "personal" `Distutils configuration
file
<https://docs.python.org/3/install/index.html#distutils-configuration-files>`_ to
manage the fulfillment.

For example, to have the dependency located at an alternate index, add this:

::

  [easy_install]
  index_url = https://my.index-mirror.com

To have the dependency located from a local directory and not crawl PyPI, add this:

::

  [easy_install]
  allow_hosts = ''
  find_links = file:///path/to/local/archives/


Build System Interface
----------------------

In order for pip to install a package from source, ``setup.py`` must implement
the following commands::

    setup.py egg_info [--egg-base XXX]
    setup.py install --record XXX [--single-version-externally-managed] [--root XXX] [--compile|--no-compile] [--install-headers XXX]

The ``egg_info`` command should create egg metadata for the package, as
described in the setuptools documentation at
https://setuptools.readthedocs.io/en/latest/userguide/commands.html#egg-info-create-egg-metadata-and-set-build-tags

The ``install`` command should implement the complete process of installing the
package to the target directory XXX.

To install a package in "editable" mode (``pip install -e``), ``setup.py`` must
implement the following command::

    setup.py develop --no-deps

This should implement the complete process of installing the package in
"editable" mode.

All packages will be attempted to built into wheels::

    setup.py bdist_wheel -d XXX

One further ``setup.py`` command is invoked by ``pip install``::

    setup.py clean

This command is invoked to clean up temporary commands from the build. (TODO:
Investigate in more detail when this command is required).

No other build system commands are invoked by the ``pip install`` command.

Installing a package from a wheel does not invoke the build system at all.

.. _PyPI: https://pypi.org/
.. _setuptools extras: https://setuptools.readthedocs.io/en/latest/userguide/dependency_management.html#optional-dependencies



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
         python -m pip install SomePackage==1.0.4     # specific version
         python -m pip install 'SomePackage>=1.0.4'   # minimum version

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install SomePackage            # latest version
         py -m pip install SomePackage==1.0.4     # specific version
         py -m pip install 'SomePackage>=1.0.4'   # minimum version


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

         python -m pip install SomeProject@git+https://git.repo/some_pkg.git@1.3.1

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install SomeProject@git+https://git.repo/some_pkg.git@1.3.1


#. Install a project from VCS in "editable" mode. See the sections on :doc:`../topics/vcs-support` and :ref:`Editable Installs <editable-installs>`.

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install -e git+https://git.repo/some_pkg.git#egg=SomePackage          # from git
         python -m pip install -e hg+https://hg.repo/some_pkg.git#egg=SomePackage            # from mercurial
         python -m pip install -e svn+svn://svn.repo/some_pkg/trunk/#egg=SomePackage         # from svn
         python -m pip install -e git+https://git.repo/some_pkg.git@feature#egg=SomePackage  # from 'feature' branch
         python -m pip install -e "git+https://git.repo/some_repo.git#egg=subdir&subdirectory=subdir_path" # install a python package from a repo subdirectory

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install -e git+https://git.repo/some_pkg.git#egg=SomePackage          # from git
         py -m pip install -e hg+https://hg.repo/some_pkg.git#egg=SomePackage            # from mercurial
         py -m pip install -e svn+svn://svn.repo/some_pkg/trunk/#egg=SomePackage         # from svn
         py -m pip install -e git+https://git.repo/some_pkg.git@feature#egg=SomePackage  # from 'feature' branch
         py -m pip install -e "git+https://git.repo/some_repo.git#egg=subdir&subdirectory=subdir_path" # install a python package from a repo subdirectory

#. Install a package with `setuptools extras`_.

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install SomePackage[PDF]
         python -m pip install "SomePackage[PDF] @ git+https://git.repo/SomePackage@main#subdirectory=subdir_path"
         python -m pip install .[PDF]  # project in current directory
         python -m pip install SomePackage[PDF]==3.0
         python -m pip install SomePackage[PDF,EPUB]  # multiple extras

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install SomePackage[PDF]
         py -m pip install "SomePackage[PDF] @ git+https://git.repo/SomePackage@main#subdirectory=subdir_path"
         py -m pip install .[PDF]  # project in current directory
         py -m pip install SomePackage[PDF]==3.0
         py -m pip install SomePackage[PDF,EPUB]  # multiple extras

#. Install a particular source archive file.

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install ./downloads/SomePackage-1.0.4.tar.gz
         python -m pip install http://my.package.repo/SomePackage-1.0.4.zip

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install ./downloads/SomePackage-1.0.4.tar.gz
         py -m pip install http://my.package.repo/SomePackage-1.0.4.zip

#. Install a particular source archive file following :pep:`440` direct references.

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip install SomeProject@http://my.package.repo/SomeProject-1.2.3-py33-none-any.whl
         python -m pip install "SomeProject @ http://my.package.repo/SomeProject-1.2.3-py33-none-any.whl"
         python -m pip install SomeProject@http://my.package.repo/1.2.3.tar.gz

   .. tab:: Windows

      .. code-block:: shell

         py -m pip install SomeProject@http://my.package.repo/SomeProject-1.2.3-py33-none-any.whl
         py -m pip install "SomeProject @ http://my.package.repo/SomeProject-1.2.3-py33-none-any.whl"
         py -m pip install SomeProject@http://my.package.repo/1.2.3.tar.gz

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

----

.. [1] This is true with the exception that pip v7.0 and v7.0.1 required quotes
       around specifiers containing environment markers in requirement files.

.. _`pip install`:

pip install
-----------

.. contents::

Usage
*****

.. pip-command-usage:: install

Description
***********

.. pip-command-description:: install


Overview
++++++++

Pip install has several stages:

1. Resolve dependencies. What will be installed is determined here.
2. Build wheels. All the dependencies that can be are built into wheels.
3. Install the packages (and uninstall anything being upgraded/replaced).

Installation Order
++++++++++++++++++

As of v6.1.0, pip installs dependencies before their dependents, i.e. in
"topological order".  This is the only commitment pip currently makes related
to order.  While it may be coincidentally true that pip will install things in
the order of the install arguments or in the order of the items in a
requirements file, this is not a promise.

In the event of a dependency cycle (aka "circular dependency"), the current
implementation (which might possibly change later) has it such that the first
encountered member of the cycle is installed last.

For instance, if quux depends on foo which depends on bar which depends on baz,
which depends on foo::

    pip install quux
    ...
    Installing collected packages baz, bar, foo, quux

    pip install bar
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
++++++++++++++++++++++++

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

Additionally, the following Package Index Options are supported:

  *  :ref:`-i, --index-url <--index-url>`
  *  :ref:`--extra-index-url <--extra-index-url>`
  *  :ref:`--no-index <--no-index>`
  *  :ref:`-f, --find-links <--find-links>`
  *  :ref:`--allow-external <--allow-external>`
  *  :ref:`--allow-all-external <--allow-external>`
  *  :ref:`--allow-unverified <--allow-unverified>`
  *  :ref:`--no-binary <install_--no-binary>`
  *  :ref:`--only-binary <install_--only-binary>`

For example, to specify :ref:`--no-index <--no-index>` and 2 :ref:`--find-links <--find-links>` locations:

::

--no-index
--find-links /my/local/archives
--find-links http://some.archives.com/archives


If you wish, you can refer to other requirements files, like this::

    -r more_requirements.txt

You can also refer to :ref:`constraints files <Constraints Files>`, like this::

    -c some_constraints.txt

.. _`Requirement Specifiers`:

Requirement Specifiers
++++++++++++++++++++++

pip supports installing from a package index using a :term:`requirement
specifier <pypug:Requirement Specifier>`. Generally speaking, a requirement
specifier is composed of a project name followed by optional :term:`version
specifiers <pypug:Version Specifier>`.  :ref:`PEP440 <pypa:PEP440s>` contains
a `full specification
<https://www.python.org/dev/peps/pep-0440/#version-specifiers>`_ of the
currently supported specifiers.

Some examples:

 ::

  SomeProject
  SomeProject == 1.3
  SomeProject >=1.2,<.2.0
  SomeProject[foo, bar]
  SomeProject~=1.4.2

Since version 6.0, pip also supports specifers containing `environment markers
<https://www.python.org/dev/peps/pep-0426/#environment-markers>`_ like so:

 ::

  SomeProject ==5.4 ; python_version < '2.7'
  SomeProject; sys.platform == 'win32'

Environment markers are supported in the command line and in requirements files.

.. note::

   Use quotes around specifiers in the shell when using ``>``, ``<``, or when
   using environment markers. Don't use quotes in requirement files. [1]_


.. _`Per-requirement Overrides`:

Per-requirement Overrides
+++++++++++++++++++++++++

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
++++++++++++++++++++

Starting with v1.4, pip will only install stable versions as specified by
`PEP426`_ by default. If a version cannot be parsed as a compliant `PEP426`_
version then it is assumed to be a pre-release.

If a Requirement specifier includes a pre-release or development version
(e.g. ``>=0.0.dev0``) then pip will allow pre-release and development versions
for that requirement. This does not include the != flag.

The ``pip install`` command also supports a :ref:`--pre <install_--pre>` flag
that will enable installing pre-releases and development releases.


.. _PEP426: http://www.python.org/dev/peps/pep-0426

.. _`Externally Hosted Files`:

Externally Hosted Files
+++++++++++++++++++++++

Starting with v1.4, pip will warn about installing any file that does not come
from the primary index. As of version 1.5, pip defaults to ignoring these files
unless asked to consider them.

The ``pip install`` command supports a
:ref:`--allow-external PROJECT <--allow-external>` option that will enable
installing links that are linked directly from the simple index but to an
external host that also have a supported hash fragment. Externally hosted
files for all projects may be enabled using the
:ref:`--allow-all-external <--allow-all-external>` flag to the ``pip install``
command.

The ``pip install`` command also supports a
:ref:`--allow-unverified PROJECT <--allow-unverified>` option that will enable
installing insecurely linked files. These are either directly linked (as above)
files without a hash, or files that are linked from either the home page or the
download url of a package.

These options can be used in a requirements file.  Assuming some fictional
`ExternalPackage` that is hosted external and unverified, then your requirements
file would be like so::

    --allow-external ExternalPackage
    --allow-unverified ExternalPackage
    ExternalPackage


.. _`VCS Support`:

VCS Support
+++++++++++

pip supports installing from Git, Mercurial, Subversion and Bazaar, and detects
the type of VCS using url prefixes: "git+", "hg+", "bzr+", "svn+".

pip requires a working VCS command on your path: git, hg, svn, or bzr.

VCS projects can be installed in :ref:`editable mode <editable-installs>` (using
the :ref:`--editable <install_--editable>` option) or not.

* For editable installs, the clone location by default is "<venv
  path>/src/SomeProject" in virtual environments, and "<cwd>/src/SomeProject"
  for global installs.  The :ref:`--src <install_--src>` option can be used to
  modify this location.
* For non-editable installs, the project is built locally in a temp dir and then
  installed normally.

The "project name" component of the url suffix "egg=<project name>-<version>"
is used by pip in its dependency logic to identify the project prior
to pip downloading and analyzing the metadata.  The optional "version"
component of the egg name is not functionally important.  It merely
provides a human-readable clue as to what version is in use.

Git
~~~

pip currently supports cloning over ``git``, ``git+https`` and ``git+ssh``:

Here are the supported forms::

    [-e] git+git://git.myproject.org/MyProject#egg=MyProject
    [-e] git+https://git.myproject.org/MyProject#egg=MyProject
    [-e] git+ssh://git.myproject.org/MyProject#egg=MyProject
    -e git+git@git.myproject.org:MyProject#egg=MyProject

Passing branch names, a commit hash or a tag name is possible like so::

    [-e] git://git.myproject.org/MyProject.git@master#egg=MyProject
    [-e] git://git.myproject.org/MyProject.git@v1.0#egg=MyProject
    [-e] git://git.myproject.org/MyProject.git@da39a3ee5e6b4b0d3255bfef95601890afd80709#egg=MyProject

Mercurial
~~~~~~~~~

The supported schemes are: ``hg+http``, ``hg+https``,
``hg+static-http`` and ``hg+ssh``.

Here are the supported forms::

    [-e] hg+http://hg.myproject.org/MyProject#egg=MyProject
    [-e] hg+https://hg.myproject.org/MyProject#egg=MyProject
    [-e] hg+ssh://hg.myproject.org/MyProject#egg=MyProject

You can also specify a revision number, a revision hash, a tag name or a local
branch name like so::

    [-e] hg+http://hg.myproject.org/MyProject@da39a3ee5e6b#egg=MyProject
    [-e] hg+http://hg.myproject.org/MyProject@2019#egg=MyProject
    [-e] hg+http://hg.myproject.org/MyProject@v1.0#egg=MyProject
    [-e] hg+http://hg.myproject.org/MyProject@special_feature#egg=MyProject

Subversion
~~~~~~~~~~

pip supports the URL schemes ``svn``, ``svn+svn``, ``svn+http``, ``svn+https``, ``svn+ssh``.

You can also give specific revisions to an SVN URL, like so::

    [-e] svn+svn://svn.myproject.org/svn/MyProject#egg=MyProject
    [-e] svn+http://svn.myproject.org/svn/MyProject/trunk@2019#egg=MyProject

which will check out revision 2019.  ``@{20080101}`` would also check
out the revision from 2008-01-01. You can only check out specific
revisions using ``-e svn+...``.

Bazaar
~~~~~~

pip supports Bazaar using the ``bzr+http``, ``bzr+https``, ``bzr+ssh``,
``bzr+sftp``, ``bzr+ftp`` and ``bzr+lp`` schemes.

Here are the supported forms::

    [-e] bzr+http://bzr.myproject.org/MyProject/trunk#egg=MyProject
    [-e] bzr+sftp://user@myproject.org/MyProject/trunk#egg=MyProject
    [-e] bzr+ssh://user@myproject.org/MyProject/trunk#egg=MyProject
    [-e] bzr+ftp://user@myproject.org/MyProject/trunk#egg=MyProject
    [-e] bzr+lp:MyProject#egg=MyProject

Tags or revisions can be installed like so::

    [-e] bzr+https://bzr.myproject.org/MyProject/trunk@2019#egg=MyProject
    [-e] bzr+http://bzr.myproject.org/MyProject/trunk@v1.0#egg=MyProject


Finding Packages
++++++++++++++++

pip searches for packages on `PyPI`_ using the
`http simple interface <http://pypi.python.org/simple>`_,
which is documented `here <http://packages.python.org/setuptools/easy_install.html#package-index-api>`_
and `there <http://www.python.org/dev/peps/pep-0301/>`_

pip offers a number of Package Index Options for modifying how packages are found.

See the :ref:`pip install Examples<pip install Examples>`.


.. _`SSL Certificate Verification`:

SSL Certificate Verification
++++++++++++++++++++++++++++

Starting with v1.3, pip provides SSL certificate verification over https, for the purpose
of providing secure, certified downloads from PyPI.


.. _`Caching`:

Caching
+++++++

Starting with v6.0, pip provides an on by default cache which functions
similarly to that of a web browser. While the cache is on by default and is
designed do the right thing by default you can disable the cache and always
access PyPI by utilizing the ``--no-cache-dir`` option.

When making any HTTP request pip will first check its local cache to determine
if it has a suitable response stored for that request which has not expired. If
it does then it simply returns that response and doesn't make the request.

If it has a response stored, but it has expired, then it will attempt to make a
conditional request to refresh the cache which will either return an empty
response telling pip to simply use the cached item (and refresh the expiration
timer) or it will return a whole new response which pip can then store in the
cache.

When storing items in the cache, pip will respect the ``CacheControl`` header
if it exists, or it will fall back to the ``Expires`` header if that exists.
This allows pip to function as a browser would, and allows the index server
to communicate to pip how long it is reasonable to cache any particular item.

While this cache attempts to minimize network activity, it does not prevent
network access altogether. If you want a fast/local install solution that
circumvents accessing PyPI, see :ref:`Fast & Local Installs`.

The default location for the cache directory depends on the Operating System:

Unix
  :file:`~/.cache/pip` and it respects the ``XDG_CACHE_HOME`` directory.
OS X
  :file:`~/Library/Caches/pip`.
Windows
  :file:`<CSIDL_LOCAL_APPDATA>\\pip\\Cache`


Wheel cache
***********

Pip will read from the subdirectory ``wheels`` within the pip cache dir and use
any packages found there. This is disabled via the same ``no-cache-dir`` option
that disables the HTTP cache. The internal structure of that cache is not part
of the pip API. As of 7.0 pip uses a subdirectory per sdist that wheels were
built from, and wheels within that subdirectory.

Pip attempts to choose the best wheels from those built in preference to
building a new wheel. Note that this means when a package has both optional
C extensions and builds `py` tagged wheels when the C extension can't be built
that pip will not attempt to build a better wheel for Pythons that would have
supported it, once any generic wheel is built. To correct this, make sure that
the wheels are built with Python specific tags - e.g. pp on Pypy.

When no wheels are found for an sdist, pip will attempt to build a wheel
automatically and insert it into the wheel cache.


Hash Verification
+++++++++++++++++

PyPI provides md5 hashes in the hash fragment of package download urls.

pip supports checking this, as well as any of the
guaranteed hashlib algorithms (sha1, sha224, sha384, sha256, sha512, md5).

The hash fragment is case sensitive (i.e. sha1 not SHA1).

This check is only intended to provide basic download corruption protection.
It is not intended to provide security against tampering. For that,
see :ref:`SSL Certificate Verification`


.. _`editable-installs`:

"Editable" Installs
+++++++++++++++++++

"Editable" installs are fundamentally `"setuptools develop mode"
<http://packages.python.org/setuptools/setuptools.html#development-mode>`_
installs.

You can install local projects or VCS projects in "editable" mode::

$ pip install -e path/to/SomeProject
$ pip install -e git+http://repo/my_project.git#egg=SomeProject

(See the :ref:`VCS Support` section above for more information on VCS-related syntax.)

For local projects, the "SomeProject.egg-info" directory is created relative to
the project path.  This is one advantage over just using ``setup.py develop``,
which creates the "egg-info" directly relative the current working directory.


.. _`controlling-setup-requires`:

Controlling setup_requires
++++++++++++++++++++++++++

Setuptools offers the ``setup_requires`` `setup() keyword
<http://pythonhosted.org/setuptools/setuptools.html#new-and-changed-setup-keywords>`_
for specifying dependencies that need to be present in order for the `setup.py`
script to run.  Internally, Setuptools uses ``easy_install`` to fulfill these
dependencies.

pip has no way to control how these dependencies are located.  None of the
Package Index Options have an effect.

The solution is to configure a "system" or "personal" `Distutils configuration
file
<http://docs.python.org/2/install/index.html#distutils-configuration-files>`_ to
manage the fulfillment.

For example, to have the dependency located at an alternate index, add this:

::

  [easy_install]
  index_url = https://my.index-mirror.com

To have the dependency located from a local directory and not crawl PyPI, add this:

::

  [easy_install]
  allow_hosts = ''
  find_links = file:///path/to/local/archives


Build System Interface
++++++++++++++++++++++

In order for pip to install a package from source, ``setup.py`` must implement
the following commands::

    setup.py egg_info [--egg-base XXX]
    setup.py install --record XXX [--single-version-externally-managed] [--root XXX] [--compile|--no-compile] [--install-headers XXX]

The ``egg_info`` command should create egg metadata for the package, as
described in the setuptools documentation at
http://pythonhosted.org/setuptools/setuptools.html#egg-info-create-egg-metadata-and-set-build-tags

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

.. _PyPI: http://pypi.python.org/pypi/
.. _setuptools extras: http://packages.python.org/setuptools/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies



.. _`pip install Options`:

Options
*******

.. pip-command-options:: install

.. pip-index-options::


.. _`pip install Examples`:

Examples
********

1) Install `SomePackage` and its dependencies from `PyPI`_ using :ref:`Requirement Specifiers`

  ::

  $ pip install SomePackage            # latest version
  $ pip install SomePackage==1.0.4     # specific version
  $ pip install 'SomePackage>=1.0.4'     # minimum version


2) Install a list of requirements specified in a file.  See the :ref:`Requirements files <Requirements Files>`.

  ::

  $ pip install -r requirements.txt


3) Upgrade an already installed `SomePackage` to the latest from PyPI.

  ::

  $ pip install --upgrade SomePackage


4) Install a local project in "editable" mode. See the section on :ref:`Editable Installs <editable-installs>`.

  ::

  $ pip install -e .                     # project in current directory
  $ pip install -e path/to/project       # project in another directory


5) Install a project from VCS in "editable" mode. See the sections on :ref:`VCS Support <VCS Support>` and :ref:`Editable Installs <editable-installs>`.

  ::

  $ pip install -e git+https://git.repo/some_pkg.git#egg=SomePackage          # from git
  $ pip install -e hg+https://hg.repo/some_pkg.git#egg=SomePackage            # from mercurial
  $ pip install -e svn+svn://svn.repo/some_pkg/trunk/#egg=SomePackage         # from svn
  $ pip install -e git+https://git.repo/some_pkg.git@feature#egg=SomePackage  # from 'feature' branch
  $ pip install -e git+https://git.repo/some_repo.git#egg=subdir&subdirectory=subdir_path # install a python package from a repo subdirectory

6) Install a package with `setuptools extras`_.

  ::

  $ pip install SomePackage[PDF]
  $ pip install SomePackage[PDF]==3.0
  $ pip install -e .[PDF]==3.0  # editable project in current directory


7) Install a particular source archive file.

  ::

  $ pip install ./downloads/SomePackage-1.0.4.tar.gz
  $ pip install http://my.package.repo/SomePackage-1.0.4.zip


8) Install from alternative package repositories.

  Install from a different index, and not `PyPI`_ ::

  $ pip install --index-url http://my.package.repo/simple/ SomePackage

  Search an additional index during install, in addition to `PyPI`_ ::

  $ pip install --extra-index-url http://my.package.repo/simple SomePackage

  Install from a local flat directory containing archives (and don't scan indexes)::

  $ pip install --no-index --find-links=file:///local/dir/ SomePackage
  $ pip install --no-index --find-links=/local/dir/ SomePackage
  $ pip install --no-index --find-links=relative/dir/ SomePackage


9) Find pre-release and development versions, in addition to stable versions.  By default, pip only finds stable versions.

 ::

  $ pip install --pre SomePackage

----

.. [1] This is true with the exception that pip v7.0 and v7.0.1 required quotes
       around specifiers containing environment markers in requirement files.

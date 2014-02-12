
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


.. _`Requirements File Format`:

Requirements File Format
++++++++++++++++++++++++

Each line of the requirements file indicates something to be installed,
and like arguments to :ref:`pip install`, the following forms are supported::

    <requirement specifier>
    <archive url/path>
    [-e] <local project path>
    [-e] <vcs project url>

See the :ref:`pip install Examples<pip install Examples>` for examples of all these forms.

A line beginning with ``#`` is treated as a comment and ignored.

Additionally, the following Package Index Options are supported:

  *  :ref:`-i, --index-url <--index-url>`
  *  :ref:`--extra-index-url <--extra-index-url>`
  *  :ref:`--no-index <--no-index>`
  *  :ref:`-f, --find-links <--find-links>`
  *  :ref:`--allow-external <--allow-external>`
  *  :ref:`--allow-all-external <--allow-external>`
  *  :ref:`--allow-unverified <--allow-unverified>`

For example, to specify :ref:`--no-index <--no-index>` and 2 :ref:`--find-links <--find-links>` locations:

::

--no-index
--find-links /my/local/archives
--find-links http://some.archives.com/archives


Lastly, if you wish, you can refer to other requirements files, like this::

    -r more_requirements.txt

.. _`Requirement Specifiers`:

Requirement Specifiers
++++++++++++++++++++++

pip supports installing from "requirement specifiers" as implemented in
`pkg_resources Requirements <http://packages.python.org/setuptools/pkg_resources.html#requirement-objects>`_

Some Examples:

 ::

  'FooProject >= 1.2'
  Fizzy [foo, bar]
  'PickyThing<1.6,>1.9,!=1.9.6,<2.0a0,==2.4c1'
  SomethingWhoseVersionIDontCareAbout

.. note::

  Use single or double quotes around specifiers to avoid ``>`` and ``<`` being
  interpreted as shell redirects. e.g. ``pip install 'FooProject>=1.2'``.




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

The url suffix "egg=<project name>" is used by pip in it's dependency logic to
identify the project prior to pip downloading and analyzing the metadata.

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


Hash Verification
+++++++++++++++++

PyPI provides md5 hashes in the hash fragment of package download urls.

pip supports checking this, as well as any of the
guaranteed hashlib algorithms (sha1, sha224, sha384, sha256, sha512, md5).

The hash fragment is case sensitive (i.e. sha1 not SHA1).

This check is only intended to provide basic download corruption protection.
It is not intended to provide security against tampering. For that,
see :ref:`SSL Certificate Verification`


Download Cache
++++++++++++++

pip offers a :ref:`--download-cache <install_--download-cache>` option for
installs to prevent redundant downloads of archives from PyPI.

The point of this cache is *not* to circumvent the index crawling process, but
to *just* prevent redundant downloads.

Items are stored in this cache based on the url the archive was found at, not
simply the archive name.

If you want a fast/local install solution that circumvents crawling PyPI, see
the :ref:`Fast & Local Installs`.

Like all options, :ref:`--download-cache <install_--download-cache>`, can also
be set as an environment variable, or placed into the pip config file.  See the
:ref:`Configuration` section.


.. _`editable-installs`:

"Editable" Installs
+++++++++++++++++++

"Editable" installs are fundamentally `"setuptools develop mode"
<http://packages.python.org/setuptools/setuptools.html#development-mode>`_
installs.

You can install local projects or VCS projects in "editable" mode::

$ pip install -e path/to/SomeProject
$ pip install -e git+http://repo/my_project.git#egg=SomeProject

For local projects, the "SomeProject.egg-info" directory is created relative to
the project path.  This is one advantage over just using ``setup.py develop``,
which creates the "egg-info" directly relative the current working directory.



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



Options
*******

.. pip-command-options:: install

.. pip-index-options::


.. _`pip install Examples`:

Examples
********

1) Install `SomePackage` and it's dependencies from `PyPI`_ using :ref:`Requirement Specifiers`

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
  $ pip install -e git+https://git.repo/some_repo.git@egg=subdir&subdirectory=subdir_path # install a python package from a repo subdirectory

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



.. _PyPI: http://pypi.python.org/pypi/
.. _setuptools extras: http://packages.python.org/setuptools/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies

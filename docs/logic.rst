.. _`pip logic`:

================
Internal Details
================

.. _`Requirements File Format`:

Requirements File Format
========================

Each line of the requirements file indicates something to be installed,
and like arguments to :ref:`pip install`, the following forms are supported::

    <requirement specifier>
    <archive url/path>
    [-e] <local project path>
    [-e] <vcs project url>

See the :ref:`pip install Examples<pip install Examples>` for examples of all these forms.

A line beginning with ``#`` is treated as a comment and ignored.

Additionally, the following :ref:`Package Index Options <Package Index Options>` are supported

  *  :ref:`-i, --index-url <--index-url>`
  *  :ref:`--extra-index-url <--extra-index-url>`
  *  :ref:`--no-index <--no-index>`
  *  :ref:`-f, --find-links <--find-links>`

For example, to specify :ref:`--no-index <--no-index>` and 2 :ref:`--find-links <--find-links>` locations:

::

--no-index
--find-links /my/local/archives
--find-links http://some.archives.com/archives


Lastly, if you wish, you can refer to other requirements files, like this::

    -r more_requirements.txt

.. _`Requirement Specifiers`:

Requirement Specifiers
======================

pip supports installing from "requirement specifiers" as implemented in
`pkg_resources Requirements <http://packages.python.org/setuptools/pkg_resources.html#requirement-objects>`_

Some Examples:

 ::

  'FooProject >= 1.2'
  Fizzy [foo, bar]
  'PickyThing<1.6,>1.9,!=1.9.6,<2.0a0,==2.4c1'
  SomethingWhoseVersionIDontCareAbout

.. note::

  Use single or double quotes around specifiers to avoid ``>`` and ``<`` being interpreted as shell redirects. e.g. ``pip install 'FooProject>=1.2'``.

.. _`Pre Release Versions`:

Pre-release Versions
====================

Starting with v1.4, pip will only install stable versions as specified by `PEP426`_ by default. If
a version cannot be parsed as a compliant `PEP426`_ version then it is assumed
to be a pre-release.

If a Requirement specifier includes a pre-release or development version (e.g. ``>=0.0.dev0``) then
pip will allow pre-release and development versions for that requirement. This does not include
the != flag.

The ``pip install`` command also supports a :ref:`--pre <install_--pre>` flag that will enable
installing pre-releases and development releases.


.. _PEP426: http://www.python.org/dev/peps/pep-0426

.. _`Externally Hosted Files`:

Externally Hosted Files
=======================

Starting with v1.4, pip will warn about installing any file that does not come
from the primary index. In future versions pip will default to ignoring these
files unless asked to consider them.

The ``pip install`` command supports a
:ref:`--allow-external PROJECT <--allow-external>` option that will enable
installing links that are linked directly from the simple index but to an
external host that also have a supported hash fragment. Externally hosted
files for all projects may be enabled using the
:ref:`--allow-all-external <--allow-all-external>` flag to the ``pip install``
command.

The ``pip install`` command also supports a
:ref:`--allow-insecure PROJECT <--allow-insecure>` option that will enable
installing insecurely linked files. These are either directly linked (as above)
files without a hash, or files that are linked from either the home page or the
download url of a package.

In order to get the future behavior in v1.4 the ``pip install`` command
supports a :ref:`--no-allow-external <--no-allow-external>` and
:ref:`--no-allow-insecure <--no-allow-external>` flags.

.. _`VCS Support`:

VCS Support
===========

pip supports installing from Git, Mercurial, Subversion and Bazaar, and detects the type of VCS using url prefixes: "git+", "hg+", "bzr+", "svn+".

pip requires a working VCS command on your path: git, hg, svn, or bzr.

VCS projects can be installed in :ref:`editable mode <editable-installs>` (using the :ref:`--editable <install_--editable>` option) or not.

* For editable installs, the clone location by default is "<venv path>/src/SomeProject" in virtual environments, and "<cwd>/src/SomeProject" for global installs.
  The :ref:`--src <install_--src>` option can be used to modify this location.
* For non-editable installs, the project is built locally in a temp dir and then installed normally.

The url suffix "egg=<project name>" is used by pip in it's dependency logic to identify the project prior to pip downloading and analyzing the metadata.

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
================

pip searches for packages on `PyPI <http://pypi.python.org>`_ using the
`http simple interface <http://pypi.python.org/simple>`_,
which is documented `here <http://packages.python.org/setuptools/easy_install.html#package-index-api>`_
and `there <http://www.python.org/dev/peps/pep-0301/>`_

pip offers a set of :ref:`Package Index Options <Package Index Options>` for modifying how packages are found.

See the :ref:`pip install Examples<pip install Examples>`.


.. _`SSL Certificate Verification`:

SSL Certificate Verification
============================

Starting with v1.3, pip provides SSL certificate verification over https, for the purpose
of providing secure, certified downloads from PyPI.


Hash Verification
=================

PyPI provides md5 hashes in the hash fragment of package download urls.

pip supports checking this, as well as any of the
guaranteed hashlib algorithms (sha1, sha224, sha384, sha256, sha512, md5).

The hash fragment is case sensitive (i.e. sha1 not SHA1).

This check is only intended to provide basic download corruption protection.
It is not intended to provide security against tampering. For that,
see :ref:`SSL Certificate Verification`


Download Cache
==============

pip offers a :ref:`--download-cache <install_--download-cache>` option for installs to prevent redundant downloads of archives from PyPI.

The point of this cache is *not* to circumvent the index crawling process, but to *just* prevent redundant downloads.

Items are stored in this cache based on the url the archive was found at, not simply the archive name.

If you want a fast/local install solution that circumvents crawling PyPI, see the :ref:`Fast & Local Installs` Cookbook entry.

Like all options, :ref:`--download-cache <install_--download-cache>`, can also be set as an environment variable, or placed into the pip config file.
See the :ref:`Configuration` section.


.. _`editable-installs`:

"Editable" Installs
===================

"Editable" installs are fundamentally `"setuptools develop mode" <http://packages.python.org/setuptools/setuptools.html#development-mode>`_ installs.

You can install local projects or VCS projects in "editable" mode::

$ pip install -e path/to/SomeProject
$ pip install -e git+http://repo/my_project.git#egg=SomeProject

For local projects, the "SomeProject.egg-info" directory is created relative to the project path.
This is one advantage over just using ``setup.py develop``, which creates the "egg-info" directly relative the current working directory.


setuptools & pkg_resources
==========================

Internally, pip uses the `setuptools` package, and the `pkg_resources` module, which are available from the project, `Setuptools`_.

Here are some examples of how pip uses `setuptools` and `pkg_resources`:

* The core of pip's install process uses the `setuptools`'s "install" command.
* Editable ("-e") installs use the `setuptools`'s "develop" command.
* pip uses `pkg_resources` for version parsing, for detecting version conflicts, and to determine what projects are installed,


.. _Setuptools: http://pypi.python.org/pypi/setuptools/

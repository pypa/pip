.. note::

    This section of the documentation is currently being written. pip
    developers welcome your help to complete this documentation. If you're
    interested in helping out, please let us know in the `tracking issue`_.


****************************
Broad functionality overview
****************************

pip is a package installer.

pip does a lot more than installation; it also has a cache, and it has
configuration, and it has a CLI, which has its own quirks. But mainly:

Things pip does:

1. | Manages the building of packages (offloads package building to a
     backend) when that’s necessary (a source distribution package --
     this is not necessary if the package is a wheel).

   1. | By default, pip delegates package-building to setuptools, for
           backwards compatibility reasons. But thing with setuptools:
           has a ``setup.py`` file that it invokes to …… get info?

2. Decides where to install stuff. Once the package is built, the resulting
   artifact is then installed to the system in its appropriate place. :pep:`517`
   defines the interface between the build backend & installer.

Broad overview of flow
======================

In sequence, what does pip do?:

1. Get user input (user-supplied string saying what package they want)
2. Figure out what that means: exactly what the user requested --
   translate to a thing pip can operate on (user input to requirements)
3. CORE OF THE WHOLE PROCESS, MAYBE? Once you have a set of reqs from
   Step 2, you have to expand those into a concrete “things to install”
   -- Figure out what other requirements it has to install based on
   user-given requirements, and where to get them from.

   a. this step is convoluted - also exploratory, involves dependency
         resolution -- we need to get to the index, see what versions
         are available

   b. Sometimes you need to build the package itself in order to get
         dependency information, which means fetching the package from
         package index, which means knowing whether it exists. For a
         single package,

4. Install the actual items to be installed.

Why? pip installs from places other than PyPI! But also, we’ve never had
guarantees of PyPI’s JSON API before now, so no one has been getting
metadata from PyPI separate from downloading the package itself.

In terms of flow of the install process:

1. For 1 package: Get abstract requirement(s) for that package, and
   try and see what that means (this abstract requirement can take
   various forms). Define abstract dependencies.

2. Once we have a set of "this package, get it from here, this is that
   version of that package",

3. Modify the environment to install those things (which means: place
   the files in the right place). For example: if you already have
   version 6.0 of a requirement and you are installing 7.2, uninstall
   6.0 and install 7.2.

Download process
----------------

What happens in an install? Well, a subset of ``install``, a process
pip usually does during a ``pip install``, is ``download`` (also
available to the user as the :ref:`pip download` command). And we
download and INSPECT packages to get manifests. For any given package
name, we need to know what files are available and what their
filenames are.

pip can download from a Python package repository, where packages are
stored in a structured format so an installer like pip can find them.

:pep:`503` defines the API we use to talk to a Python package repository.

PyPI
^^^^

What happens if we run ``pip download somepackage`` with no other
arguments?  By default we look at `PyPI`_, which is where pip knows
where to look to get more info for what the package index knows about
``somepackage``.

``pip`` then knows: what files are available, and what their filenames
are.

IN OTHER WORDS

While all dependencies have not been resolved, do the following:

1.  Following the API defined in :pep:`503`, fetch the index page from
    `http://{pypi_index}/simple/{package_name <http://pypi.org/simple/%7Bpackage_name>`__}
2.  Parse all of the file links from the page.
3.  Select a single file to download from the list of links.
4.  Extract the metadata from the downloaded package.
5.  Update the dependency tree based on the metadata.

The package index gives pip a list of files for that package (via the existing PyPI API). The files have the version and some other info that helps pip decide whether that's something pip ought to download.

pip chooses from the list a single file to download.

It may go back and choose another file to download.

When pip looks at the package index, the place where it looks has
basically a link. The link’s text is the name of the file.

This is the `PyPI Simple API`_ (PyPI has several APIs, some are being
deprecated). pip looks at Simple API, documented initially at :pep:`503` --
packaging.python.org has PyPA specifications with more details for
Simple Repository API.

For this package name -- this is the list of files available.

Looks there for:

* The list of filenames
* Other info

Once it has those, it selects one file and downloads it.

(Question: If I want to ``pip install flask``, I think the whole list of filenames
cannot….should not be …. ? I want only the Flask …. Why am I getting the
whole list?

Answer: It's not every file, just files of Flask. No API for getting alllllll
files on PyPI. It’s for getting all files of Flask.)

.. _`tracking issue`: https://github.com/pypa/pip/issues/6831
.. _PyPI: https://pypi.org/
.. _PyPI Simple API: https://warehouse.readthedocs.io/api-reference/legacy/#simple-project-api

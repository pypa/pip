############
Architecture
############

.. contents::

****************************
Broad functionality overview
****************************

Pip is a package installer.

pip does a lot more than installation; it also has a cache, and it has
configuration, and it has a CLI, which has its own quirks. But mainly:

Things pip does:

1. | Manages the building of packages (offloads package building to a
     backend) when that’s necessary (a source distribution package --
     this is not necessary if the package is a wheel).

   1. | By default, pip delegates package-building to setuptools, for
           backwards compat reasons. But thing with setuptools: has a
           setup.py file that it invokes to …… get info?

2. Decides where to install stuff. Once the package is built, resulting
   artifact is then installed into system in appropriate place. PEP 517
   defines interface between build backend & installer.

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

Why? Pip installs from places other than PyPI! But also, we’ve never had
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

pip then knows: what files are available, and what their filenames are

IN OTHER WORDS

While all dependencies have not been resolved, do the following:

1.  Following the API defined in PEP503, fetch the index page from
    `http://{pypi_index}/simple/{package_name <http://pypi.org/simple/%7Bpackage_name>`__}
2.  Parse all of the file links from the page.
3.  Select a single file to download from the list of links.
4.  Extract the metadata from the downloaded package
5.  Update the dependency tree based on the metadata

The package index gives pip a list of files for that pkg (via the existing PyPI API). The files have the version and some other info that helps pip decide whether that's something pip ought to download.

pip chooses from the list a single file to download.

It may go back and choose another file to download

When pip looks at the package index, the place where it looks has
basically a link. The link’s text is the name of the file

This is the PyPI Simple API -- docs
https://warehouse.readthedocs.io/api-reference/legacy/#simple-project-api

(PyPI has several APIs, some are being deprecated)

Pip looks at Simple API, documented initially at PEP 503 --
packaging.python.org has PyPA specifications with more details for
Simple Repository API

For this package name -- this is the list of files available

Looks there for:

* The list of filenames
* Other info

Once it has those, selects one file, downloads it

(Question: If I want to ``pip install flask``, I think the whole list of filenames
cannot….should not be …. ? I want only the Flask …. Why am I getting the
whole list?

Answer: It's not every file, just files of Flask. No API for getting alllllll
files on PyPI. It’s for getting all files of Flask.)

****************************************
Repository anatomy & directory structure
****************************************

https://github.com/pypa/pip/

``pip``’s repo: it’s a standard Python package. ``README``, license,
``pyproject.toml``, ``setup.py``, etc. in the top level.

There’s a tox.ini https://github.com/pypa/pip/blob/master/tox.ini that
has a lot of …. Describes a few environments pip uses during development
for simplifying how tests are run (complicated situation there) -- tox
-e -py36 …. Can run for different versions of Python by changing “36” to
“27” or similar. Tox is an automation tool

[question: why a news directory? Mostly description is based on GitHub
issues….]

[question: is the \_template.rst a Jinja 2 file? Pradyun: idk, check
towncrier docs]

├── docs/ *[documentation, built with Sphinx]*

│ ├── html/ *[sources to HTML documentation avail. online]*

│ ├── man/ *[man pages the distros can use by running ``man pip``]*

│ └── pip_sphinxext.py *[an extension -- pip-specific plugins to Sphinx
that do not apply to other packages]*

├── news/ *[pip stores news fragments… Every time pip makes a
user-facing change, a file is added to this directory with the right
extension & name so it gets included in release notes…. So every release
the maintainers will be deleting old files in this directory? Yes - we
use the towncrier automation to generate a NEWS file and auto-delete old
stuff. There’s more about this in the contributor documentation!]*

│ └── \_template.rst *[template for release notes -- this is a file
towncrier uses…. Is this jinja? I don’t know]*

├── src/ *[source]*

│ ├── pip/ *[where all the source code lives. Within that, 2
directories]*

│ │ ├── \__init__.py

│ │ ├── \__main__.py

│ │ ├── \__pycache__/ *[not discussing contents right now]*

│ │ ├── \_internal/ *[where all the pip code lives that’s written by pip
maintainers -- underscore means private. Pip is not a library -- it’s a
command line tool! A very important distinction! People who want to
install stuff with pip should not use the internals -- they should use
the CLI. There’s a note on this in the docs.]*

│ │ │ ├── \__init__.py

│ │ │ ├── build_env.py [not discussing now]

│ │ │ ├── cache.py *[has all the info for how to handle caching within
pip -- cache-handling stuff. Uses cachecontrol from PyPI, vendored into
pip]*

│ │ │ ├── cli/ *[subpackage containing helpers & additional code for
managing the command line interface. Uses argparse from stdlib]*

│ │ │ │ ├── \__init__.py

│ │ │ │ ├── autocompletion.py

│ │ │ │ ├── base_command.py

│ │ │ │ ├── cmdoptions.py

│ │ │ │ ├── main_parser.py

│ │ │ │ ├── parser.py

│ │ │ │ └── status_codes.py

│ │ │ ├── commands/ *[literally - each file is the name of the command
on the pip CLI. Each has a class that defines what’s needed to set it
up, what happens]*

│ │ │ │ ├── \__init__.py

│ │ │ │ ├── check.py

│ │ │ │ ├── completion.py

│ │ │ │ ├── configuration.py

│ │ │ │ ├── download.py

│ │ │ │ ├── freeze.py

│ │ │ │ ├── hash.py

│ │ │ │ ├── help.py

│ │ │ │ ├── install.py

│ │ │ │ ├── list.py

│ │ │ │ ├── search.py

│ │ │ │ ├── show.py

│ │ │ │ ├── uninstall.py

│ │ │ │ └── wheel.py

│ │ │ ├── configuration.py

│ │ │ ├── download.py

│ │ │ ├── exceptions.py

│ │ │ ├── index.py

│ │ │ ├── locations.py

│ │ │ ├── models/ *[in-process refactoring! Goal: improve how pip
internally models representations it has for data -- data
representation. General overall cleanup. Data reps are spread throughout
codebase….link is defined in a class in 1 file, and then another file
imports Link from that file. Sometimes cyclic dependency?!?! To prevent
future situations like this, etc., Pradyun started moving these into a
models directory.]*

│ │ │ │ ├── \__init__.py

│ │ │ │ ├── candidate.py

│ │ │ │ ├── format_control.py

│ │ │ │ ├── index.py

│ │ │ │ └── link.py

│ │ │ ├── operations/ *[a bit of a weird directory….. Freeze.py used to
be in there. Freeze is an operation -- there was an operations.freeze.
Then “prepare” got added (the operation of preparing a pkg). Then
“check” got added for checking the state of an env.] [what’s a command
vs an operation? Command is on CLI; an operation would be an internal
bit of code that actually does some subset of the operation the command
says. ``install`` command uses bits of ``check`` and ``prepare``, for
instance. In the long run, Pradyun’s goal: ``prepare.py`` goes away
(gets refactored into other files) such that ``operations`` is just
``check`` and ``freeze``..... … Pradyun plans to refactor this.] [how
does this compare to ``utils``?]*

│ │ │ │ ├── \__init__.py

│ │ │ │ ├── check.py

│ │ │ │ ├── freeze.py

│ │ │ │ └── prepare.py

│ │ │ ├── pep425tags.py *[getting refactored into packaging.tags (a
library on PyPI) which is external to pip (but vendored by pip). PEP 425
tags: turns out lots of people want this! Compatibility tags for built
distributions -> e.g., platform, Python version, etc.]*

│ │ │ ├── pyproject.py *[pyproject.toml is a new standard (PEP 518 and
517). This file reads pyproject.toml and passes that info elsewhere. The
rest of the processing happens in a different file. All the handling for
517 and 518 is in a different file.]*

│ │ │ ├── req/ *[*\ **A DIRECTORY THAT NEEDS REFACTORING. A LOT**\ *\ ……
Remember Step 3? Dependency resolution etc.? This is that step! Each
file represents … have the entire flow of installing & uninstalling,
getting info about packages…. Some files here are more than 1,000 lines
long! (used to be longer?!) Refactor will deeply improve developer
experience.]*

│ │ │ │ ├── \__init__.py

│ │ │ │ ├── constructors.py

│ │ │ │ ├── req_file.py

│ │ │ │ ├── req_install.py

│ │ │ │ ├── req_set.py

│ │ │ │ ├── req_tracker.py

│ │ │ │ └── req_uninstall.py

│ │ │ ├── resolve.py *[This is where the current dependency resolution
algorithm sits. Pradyun is improving the pip dependency
resolver*\ https://github.com/pypa/pip/issues/988\ *. Pradyun will get
rid of this file and replace it with a directory called “resolution”.
[this work is in git master…. There is further work that is going to be
in a branch soon]]*

│ │ │ ├── utils/ *[everything that is not “operationally” pip ….. Misc
functions and files get dumped. There’s some organization here. There’s
a models.py here which needs refactoring. Deprecation.py is useful, as
are other things, but some things do not belong here. There ought to be
some GitHub issues for refactoring some things here. Maybe a few issues
with checkbox lists.]*

│ │ │ │ ├── \__init__.py

│ │ │ │ ├── appdirs.py

│ │ │ │ ├── compat.py

│ │ │ │ ├── deprecation.py

│ │ │ │ ├── encoding.py

│ │ │ │ ├── filesystem.py

│ │ │ │ ├── glibc.py

│ │ │ │ ├── hashes.py

│ │ │ │ ├── logging.py

│ │ │ │ ├── misc.py

│ │ │ │ ├── models.py

│ │ │ │ ├── outdated.py

│ │ │ │ ├── packaging.py

│ │ │ │ ├── setuptools_build.py

│ │ │ │ ├── temp_dir.py

│ │ │ │ ├── typing.py

│ │ │ │ └── ui.py

│ │ │ ├── vcs/ *[stands for Version Control System. Where pip handles
all version control stuff -- one of the ``pip install`` arguments you
can use is a version control link. …. Are any of these commands
vendored? No, via subprocesses. For performance, it makes sense (we
think) to do this instead of pygitlib2 or similar -- and has to be pure
Python, can’t include C libraries, because you can’t include compiled C
stuff, because you might not have it for the platform you are running
on.]*

│ │ │ │ ├── \__init__.py

│ │ │ │ ├── bazaar.py

│ │ │ │ ├── git.py

│ │ │ │ ├── mercurial.py

│ │ │ │ └── subversion.py

│ │ │ └── wheel.py *[file that manages installation of a wheel file.
This handles unpacking wheels -- “unpack and spread”. There is a package
on PyPI called ``wheel`` that builds wheels -- do not confuse it with
this.]*

│ │ └── \_vendor/ *[code from other packages -- pip’s own dependencies….
Has them in its own source tree, because pip cannot depend on pip being
installed on the machine already!]*

│ └── pip.egg-info/ *[ignore the contents for now]*

├── tasks/ *[invoke is a PyPI library which uses files in this directory
to define automation commands that are used in pip’s development
processes -- not discussing further right now. For instance, automating
the release.]*

├── tests/ *[contains tests you can run. There are instructions in pip’s
Getting Started guide! Which Pradyun wrote!!!!!]*

│ ├── \__init__.py

│ ├── conftest.py

│ ├── data/ *[test data for running tests -- pesudo package index in it!
Lots of small packages that are invalid or are valid. Test fixtures.
Used by functional tests]*

│ ├── functional/ *[functional tests of pip’s CLI -- end-to-end, invoke
pip in subprocess & check results of execution against desired result.
This also is what makes test suite slow]*

│ ├── lib/ *[helpers for tests]*

│ ├── scripts/ *[will probably die in future in a refactor -- scripts
for running all of the tests, but we use pytest now. Someone could make
a PR to remove this! Good first issue!]*

│ ├── unit/ *[unit tests -- fast and small and nice!]*

│ └── yaml/ *[resolver tests! They’re written in YAML. This folder just
contains .yaml files -- actual code for reading/running them is in
lib/yaml.py . This is fine!]*

├── tools/ *[misc development workflow tools, like requirements files &
Travis CI files & helpers for tox]*

├── AUTHORS.txt

├── LICENSE.txt

├── MANIFEST.in

├── NEWS.rst

├── README.rst

├── pyproject.toml

├── setup.cfg

├── setup.py

└── tox.ini



.. _PyPI: https://pypi.org/

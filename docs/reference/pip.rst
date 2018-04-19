pip
---

.. contents::

Usage
*****

::

 pip <command> [options]


Description
***********


.. _`Logging`:

Logging
=======

Console logging
~~~~~~~~~~~~~~~

pip offers :ref:`-v, --verbose <--verbose>` and :ref:`-q, --quiet <--quiet>`
to control the console log level. By default, some messages (error and warnings)
are colored in the terminal. If you want to suppress the colored output use
:ref:`--no-color <--no-color>`.


.. _`FileLogging`:

File logging
~~~~~~~~~~~~

pip offers the :ref:`--log <--log>` option for specifying a file where a maximum
verbosity log will be kept.  This option is empty by default. This log appends
to previous logging.

Like all pip options, ``--log`` can also be set as an environment variable, or
placed into the pip config file.  See the :ref:`Configuration` section.

.. _`exists-action`:

--exists-action option
======================

This option specifies default behavior when path already exists.
Possible cases: downloading files or checking out repositories for installation,
creating archives. If ``--exists-action`` is not defined, pip will prompt
when decision is needed.

*(s)witch*
    Only relevant to VCS checkout. Attempt to switch the checkout
    to the appropriate url and/or revision.
*(i)gnore*
    Abort current operation (e.g. don't copy file, don't create archive,
    don't modify a checkout).
*(w)ipe*
    Delete the file or VCS checkout before trying to create, download, or checkout a new one.
*(b)ackup*
    Rename the file or checkout to ``{name}{'.bak' * n}``, where n is some number
    of ``.bak`` extensions, such that the file didn't exist at some point.
    So the most recent backup will be the one with the largest number after ``.bak``.
*(a)abort*
    Abort pip and return non-zero exit status.

.. _`build-interface`:

Build System Interface
======================

Pip builds packages by invoking the build system. Presently, the only supported
build system is ``setuptools``, but in the future, pip will support :pep:`517`
which allows projects to specify an alternative build system in a
``pyproject.toml`` file.  As well as package building, the build system is also
invoked to install packages direct from source.  This is handled by invoking
the build system to build a wheel, and then installing from that wheel.  The
built wheel is cached locally by pip to avoid repeated identical builds.

The current interface to the build system is via the ``setup.py`` command line
script - all build actions are defined in terms of the specific ``setup.py``
command line that will be run to invoke the required action.

Setuptools Injection
~~~~~~~~~~~~~~~~~~~~

As noted above, the supported build system is ``setuptools``. However, not all
packages use ``setuptools`` in their build scripts. To support projects that
use "pure ``distutils``", pip injects ``setuptools`` into ``sys.modules``
before invoking ``setup.py``. The injection should be transparent to
``distutils``-based projects, but 3rd party build tools wishing to provide a
``setup.py`` emulating the commands pip requires may need to be aware that it
takes place.

Build System Output
~~~~~~~~~~~~~~~~~~~

Any output produced by the build system will be read by pip (for display to the
user if requested). In order to correctly read the build system output, pip
requires that the output is written in a well-defined encoding, specifically
the encoding the user has configured for text output (which can be obtained in
Python using ``locale.getpreferredencoding``). If the configured encoding is
ASCII, pip assumes UTF-8 (to account for the behaviour of some Unix systems).

Build systems should ensure that any tools they invoke (compilers, etc) produce
output in the correct encoding. In practice - and in particular on Windows,
where tools are inconsistent in their use of the "OEM" and "ANSI" codepages -
this may not always be possible. Pip will therefore attempt to recover cleanly
if presented with incorrectly encoded build tool output, by translating
unexpected byte sequences to Python-style hexadecimal escape sequences
(``"\x80\xff"``, etc). However, it is still possible for output to be displayed
using an incorrect encoding (mojibake).

PEP 518 Support
~~~~~~~~~~~~~~~

As of 10.0, pip supports projects declaring dependencies that are required at
install time using a ``pyproject.toml`` file, in the form described in
:pep:`518`. When building a project, pip will install the required dependencies
locally, and make them available to the build process.

When making build requirements available, pip does so in an *isolated
environment*. That is, pip does not install those requirements into the user's
``site-packages``, but rather installs them in a temporary directory which it
adds to the user's ``sys.path`` for the duration of the build. This ensures
that build requirements are handled independently of the user's runtime
environment. For example, a project that needs a recent version of setuptools
to build can still be installed, even if the user has an older version
installed (and without silently replacing that version).

In certain cases, projects (or redistributors) may have workflows that
explicitly manage the build environment. For such workflows, build isolation
can be problematic. If this is the case, pip provides a
``--no-build-isolation`` flag to disable build isolation. Users supplying this
flag are responsible for ensuring the build environment is managed
appropriately.

.. _pep-518-limitations:

**Limitations**:

* until :pep:`517` support is added, ``setuptools`` and ``wheel`` **must** be
  included in the list of build requirements: pip will assume these as default,
  but will not automatically add them to the list of build requirements if
  explicitly defined in ``pyproject.toml``.

* the current implementation only support installing build requirements from
  wheels: this is a technical limitation of the implementation - source
  installs would require a build step of their own, potentially recursively
  triggering another :pep:`518` dependency installation process. The possible
  unbounded recursion involved was not considered acceptable, and so
  installation of build dependencies from source has been disabled until a safe
  resolution of this issue is found.

* ``pip<18.0``: only support installing build requirements from wheels, and
  does not support the use of environment markers and extras (only version
  specifiers are respected).


Future Developments
~~~~~~~~~~~~~~~~~~~

:pep:`426` notes that the intention is to add hooks to project metadata in
version 2.1 of the metadata spec, to explicitly define how to build a project
from its source. Once this version of the metadata spec is final, pip will
migrate to using that interface. At that point, the ``setup.py`` interface
documented here will be retained solely for legacy purposes, until projects
have migrated.

Specifically, applications should *not* expect to rely on there being any form
of backward compatibility guarantees around the ``setup.py`` interface.


Build Options
~~~~~~~~~~~~~

The ``--global-option`` and ``--build-option`` arguments to the ``pip install``
and ``pip wheel`` inject additional arguments into the ``setup.py`` command
(``--build-option`` is only available in ``pip wheel``).  These arguments are
included in the command as follows::

    python setup.py <global_options> BUILD COMMAND <build_options>

The options are passed unmodified, and presently offer direct access to the
distutils command line. Use of ``--global-option`` and ``--build-option``
should be considered as build system dependent, and may not be supported in the
current form if support for alternative build systems is added to pip.


.. _`General Options`:

General Options
***************

.. pip-general-options::


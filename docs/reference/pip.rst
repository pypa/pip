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
to control the console log level.


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
build system is ``setuptools``, but future developments to the Python packaging
infrastructure are expected to include support for other build systems.  As
well as package building, the build system is also invoked to install packages
direct from source.

The interface to the build system is via the ``setup.py`` command line script -
all build actions are defined in terms of the specific ``setup.py`` command
line that will be run to invoke the required action.

Setuptools Injection
~~~~~~~~~~~~~~~~~~~~

As noted above, the supported build system is ``setuptools``. However, not all
packages use ``setuptools`` in their build scripts. To support projects that
use "pure ``distutils``", pip injects ``setuptools`` into ``sys.modules``
before invoking ``setup.py``. The injection should be transparent to
``distutils``-based projects, but 3rd party build tools wishing to provide a
``setup.py`` emulating the commands pip requires may need to be aware that it
takes place.

Future Developments
~~~~~~~~~~~~~~~~~~~

`PEP426`_ notes that the intention is to add hooks to project metadata in
version 2.1 of the metadata spec, to explicitly define how to build a project
from its source. Once this version of the metadata spec is final, pip will
migrate to using that interface. At that point, the ``setup.py`` interface
documented here will be retained solely for legacy purposes, until projects
have migrated.

Specifically, applications should *not* expect to rely on there being any form
of backward compatibility guarantees around the ``setup.py`` interface.

.. _PEP426: http://www.python.org/dev/peps/pep-0426/#metabuild-system

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


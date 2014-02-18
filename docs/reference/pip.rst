
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
to control the console log level.  Each option can be used multiple times and
used together. One ``-v`` increases the verbosity by one, whereas one ``-q`` decreases it by
one.

The series of log levels, in order, are as follows::

  VERBOSE_DEBUG, DEBUG, INFO, NOTIFY, WARN, ERROR, FATAL

``NOTIFY`` is the default level.

A few examples on how the parameters work to affect the level:

* specifying nothing results in ``NOTIFY``
* ``-v`` results in ``INFO``
* ``-vv`` results in ``DEBUG``
* ``-q`` results in ``WARN``
* ``-vq`` results in ``NOTIFY``

The most practical use case for users is either ``-v`` or ``-vv`` to see
additional logging to help troubleshoot an issue.


.. _`FileLogging`:

File logging
~~~~~~~~~~~~

pip offers the :ref:`--log <--log>` option for specifying a file where a maximum
verbosity log will be kept.  This option is empty by default. This log appends
to previous logging.

Additionally, when commands fail (i.e. return a non-zero exit code), pip writes
a "failure log" for the failed command. This log overwrites previous
logging. The default location is as follows:

* On Unix and Mac OS X: :file:`$HOME/.pip/pip.log`
* On Windows, the configuration file is: :file:`%HOME%\\pip\\pip.log`

The option for the failure log, is :ref:`--log-file <--log-file>`.

Both logs add a line per execution to specify the date and what pip executable wrote the log.

Like all pip options, ``--log`` and ``log-file``, can also be set as an environment
variable, or placed into the pip config file.  See the :ref:`Configuration`
section.

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


.. _`General Options`:

General Options
***************

.. pip-general-options::


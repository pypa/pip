===
pip
===


Usage
*****

.. tab:: Unix/macOS

    .. code-block:: shell

        python -m pip <command> [options]

.. tab:: Windows

    .. code-block:: shell

        py -m pip <command> [options]

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
placed into the pip config file. See the :doc:`../topics/configuration` section.

.. _`exists-action`:

--exists-action option
======================

This option specifies default behavior when path already exists.
Possible cases: downloading files or checking out repositories for installation,
creating archives. If ``--exists-action`` is not defined, pip will prompt
when decision is needed.

*(s)witch*
    Only relevant to VCS checkout. Attempt to switch the checkout
    to the appropriate URL and/or revision.
*(i)gnore*
    Abort current operation (e.g. don't copy file, don't create archive,
    don't modify a checkout).
*(w)ipe*
    Delete the file or VCS checkout before trying to create, download, or checkout a new one.
*(b)ackup*
    Rename the file or checkout to ``{name}{'.bak' * n}``, where n is some number
    of ``.bak`` extensions, such that the file didn't exist at some point.
    So the most recent backup will be the one with the largest number after ``.bak``.
*(a)bort*
    Abort pip and return non-zero exit status.

.. _`2-build-system-interface`:
.. rubric:: Build System Interface

This is now covered in :doc:`../reference/build-system/index`.

.. _`General Options`:

General Options
***************

.. pip-general-options::

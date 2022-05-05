===========================
Configuration File Handling
===========================

The ``pip._internal.configuration`` module is responsible for handling
(eg. loading from and saving values to) configuration files that are used by
pip. The module's functionality is largely exposed through and coordinated by
the module's ``Configuration`` class.

.. note::

    This section of the documentation is currently being written. pip
    developers welcome your help to complete this documentation. If you're
    interested in helping out, please let us know in the
    `tracking issue <https://github.com/pypa/pip/issues/6831>`_.


.. _configuration-overview:

Overview
========

pip stores configuration files in standard OS-appropriate locations, which are
determined by ``appdirs``. These files are in the INI format and are processed
with ``RawConfigParser``.

pip uses configuration files in two operations:

* During processing of command line options.

  * Reading from *all* configuration sources

* As part of ``pip config`` command.

  * Reading from *all* configuration sources
  * Manipulating a single configuration file

Both of these operations utilize functionality provided the ``Configuration``
object, which encapsulates all the logic for handling configuration files and
provides APIs for the same.

The remainder of this section documents the ``Configuration`` class, and
discusses potential future refactoring ideas.


.. _configuration-class:

``Configuration`` class
=======================

``Configuration`` loads configuration values from sources in the local
environment: a combination of configuration files and environment variables.

It can be used in two "modes", for reading all the values from the local
environment and for manipulating a single configuration file. It differentiates
between these two modes using the ``load_only`` attribute, which can be None or
represent the :ref:`kind <config-kinds>` of the configuration file to be
manipulated.

The ``isolated`` attribute determines which sources are used when loading the
configuration. If ``isolated`` is ``True``, user-specific configuration files
and environment variables are not used.

Reading from local environment
------------------------------

``Configuration`` can be used to read from all configuration sources in the
local environment and access the values, as per the precedence logic described
in the :ref:`Config Precedence <config-precedence>` section.

For this use case, the ``Configuration.load_only`` attribute would be ``None``,
and the methods used would be:

.. py:class:: Configuration

  .. py:method:: load()

    Handles all the interactions with the environment, to load all the
    configuration data into objects in memory.

  .. py:method:: items()

    Provides key-value pairs (like ``dict.items()``) from the loaded-in-memory
    information, handling all of the override ordering logic.

  .. py:method:: get_value(key)

    Provides the value of the given key from the loaded configuration.
    The loaded configuration may have ``load_only`` be None or non-None.
    This uses the same underlying mechanism as ``Configuration.items()`` and
    does follow the precedence logic described in :ref:`Config Precedence
    <config-precedence>`.

At the time of writing, the parts of the codebase that use ``Configuration``
in this manner are: ``ConfigOptionParser``, to transparently include
configuration handling as part of the command line processing logic,
and ``pip config get``, for printing the entire configuration when no
:ref:`kind <config-kinds>` is specified via the CLI.

Manipulating a single configuration file
----------------------------------------

``Configuration`` can be used to manipulate a single configuration file,
such as to add, change or remove certain key-value pairs.

For this use case, the ``load_only`` attribute would be non-None, and would
represent the :ref:`kind <config-kinds>` of the configuration file to be
manipulated. In addition to the methods discussed in the previous section,
the methods used would be:

.. py:class:: Configuration
  :noindex:

  .. py:method:: get_file_to_edit()

    Provides the "highest priority" file, for the :ref:`kind <config-kinds>` of
    configuration file specified by ``load_only``. This requires ``load_only``
    to be non-None.

  .. py:method:: set_value(key, value)

    Provides a way to add/change a single key-value pair, in the file specified
    by ``Configuration.get_file_to_edit()``.

  .. py:method:: unset_value(key)

    Provides a way to remove a single key-value pair, in the file specified
    by ``Configuration.get_file_to_edit()``.

  .. py:method:: save()

    Saves the in-memory state of to the original files, saving any modifications
    made to the ``Configuration`` object back into the local environment.

.. _config-kinds:

kinds
=====

This is an enumeration that provides values to represent a "source" for
configuration. This includes environment variables and various types of
configuration files (global, site-specific, user_specific, specified via
``PIP_CONFIG_FILE``).

Future Refactoring Ideas
========================

* Break up the ``Configuration`` class into 2 smaller classes, by use case
    * ``Command`` use-case (read only) -- ``ConfigurationReader``
    * ``pip config`` use-case (read / write) -- ``ConfigurationModifier`` (inherit from ``ConfigurationReader``)
* Eagerly populate ``Configuration._dictionary`` on load.

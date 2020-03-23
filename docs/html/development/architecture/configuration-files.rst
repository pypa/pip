===========================
Configuration File Handling
===========================

The ``pip._internal.configuration`` module is responsible for handling
configuration files (eg. loading from and saving values to) that are used by
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

- During processing of command line options.
  - Reading from *all* configuration sources
- As part of ``pip config`` command.
  - Reading from *all* configuration sources
  - Manipulating a single configuration file

Both of these operations utilize functionality provided the ``Configuration``
object, which encapsulates all the logic for handling configuration files and
provides APIs for the same.

The remainder of this section documents the ``Configuration`` class, and
discusses potential future refactoring ideas.


.. _configuration-class:

``Configuration`` class
=======================

``Configuration`` loads configuration values from sources in the local
environment: a combination of config files and environment variables.

It can be used in two "modes", for reading all the values from the local
environment and for manipulating a single config file. It differentiates
between these two modes using the ``load_only`` attribute.

The ``isolated`` attribute manipulates which sources are used when loading the
configuration. If ``isolated`` is ``True``, user-specific config files and
environment variables are not used.

Reading from local environment
------------------------------

When using a ``Configuration`` object to read from all sources in the local
environment, the ``load_only`` attribute is ``None``. The API provided for this
use case is ``Configuration.load`` and ``Configuration.items``.

``Configuration.load`` does all the interactions with the environment to load
all the configuration into objects in memory. ``Configuration.items``
provides key-value pairs (like ``dict.items``) from the loaded-in-memory
information, handling all of the override ordering logic.

At the time of writing, the only part of the codebase that uses
``Configuration`` like this is the ``ConfigOptionParser`` in the command line parsing
logic.

Manipulating a single config file
---------------------------------

When using a ``Configuration`` object to read from a single config file, the
``load_only`` attribute would be non-None, and would represent the
:ref:`kind <config-kinds>` of the config file.

This use case uses the methods discussed in the previous section
(``Configuration.load`` and ``Configuration.items``) and a few more that
are more specific to this use case.

``Configuration.get_file_to_edit`` provides the "highest priority" file, for
the :ref:`kind <config-kinds>` of config file specified by ``load_only``.
The rest of this document will refer to this file as the "``load_only`` file".

``Configuration.set_value`` provides a way to add/change a single key-value pair
in the ``load_only`` file. ``Configuration.unset_value`` removes a single
key-value pair in the ``load_only`` file. ``Configuration.get_value`` gets the
value of the given key from the loaded configuration. ``Configuration.save`` is
used save the state ``load_only`` file, back into the local environment.

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

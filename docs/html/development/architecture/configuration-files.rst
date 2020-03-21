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

The remainder of this section documents the ``Configuration`` class and
other implementation details of the ``configuration`` module.


.. _config-kinds:

kinds
=====

- used to represent "where" a configuration value comes from
  (eg. environment variables, site-specific configuration file,
  global configuration file)

.. _configuration-class:

Configuration
============

- TODO: API & usage - ``Command``, when processing CLI options.
    - __init__()
    - load()
    - items()
- TODO: API & usage - ``pip config``, when loading / manipulating config files.
    - __init__()
    - get_file_to_edit()
    - get_value()
    - set_value()
    - unset_value()
    - save()
- TODO: nuances of ``load_only`` and ``get_file_to_edit``
- TODO: nuances of ``isolated``

Future Refactoring Ideas
========================

* Break up the ``Configuration`` class into 2 smaller classes, by use case
    * ``Command`` use-case (read only) -- ``ConfigurationReader``
    * ``pip config`` use-case (read / write) -- ``ConfigurationModifier`` (inherit from ``ConfigurationReader``)
* Eagerly populate ``Configuration._dictionary`` on load.

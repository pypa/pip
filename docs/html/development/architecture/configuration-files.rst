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

TODO: Figure out how to structure the initial part of this document.

Loading
-------

#. Determine configuration files to be used (built on top of :pypi:`appdirs`).
#. Load from all the configuration files.
    #. For each file, construct a ``RawConfigParser`` instance and read the
       file with it. Store the filename and parser for accessing / manipulating
       the file's contents later.
#. Load values stored in ``PIP_*`` environment variables.

The precedence of the various "configuration sources" is determined by
``Configuration._override_order``, and the precedence-respecting values are
lazily computed when values are accessed by a callee.

Saving
------

Once the configuration is loaded, it is saved by iterating through all the
"modified parser" pairs (filename and associated parser, that were modified
in-memory after the initial load), and writing the state of the parser to file.

-----

The remainder of this section is organized by documenting some of the
implementation details of the ``configuration`` module, in the following order:

* the :ref:`kinds <config-kinds>` enum,
* the :ref:`Configuration <configuration-class>` class,


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

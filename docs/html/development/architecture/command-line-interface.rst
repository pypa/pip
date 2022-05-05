======================
Command Line Interface
======================

The ``pip._internal.cli`` package is responsible for processing and providing
pip's command line interface. This package handles:

* CLI option definition and parsing
* autocompletion
* dispatching to the various commands
* utilities like progress bars and spinners

.. note::

    This section of the documentation is currently being written. pip
    developers welcome your help to complete this documentation. If you're
    interested in helping out, please let us know in the
    `tracking issue <https://github.com/pypa/pip/issues/6831>`_.


.. _cli-overview:

Overview
========

A ``ConfigOptionParser`` instance is used as the "main parser",
for parsing top level args.

``Command`` then uses another ``ConfigOptionParser`` instance, to parse command-specific args.

* TODO: How & where options are defined
  (cmdoptions, command-specific files).

* TODO: How & where arguments are processed.
  (main_parser, command-specific parser)

* TODO: How processed arguments are accessed.
  (attributes on argument to ``Command.run()``)

* TODO: How configuration and CLI "blend".
  (implemented in ``ConfigOptionParser``)

* TODO: progress bars and spinners

* TODO: quirks / standard practices / broad ideas.
  (avoiding lists in option def'n, special cased option value types,
  )


Future Refactoring Ideas
========================

* Change option definition to be a more declarative, consistent, static
  data-structure, replacing the current ``partial(Option, ...)`` form
* Move progress bar and spinner to a ``cli.ui`` subpackage
* Move all ``Command`` classes into a ``cli.commands`` subpackage
  (including base classes)

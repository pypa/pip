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

Command structure
-----------------

This section shows the class hierarchy from which every command's class will inherit
from.

`base_command.py <https://github.com/pypa/pip/blob/main/src/pip/_internal/cli/base_command.py>`_
defines the base ``Command`` class, from which every other command will inherit directly or
indirectly (see the *command tree* at the end of this section).

Using the ``ConfigOptionParser`` (see `Configuration and CLI "blend" <Configuration and CLI "blend"_>`_),
this class adds the general options and instantiates the *cmd_opts* group, where every other specific
option will be added if needed on each command's class. For those commands that define specific
options, like ``--dry-run`` on ``pip install`` command, the options must be added to *cmd_opts*
this is the job of *add_options* method), which will be automatically called on ``Command``'s initialization.

The base ``Command`` has the following methods:

.. py:class:: Command

  .. py:method:: main()

    Main method of the class, it's always called (as can be seen in main.py's
    `main <https://github.com/pypa/pip/blob/main/src/pip/_internal/cli/main.py#L46>`_).
    It's in charge of calling the specific ``run`` method of the class and handling the possible errors.

  .. py:method:: run()

    Abstract method where the actual action of a command is defined.

  .. py:method:: add_options()

    Optional method to insert additional options on a class, called on ``Command`` initialization.

Some commands have more specialized behavior, (see for example ``pip index``).
These commands instead will inherit from ``IndexGroupCommand``, which inherits from ``Command``
and  ``SessionCommandMixin`` to build build the pip session for the corresponding requests.

Lastly, ``RequirementCommand``, which inherits from ``IndexGroupCommand`` is the base class
for those commands which make use of requirements in any form, like ``pip install``.

In addition to the previous classes, a last mixin class must be mentioned, from which
``Command`` as well as ``SessionCommandMixin`` inherit: ``CommandContextMixIn``, in
charge of the command's context.

In the following command tree we can see the hierarchy defined for the different pip
commands, where each command is defined under the base class it inherits from:

| ``Command``
|  ├─ ``cache``, ``check``, ``completion``, ``configuration``, ``debug``, ``freeze``, ``hash``, ``help``, ``inspect``, ``show``, ``search``, ``uninstall``
|  └─ ``IndexGroupCommand``
|      ├─ ``index``, ``list``
|      └─ ``RequirementCommand``
|           └─ ``wheel``, ``download``, ``install``


Option definition
-----------------

The set of shared options are defined in `cmdoptions.py <https://github.com/pypa/pip/blob/main/src/pip/_internal/cli/cmdoptions.py>`_
module, as well as the *general options* and *package index options* groups of options
we see when we call a command's help, or the ``pip index``'s help message respectively.
All options are defined in terms of functions that return `optparse.Option <https://docs.python.org/3/library/optparse.html#optparse.Option>`_
instances once called, while specific groups of options, like *Config Options* for
``pip config`` are defined in each specific command file (see for example the
`configuration.py <https://github.com/pypa/pip/blob/main/src/pip/_internal/commands/configuration.py>`_).

Argument parsing
----------------

The main entrypoint for the application is defined in the ``main`` function in the
`main.py <https://github.com/pypa/pip/blob/main/src/pip/_internal/cli/main.py>`_ module.
This function is in charge of the `autocompletion <https://github.com/pypa/pip/blob/main/src/pip/_internal/cli/autocompletion.py>`_,
calling the ``parse_command`` function and creating and running the subprograms
via ``create_command``, on which the ``main`` method is called.

The ``parse_command`` is defined in the `main_parser.py <https://github.com/pypa/pip/blob/main/src/pip/_internal/cli/main_parser.py>`_
module, which defines the following two functions:

.. py:function:: parse_command()

  Function in charge of the initial parse of ``pip``'s program. Creates the main parser (see
  the next function ``create_main_parser``) to extract the general options
  and the remaining arguments. For example, running ``pip --timeout=5 install --user INITools``
  will split ``['--timeout=5']`` as general option and  ``['install', '--user', 'INITools']``
  as the remainder.

  At this step the program deals with the options ``--python``, ``--version``, ``pip``
  or ``pip help``. If neither of the previous options is found, it tries to extract the command
  name and arguments.

.. py:function:: create_main_parser()

  Creates the main parser (type ``pip`` in the console to see the description of the
  program). The internal parser (`ConfigOptionParser <Configuration and CLI "blend"_>`_),
  adds the general option group and the list of commands coming from ``cmdoptions.py``
  at this point.

After the initial parsing is done, ``create_command`` is in charge of creating the appropriate
command using the information stored in `commands_dict <https://github.com/pypa/pip/blob/main/src/pip/_internal/commands/__init__.py>`_
variable, and calling its ``main`` method (see `Command structure <Command structure>`_).

A second argument parsing is done at each specific command (defined in the base ``Command`` class),
again using the ``ConfigOptionParser``.

Argument access
---------------

To access all the options and arguments, ``Command.run()`` takes
the options as `optparse.Values <https://docs.python.org/3/library/optparse.html#optparse.Values>`_
and a list of strings for the arguments (parsed in ``Command.main()``). The internal methods of
the base ``Command`` class are in charge of passing these variables after ``parse_args`` is
called for a specific command.

Configuration and CLI "blend"
-----------------------------

The base ``Command`` instantiates the class `ConfigOptionParser <https://github.com/pypa/pip/blob/main/src/pip/_internal/cli/parser.py>`_
which is in charge of the parsing process (via its parent class
`optparse.OptionParser <https://docs.python.org/3/library/optparse.html#optparse.OptionParser>`_).
Its main addition consists of the following function:

.. py:class:: ConfigOptionParser(OptionParser)

  .. py:method:: get_default_values()

    Overrides the original method to allow updating the defaults after the instantiation of the
    option parser.

It allows overriding the default options and arguments using the ``Configuration`` class
(more information can be found on :ref:`Configuration`) to include environment variables and
settings from configuration files.

Progress bars and spinners
--------------------------

There are two more modules in the ``cli`` subpackage in charge of showing the state of the
program.

* `progress_bars.py <https://github.com/pypa/pip/blob/main/src/pip/_internal/cli/progress_bars.py>`_

  This module contains the following function:

  .. py:function:: get_download_progress_renderer()

    It uses `rich <https://rich.readthedocs.io/en/stable/reference/progress.html#module-rich.progress>`_
    functionalities to render the download progress.

  This function (used in `download.py <https://github.com/pypa/pip/blob/main/src/pip/_internal/network/download.py>`_,
  inside the ``Downloader`` class), allows watching the download process when running
  ``pip install`` on *big* packages.

* `spinner.py <https://github.com/pypa/pip/blob/main/src/pip/_internal/cli/spinners.py>`_

  The main function of this module is:

  .. py:function:: open_spinner()

    It yields the appropriate type of spinner, which is used in ``call_subprocess``
    function, inside `subprocess.py <https://github.com/pypa/pip/blob/main/src/pip/_internal/utils/subprocess.py>`_
    module, so the user can see there is a program running.

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

.. _`Configuration`:

Configuration
=================

Config file
------------

pip allows you to set all command line option defaults in a standard ini
style config file.

The names and locations of the configuration files vary slightly across
platforms.

* On Unix and Mac OS X the configuration file is: :file:`$HOME/.pip/pip.conf`
* On Windows, the configuration file is: :file:`%HOME%\\pip\\pip.ini`

You can set a custom path location for the config file using the environment variable ``PIP_CONFIG_FILE``.

The names of the settings are derived from the long command line option, e.g.
if you want to use a different package index (``--index-url``) and set the
HTTP timeout (``--default-timeout``) to 60 seconds your config file would
look like this:

.. code-block:: ini

    [global]
    timeout = 60
    index-url = http://download.zope.org/ppix

Each subcommand can be configured optionally in its own section so that every
global setting with the same name will be overridden; e.g. decreasing the
``timeout`` to ``10`` seconds when running the `freeze`
(`Freezing Requirements <./#freezing-requirements>`_) command and using
``60`` seconds for all other commands is possible with:

.. code-block:: ini

    [global]
    timeout = 60

    [freeze]
    timeout = 10


Boolean options like ``--ignore-installed`` or ``--no-dependencies`` can be
set like this:

.. code-block:: ini

    [install]
    ignore-installed = true
    no-dependencies = yes

Appending options like ``--find-links`` can be written on multiple lines:

.. code-block:: ini

    [global]
    find-links =
        http://download.example.com

    [install]
    find-links =
        http://mirror1.example.com
        http://mirror2.example.com


Environment Variables
---------------------

pip's command line options can be set with
environment variables using the format ``PIP_<UPPER_LONG_NAME>`` . Dashes (``-``) have to replaced with underscores (``_``).

For example, to set the default timeout::

    export PIP_DEFAULT_TIMEOUT=60

This is the same as passing the option to pip directly::

    pip --default-timeout=60 [...]

To set options that can be set multiple times on the command line, just add spaces in between values. For example::

    export PIP_FIND_LINKS="http://mirror1.example.com http://mirror2.example.com"

is the same as calling::

    pip install --find-links=http://mirror1.example.com --find-links=http://mirror2.example.com


Config Precedence
-----------------

Command line options have precedence over environment variables, which have precedence over the config file.

Within the config file, command specific sections have precedence over the global section.

Examples:

- ``--host=foo`` overrides ``PIP_HOST=foo``
- ``PIP_HOST=foo`` overrides a config file with ``[global] host = foo``
- A command specific section in the config file ``[<command>] host = bar``
  overrides the option with same name in the ``[global]`` config file section


Command Completion
------------------

pip comes with support for command line completion in bash and zsh.

To setup for bash::

    $ pip completion --bash >> ~/.profile

To setup for zsh::

    $ pip completion --zsh >> ~/.zprofile

Alternatively, you can use the result of the ``completion`` command
directly with the eval function of you shell, e.g. by adding the following to your startup file::

    eval "`pip completion --bash`"


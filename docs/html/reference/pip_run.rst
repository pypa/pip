pip run
-------

.. contents::

Usage
*****

.. pip-command-usage:: run

Description
***********

.. pip-command-description:: run


Overview
++++++++

Pip run in a specialized invocation of pip install that makes
packages available only for the duration of a single Python invocation
for one-off needs. The command is based on the
`pip-run project <https://pypi.org/project/pip-run>`_.

Argument Handling
+++++++++++++++++

As a wrapper around ``pip install``, the arguments to ``run`` are split into
two segments, separated by a double-dash (``--``). The arguments prior
to the ``--`` are passed directly to :ref:`pip install`, so should contain
requirements, requirments files, and index directives.

The arguments after the ``--`` are passed to a new Python interpreter in the
context of the installed dependencies.

For more details and examples, see the
`pip-run project <https://pypi.org/project/pip-run>`_.

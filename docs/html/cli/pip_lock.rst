
.. _`pip lock`:

========
pip lock
========



Usage
=====

.. tab:: Unix/macOS

   .. pip-command-usage:: lock "python -m pip"

.. tab:: Windows

   .. pip-command-usage:: lock "py -m pip"


Description
===========

.. pip-command-description:: lock

Options
=======

.. pip-command-options:: lock

.. pip-index-options:: lock


Examples
========

#. Emit a ``pylock.toml`` for the the project in the current directory

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip lock -e .

   .. tab:: Windows

      .. code-block:: shell

         py -m pip lock -e .

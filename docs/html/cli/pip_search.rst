.. _`pip search`:

==========
pip search
==========



Usage
=====

.. tab:: Unix/macOS

   .. pip-command-usage:: search "python -m pip"

.. tab:: Windows

   .. pip-command-usage:: search "py -m pip"


Description
===========

.. attention::
    PyPI no longer supports ``pip search`` (or XML-RPC search). Please use https://pypi.org/search (via a browser)
    instead. See https://warehouse.pypa.io/api-reference/xml-rpc.html#deprecated-methods for more information.

    However, XML-RPC search (and this command) may still be supported by indexes other than PyPI.

.. pip-command-description:: search


Options
=======

.. pip-command-options:: search


Examples
========

#. Search for "peppercorn"

   .. tab:: Unix/macOS

      .. code-block:: console

         $ python -m pip search peppercorn
         pepperedform    - Helpers for using peppercorn with formprocess.
         peppercorn      - A library for converting a token stream into [...]

   .. tab:: Windows

      .. code-block:: console

         C:\> py -m pip search peppercorn
         pepperedform    - Helpers for using peppercorn with formprocess.
         peppercorn      - A library for converting a token stream into [...]

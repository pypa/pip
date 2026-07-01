.. _`pip index`:

===========
pip index
===========



Usage
=====

.. tab:: Unix/macOS

   .. pip-command-usage:: index "python -m pip"

.. tab:: Windows

   .. pip-command-usage:: index "py -m pip"


Description
===========

.. pip-command-description:: index



Options
=======

.. pip-command-options:: index

.. pip-index-options:: index

.. pip-package-selection-options:: index


Examples
========

#. Search for "peppercorn" versions

   .. tab:: Unix/macOS

      .. code-block:: console

         $ python -m pip index versions peppercorn
         peppercorn (0.6)
         Available versions: 0.6, 0.5, 0.4, 0.3, 0.2, 0.1


   .. tab:: Windows

      .. code-block:: console

         C:\> py -m pip index peppercorn
         peppercorn (0.6)
         Available versions: 0.6, 0.5, 0.4, 0.3, 0.2, 0.1

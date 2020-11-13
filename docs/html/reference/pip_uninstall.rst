.. _`pip uninstall`:

=============
pip uninstall
=============



Usage
=====

.. tab:: Unix/macOS

   .. pip-command-usage:: uninstall "python -m pip"

.. tab:: Windows

   .. pip-command-usage:: uninstall "py -m pip"


Description
===========

.. pip-command-description:: uninstall


Options
=======

.. pip-command-options:: uninstall


Examples
========

#. Uninstall a package.

   .. tab:: Unix/macOS

      .. code-block:: console

         $ python -m pip uninstall simplejson
         Uninstalling simplejson:
            /home/me/env/lib/python2.7/site-packages/simplejson
            /home/me/env/lib/python2.7/site-packages/simplejson-2.2.1-py2.7.egg-info
         Proceed (y/n)? y
            Successfully uninstalled simplejson

   .. tab:: Windows

      .. code-block:: console

         C:\> py -m pip uninstall simplejson
         Uninstalling simplejson:
            /home/me/env/lib/python2.7/site-packages/simplejson
            /home/me/env/lib/python2.7/site-packages/simplejson-2.2.1-py2.7.egg-info
         Proceed (y/n)? y
            Successfully uninstalled simplejson


.. _`pip freeze`:

==========
pip freeze
==========


Usage
=====

.. tab:: Unix/macOS

   .. pip-command-usage:: freeze "python -m pip"

.. tab:: Windows

   .. pip-command-usage:: freeze "py -m pip"


Description
===========

.. pip-command-description:: freeze


Options
=======

.. pip-command-options:: freeze




.. note::

   By default, ``pip freeze`` omits pip's own bootstrap tools (``pip``,
   ``setuptools``, and ``wheel``) to keep the output focused on project
   dependencies. Use ``--all`` to include these as well, which is helpful when
   capturing a full environment snapshot. Remember that ``pip freeze`` only
   reports what is currently installed; it is not a lockfile or solver result.


Examples
========
         env1\bin\python -m pip freeze > requirements.txt
         env2\bin\python -m pip install -r requirements.txt

#. Compare default output with ``--all``.

   .. tab:: Unix/macOS

      .. code-block:: console

         $ python -m pip freeze
         certifi==...
         idna==...
         requests==...
         urllib3==...

         $ python -m pip freeze --all
         certifi==...
         idna==...
         requests==...
         urllib3==...
         pip==...
         setuptools==...
         wheel==...

   .. tab:: Windows

      .. code-block:: console

         C:\> py -m pip freeze
         certifi==...
         idna==...
         requests==...
         urllib3==...

         C:\> py -m pip freeze --all
         certifi==...
         idna==...
         requests==...
         urllib3==...
         pip==...
         setuptools==...
         wheel==...

Fixing "Permission denied:" errors
==================================

The purpose of this section of documentation is to provide practical
suggestions to users seeing a `"Permission denied" error <https://github.com/pypa/pip/issues/8418>`__ on ``pip freeze``.

This error occurs, for instance, when the command is installed only for another
user, and the current user doesn't have the permission to execute the other
user's command.

To solve that issue, you can try one of the following:

- Install the command for yourself (e.g. in your home directory).
- Ask the system admin to allow this command for all users.
- Check and correct the PATH variable of your own environment.
- Check the `ACL (Access-Control List) <https://en.wikipedia.org/wiki/Access-control_list>`_ for this command.

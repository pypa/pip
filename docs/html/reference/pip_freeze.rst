
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


Examples
========

#. Generate output suitable for a requirements file.

   .. tab:: Unix/macOS

      .. code-block:: console

         $ python -m pip freeze
         docutils==0.11
         Jinja2==2.7.2
         MarkupSafe==0.19
         Pygments==1.6
         Sphinx==1.2.2

   .. tab:: Windows

      .. code-block:: console

         C:\> py -m pip freeze
         docutils==0.11
         Jinja2==2.7.2
         MarkupSafe==0.19
         Pygments==1.6
         Sphinx==1.2.2

#. Generate a requirements file and then install from it in another environment.

   .. tab:: Unix/macOS

      .. code-block:: shell

         env1/bin/python -m pip freeze > requirements.txt
         env2/bin/python -m pip install -r requirements.txt

   .. tab:: Windows

      .. code-block:: shell

         env1\bin\python -m pip freeze > requirements.txt
         env2\bin\python -m pip install -r requirements.txt


Fixing permission denied
========================

The purpose of this section of documentation is to provide practical suggestions to
pip users who encounter an error where ``pip freeze`` issue a permission error
during requirements info extraction. See issue:
`pip freeze returns "Permission denied: 'hg'" <https://github.com/pypa/pip/issues/8418>`_.

When you get a "No permission to execute 'cmd'" error, where *cmd* is 'bzr',
'git', 'hg' or 'svn', it means that the VCS command exists, but you have
no permission to execute it.

This error occurs, for instance, when the command is installed only for another user.
So, the current user don't have permission to execute the other user command.

To solve that issue, you can:

- install the command for yourself (local installation),
- ask admin support to install for all users (global installation),
- check and correct the PATH variable of your own environment,
- check the ACL (Access Control List) for this command.


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

   By default, ``pip freeze`` omits some bootstrap tooling so the output focuses on
   your project’s dependencies. In Python **3.11 and earlier**, this means ``pip``,
   ``setuptools`` and ``wheel`` are skipped by default; in Python **3.12 and later**,
   only ``pip`` is skipped. Use ``--all`` to include those entries as well when you
   need a complete environment snapshot. Note that ``pip freeze`` reports what is
   installed—it does **not** compute a lockfile or a solver result.


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

#. Compare default output with ``--all``.

   The exact entries vary by Python version; on Python 3.12 and later only
   ``pip`` is omitted by default.

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

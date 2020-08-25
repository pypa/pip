
.. _`pip freeze`:

==========
pip freeze
==========

.. contents::


Usage
=====

.. tabs::

   .. group-tab:: Unix/macOS

      .. pip-command-usage:: freeze "python -m pip"

   .. group-tab:: Windows

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

   .. tabs::

      .. group-tab:: Unix/macOS

         .. code-block:: console

            $ python -m pip freeze
            docutils==0.11
            Jinja2==2.7.2
            MarkupSafe==0.19
            Pygments==1.6
            Sphinx==1.2.2

      .. group-tab:: Windows

         .. code-block:: console

            C:\> py -m pip freeze
            docutils==0.11
            Jinja2==2.7.2
            MarkupSafe==0.19
            Pygments==1.6
            Sphinx==1.2.2


#. Generate a requirements file and then install from it in another environment.

   .. tabs::

      .. group-tab:: Unix/macOS

         .. code-block:: shell

            env1/bin/python -m pip freeze > requirements.txt
            env2/bin/python -m pip install -r requirements.txt

      .. group-tab:: Windows

         .. code-block:: shell

            env1\bin\python -m pip freeze > requirements.txt
            env2\bin\python -m pip install -r requirements.txt

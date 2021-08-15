.. _`pip list`:

========
pip list
========



Usage
=====

.. tab:: Unix/macOS

   .. pip-command-usage:: list "python -m pip"

.. tab:: Windows

   .. pip-command-usage:: list "py -m pip"


Description
===========

.. pip-command-description:: list


Options
=======

.. pip-command-options:: list

.. pip-index-options:: list


Examples
========

#. List installed packages (with the default column formatting).

   .. tab:: Unix/macOS

      .. code-block:: console

         $ python -m pip list
         Package Version
         ------- -------
         docopt  0.6.2
         idlex   1.13
         jedi    0.9.0

   .. tab:: Windows

      .. code-block:: console

         C:\> py -m pip list
         Package Version
         ------- -------
         docopt  0.6.2
         idlex   1.13
         jedi    0.9.0

#. List outdated packages with column formatting.

   .. tab:: Unix/macOS

      .. code-block:: console

         $ python -m pip list --outdated --format columns
         Package    Version Latest Type
         ---------- ------- ------ -----
         retry      0.8.1   0.9.1  wheel
         setuptools 20.6.7  21.0.0 wheel

   .. tab:: Windows

      .. code-block:: console

         C:\> py -m pip list --outdated --format columns
         Package    Version Latest Type
         ---------- ------- ------ -----
         retry      0.8.1   0.9.1  wheel
         setuptools 20.6.7  21.0.0 wheel

#. List packages that are not dependencies of other packages. Can be combined with
   other options.

   .. tab:: Unix/macOS

      .. code-block:: console

         $ python -m pip list --outdated --not-required
         Package  Version Latest Type
         -------- ------- ------ -----
         docutils 0.14    0.17.1 wheel

   .. tab:: Windows

      .. code-block:: console

         C:\> py -m pip list --outdated --not-required
         Package  Version Latest Type
         -------- ------- ------ -----
         docutils 0.14    0.17.1 wheel

#. Use json formatting

   .. tab:: Unix/macOS

      .. code-block:: console

         $ python -m pip list --format=json
         [{'name': 'colorama', 'version': '0.3.7'}, {'name': 'docopt', 'version': '0.6.2'}, ...

   .. tab:: Windows

      .. code-block:: console

         C:\> py -m pip list --format=json
         [{'name': 'colorama', 'version': '0.3.7'}, {'name': 'docopt', 'version': '0.6.2'}, ...

#. Use freeze formatting

   .. tab:: Unix/macOS

      .. code-block:: console

         $ python -m pip list --format=freeze
         colorama==0.3.7
         docopt==0.6.2
         idlex==1.13
         jedi==0.9.0

   .. tab:: Windows

      .. code-block:: console

         C:\> py -m pip list --format=freeze
         colorama==0.3.7
         docopt==0.6.2
         idlex==1.13
         jedi==0.9.0

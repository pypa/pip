.. _`pip list`:

========
pip list
========

.. contents::


Usage
=====

.. tabs::

   .. group-tab:: Unix/macOS

      .. pip-command-usage:: list "python -m pip"

   .. group-tab:: Windows

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

#. List installed packages.

   .. tabs::

      .. group-tab:: Unix/macOS

         .. code-block:: console

            $ python -m pip list
            docutils (0.10)
            Jinja2 (2.7.2)
            MarkupSafe (0.18)
            Pygments (1.6)
            Sphinx (1.2.1)

      .. group-tab:: Windows

         .. code-block:: console

            C:\> py -m pip list
            docutils (0.10)
            Jinja2 (2.7.2)
            MarkupSafe (0.18)
            Pygments (1.6)
            Sphinx (1.2.1)

#. List outdated packages (excluding editables), and the latest version available.

   .. tabs::

      .. group-tab:: Unix/macOS

         .. code-block:: console

            $ python -m pip list --outdated
            docutils (Current: 0.10 Latest: 0.11)
            Sphinx (Current: 1.2.1 Latest: 1.2.2)

      .. group-tab:: Windows

         .. code-block:: console

            C:\> py -m pip list --outdated
            docutils (Current: 0.10 Latest: 0.11)
            Sphinx (Current: 1.2.1 Latest: 1.2.2)


#. List installed packages with column formatting.

   .. tabs::

      .. group-tab:: Unix/macOS

         .. code-block:: console

            $ python -m pip list --format columns
            Package Version
            ------- -------
            docopt  0.6.2
            idlex   1.13
            jedi    0.9.0

      .. group-tab:: Windows

         .. code-block:: console

            C:\> py -m pip list --format columns
            Package Version
            ------- -------
            docopt  0.6.2
            idlex   1.13
            jedi    0.9.0

#. List outdated packages with column formatting.

   .. tabs::

      .. group-tab:: Unix/macOS

         .. code-block:: console

            $ python -m pip list -o --format columns
            Package    Version Latest Type
            ---------- ------- ------ -----
            retry      0.8.1   0.9.1  wheel
            setuptools 20.6.7  21.0.0 wheel

      .. group-tab:: Windows

         .. code-block:: console

            C:\> py -m pip list -o --format columns
            Package    Version Latest Type
            ---------- ------- ------ -----
            retry      0.8.1   0.9.1  wheel
            setuptools 20.6.7  21.0.0 wheel

#. List packages that are not dependencies of other packages. Can be combined with
   other options.

   .. tabs::

      .. group-tab:: Unix/macOS

         .. code-block:: console

            $ python -m pip list --outdated --not-required
            docutils (Current: 0.10 Latest: 0.11)

      .. group-tab:: Windows

         .. code-block:: console

            C:\> py -m pip list --outdated --not-required
            docutils (Current: 0.10 Latest: 0.11)

#. Use legacy formatting

   .. tabs::

      .. group-tab:: Unix/macOS

         .. code-block:: console

            $ python -m pip list --format=legacy
            colorama (0.3.7)
            docopt (0.6.2)
            idlex (1.13)
            jedi (0.9.0)

      .. group-tab:: Windows

         .. code-block:: console

            C:\> py -m pip list --format=legacy
            colorama (0.3.7)
            docopt (0.6.2)
            idlex (1.13)
            jedi (0.9.0)

#. Use json formatting

   .. tabs::

      .. group-tab:: Unix/macOS

         .. code-block:: console

            $ python -m pip list --format=json
            [{'name': 'colorama', 'version': '0.3.7'}, {'name': 'docopt', 'version': '0.6.2'}, ...

      .. group-tab:: Windows

         .. code-block:: console

            C:\> py -m pip list --format=json
            [{'name': 'colorama', 'version': '0.3.7'}, {'name': 'docopt', 'version': '0.6.2'}, ...

#. Use freeze formatting

   .. tabs::

      .. group-tab:: Unix/macOS

         .. code-block:: console

            $ python -m pip list --format=freeze
            colorama==0.3.7
            docopt==0.6.2
            idlex==1.13
            jedi==0.9.0

      .. group-tab:: Windows

         .. code-block:: console

            C:\> py -m pip list --format=freeze
            colorama==0.3.7
            docopt==0.6.2
            idlex==1.13
            jedi==0.9.0

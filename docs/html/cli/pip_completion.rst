.. _`pip completion`:

==============
pip completion
==============


Usage
=====

.. tab:: Unix/macOS

   .. pip-command-usage:: completion "python -m pip"

.. tab:: Windows

   .. pip-command-usage:: completion "py -m pip"


Description
===========

.. pip-command-description:: completion

Options
=======

.. pip-command-options:: completion


Example Setups
==============

Enable pip tab completion in your shell:

.. tab:: Bash

   Add the following line to your ~/.bashrc:

   .. code-block:: console

      echo 'eval "$(python -m pip completion --bash)"' >> ~/.bashrc

   Then reload your shell or run ``source ~/.bashrc`` to enable it immediately.

.. tab:: Zsh

   Add the following line to your ~/.zshrc:

   .. code-block:: console

      echo 'eval "$(python -m pip completion --zsh)"' >> ~/.zshrc

   Reload your shell or run ``source ~/.zshrc``.

.. tab:: PowerShell

   Add the following line to your PowerShell profile:

   .. code-block:: powershell

      python -m pip completion --powershell | Out-String | Invoke-Expression

   Restart your PowerShell session for the changes to take effect.

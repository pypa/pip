.. _`Installation`:

============
Installation
============

Do I need to install pip?
=========================

pip is already installed if you are using Python 2 >=2.7.9 or Python 3 >=3.4
downloaded from `python.org <https://www.python.org>`_ or if you are working
in a :ref:`Virtual Environment <pypug:Creating and using Virtual Environments>`
created by :ref:`pypug:virtualenv` or :ref:`venv <pypug:venv>`. Just make sure
to :ref:`upgrade pip <Upgrading pip>`.

Use the following command to check whether pip is installed:

.. tab:: Unix/macOS

   .. code-block:: console

      $ python -m pip --version
      pip X.Y.Z from .../site-packages/pip (python X.Y)

.. tab:: Windows

   .. code-block:: console

      C:\> py -m pip --version
      pip X.Y.Z from ...\site-packages\pip (python X.Y)

Using Linux Package Managers
============================

.. warning::

   If you installed Python from a package manager on Linux, you should always
   install pip for that Python installation using the same source.

See `pypug:Installing pip/setuptools/wheel with Linux Package Managers <https://packaging.python.org/guides/installing-using-linux-tools/>`_
in the Python Packaging User Guide.

Here are ways to contact a few Linux package maintainers if you run into
problems:

* `Deadsnakes PPA <https://github.com/deadsnakes/issues>`_
* `Debian Python Team <https://wiki.debian.org/Teams/PythonTeam>`_ (for general
  issues related to ``apt``)
* `Red Hat Bugzilla <https://bugzilla.redhat.com/>`_

pip developers do not have control over how Linux distributions handle pip
installations, and are unable to provide solutions to related issues in
general.

Using ensurepip
===============

Python >=3.4 can self-bootstrap pip with the built-in
:ref:`ensurepip <pypug:ensurepip>` module. Refer to the standard library
documentation for more details. Make sure to :ref:`upgrade pip <Upgrading pip>`
after ``ensurepip`` installs pip.

See the `Using Linux Package Managers`_ section if your Python reports
``No module named ensurepip`` on Debian and derived systems (e.g. Ubuntu).


.. _`get-pip`:

Installing with get-pip.py
==========================

.. warning::

   Be cautious if you are using a Python install that is managed by your operating
   system or another package manager. ``get-pip.py`` does not coordinate with
   those tools, and may leave your system in an inconsistent state.

To manually install pip, securely [1]_ download ``get-pip.py`` by following
this link: `get-pip.py
<https://bootstrap.pypa.io/get-pip.py>`_. Alternatively, use ``curl``::

 curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py

Then run the following command in the folder where you
have downloaded ``get-pip.py``:

.. tab:: Unix/macOS

   .. code-block:: shell

      python get-pip.py

.. tab:: Windows

   .. code-block:: shell

      py get-pip.py

``get-pip.py`` also installs :ref:`pypug:setuptools` [2]_ and :ref:`pypug:wheel`
if they are not already. :ref:`pypug:setuptools` is required to install
:term:`source distributions <pypug:Source Distribution (or "sdist")>`.  Both are
required in order to build a :ref:`Wheel cache` (which improves installation
speed), although neither are required to install pre-built :term:`wheels
<pypug:Wheel>`.

.. note::

   The get-pip.py script is supported on the same python version as pip.
   For the now unsupported Python 2.6, alternate script is available
   `here <https://bootstrap.pypa.io/2.6/get-pip.py>`__.


get-pip.py options
------------------

.. option:: --no-setuptools

    If set, do not attempt to install :ref:`pypug:setuptools`

.. option:: --no-wheel

    If set, do not attempt to install :ref:`pypug:wheel`


``get-pip.py`` allows :ref:`pip install options <pip
install Options>` and the :ref:`general options <General Options>`. Below are
some examples:

Install from local copies of pip and setuptools:

.. tab:: Unix/macOS

   .. code-block:: shell

      python get-pip.py --no-index --find-links=/local/copies

.. tab:: Windows

   .. code-block:: shell

      py get-pip.py --no-index --find-links=/local/copies

Install to the user site [3]_:

.. tab:: Unix/macOS

   .. code-block:: shell

      python get-pip.py --user

.. tab:: Windows

   .. code-block:: shell

      py get-pip.py --user

Install behind a proxy:

.. tab:: Unix/macOS

   .. code-block:: shell

      python get-pip.py --proxy="http://[user:passwd@]proxy.server:port"

.. tab:: Windows

   .. code-block:: shell

      py get-pip.py --proxy="http://[user:passwd@]proxy.server:port"

``get-pip.py`` can also be used to install a specified combination of ``pip``,
``setuptools``, and ``wheel`` using the same requirements syntax as pip:

.. tab:: Unix/macOS

   .. code-block:: shell

      python get-pip.py pip==9.0.2 wheel==0.30.0 setuptools==28.8.0

.. tab:: Windows

   .. code-block:: shell

      py get-pip.py pip==9.0.2 wheel==0.30.0 setuptools==28.8.0

.. _`Upgrading pip`:

Upgrading pip
=============

.. tab:: Unix/macOS

   .. code-block:: shell

      python -m pip install -U pip

.. tab:: Windows

   .. code-block:: shell

      py -m pip install -U pip


.. _compatibility-requirements:

Python and OS Compatibility
===========================

pip works with CPython versions 2.7, 3.5, 3.6, 3.7, 3.8 and also PyPy.

This means pip works on the latest patch version of each of these minor
versions. Previous patch versions are supported on a best effort approach.

pip works on Unix/Linux, macOS, and Windows.


----

.. [1] "Secure" in this context means using a modern browser or a
       tool like ``curl`` that verifies SSL certificates when downloading from
       https URLs.

.. [2] Beginning with pip v1.5.1, ``get-pip.py`` stopped requiring setuptools to
       be installed first.

.. [3] The pip developers are considering making ``--user`` the default for all
       installs, including ``get-pip.py`` installs of pip, but at this time,
       ``--user`` installs for pip itself, should not be considered to be fully
       tested or endorsed. For discussion, see `Issue 1668
       <https://github.com/pypa/pip/issues/1668>`_.

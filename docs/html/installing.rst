.. _`Installation`:

Installation
============

Do I need to install pip?
-------------------------

pip is already installed if you are using Python 2 >=2.7.9 or Python 3 >=3.4
downloaded from `python.org <https://www.python.org>`_ or if you are working
in a :ref:`Virtual Environment <pypug:Creating and using Virtual Environments>`
created by :ref:`pypug:virtualenv` or :ref:`pyvenv <pypug:venv>`.
Just make sure to :ref:`upgrade pip <Upgrading pip>`.


.. _`get-pip`:

Installing with get-pip.py
--------------------------

To install pip, securely download `get-pip.py
<https://bootstrap.pypa.io/get-pip.py>`_. [1]_::

 curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py

Then run the following::

 python get-pip.py


.. warning::

   Be cautious if you are using a Python install that is managed by your operating
   system or another package manager. ``get-pip.py`` does not coordinate with
   those tools, and may leave your system in an inconsistent state.

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
~~~~~~~~~~~~~~~~~~~

.. option:: --no-setuptools

    If set, do not attempt to install :ref:`pypug:setuptools`

.. option:: --no-wheel

    If set, do not attempt to install :ref:`pypug:wheel`


``get-pip.py`` allows :ref:`pip install options <pip
install Options>` and the :ref:`general options <General Options>`. Below are
some examples:

Install from local copies of pip and setuptools::

  python get-pip.py --no-index --find-links=/local/copies

Install to the user site [3]_::

  python get-pip.py --user

Install behind a proxy::

  python get-pip.py --proxy="http://[user:passwd@]proxy.server:port"

``get-pip.py`` can also be used to install a specified combination of ``pip``,
``setuptools``, and ``wheel`` using the same requirements syntax as ``pip``::

  python get-pip.py pip==9.0.2 wheel==0.30.0 setuptools==28.8.0


Using Linux Package Managers
----------------------------

See :ref:`pypug:Installing pip/setuptools/wheel with Linux Package Managers` in
the `Python Packaging User Guide
<https://packaging.python.org/en/latest/current/>`_.

.. _`Upgrading pip`:

Upgrading pip
-------------

On Linux or macOS::

 pip install -U pip


On Windows [4]_::

 python -m pip install -U pip


.. _compatibility-requirements:

Python and OS Compatibility
---------------------------

pip works with CPython versions 2.7, 3.4, 3.5, 3.6, 3.7 and also pypy.

This means pip works on the latest patch version of each of these minor
versions. Previous patch versions are supported on a best effort approach.

pip works on Unix/Linux, macOS, and Windows.


----

.. [1] "Secure" in this context means using a modern browser or a
       tool like `curl` that verifies SSL certificates when downloading from
       https URLs.

.. [2] Beginning with pip v1.5.1, ``get-pip.py`` stopped requiring setuptools to
       be installed first.

.. [3] The pip developers are considering making ``--user`` the default for all
       installs, including ``get-pip.py`` installs of pip, but at this time,
       ``--user`` installs for pip itself, should not be considered to be fully
       tested or endorsed. For discussion, see `Issue 1668
       <https://github.com/pypa/pip/issues/1668>`_.

.. [4] https://github.com/pypa/pip/issues/1299

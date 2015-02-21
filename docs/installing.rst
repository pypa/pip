.. _`Installation`:

Installation
============

Python & OS Support
-------------------

pip works with CPython versions 2.6, 2.7, 3.2, 3.3, 3.4 and also pypy.

pip works on Unix/Linux, OS X, and Windows.

.. note::

  Python 2.5 was supported through v1.3.1, and Python 2.4 was supported through v1.1.

pip included with Python
------------------------
Python 2.7.9 and later (on the python2 series), and Python 3.4
and later include pip by default [1]_, so you may have pip already.

.. _`get-pip`:

Install pip
-----------

To install pip, securely download `get-pip.py
<https://bootstrap.pypa.io/get-pip.py>`_. [2]_

Then run the following (which may require administrator access):

::

 python get-pip.py

If `setuptools`_ is not already installed, ``get-pip.py`` will install
`setuptools`_ for you. [3]_

To upgrade an existing `setuptools`_, run ``pip install -U setuptools``.

Additionally, ``get-pip.py`` supports using the :ref:`pip install options <pip
install Options>` and the :ref:`general options <General Options>`. Below are
some examples:

Install from local copies of pip and setuptools::

  python get-pip.py --no-index --find-links=/local/copies

Install to the user site [4]_::

  python get-pip.py --user

Install behind a proxy::

  python get-pip.py --proxy="[user:passwd@]proxy.server:port"


Upgrade pip
-----------

On Linux or OS X:

::

 pip install -U pip


On Windows [5]_:

::

 python -m pip install -U pip



Using OS Package Managers
-------------------------

On Linux, pip will generally be available for the system install of python using
the system package manager, although often the latest version will be
unavailable.

On Debian and Ubuntu::

   sudo apt-get install python-pip

On Fedora::

   sudo yum install python-pip


----

.. [1] https://docs.python.org/3/installing/

.. [2] "Secure" in this context means using a modern browser or a
       tool like `curl` that verifies SSL certificates when downloading from
       https URLs.

.. [3] Beginning with pip v1.5.1, ``get-pip.py`` stopped requiring setuptools to
       be installed first.

.. [4] The pip developers are considering making ``--user`` the default for all
       installs, including ``get-pip.py`` installs of pip, but at this time,
       ``--user`` installs for pip itself, should not be considered to be fully
       tested or endorsed. For discussion, see `Issue 1668
       <https://github.com/pypa/pip/issues/1668>`_.

.. [5] https://github.com/pypa/pip/issues/1299

.. _setuptools: https://pypi.python.org/pypi/setuptools
.. _distribute: https://pypi.python.org/pypi/distribute

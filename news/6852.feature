Cache wheels that ``pip wheel`` built locally, matching what
``pip install`` does. This particularly helps performance in workflows where
``pip wheel`` is used for `building before installing
<https://pip.pypa.io/en/stable/user_guide/#installing-from-local-packages>`_.
Users desiring the original behavior can use ``pip wheel --no-cache-dir``.

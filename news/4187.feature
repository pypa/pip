Allow PEP 508 URL requirements to be used as dependencies.

As a security measure, pip will raise an exception when installing packages from
PyPI if those packages depend on packages not also hosted on PyPI.
In the future, PyPI will block uploading packages with such external URL dependencies directly.

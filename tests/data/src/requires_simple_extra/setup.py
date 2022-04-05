from setuptools import setup

setup(
    name="requires_simple_extra",
    version="0.1",
    py_modules=["requires_simple_extra"],
    extras_require={"extra": ["simple==1.0"]},
)

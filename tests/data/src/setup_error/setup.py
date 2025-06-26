from setuptools import setup

# This is to get an error that originates from setuptools, which generates a
# decently sized output.
setup(
    cmdclass={
        "egg_info": "<make-me-fail>",
        "install": "<make-me-fail>",
        "bdist_wheel": "<make-me-fail>",
    }
)

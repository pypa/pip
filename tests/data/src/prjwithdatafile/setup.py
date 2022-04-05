from setuptools import setup

setup(
    name="prjwithdatafile",
    version="1.0",
    packages=["prjwithdatafile"],
    data_files=[
        (r"packages1", ["prjwithdatafile/README.txt"]),
        (r"packages2", ["prjwithdatafile/README.txt"]),
    ],
)

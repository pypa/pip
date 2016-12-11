# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name='pip_issue_4092',
    version="1.0",
    packages=['pip_issue_4092'],
    data_files=[
        (r'packages1', ['pip_issue_4092/README.txt']),
        (r'packages2', ['pip_issue_4092/README.txt'])
    ]
)

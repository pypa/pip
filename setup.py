import sys

from setuptools import setup


setup(
    package_data={
        "pip._vendor.certifi": ["*.pem"],
        "pip._vendor.requests": ["*.pem"],
        "pip._vendor.distlib._backport": ["sysconfig.cfg"],
        "pip._vendor.distlib": ["t32.exe", "t64.exe", "w32.exe", "w64.exe"],
    },
    entry_points={
        "console_scripts": [
            "pip=pip._internal:main",
            "pip%s=pip._internal:main" % sys.version_info[:1],
            "pip%s.%s=pip._internal:main" % sys.version_info[:2],
        ],
    },
)

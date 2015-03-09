from setuptools import setup, find_packages

version = '0.1.2'

setup(
    name='django-wikiapp',
    version=version,
    description=("A simple pluggable wiki application for Django"
                 " with revision and multiple markup support."),
    classifiers=[
        "Framework :: Django",
        "Programming Language :: Python",
        "Environment :: Web Environment",
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
    ],
    keywords='wiki,django',
    author='Eduardo de Oliveira Padoan',
    author_email='eduardo.padoan@gmail.com',
    url='http://launchpad.net/django-wikiapp/',
    license='BSD',
    packages=find_packages(),
    zip_safe=False,
    package_data = {
        'wiki': [
            'media/*.css',
            'templates/*/*.html',
            'templates/notification/*/*',
        ],
    }
)

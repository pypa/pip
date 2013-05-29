from setuptools import setup, find_packages

version = '0.1'

setup(name='FSPkg',
      version=version,
      description="File system test package",
      long_description="""\
File system test package""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='pip tests',
      author='pip',
      author_email='pip@openplans.org',
      url='http://pip.openplans.org',
      license='',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )

# How Users Understand pip

## Problem

We want to understand how pip's users understand pip as a tool: what they think it is and what it does.

[Skip to recommendations](#recommendations)

## Research

In order to capture participants mental models of pip and how package management works, we asked participants the following questions:

- In your own words, explain what pip is
- In your own words, explain what happens when pip installs a software package
- In your own words, explain what a Python package dependency is

When we talk about mental models, we talk about "deep" or "shallow" mental models. When a user has a deep mental models of something, their have a deep understanding with a lot of detail, shallow models are the opposite.

In order to evaluate those mental models - do they match the reality of pip and package management - we worked with the maintainers to identify 1. pip's behaviours and activities (18 aspects), and 2. the aspects of package dependencies (13), and what a Python package dependency is (10). We then scored participants' answers against those.

## Results

The analysis focused on participants with between 2 and 10 years of Python experience.

Over 90% of participants did not have a deep understanding of pip - with limited understanding of what pip is, what it does during the install process, and of package management in general.
However, while participants' understanding was low, only 4 participants had factually incorrect understandings of what pip is and does.

Participants had a slightly deeper understanding of what happens during a pip install process. The most in depth answer included 7 of the 13 identified aspects. The median was 3. Answers focused on resolving dependencies, finding possible package names, downloading assets and installing the package.

Participants' understanding of software dependencies was again shallow - the most in depth answer included 8 identified aspects. The median was 3. Answers focused on the fact that software dependencies were a result of code reuse, that constraining package versions reduced the possibility of dependency conflicts.

The full data is available in[ this spreadsheet](https://docs.google.com/spreadsheets/d/1HBiNyehaILxhzZKWcBavkKXDzJr6gIt_Y8Jm8RRgJYg/edit#gid=0).

### Responses to "In your own words, explain what pip is"

> "pip is a standard command-line tool for managing python packages. It has three primary functions: (1) obtaining & caching python packages and/or their dependencies from a repository (typically pypi), (2) building (if needed) and installing python packages--and related dependencies--to a 'site-packages' location in the python path, and (optionally) (3) uninstalling previously-installed packages." **- participant 242608909 (Scientist, Professor in the Earth and Atmospheric Sciences Department, using Python for 7 - 10 years)**

> "Pip is a package management system for python. Kind of like apt in linux, it can be used to install packages in public or private repositories into the current version or environment of Python that invoked the pip command." **- participant 240364032 (Professional software developer using Python for 7-10 years)**

> "pip allows to install/update remove python libraries in your environment. pip manage the library. you will need something else to manage your environment. To use it the easiest is pip install `package-name` I recommend using a requirements.txt and add as you go the library and do pip install -r requirements.txt each time. it avoid to forget a library at the end of the project :)" **- participant 241178995 (Data scientist working in software engineering)**

> "python's npm/cargo/opam... dedicated package manager and ecosystem for python libraries and applications" **- participant 240306262 (self-taught Python creative artist and web developer, using Python for 5-6 years)**

> "A tool to download & install packages and resolve dependencies. I see it in the same area as yum, zypper or apt-get install in the Linux world." **- participant 240306204 (Using Python for scientific research and data analysis for 3 - 4 years)**

> "Pip is the tool primarily used in the Python community to install packages. ("Package" means two different things in Python; it can be a target of the `import` statement that includes modules and other packages, or it can mean a collection of code with a defined interface that can be installed for reuse. I'm referring to the second thing here.) Pip's implementation defines what it means for a package to be installed in a Python environment. Any other tool that wishes to install software into a Python environment (e.g. conda) must match Pip's implementation." **- participant 240313922 (Computer security researcher at a university, using Python for 7-10 years)**

### Responses to "In your own words, explain what happens when pip installs a software package"

> "I think pip looks up package "tea" in the repository of packages (PyPI by default, but can be changed). If it doesn't find it, it gives an error. If it exists, it downloads some information about the package, like what form it exists in. This can be a wheel, or a package that needs to be built. If it is a wheel, it checks the dependencies and installs them, then it installs the wheel (not sure what this means, probably it extracts it). The wheel is specific to a python distribution and base OS, so it might be available on certain platforms but not others. If it is a package that needs to be built, pip downloads the package source (or clones the repository), and runs setup.py, which installs dependencies and other packages, then the package itself. I forgot to mention that before installing there is some check for checking compatibility of the version required and the versions required by other packages." **- participant 240426799 (Scientific researcher - data analysis and computer vision models, using Python for 5-6 years)**

> "pip searches for a package source (and for me uses the default, so Pypi), then ask the package source for a package with the given name and versions (if specified), then if the package is available download the package in the most appropriate format (depending on my platform), then unzip the package and runs the installer (most probably calls setuptools with the included setup.py file) which will perform the required installation steps. This installation process may contain dependencies (typically specified in setup.py), which will trigger the same process for the dependencies, and so on until all dependencies are installed (if everything is OK)." **- participant 240670292 (Software developer industrial systems control, using Python for 5-6 years)**

> "Pip checks PyPI (default package index, assuming that wasn't overridden) for the package matching `tea`. It uses the various specifiers (eg. OS compatibility, Python compatibility, etc) to find the latest version of `tea` compatible with my system. Within that version, it finds the best possible installation match (eg. a `wheel`, if supported on my system and my version of `pip` contains the relevant versioned support [eg. most recently manylinux2010], potentially falling back all the way to a source distribution). After downloading the relevant distribution, it performs the same operations recursively up the dependency chain as specified by the `install_requires` of the `setuptools.setup()` method. After grabbing all relevant packages, it performs the installations as specified in their setup methods -- generally, this involves extracting python files to specific system paths, but various levels of complexity may be added as need be such as compilations, system library bindings, etc. I believe the new resolver changes the above by performing all the lookups simultaneously (eg. by building and solving a dependency graph rather than traversing incrementally) but have not yet read the PEP to learn more. I've answered the above with setuptools in mind -- I believe there was a step added recently to check pyproject.toml first to allow for alternate systems here, but I find the added customization to be a net negative to the ecosystem and have not yet played with it -- the entire Poetry/Pipenv/Pipfile.lock/Flit thing just seems to be adding unnecessary complexity; users who know what they're doing have solved all these issues years ago for their packages and users who find the porcelain makes their lives easier are likely going to run into UX trouble no matter the veneer." **- participant 241463652 (Using Python for 5-6 years)**

> "pip accesses the tea package from pypi (guessing that's where, online at least) and downloads a copy of the files into my local venv" **- participant 243434435 (Data analysis & machine learning, using Python for 1-2 years)**

> "Looking up the latest version of of the package from pypi" **- participant 243897973 (Software testing/writing automated tests using Python 3 - 4 years)**

> "Download, unpack, sometimes compile a module for my target arch" **- participant 243428875 (System administration using Python 7 - 10 years)**

## Recommendations

It's difficult to know what to recommend. Some ideas:

- Question: Is it actually necessary for users to know everything that pip is doing?
- Better documentation:
  - Describing the "blocks of functionality" that pip carries out and how to deal with them when it breaks
  - Curating package manager training and help
  - Improving pip output to expose the different pip functionality blocks

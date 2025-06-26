# Prioritizing pip Features

## Problem

The pip development team is small, and has limited time and energy to work on issues reported via the [issue tracker](https://github.com/pypa/pip/issues). There is also a significant backlog of issues (782 as of November, 2020) for the team to respond to.
For the team to prioritize their work based on what will have the most impact, we need to develop a better understanding of what users want from pip.

[Skip to recommendations](#recommendations)

## Research

To help answer this question, we developed a "buy a feature" survey, with the following scenario:

<blockquote>
Help us to understand what's important to you by participating in our "buy a feature" game:

You have an allocated budget of $200 to spend on redesigning pip.

With your $200 budget, "buy" the functionality you'd most like to keep.

You don't have to spend the whole $200, but you should also not overspend your budget!

</blockquote>

We asked users to spend their first $100 on features related to `pip install`, and to spend their remaining $100 on other pip features. We also gave users an additional $10 to suggest a new feature:

![survey question where users are asked to buy features for pip install](https://i.imgur.com/2QShgYo.png)

![survey question where users are asked to buy features other than pip install](https://i.imgur.com/sY8gdXD.png)

![survey question where users are asked to spend an additional ten dollars](https://i.imgur.com/hvgjdEG.png)

## Results

We received 1076 responses, 1070 of which were valid. The most popular features included the core competencies of pip:

- Recreating an environment from a list of installed dependencies;
- Install, uninstall, and upgrade packages from a virtual control system, file, or local directory;
- Warn about broken or conflicting dependencies.

### pip install

The top ten features related to pip install were:

![pip install results](https://i.imgur.com/1rNIOB7.png)

1. Install and uninstall packages
2. Upgrade packages to the latest version
3. Warn about broken dependencies
4. Install a package from a version control system (e.g. Git, Mercurial, etc.)
5. Install packages as specified in a file
6. Install a package from a local directory
7. Verify downloaded packages against hashes
8. Install packages from an alternative package index, or indexes (default is PyPI only)
9. Install a package from wheels (no need for compiling code)
10. Control where you want your installed package to live on your computer

### Other pip functionality

The top ten features related to other pip functionality were:

![other pip functionality results](https://i.imgur.com/xrp9XWw.png)

1. Generate a list of installed packages that can be used to recreate the environment
2. Check that your installed packages do not have dependency conflicts
3. Run pip without requiring any user input (e.g. in CI)
4. Show information about all installed packages
5. Show information about a single installed package
6. Search pypi.org for packages
7. Show information about pip (version information, help information, etc.)
8. Download packages, build wheels and keep them in a directory for offline use
9. Manage pip's default configuration (e.g. by using configuration files)
10. Customise pip's output (e.g. reduce or increase verbosity, suppress colors, send output to a log)

Results varied by the amount of Python experience the user had.

<details>
<summary>See how likely users are to select a feature based on their experience level</summary>

#### Verify downloaded packages against hashes

![screenshot of verify downloaded packages against hashes](https://i.imgur.com/oVHOGBQ.png)

#### Warn about broken dependencies

![Screenshot of Warn about broken dependencies](https://i.imgur.com/uNv2tnG.png)

#### Upgrade packages to the latest version

![Screenshot of Upgrade packages to the latest version](https://i.imgur.com/pQgCLBO.png)

#### Install packages from an alternative package index, or indexes

![Screenshot of Install packages from an alternative package index, or indexes](https://i.imgur.com/E1LnTBt.png)

#### Install packages as specified in a file

![Screenshot of Install packages as specified in a file](https://i.imgur.com/87uh4xp.png)

#### Install and uninstall packages

![Screenshot of Install and uninstall packages](https://i.imgur.com/GRsazBy.png)

#### Install packages from a version control system

![Screenshot of Install packages from a version control system](https://i.imgur.com/iW7d0Sq.png)

#### Install a package from wheels

![Screenshot of Install a package from wheels](https://i.imgur.com/9DMBfNL.png)

#### Install a package from a local directory

![Screenshot of Install a package from a local directory](https://i.imgur.com/Jp95rak.png)

#### Control where you want your installed package to live on your computer

![Screenshot of Control where you want your installed package to live on your computer](https://i.imgur.com/32fpww2.png)

</details>

## Recommendations

### Environment recreation

Environment recreation is already included in pip as part of the `requirements.txt` feature; however, with it's popularity and demand, we recommend that **pip should improve it's support of this feature.**

- Improve environment recreation user output and help guides directly in the pip CLI;
- Improve pip documentation & user guide to prominently feature environment recreation as a core feature of pip;
- Improve environment recreation process itself by considering virtual environments as a core competency "built-in" to pip.

**Recreating an environment from a list of installed dependencies was the most valued feature request overall** as well as in each user group, _except for those with less than 6 months of experience and those with 16-19 years of experience (for which it was the second most valued)._

When asked to enter a feature request with freetext, users placed the words 'built-in,' 'virtual,' 'automatic,' and 'isolation' alongside the word 'environment,' which suggest that users expect pip to recreate environments with a high level of intelligence and usability.

**Selected direct quotes**

> Make pip warn you when you are not in virtualenv

> Automatic virtual env creation with a command line argument

> Eliminate virtual environments. Just use ./python_modules/ like everyone else

> I would love to see pip manage the python version and virtual env similar to the minicona

> Would spend all my $200 on this: Integrate pipenv or venv into pip so installing an application doesn't install it's dependencies in the system package store. And allow pinning dependency versions for application packages (like how pip-compile does it)

### Dependency management

We recommend that the pip team improve warning and error messages related to dependencies (e.g., conflicts) with practical hints for resolution. This can be rolled out in multiple timescales, including:

- Give hints to the user on how to resolve this issue directly alongside the error message;
- Prominently include virtual environment creation in the documentation, upon `pip install` conflict errors, and if possible as a built-in feature of pip;
- Upgrading the dependency resolver (in progress).

It is clear that dependency management, including warning about conflicting packages and upgrades, is important for pip users. By helping users better manage their dependencies through virtual environments, pip can reduce the overall warnings and conflict messages that users encounter.

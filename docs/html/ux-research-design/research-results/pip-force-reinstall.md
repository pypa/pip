# pip --force-reinstall

## Problem

Currently, when `pip install [package-name] --force-reinstall` is executed, instead of reinstalling the package at the version previously installed, pip installs the package at the newest version available.

i.e. `pip install [package name] --force-reinstall` acts as `pip [package name] --upgrade`

We want to find out if users understand (or desire) this implicit behaviour.

More information can be found on [this GitHub issue](https://github.com/pypa/pip/issues/8238).

[Skip to recommendations](#recommendations)

## Research

To help us understand what users want from the `--force-reinstall` option, we launched a survey with the following scenario:

<blockquote>
You have the requests package and its dependencies installed:

requests==2.22.0<br>
asgiref==3.2.10<br>
certifi==2020.6.20<br>
chardet==3.0.4<br>
Django==3.1<br>
idna==2.8<br>
pytz==2020.1<br>
sqlparse==0.3.1<br>
urllib3==1.25.10<br>

You run 'pip install requests --force-reinstall'. What should happen?

</blockquote>

Respondents could choose from one of the following options:

- pip reinstalls the same version of requests. pip does not reinstall request's dependencies.
- pip reinstalls requests and its dependencies, updating all these packages to the latest compatible versions
- pip reinstalls requests and its dependencies, keeping every package on the same version
- pip reinstalls requests, updating it to the latest version. pip updates request's dependencies where necessary to support the newer version.
- I don't know what pip should do
- I don't understand the question
- Other (allows respondent to provide their own answer)

We also asked how useful `pip --force-reinstall` is, and how often it is used.

## Results

In total we received 190 responses to our survey, with 186 people telling us what pip should do when the `--force-reinstall` option is executed.

![pie chart with survey results](https://i.imgur.com/yoN02o9.png)

- **31.7%** (59/186) of respondents said that pip should reinstall requests and its dependencies, keeping every package on the same version
- **28%** (52/186) of respondents said that pip should reinstall requests, updating it to the latest version, with pip updating request's dependencies where necessary to support the newer version.
- **15.6%** (29/186) of respondents said that pip should reinstall requests and its dependencies, updating all these packages to the latest compatible versions
- **14%** (26/186) of respondents said that pip should reinstall the same version of requests, and not reinstall request's dependencies

If we group responses into "upgrade" or "do not upgrade" (ignoring responses that could not be grouped), we find:

- 46.32% (88/186) of respondents thought that pip should install the same version of requests - i.e. that `--force-reinstall` should _not_ implicitly upgrade
- 43.16% (82/186) of respondents thought that pip should upgrade requests to the latest version - i.e that `--force-reinstall` _should_ implicitly upgrade

Most respondents use `--force-reinstall` "almost never" (65.6%):

![screenshot of survey question of how often users use --force-reinstall](https://i.imgur.com/fjLQUPV.png)
![bar chart of how often users use --force-reinstall](https://i.imgur.com/Xe1XDkI.png)

Amongst respondents who said they use `--force-reinstall` often or very often:

- 54.54% (6/11) of respondents thought that pip should install the same version of requests - i.e. that `--force-reinstall` should _not_ implicitly upgrade
- 45.45% (5/11) of respondents thought that pip should upgrade requests to the latest version - i.e that `--force-reinstall` _should_ implicitly upgrade

Respondents find `--force-reinstall` less useful than useful:

![screenshot of survey question of how useful users find --force-reinstall](https://i.imgur.com/6cv4lFn.png)
![bar chart of how useful users find --force-reinstall](https://i.imgur.com/gMUBDBo.png)

Amongst respondents who said they find `--force-reinstall` useful or very useful:

- 38.46% (20/52) of respondents thought that pip should install the same version of requests - i.e. that `--force-reinstall` should _not_ implicitly upgrade
- 50% (26/52) of respondents thought that pip should upgrade requests to the latest version - i.e that `--force-reinstall` _should_ implicitly upgrade

## Recommendations

Given that this option is not regularly used and not strongly rated as useful, we recommend that the development team consider removing `--force-reinstall` _should they wish to reduce maintenance overhead_.

In this case, we recommend showing the following message when a user tries to use `--force-reinstall`:

> Error: the pip install --force-reinstall option no longer exists. Use pip uninstall then pip install to replace up-to-date packages, or pip install --upgrade to update your packages to the latest available versions.

Should the pip development team wish to keep `--force-reinstall`, we recommend maintaining the current (implicit upgrade) behaviour, as pip's users have not expressed a clear preference for a different behaviour.

In this case, we recommend upgrading the [help text](https://pip.pypa.io/en/stable/reference/pip_install/#cmdoption-force-reinstall) to be more explicit:

Old help text:

> Reinstall all packages even if they are already up-to-date.

New help text:

> Reinstall package(s), and their dependencies, even if they are already up-to-date. Where package(s) are not up-to-date, upgrade these to the latest version (unless version specifiers are used).

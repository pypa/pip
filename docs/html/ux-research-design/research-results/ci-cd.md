# How pip is used in interactive environments (i.e. CI, CD)

## Problem

We want to know about the contexts in which pip users use pip - interactively (i.e. typing pip commands at the command line terminal) and in an automated environment (i.e. as part of continuous software integration or continuous software development pipelines).

Different contexts of use mean that users have different important and common tasks; it means when, where and how they complete these tasks are different.

Each of these contexts bring different needs: interactive usage requires the right feedback/output at the right time, whereas an automated environment requires little or no feedback in the moment but detailed feedback after the task has finished.

We also wanted to know what users used pip for - as part of their software development toolchain, or purely as a software installer (analogous to Ubuntu Aptitude or Mac Appstore). We also asked about their need for pip to build packages from source.

## Research

We created a survey and asked users to give answers to the following statements:

- I use pip in an automated environment (e.g. CI/CD pipelines)
- I have problems with pip in CI/CD pipelines
- I use pip interactively (e.g. typing pip commands on the commandline)
- I make software and use pip as part of my software development workflow
- I use pip only to install and use Python packages
- I need pip to build software packages from source

## Results

Using pip interactively makes up the majority of pip usage (91%), the majority (73%) of this usage is basic usage - to only install and use Python packages.

Half (51%) of all participants used pip in an automated environment, with only 9% having issues with pip in that automated environment. This points to a good use experience for these users.

71% use pip as part of their software toolchain, only 29% needing pip to build from source.

These results show that the main context of use is interactive - users either writing code, installing software at the command line and we know from other research that interactive usage has its issues e.g. pip output being too verbose.

While it is important to provide automated environment users with a good experience, interactive mode users are being underserved.

![Answer to question - I use pip in an automated environment](https://i.imgur.com/pLHqBpN.png)

![Answer to question - I use pip interactively](https://i.imgur.com/8ETVMYS.png)

91% of users said they used pip interactively. This does not preclude them from automated usage.

![Answer to the question - What do you use Python for?](https://i.imgur.com/ySlo2Es.png)

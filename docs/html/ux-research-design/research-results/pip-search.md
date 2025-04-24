# pip search

## Problem

By default, `pip search` searches packages on PyPI.org from the command line. However, the team are [considering removing it](https://github.com/pypa/pip/issues/5216), because they think it's not that useful and using too many resources on PyPI ([PyPI XMLRPC search has been disabled](https://status.python.org/incidents/grk0k7sz6zkp) because of abuse/overuse).

[Skip to recommendations](#recommendations)

## Research

Prior to PyPI XMLRPC search being disabled, we:

- Gathered feedback on pip search via the "buy a feature" survey
- Published a survey specifically about pip search, asking users about:
  - Their current use of pip search
  - How useful they find pip search results
  - How clear they find pip search results
  - Where users expect pip to search (e.g. PyPI vs private index)
  - What data pip should search _other_ than project name
  - What changes or additions they would make to pip search

## Results

In total, we received 1070 responses to the buy a feature survey, with 541 (50.4%) respondents selecting "Search pypi.org for packages" in their top 10 features.

However, search ranked lower than the following features:

1. Run pip without requiring any user input (e.g. in CI) _718_
2. Show information about all installed packages _707_
3. Show information about a single installed package _596_

We received 302 responses to the pip search survey, with 62 of the 302 (20.5%) respondents either not knowing that the command existed, never using it, or using it "rarely".

We found that the remaining ~80% of respondents who do use pip search use it to:

- Find/search for the right/new/alternate packages to install:
  - Checking package name (verify correct spelling)
  - Assessing functionality (check a package's description)
  - Verifying availability (check if such package exists)
- Search for the latest version of a package (verify version)
- Find package libraries and new modules

In general, pip search is regarded as:

- more useful than not useful
- more clear than not clear

When asked if pip should search on items _other_ than the package name, respondents most commonly asked to search the package description:

![wordcloud of common search terms](https://i.imgur.com/lxS2TG6.png)

Some users also mentioned that they would like the search to be configurable, e.g. by passing flags/options.

When asked how they would improve pip search, users said they would improve:

**1. Search methods:**

- fuzzy search and insensitive case should be acceptable
- users should have the option to filter/sort by description, name, tag

**2. Search results:**

- relevancy: the results should show both the exact match and closest match
- order/category: the result should display items in a certain order, e.g highest number of downloads (popularity), development status (last updated/latest version), etc.
- there should be a limited number of search results

**3. User interface:**

- link package to pypi page
- use color coding / system for better clarity
- distinguish exact match search results from others: by highlighting, or using a different color
- indicate version compatibility

## Recommendations

### Deprecation strategy

Given that the [PyPI](https://pypi.org/pypi) search API is currently disabled (as of 1st Jan, 2021) for technical and sustainability reasons, we recommend that the pip team display a clear error message to users who use the command:

```
The PyPI search API has been disabled due to unmanageable load.
To search PyPI, open your browser to search for packages at https://pypi.org
Alternatively, you can search a different index using the --index command.
```

In the longer term, **we recommend that the PyPI team investigate alternative methods of serving search results (e.g. via caching)** that would enable pip search to work again. This recommendation is supported by our research which suggests that many pip users find this functionality useful.

If this is not possible, the pip team should create clear instructions that tells users what to use instead. Some suggestions (based on common user flows) are listed below:

#### Finding a new package based on tags and keywords

This is the most common feature that you would expect from `pip search` and likely the hardest to replace after deprecation.

As mentioned above, the pip CLI should - as soon as possible - hide the full-trace error message present when a user types `pip search`. Instead, pip should show a message that encourages users to use the search index on the website itself (in their browser) by providing a link directly to [https://pypi.org](https://pypi.org). Also, pip should provide a short hint on how to use an alternative index.

```
$ pip search pytest

The PyPI search API has been disabled due to unmanageable load.

Please open your browser to search for packages at https://pypi.org

Alternatively, you can use a different index using the --index command.

   pip search pytest --index <URL>
```

In addition, the pip team could implement an alternative to the PyPI search API that works without a hard dependency on a centralized service. Similar to other distribution systems like `apt` and `yum`, the metadata of all package names could be downloaded on the user's machine with an opt-in workflow:

```
$ pip search pytest
Using pip search on the command line requires you to download the index first.
Alternatively, you can open your browser to search for packages at https://pypi.org

Download the index to /System/Library/Frameworks/Python.framework/
Versions/2.7/Resources/Python.app/Contents/MacOS/search.db? (y/n) y
......... done!

<results>

$ pip search pytest
<results>
```

This is a more complex route that will require more engineering time, but can aim to provide command line users with a similar functionality to the old `pip search` command. It can also check the age of the local index and show a warning if it is getting old.

#### Verifying the latest version of a package

Users also use the `pip search` command to find or verify a particular package's version.

As a replacement, the pip team could do either of the following:

1. Extend the `pip show` feature to include known latest versions of the package;
2. Create a `pip outdated` command which scans the current dependency tree and outputs the packages that are outdated (compared to the latest versions on the configured index).

### UX improvements

Should it be possible to continue to support pip search, we strongly recommend the following UX improvements:

- Adding support for [fuzzy search](https://en.wikipedia.org/wiki/Approximate_string_matching), or suggesting alternative/related search terms
- Adding support for case insensitive search
- Searching based on a package's description
- Linking search results to a package's PyPI page (where appropriate)

Other user feedback (as detailed above) should also be considered by the team on a case-by-case basis.

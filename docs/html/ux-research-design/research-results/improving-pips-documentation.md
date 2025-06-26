# Improving pip's Documentation

## Problem

We want to establish whether or not the [official pip documentation](https://pip.pypa.io/en/stable/) helps users to solve their pip problems. We also want to identify possible improvements to the content and structure of the docs.

[Skip to recommendations](#recommendations)

## Research

### Interviews

We conducted interviews with pip users specifically discussing documentation. During these interviews we asked about:

- Problems they had experienced while using pip, and how they solved them (with a focus on what information sources they used)
- How they rate pip's documentation, and what we could do to make the docs more useful
- What documentation (from other projects or languages) they find valuable, and why

### Surveys

We collected documentation feedback via two surveys:

- In our survey that profiled pip users, we asked "What would be your ideal way of getting help with pip?"
- We also published a survey specific to pip's docs:

![Screenshot of survey](https://i.imgur.com/dtTnTQJ.png)

### Keyword research

We used keyword research tools to understand what words ("keywords") people use when using search engines to troubleshoot pip problems.

### Other research methods

We also:

1. Asked for volunteers to participate in a diary study, documenting their experience solving pip problems. Unfortunately this was not completed due to lack of interest from the community.
2. Asked for user feedback on the pip documentation site:
   ![screenshot of user feedback mechanism on pip docs](https://i.imgur.com/WJVjl8N.png)
   Unfortunately, we did not gather any useful feedback via this effort
3. [Installed analytics on the pip docs](https://github.com/pypa/pip/pull/9146). We are waiting for this to be merged and start providing useful data.

## Results

In total, we:

- Conducted 5 user interviews about pip's documentation
- Received 141 responses to the question "What would be your ideal way of getting help with pip?"
- Received 159 responses to the documentation survey

In general, we found that pip's documentation is underutilized by the community, with many users not knowing that it exists. Instead, most users turn to common tools (Google, Stack Overflow) to solve their pip problems.

In response to the question "When you have a problem using pip, what do you do?" (multiselect):

- 81.9% of respondents Google it
- 56.9% of respondents search or ask on Stack Overflow
- 33.8% of respondents use pip help from the command line
- **25.6% of respondents go to the pip docs**
- 20.6% of respondents go the the Python Packaging User Guide
- 8.1% of respondents ask on a forum, community board, or chat channel

![screenshot of survey results](https://i.imgur.com/qlt1b4n.png)

Based on survey results, users find pip's docs:

- Marginally more useful than not useful
- Marginally more clear than unclear
- Not opinionated enough

Common feedback that emerged from both surveys and user interviews includes:

- The documentation performs poorly in search engine results
- The style and layout is dated (note: this feedback was collected before the [new theme was deployed](https://github.com/pypa/pip/pull/9012))
- There is not enough guidance/examples on how to resolve common problems, or achieve specific goals
- The documentation information architecture is difficult to navigate (the monolithic structure of the user guide is a problem) and does not prioritise the most useful content
- There should be more instructions specific to each user's different situation (e.g. what operating system they are using)
- The scope of the documentation is unclear
- The documentation should recognise that pip exists within an ecosystem of other packaging tools
- ["There should be one-- and preferably only one --obvious way to do it."](https://www.python.org/dev/peps/pep-0020/) - i.e. the documentation should provide stronger recommendations

While some users mentioned that video would be helpful, more said that video was too long, or inappropriate for the kind of problems they experience using pip.

Some users mentioned that in person support, forums or chat would be helpful, with many unaware of existing support / community channels.

Several users also noted that improving pip's error messages would reduce the need for better documentation.

From our keyword research we identified seven _query types_: "about pip", "install pip", "uninstall pip" "update pip", "using pip", "errors", and "other".

<details><summary> See keyword research results</summary>

### About pip

- what is pip
- what is pip in python
- what is pip python
- what does pip mean
- what does pip stand for
- what does pip stand for python
- pip meaning

### Install pip

- get pip
- python install pip
- install pip
- installing pip
- how to install pip python
- how to install pip
- how to download pip
- how to get pip
- how to check if pip is installed
- install pip mac
- how to install pip on mac
- install pip on mac
- install pip linux
- how to install pip linux
- how to install pip on linux
- how to install pip in ubuntu
- how to install pip ubuntu
- install pip ubuntu
- ubuntu install pip
- pip windows
- install pip windows
- pip install windows
- how to install pip windows
- how to install pip in windows
- how to install pip on windows
- how to pip install on windows
- how to install pip on windows 10
- how to run pip on windows

### Uninstall pip

- how to uninstall pip
- uninstall pip
- pip uninstall

### Update pip

- how to update pip
- how to upgrade pip
- pip update
- pip upgrade
- upgrade pip
- how to upgrade pip on windows

### Using pip

- how to use pip
- how to use pip install
- how to pip install
- how to use pip python
- how to install with pip
- how to run pip
- python how to use pip
- pip install requirements.txt
- pip requirements.txt
- pip freeze
- pip update package
- pip install specific version
- pip upgrade package
- pip uninstall package

### Errors

- no module named pip
- pip command not found
- pip is not recognized
- 'pip' is not recognized as an internal or external command, operable program or batch file.
- -bash: pip: command not found
- pip is not recognized as an internal or external command
- pip install invalid syntax

### Other

- how to add pip to path
- how to check pip version
- how does pip work
- where does pip install packages
- pip vs pip3
- where is pip installed

</details>
<br/>

The prevalence of "install pip" queries strongly suggests that the current installation documentation should be improved and that users are searching for solutions specific to their operating system.

The "about pip" queries also suggest that beginners would benefit from documentation that better explains pip basics - e.g. what pip is and what it does.

## Recommendations

Based on our research, we recommend that the pip team:

- Revise the structure of the documentation:
  - Break monolithic pages into standalone pages on different subjects, with appropriate meta tags. This will help the docs appear higher in search results for the 81.9% of users who use Google to troubleshoot their pip problems.
  - Prioritise most used features (see "[buy a feature](prioritizing-features)" results for guidance)
- Add a "troubleshooting" section to the documentation that addresses common questions, explains error messages and tells users where they can find more help
- Provide more context about pip's role in the Python packaging ecosystem by:
  - Introducing packaging concepts that users need to understand in order to use pip
  - Explaining pip's role/scope within the packaging ecosystem
  - Comparing pip to other tools
- Develop a beginner's guide that walks new pip users through everything they need to know to use pip's most basic functionality. This should include addressing concepts outside of pip's scope (e.g. how to open and use a terminal, how to set up a virtual environment), that may block users from being successful
- For each page, (where appropriate), add sections for:
  - "tips and tricks" - things to know / gotchas
  - "troubleshooting" - possible error messages and recommended solutions. Where appropriate, this should link to content in the troubleshooting section.
  - "see also" (links to external resources - e.g. useful stack overflow questions, blog articles, etc.)
- In general, write content that:
  - Is opinionated. Prioritize solutions that will work in the majority of cases, while pointing to possible edge cases and workarounds in "tips and tricks", "troubleshooting" and "see also" content
  - Uses keywords to increase search results visibility
  - Provides instructions for different contexts - e.g. for users on Windows, Linux, MacOSX
  - Increases interlinking with external sources, including packaging.python.org

### Suggested site map

Based on the above user input, we have developed a proposed [site map](https://i.imgur.com/UP5q09W.png) (link opens larger format image) to help guide the redevelopment of pip's documentation in line with the above recommendations.

![sitemap. for details see summary below](https://i.imgur.com/UP5q09W.png)

<details><summary> See notes for this site map</summary>

#### Node 1.0: Quick reference

_Page purpose:_

- To give pip users a quick overview of how to install pip, and use pip's main functionality
- To link to other (more detailed) areas of the documentation

_Suggested content:_

- Quick installation guide, including how to use a virtual environment. This is necessary for user who want to install more than one Python project on their machine.
- Common commands / tasks (based on [buy a feature](prioritizing-features) data)

---

#### Node 2.0: About pip

_Page purpose:_

- To introduce pip to new users

_Suggested content:_

- Introduce pip as a command line program
- Explain what the command line is and how to use it in different operating systems
- Explain what pip is/does, and what it stands for
- Link to packaging concepts (node 2.1)
- Explain pip's scope (e.g. to install and uninstall packages) and link to other tools (node 2.2)

#### Node 2.1: Packaging concepts

_Page purpose:_

- To introduce packaging concepts for new pip users

_Suggested content:_

- What is a package?
- What types of packages are there? e.g. file types
- What is package versioning / what are requirement specifiers? (note: talk about potential dependency conflicts here)
- Where do I get packages from?
- How should I control how packages are installed on my system (e.g. virtualenv and environment isolation)
- How can I reproduce an environment / ensure repeatability? (e.g requirements files)
- What do I need to know about security? (e.g. hash checking, PyPI name squatting)
- Link to node 2.2 ("pip vs other packaging tools")

#### Node 2.2: pip vs other packaging tools

_Page purpose:_

- To compare pip to other tools with the same scope
- To highlight that pip exists within a _packaging ecosystem_ and link to other packaging tools

_Suggested content:_

- Compare pip to other installation tools - e.g. poetry, pipenv, conda. What are the features, pros and cons of each? Why do packaging users choose one over the other?
- Briefly introduce other packaging projects. Link to https://packaging.python.org/key_projects/

---

#### Node 3.0: Installing pip

_Page purpose:_

- To help pip users install pip

_Suggested content:_

- Refactor current page, emphasising pathways for different operating systems
- Add "tips and tricks", "troubleshooting" and "see also" (link to external resources) sections to provide additional help

---

#### Node 4.0: Tutorials

_Page purpose:_

- To provide a jumping off place into pip's tutorials

_Suggested content:_

- Link to tutorials, including sub pages, where appropriate

#### Node 4.1: Using pip to install your first package

_Page purpose:_

- To help new pip users get started with pip

_Suggested content:_
Step by step tutorial (possibly broken into several pages) that covers:

- Using the command line
- Installing pip (or checking pip is installed)
- Creating/activating a virtual env (use venv for this, but point to alternatives)
- Installing a package
- Showing where the package has been installed
- Deactivating/reactivating virtualenv
- Uninstalling a package

#### Node 4.2: Advanced tutorial - using pip behind a proxy

_Page purpose:_

- To help advanced pip users achieve specific goals

_Suggested content:_

- Step by step tutorial for using pip behind a proxy

NB: other advanced tutorials should be added as identified by the team and/or requested by the community.

---

#### 5.0: Using pip

_Page purpose:_

- To provide a jumping off point for the user guide and reference guide

_Suggested content:_

- Link to each subject in the user guide
- Link to reference guide

#### 5.1: User guide

_Page purpose:_

- To provide users with specific detailed instructions on pip's key features

_Suggested content:_
Break down current user guide into separate pages, or pages linked by subject. Suggested order:

- Running pip
- Installing Packages
- Uninstalling Packages
- Environment recreation with requirements files
  - sub heading: "pinned version numbers"
  - sub heading: "hash checking mode"
- Listing Packages
- Searching for Packages
- Installing from local packages
- Installing from Wheels
- Wheel bundles
- “Only if needed” Recursive Upgrade
- Configuration
- User Installs
- Command Completion
- Basic Authentication Credentials
- Using a Proxy Server (includes link to tutorial)
- Constraints Files
- Using pip from your program

Where possible, each page should include:

- "tips and tricks" for workarounds, common _gotchas_ and edge use cases
- "troubleshooting" information, linking to content in node 6.2 ("Troubleshooting error messages") where applicable
- "see also", linking to external resources (e.g. stack overflow questions, useful threads on message boards, blogs posts, etc.

Note: the following content should be moved:

- Fixing conflicting dependencies (move to node 6.2 - "Troubleshooting error messages")
- Dependency resolution backtracking (move to node 6.2 - "Troubleshooting error messages")
- Changes to the pip dependency resolver in 20.3 (move to node 7.0 - "News, changelog and roadmap")

#### 5.2: Reference guide

_Page purpose:_

- To document pip's CLI

_Suggested content:_

- https://pip.pypa.io/en/stable/reference/

---

#### 6.0: Help

_Page purpose:_

- To provide a jumping off place for users to find answers to their pip questions

_Suggested content:_

- Links to
  - 6.1 "FAQs"
  - 6.2 "Troubleshooting error messages"
  - 6.3 "Finding more help"

#### 6.1: FAQs

_Page purpose:_

- To answer common pip questions / search terms

_Suggested content:_

- What is the difference between pip and pip3?
- Where does pip install packages?
- How can I check pip's version?
- How can I add pip to my path?
- Where is pip installed?
- What does pip stand for?

See [popular questions on Stack Overflow](https://stackoverflow.com/search?q=pip&s=ec4ee117-277a-4c5d-a3f5-c921ca6c5da6) for more examples.

#### 6.2: Troubleshooting error messages

_Page purpose:_

- To help pip users solve their problem when they experience an error using pip

_Suggested content:_
For each (common) error message:

- Explain what happened
- Explain why it happened
- Explain what the user can do to resolve the problem

Note: the [ResolutionImpossible](https://pip.pypa.io/en/stable/user_guide/#fixing-conflicting-dependencies) and [dependency resolution backtracking](https://pip.pypa.io/en/stable/user_guide/#dependency-resolution-backtracking)
documentation should both be moved here.

#### 6.3: Finding more help

_Page purpose:_

- To point pip users to other resources if they cannot find the information they need within the pip documentation

_Suggested content:_

- See [getting help](https://pip.pypa.io/en/stable/user_guide/#getting-help)

---

#### 7.0: News, changelog and roadmap

_Page purpose:_

- To share information about:
  - Recent changes to pip
  - Upcoming changes to pip
  - Ideas for improving pip, specifically highlighting where funding would be useful

_Suggested content:_

- [Changes to the pip dependency resolver in 20.3 (2020)](https://pip.pypa.io/en/stable/user_guide/#changes-to-the-pip-dependency-resolver-in-20-3-2020)
- Links to PSF blog posts about pip
- Link to [fundable packaging improvements](https://github.com/psf/fundable-packaging-improvements/blob/master/FUNDABLES.md)

---

#### 8.0: Contributing

_Page purpose:_

- To encourage new people to contribute to the pip project
- To demonstrate that the project values different _types_ of contributions, e.g. not just development
- To recognise past and current contributors

_Suggested content:_

- Introduction to pip as an open source project
- Contributors code of conduct
- Recognition of the different types of contributions that are valued
- Credit list of contributors, including pip maintainers

#### 8.1: Development

_Page purpose:_

- To onboard people who want to contribute code to pip

_Suggested content:_

- https://pip.pypa.io/en/stable/development/

#### 8.2: UX design

_Page purpose:_

- To onboard people who want to contribute UX (research or design) to pip
- To share UX knowledge and research results with the pip team

_Suggested content:_

- UX guidelines, and how they apply to the pip project
- Current UX initiatives (e.g. open surveys, interview slots, etc.)
- Previous research and results, including UX artifacts (e.g. personas)

#### 8.3: Documentation

_Page purpose:_

- To onboard people who want to contribute to pip's docs
- To share previous research and recommendations related to pip's docs

_Suggested content:_

- This guide
- Writing styleguide / glossary of terms - see the [Warehouse documentation](https://warehouse.readthedocs.io/ui-principles.html#write-clearly-with-consistent-style-and-terminology) for an example.

</details>

### Future research suggestions

To continue to improve pip's documentation, we suggest:

- Conducting [card sorting](https://www.nngroup.com/articles/card-sorting-definition/) with pip users to establish the ideal order and grouping of pages
- Regularly reviewing the documentation analytics, to understand those pages which are most/least visited
- Regularly reviewing Stack Overflow to identify questions for the FAQ
- Setting up a mechanism for collecting user feedback while users are on the documentation site

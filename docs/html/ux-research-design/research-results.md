# UX Research Results

## <a name="2020-research"></a>2020 Research Synthesis

Over the course of 2020, the pip team worked on improving pip's user experience, developing a better understanding of pip's UX challenges and opportunities, with a particular focus on pip's new dependency resolver. The [Simply Secure](https://simplysecure.org/) team focused on 4 key areas:

- [Understanding who uses pip](https://github.com/pypa/pip/issues/8518)
- [Understanding how pip compares to other package managers, and supports other Python packaging tools](https://github.com/pypa/pip/issues/8515)
- [Understanding how pip's functionality is used could be improved](https://github.com/pypa/pip/issues/8516), and
- [Understanding how pip's documentation is used, and how it could be improved](https://github.com/pypa/pip/issues/8517)

Some key outcomes from the 2020 work are:

- This documentation & resource section!
- A pip UX research panel ([Sign up here!](https://mail.python.org/mailman3/lists/pip-ux-studies.python.org/))
- New and expanded GitHub issues
- UX improvements in 2020
  - UX work supporting the dependency resolver
  - Improved error messaging
  - Supporting Documentation
- UX Training for the Pypa + pip maintainers

This work was made possible through the [pip donor funded roadmap](https://wiki.python.org/psf/Pip2020DonorFundedRoadmap).

### Research Methods

#### Outreach

We [recruited participants](https://www.ei8fdb.org/thoughts/2020/03/pip-ux-study-recruitment/) for a user research panel that we could contact when we wanted to run surveys and interviews about pip. In total 472 people signed up to the panel, although some unsubscribed during the research period.

At the end of the 2020 research, we asked users to opt-in to a [long-term panel](https://mail.python.org/mailman3/lists/pip-ux-studies.python.org/), where they can be contacted for future UX studies. Should the pip team wish to continue to build this panel, we recommend translating the sign-up form into multiple languages and better leveraging local communities and outreach groups (e.g. PyLadies) to increase the diversity of the participants.

#### User Interviews

In total, we **interviewed 48 pip users**, recruited from the user panel, and through social media channels.

During the interviews, we asked users about:

- How they use Python
- How long they have been using pip
- Whether or not they use a virtual environment
- If and how they address security issues associated with pip
- Which pip commands they regularly use
- How they install packages with pip
- Their experience using pip list, pip show and pip freeze
- Their experience using pip wheel
- Whether or not they use other package managers, and how pip compares to their experience with these other tools
- What the pip team could do to improve pip
- Problems they have experienced while using pip, and how they solved these problems
- Their perception and use of the pip documentation
- What other technical documentation they value, and how the pip docs could take inspiration from these
- What other resources the pip team could provide to help pip users solve their problems

#### <a name="survey-results"></a>Surveys

We **published 10 surveys** to gather feedback about pip's users and their preferences:

<table>
  <thead>
    <tr>
     <th>Title</th>
     <th>Purpose</th>
     <th>Results</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>
        <a href="https://tools.simplysecure.org/survey/index.php?r=survey/index&sid=827389&lang=en">Pip research panel survey</a>
      </th>
      <td>
        Recruit pip users to participate in user research, user tests and participate in future surveys. See <a href="https://bit.ly/pip-ux-studies">associated blog post</a> for more information.
      </td>
      <td>
        472 full sign-ups
      </td>
    </tr>
    <tr>
      <td>
        <a href="https://tools.simplysecure.org/survey/index.php?r=survey/index&sid=989272&lang=en">Feedback for testing the new pip resolver</a>
      </td>
      <td>
        Understand use cases where the new resolver fails due to dependency conflicts. See <a href="https://bit.ly/pip-ux-test-the-new-resolver">associated blog post</a> for more information.
      </td>
      <td>
        459 responses via the feedback form, approx. 8 issues transferred to issue tracker
      </td>
    </tr>
    <tr>
      <td>
        <a href="https://bit.ly/2ZqJijr">How should pip handle conflicts with already installed packages when updating other packages?</a>
      </td>
      <td>
        Determine if the way that pip handles package upgrades is in-line with user's expectations/needs. See <a href="https://www.ei8fdb.org/thoughts/2020/07/how-should-pip-handle-conflicts-when-updating-already-installed-packages/">related blog post</a> and <a href="https://github.com/pypa/pip/issues/7744">GitHub issue</a> for more information.
      </td>
      <td>
        See <a href="https://hackmd.io/2F74AQYbRzeHl3zTgoWUvQ">write up, including recommendations</a>
      </td>
    </tr>
    <tr>
      <td>
        <a href="https://bit.ly/pip-learning-about-users-survey">Learning about our users</a>
      </td>
      <td>
        Learn about pip's users, including:
        <ul>
          <li>their usage of Python and pip</li>
          <li>why and how they started using Python</li>
          <li>if they are living with any disabilities, and if so what effect (if any) this has on their usage of Python and pip</li>
          <li>if they use assistive technologies when using Python and pip and how this work for them</li>
          <li>where they get support when you have issues with pip</li>
        </ul>
      </td>
      <td>
        See <a href="https://www.notion.so/simplysecure/pip-UX-research-report-skeleton-3a6efacc3b2e44c8bc9ed707d7f56417">write up</a>
      </td>
    </tr>
    <tr>
      <td>
        <a href="http://bit.ly/buy-a-pip-feature">Buy a pip feature</a>
      </td>
      <td>
        Establish which features are most important to pip's users
      </td>
      <td>
        See <a href="https://hackmd.io/5YttjmuRSlO1LOz0YexO4g">write up</a>
      </td>
    </tr>
    <tr>
      <td>
        <a href="http://bit.ly/should-pip-install-conflicting-dependencies">Should pip install conflicting dependencies?</a>
      </td>
      <td>
        Establish whether pip should provide an override that allows users to install packages with conflicting dependencies
      </td>
      <td>
        See <a href="https://hackmd.io/MIRY9jpRSNyuzMXoWmSqIg">write up</a>
      </td>
    </tr>
    <tr>
      <td>
        <a href="http://bit.ly/how-should-pip-force-reinstall-work">How should pip force reinstall work?</a>
      </td>
      <td>
        Establish whether or not pip force reinstall should continue to behave the way it currently does, if the functionality should be changed, or if the option should be removed
      </td>
      <td>
        See <a href="https://hackmd.io/2naLnfq-SKCaUTZxZmYDNA">write up</a>
      </td>
    </tr>
    <tr>
      <td>
        <a href="http://bit.ly/pip-search">Feedback on pip search</a>
      </td>
      <td>
        To establish whether or not to remove or redesign pip search. See <a href="https://github.com/pypa/pip/issues/5216">this GitHub issue</a> for more information.
      </td>
      <td>
        See <a href="https://hackmd.io/okbYASpyQJ-XDIdDAZFQYQ">write up</a>
      </td>
    </tr>
    <tr>
      <td>
        <a href="http://bit.ly/pip-logo">Design brief for pip's logo</a>
      </td>
      <td>
        To gather information and inspiration from the community to form the basis of a design brief for pip's logo.
      </td>
      <td>
        See <a href="https://opensourcedesign.net/jobs/jobs/2020-12-15-help-design-a-logo-for-pip">design brief</a>
      </td>
    </tr>
    <tr>
      <td>
        <a href="https://bit.ly/pip-docs">Feedback on pip's docs</a>
      </td>
      <td>
        To gather feedback on pip's docs, supplementing feedback gathered in user interviews
      </td>
      <td>
        See <a href="https://hackmd.io/WuoCani0T0qwqbMinCJTaA">write up</a>
      </td>
    </tr>
  </tbody>
</table>

#### Research Results

Below is a compiled list of all research outputs and recommendations made by the pip UX team based on the research conducted in 2020.

We are currently looking for volunteers to take recommendations made by the UX team and move them into pip's issue tracker. This will ensure that the research conducted in 2020 is leveraged by the pip development team.

<table>
  <thead>
    <tr>
      <th>Title</th>
      <th>Category</th>
      <th>Description</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>
        <a href="2020-research-outputs/about-our-users">About our users</a>
      </td>
      <td>
        Who uses pip
      </td>
      <td>
        High-level summary of who uses pip. Includes recommendations for supporting languages other than English, supporting users with disabilities, and improving pip's output
      </td>
    </tr>
    <tr>
      <td>
        <a href="2020-research-outputs/personas">Pip personas</a>
      </td>
      <td>
        Who uses pip
      </td>
      <td>
        Defines and explores three Python user personas
      </td>
    </tr>
    <tr>
      <td>
        <a href="2020-research-outputs/mental-models">Mental models of pip</a>
      </td>
      <td>
        Who uses pip
      </td>
      <td>
        Explores users' general knowledge of package management, what pip is, and what pip does during an install process.
      </td>
    </tr>
    <tr>
      <td>
        <a href="2020-research-outputs/users-and-security">Behaviours and attitudes towards code security and integrity</a>
      </td>
      <td>
        Who uses pip
      </td>
      <td>
        Explores pip users behaviour and attitudes towards security and makes recommendations on how to improve pips security experience
      </td>
    </tr>
    <tr>
      <td>
        <a href="2020-research-outputs/ci-cd">Usage of pip in automated and interactive environments</a>
      </td>
      <td>
        Who uses pip
      </td>
      <td>
        Assessment of use of pip in automated environments (i.e. continuous integration, continuous deployment) vs manual input from the command line
      </td>
    </tr>
    <tr>
      <td>
        <a href="2020-research-outputs/improving-pips-documentation">Improving pip's documentation</a>
      </td>
      <td>
        Documentation
      </td>
      <td>
        Summarises how pip users get pip help, and make recommendations on how to improve pip's documentation
      </td>
    </tr>
    <tr>
      <td>
        <a href="2020-research-outputs/pip-logo">Pip's identity: In search of a logo</a>
      </td>
      <td>
        Pip community
      </td>
      <td>
        Summarises community ideas for a new pip logo as input for a design brief
      </td>
    </tr>
    <tr>
      <td>
        <a href="2020-research-outputs/prioritizing-features">Prioritizing features (buy a feature)</a>
      </td>
      <td>
        How pip works
      </td>
      <td>
        Summarises which features are most important to pip's users
      </td>
    </tr>
    <tr>
      <td>
        <a href="2020-research-outputs/pip-search">Pip Search</a>
      </td>
      <td>
        How pip works
      </td>
      <td>
        Summarises current use of pip search and makes recommendations on how to move forward with pip search, given that PyPI XMLRPC search has been disabled
      </td>
    </tr>
    <tr>
      <td>
        <a href="2020-research-outputs/pip-force-reinstall">Pip Force reinstall</a>
      </td>
      <td>
        How pip works
      </td>
      <td>
        Looks at at current use of `pip --force-reinstall` and whether the current behavior matches users expectations
      </td>
    </tr>
    <tr>
      <td>
        <a href="2020-research-outputs/pip-upgrade-conflict">Dependency conflict resolution when upgrading packages</a>
      </td>
      <td>
        2020 dependency resolver
      </td>
      <td>
        Recommends whether pip should take into account packages that are already installed when a user asks pip to upgrade a package
      </td>
    </tr>
    <tr>
      <td>
        <a href="2020-research-outputs/override-conflicting-dependencies">Providing an override to install packages with conflicting dependencies</a>
      </td>
      <td>
        2020 dependency resolver
      </td>
      <td>
        Recommends weather or not to provide an override for users to install packages with conflicts (the new pip resolver blocks this behaviour by default)
      </td>
    </tr>
  </tbody>
</table>

## Read More

- [Pip team midyear report (blog, July 2020)](https://pyfound.blogspot.com/2020/07/pip-team-midyear-report.html)
- [Creating rapid CLI prototypes with cli-output (blog, Oct 2020)](https://www.ei8fdb.org/thoughts/2020/10/prototyping-command-line-interfaces-with-cli-output/)
- [Changes are coming to pip (video)](https://www.youtube.com/watch?v=B4GQCBBsuNU)
- [How should pip handle dependency conflicts when updating already installed packages? (blog, July 2020)](https://www.ei8fdb.org/thoughts/2020/07/how-should-pip-handle-conflicts-when-updating-already-installed-packages/)
- [Test pip's alpha resolver and help us document dependency conflicts (blog, May 2020)](https://www.ei8fdb.org/thoughts/2020/05/test-pips-alpha-resolver-and-help-us-document-dependency-conflicts/)
- [How do you deal with conflicting dependencies caused by pip installs? (blog, April 2020)](https://www.ei8fdb.org/thoughts/2020/04/how-do-you-deal-with-conflicting-dependencies-caused-by-pip-installs/)
- [pip UX studies: response data (blog, March 2020)](https://www.ei8fdb.org/thoughts/2020/03/pip-ux-studies-response-data/)
- Other PyPA UX work:
  - [PyPI User Research (blog, July 2018)](https://whoisnicoleharris.com/2018/07/22/pypi-user-research.html)
  - [Warehouse - The Future of PyPI](https://whoisnicoleharris.com/warehouse/)<span style="text-decoration:underline;"> (overview)</span>
  - [Accessibility on Warehouse (PyPI) (blog, May 2018)](https://whoisnicoleharris.com/2018/05/17/warehouse-accessibility.html)
  - [User Testing Warehouse (blog, Mar 2018)](https://whoisnicoleharris.com/2018/03/13/user-testing-warehouse.html)
  - [Designing Warehouse - An Overview (blog, Dec 2015)](https://whoisnicoleharris.com/2015/12/31/designing-warehouse-an-overview.html)

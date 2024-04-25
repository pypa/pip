# UX Research Results

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

## Outreach

We [recruited participants](https://www.ei8fdb.org/thoughts/2020/03/pip-ux-study-recruitment/) for a user research panel that we could contact when we wanted to run surveys and interviews about pip. In total 472 people signed up to the panel, although some unsubscribed during the research period.

At the end of the 2020 research, we asked users to opt-in to a [long-term panel](https://mail.python.org/mailman3/lists/pip-ux-studies.python.org/), where they can be contacted for future UX studies. Should the pip team wish to continue to build this panel, we recommend translating the sign-up form into multiple languages and better leveraging local communities and outreach groups (e.g. PyLadies) to increase the diversity of the participants.

## User Interviews

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

## Surveys

We **published 10 surveys** to gather feedback about pip's users and their preferences:

<div class="wy-table-responsive">
  <table class="colwidths-auto docutils">
    <thead>
      <tr>
      <th>Title</th>
      <th>Purpose</th>
      <th>Results</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>
          Pip research panel survey
        </td>
        <td>
          Recruit pip users to participate in user research, user tests and participate in future surveys. See <a href="https://bit.ly/pip-ux-studies">associated blog post</a> for more information.
        </td>
        <td>
          472 full sign-ups
        </td>
      </tr>
      <tr>
        <td>
          Feedback for testing the new pip resolver
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
          How should pip handle conflicts with already installed packages when updating other packages?
        </td>
        <td>
          Determine if the way that pip handles package upgrades is in-line with user's expectations/needs. See <a href="https://www.ei8fdb.org/thoughts/2020/07/how-should-pip-handle-conflicts-when-updating-already-installed-packages/">related blog post</a> and <a href="https://github.com/pypa/pip/issues/7744">GitHub issue</a> for more information.
        </td>
        <td>
          See <a href="pip-upgrade-conflict">write up, including recommendations</a>
        </td>
      </tr>
      <tr>
        <td>
          Learning about our users
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
          See <a href="about-our-users">write up</a>
        </td>
      </tr>
      <tr>
        <td>
          Buy a pip feature
        </td>
        <td>
          Establish which features are most important to pip's users
        </td>
        <td>
          See <a href="prioritizing-features">write up</a>
        </td>
      </tr>
      <tr>
        <td>
          Should pip install conflicting dependencies?
        </td>
        <td>
          Establish whether pip should provide an override that allows users to install packages with conflicting dependencies
        </td>
        <td>
          See <a href="override-conflicting-dependencies">write up</a>
        </td>
      </tr>
      <tr>
        <td>
          How should pip force reinstall work?
        </td>
        <td>
          Establish whether or not pip force reinstall should continue to behave the way it currently does, if the functionality should be changed, or if the option should be removed
        </td>
        <td>
          See <a href="pip-force-reinstall">write up</a>
        </td>
      </tr>
      <tr>
        <td>
          Feedback on pip search
        </td>
        <td>
          To establish whether or not to remove or redesign pip search. See <a href="https://github.com/pypa/pip/issues/5216">this GitHub issue</a> for more information.
        </td>
        <td>
          See <a href="pip-search">write up</a>
        </td>
      </tr>
      <tr>
        <td>
          Feedback on pip's docs
        </td>
        <td>
          To gather feedback on pip's docs, supplementing feedback gathered in user interviews
        </td>
        <td>
          See <a href="improving-pips-documentation">write up</a>
        </td>
      </tr>
    </tbody>
  </table>
</div>

## All Results

```{toctree}
:maxdepth: 1

about-our-users
mental-models
users-and-security
ci-cd
personas
prioritizing-features
override-conflicting-dependencies
pip-force-reinstall
pip-search
pip-upgrade-conflict
improving-pips-documentation
```

## Read More

- [Pip team midyear report (blog, July 2020)](https://pyfound.blogspot.com/2020/07/pip-team-midyear-report.html)
- [Creating rapid CLI prototypes with cli-output (blog, Oct 2020)](https://www.ei8fdb.org/prototyping-command-line-interfaces-with-cli-output/)
- [Changes are coming to pip (video)](https://www.youtube.com/watch?v=B4GQCBBsuNU)
- [How should pip handle dependency conflicts when updating already installed packages? (blog, July 2020)](https://www.ei8fdb.org/how-should-pip-handle-conflicts-when-updating-already-installed-packages/)
- [Test pip's alpha resolver and help us document dependency conflicts (blog, May 2020)](https://www.ei8fdb.org/test-pips-alpha-resolver-and-help-us-document-dependency-conflicts/)
- [How do you deal with conflicting dependencies caused by pip installs? (blog, April 2020)](https://www.ei8fdb.org/how-do-you-deal-with-conflicting-dependencies-caused-by-pip-installs/)
- [pip UX studies: response data (blog, March 2020)](https://www.ei8fdb.org/pip-ux-studies-response-data/)

Other PyPA UX work:

- [PyPI User Research (blog, July 2018)](https://whoisnicoleharris.com/2018/07/22/pypi-user-research.html)
- [Warehouse - The Future of PyPI](https://whoisnicoleharris.com/warehouse/)
- [Accessibility on Warehouse (PyPI) (blog, May 2018)](https://whoisnicoleharris.com/2018/05/17/warehouse-accessibility.html)
- [User Testing Warehouse (blog, Mar 2018)](https://whoisnicoleharris.com/2018/03/13/user-testing-warehouse.html)
- [Designing Warehouse - An Overview (blog, Dec 2015)](https://whoisnicoleharris.com/2015/12/31/designing-warehouse-an-overview.html)

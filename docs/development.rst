===========
Development
===========

Pull Requests
=============

- Submit Pull Requests against the `master` branch.
- Provide a good description of what you're doing and why.
- Provide tests that cover your changes and try to run the tests locally first.

**Example**. Assuming you set up GitHub account, forked pip repository from
https://github.com/pypa/pip to your own page via web interface, and your
fork is located at https://github.com/yourname/pip

::

  $ git clone git@github.com:pypa/pip.git
  $ cd pip
  # ...
  $ git diff
  $ git add <modified> ...
  $ git status
  $ git commit

You may reference relevant issues in commit messages (like #1259) to
make GitHub link issues and commits together, and with phrase like
"fixes #1259" you can even close relevant issues automatically. Now
push the changes to your fork::

  $ git push git@github.com:yourname/pip.git

Open Pull Requests page at https://github.com/yourname/pip/pulls and
click "New pull request" and select your fork. That's it.

Pull requests should be self-contained, and limited in scope. Before being
merged, a pull request must be reviewed, and keeping individual PRs limited
in scope makes this far easier. In particular, pull requests must not be
treated as "feature branches", with ongoing development work happening
within the PR. Instead, the feature should be broken up into smaller,
independent parts which can be reviewed and merged individually.

When creating a pull request, avoid including "cosmetic" changes to
code that is unrelated to your change, as these make reviewing the PR
more difficult. Examples include re-flowing text in comments or
documentation, or addition or removal of blank lines or whitespace
within lines. Such changes can be made separately, as a "formatting
cleanup" PR, if needed.


.. _`mailing list`: https://mail.python.org/mailman/listinfo/distutils-sig
.. _`appveyor.yml`: https://github.com/pypa/pip/blob/master/appveyor.yml
.. _`Travis CI Pull Requests`: https://travis-ci.org/pypa/pip/pull_requests
.. _`tools/test-requirements.txt`: https://github.com/pypa/pip/blob/master/tools/test-requirements.txt

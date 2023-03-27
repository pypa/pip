(vcs support)=
# VCS Support

pip supports installing from various version control systems (VCS).
This support requires a working executable to be available (for the version
control system being used). It is used through URL prefixes:

- Git -- `git+`
- Mercurial -- `hg+`
- Subversion -- `svn+`
- Bazaar -- `bzr+`

## Supported VCS

### Git

The supported schemes are `git+file`, `git+https`, `git+ssh`, `git+http`,
`git+git` and `git`. Here are some of the supported forms:

```none
MyProject @ git+ssh://git@git.example.com/MyProject
MyProject @ git+file:///home/user/projects/MyProject
MyProject @ git+https://git.example.com/MyProject
```

```{warning}
The use of `git`, `git+git`, and `git+http` schemes is discouraged.
The former two use [the Git Protocol], which lacks authentication, and HTTP is
insecure due to lack of TLS based encryption.
```

[the Git Protocol]: https://git-scm.com/book/en/v2/Git-on-the-Server-The-Protocols

It is also possible to specify a "git ref" such as branch name, a commit hash or
a tag name:

```none
MyProject @ git+https://git.example.com/MyProject.git@master
MyProject @ git+https://git.example.com/MyProject.git@v1.0
MyProject @ git+https://git.example.com/MyProject.git@da39a3ee5e6b4b0d3255bfef95601890afd80709
MyProject @ git+https://git.example.com/MyProject.git@refs/pull/123/head
```

When passing a commit hash, specifying a full hash is preferable to a partial
hash because a full hash allows pip to operate more efficiently (e.g. by
making fewer network calls).

### Mercurial

The supported schemes are `hg+file`, `hg+http`, `hg+https`, `hg+ssh`
and `hg+static-http`. Here are some of the supported forms:

```
MyProject @ hg+http://hg.myproject.org/MyProject
MyProject @ hg+https://hg.myproject.org/MyProject
MyProject @ hg+ssh://hg.myproject.org/MyProject
MyProject @ hg+file:///home/user/projects/MyProject
```

It is also possible to specify a revision number, a revision hash, a tag name
or a local branch name:

```none
MyProject @ hg+http://hg.example.com/MyProject@da39a3ee5e6b
MyProject @ hg+http://hg.example.com/MyProject@2019
MyProject @ hg+http://hg.example.com/MyProject@v1.0
MyProject @ hg+http://hg.example.com/MyProject@special_feature
```

### Subversion

The supported schemes are `svn`, `svn+svn`, `svn+http`, `svn+https` and
`svn+ssh`. Here are some of the supported forms:

```none
MyProject @ svn+https://svn.example.com/MyProject
MyProject @ svn+ssh://svn.example.com/MyProject
MyProject @ svn+ssh://user@svn.example.com/MyProject
```

You can also give specific revisions to an SVN URL, like so:

```none
-e svn+http://svn.example.com/svn/MyProject/trunk@2019#egg=MyProject
-e svn+http://svn.example.com/svn/MyProject/trunk@{20080101}#egg=MyProject
```

Note that you need to use [Editable VCS installs](#editable-vcs-installs) for
using specific revisions from Subversion.

### Bazaar

The supported schemes are `bzr+http`, `bzr+https`, `bzr+ssh`, `bzr+sftp`,
`bzr+ftp` and `bzr+lp`. Here are the supported forms:

```none
MyProject @ bzr+http://bzr.example.com/MyProject/trunk
MyProject @ bzr+sftp://user@example.com/MyProject/trunk
MyProject @ bzr+ssh://user@example.com/MyProject/trunk
MyProject @ bzr+ftp://user@example.com/MyProject/trunk
MyProject @ bzr+lp:MyProject
```

Tags or revisions can be installed like so:

```none
MyProject @ bzr+https://bzr.example.com/MyProject/trunk@2019
MyProject @ bzr+http://bzr.example.com/MyProject/trunk@v1.0
```

(editable-vcs-installs)=

## Editable VCS installs

VCS projects can be installed in {ref}`editable mode <editable-installs>` (using
the {ref}`--editable <install_--editable>` option) or not.

- The default clone location (for editable installs) is:

  - `<venv path>/src/SomeProject` in virtual environments
  - `<cwd>/src/SomeProject` for global Python installs

  The {ref}`--src <install_--src>` option can be used to modify this location.

- For non-editable installs, the project is built locally in a temp dir and then
  installed normally.

Note that if a satisfactory version of the package is already installed, the
VCS source will not overwrite it without an `--upgrade` flag. Further, pip
looks at the package version, at the target revision to determine what action to
take on the VCS requirement (not the commit itself).

## URL fragments

pip looks at the `subdirectory` fragments of VCS URLs for specifying the path to the
Python package, when it is not in the root of the VCS directory. eg: `pkg_dir`.

pip also looks at the `egg` fragment specifying the "project name". In practice the
`egg` fragment is only required to help pip determine the VCS clone location in editable
mode. In all other circumstances, the `egg` fragment is not necessary and its use is
discouraged.

The `egg` fragment **should** be a bare
[PEP 508](https://peps.python.org/pep-0508/) project name. Anything else
is not guaranteed to work.

````{admonition} Example
If your repository layout is:

```
pkg_dir
├── setup.py  # setup.py for package "pkg"
└── some_module.py
other_dir
└── some_file
some_other_file
```

Then, to install from this repository, the syntax would be:

```{pip-cli}
$ pip install "pkg @ vcs+protocol://repo_url/#subdirectory=pkg_dir"
```

or:

```{pip-cli}
$ pip install -e "vcs+protocol://repo_url/#egg=pkg&subdirectory=pkg_dir"
```
````

# Installation Report

```{versionadded} 22.2
```

```{versionchanged} 23.0
``version`` has been bumped to ``1`` and the format declared stable.
```

The `--report` option of the pip install command produces a detailed JSON report of what
it did install (or what it would have installed, if used with the `--dry-run` option).

```{note}
When considering use cases, please bear in mind that

- while the `--report` option may be used to implement requirement locking tools (among
  other use cases), this format is *not* meant to be a lock file format as such;
- there is no plan for pip to accept an installation report as input for the `install`,
  `download` or `wheel` commands;
- while the `--report` option and this format is a supported pip feature,
  it is *not* a PyPA interoperability standard and as such its evolution is governed by
  the pip processes and not the PyPA standardization processes.
```

## Specification

The report is a JSON object with the following properties:

- `version`: the string `1`. It will change only if
  and when backward incompatible changes are introduced, such as removing mandatory
  fields or changing the semantics or data type of existing fields. The introduction of
  backward incompatible changes will follow the usual pip processes such as the
  deprecation cycle or feature flags. Tools must check this field to ensure they support
  the corresponding version.

- `pip_version`: a string with the version of pip used to produce the report.

- `install`: an array of [`InstallationReportItem`](InstallationReportItem) representing
  the distribution packages (to be) installed.

- `environment`: an object describing the environment where the installation report was
  generated. See [PEP 508 environment
  markers](https://peps.python.org/pep-0508/#environment-markers) for more information.
  Values have a string type.

(InstallationReportItem)=

An `InstallationReportItem` is an object describing a (to be) installed distribution
package with the following properties:

- `metadata`: the metadata of the distribution, converted to a JSON object according to
  the [PEP 566
  transformation](https://www.python.org/dev/peps/pep-0566/#json-compatible-metadata).

- `is_direct`: `true` if the requirement was provided as, or constrained to, a direct
  URL reference. `false` if the requirements was provided as a name and version
  specifier.

- `download_info`: Information about the artifact (to be) downloaded for installation,
  using the [direct URL data
  structure](https://packaging.python.org/en/latest/specifications/direct-url-data-structure/).
  When `is_direct` is `true`, this field is the same as the
  [`direct_url.json`](https://packaging.python.org/en/latest/specifications/direct-url)
  metadata, otherwise it represents the URL of the artifact obtained from the index or
  `--find-links`.

  ```{note}
  For source archives, `download_info.archive_info.hashes` may
  be absent when the requirement was installed from the wheel cache
  and the cache entry was populated by an older pip version that did not
  record the origin URL of the downloaded artifact.
  ```

- `requested`: `true` if the requirement was explicitly provided by the user, either
  directly via a command line argument or indirectly via a requirements file. `false`
  if the requirement was installed as a dependency of another requirement.

- `requested_extras`: extras requested by the user. This field is only present when the
  `requested` field is true.

## Example

The following command:

```console
pip install \
  --ignore-installed --dry-run --quiet \
  --report - \
  "pydantic>=1.9" git+https://github.com/pypa/packaging@main
```

will produce an output similar to this (metadata abriged for brevity):

```json
{
  "version": "1",
  "pip_version": "22.2",
  "install": [
    {
      "download_info": {
        "url": "https://files.pythonhosted.org/packages/a4/0c/fbaa7319dcb5eecd3484686eb5a5c5702a6445adb566f01aee6de3369bc4/pydantic-1.9.1-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
        "archive_info": {
          "hashes": {
            "sha256": "18f3e912f9ad1bdec27fb06b8198a2ccc32f201e24174cec1b3424dda605a310"
          }
        }
      },
      "is_direct": false,
      "requested": true,
      "metadata": {
        "name": "pydantic",
        "version": "1.9.1",
        "requires_dist": [
          "typing-extensions (>=3.7.4.3)",
          "dataclasses (>=0.6) ; python_version < \"3.7\"",
          "python-dotenv (>=0.10.4) ; extra == 'dotenv'",
          "email-validator (>=1.0.3) ; extra == 'email'"
        ],
        "requires_python": ">=3.6.1",
        "provides_extra": [
          "dotenv",
          "email"
        ]
      }
    },
    {
      "download_info": {
        "url": "https://github.com/pypa/packaging",
        "vcs_info": {
          "vcs": "git",
          "requested_revision": "main",
          "commit_id": "4f42225e91a0be634625c09e84dd29ea82b85e27"
        }
      },
      "is_direct": true,
      "requested": true,
      "metadata": {
        "name": "packaging",
        "version": "21.4.dev0",
        "requires_dist": [
          "pyparsing (!=3.0.5,>=2.0.2)"
        ],
        "requires_python": ">=3.7"
      }
    },
    {
      "download_info": {
        "url": "https://files.pythonhosted.org/packages/6c/10/a7d0fa5baea8fe7b50f448ab742f26f52b80bfca85ac2be9d35cdd9a3246/pyparsing-3.0.9-py3-none-any.whl",
        "archive_info": {
          "hashes": {
            "sha256": "5026bae9a10eeaefb61dab2f09052b9f4307d44aee4eda64b309723d8d206bbc"
          }
        }
      },
      "is_direct": false,
      "requested": false,
      "metadata": {
        "name": "pyparsing",
        "version": "3.0.9",
        "requires_dist": [
          "railroad-diagrams ; extra == \"diagrams\"",
          "jinja2 ; extra == \"diagrams\""
        ],
        "requires_python": ">=3.6.8"
      }
    },
    {
      "download_info": {
        "url": "https://files.pythonhosted.org/packages/75/e1/932e06004039dd670c9d5e1df0cd606bf46e29a28e65d5bb28e894ea29c9/typing_extensions-4.2.0-py3-none-any.whl",
        "archive_info": {
          "hashes": {
            "sha256": "6657594ee297170d19f67d55c05852a874e7eb634f4f753dbd667855e07c1708"
          }
        }
      },
      "is_direct": false,
      "requested": false,
      "metadata": {
        "name": "typing_extensions",
        "version": "4.2.0",
        "requires_python": ">=3.7"
      }
    }
  ],
  "environment": {
    "implementation_name": "cpython",
    "implementation_version": "3.10.5",
    "os_name": "posix",
    "platform_machine": "x86_64",
    "platform_release": "5.13-generic",
    "platform_system": "Linux",
    "platform_version": "...",
    "python_full_version": "3.10.5",
    "platform_python_implementation": "CPython",
    "python_version": "3.10",
    "sys_platform": "linux"
  }
}
```

import io
import itertools
import os.path
import re

import invoke
import yaml

from . import paths

TRAVIS = """
language: python

python:
{python}

env:
{env}

install: .travis/install.sh

script: .travis/run.sh

branches:
  only:
    - master
    - develop
    - /^[0-9]+\.[0-9]+\.X$/

notifications:
  irc:
    channels:
      - "irc.freenode.org#pypa-dev"
    use_notice: true
    skip_join: true

"""


def _write_tox_env(fp, config):
    for config, value in sorted(config.items()):
        if isinstance(value, str):
            pass  # str values do not need anything done to them
        elif isinstance(value, list):
            value = "".join([
                "\n",
                "\n".join("    {0}".format(v) for v in value)
            ])
        else:
            raise ValueError("Unknown type {0}".format(type(value)))

        fp.write("{0} = {1}\n".format(config, value))


@invoke.task
def matrix():
    with open(os.path.join(paths.PROJECT_ROOT, ".matrix.yml")) as fp:
        matrix_config = yaml.safe_load(fp)

    labels = matrix_config["matrix"]
    key_format = "-".join(["{" + k + "}" for k in labels])
    axes = [[(a, i) for i in sorted(matrix_config[a])] for a in labels]

    envs = [
        (key_format.format(**dict(a)), dict(a))
        for a in itertools.product(*axes)
    ]

    extras = matrix_config.get("extra", {})

    # Write the tox.ini file
    with io.open(
            os.path.join(paths.PROJECT_ROOT, "tox.ini"), "w",
            encoding="utf8") as fp:

        # Add an environment for each of our matrix rows
        for key, items in envs:
            # Write out a section header for this environment
            fp.write("[testenv:{0}]\n".format(key))

            # Get our configuration values
            config = matrix_config.get("base", {}).copy()
            for axis, a_value in sorted(
                    items.items(), key=lambda x: labels.index(x[0])):
                config.update(matrix_config[axis][a_value])

            # Write out the configuration items for this environment)
            _write_tox_env(fp, config)

            # Add an empty line at the end of this environment section
            fp.write("\n")

        # Add any extra environments we have
        for key, config in sorted(extras.items()):
            # Write out a section header for this environment
            fp.write("[testenv:{0}]\n".format(key))

            # Write out the configuration items for this environment
            _write_tox_env(fp, config)

            # Add an empty line at the end of this environment section
            fp.write("\n")

    # Write the .travis.yml file
    with io.open(
            os.path.join(paths.PROJECT_ROOT, ".travis.yml"), "w",
            encoding="utf8") as fp:

        evars = [
            dict(i)
            for i in set(
                tuple((k, v) for k, v in e.items() if k != "python")
                for _, e in sorted(envs)
            )
        ]

        pythons = []
        for python in matrix_config["python"]:
            m = re.search(r"^py([23])([0-9])$", python)
            if m:
                pythons.append(".".join(m.groups()))
            else:
                pythons.append(python)

        env = "\n".join([
            "  - {0}".format(
                " ".join("{0}={1}".format(k.upper(), v) for k, v in e.items())
            )
            for e in evars
        ])

        includes = [
            "    - python: \"2.7\"\n      env: TOXENV={0}\n".format(e)
            for e in sorted(extras)
        ]

        fp.write(
            TRAVIS.format(
                env=env,
                python="\n".join([
                    "  - \"{0}\"".format(i) for i in sorted(pythons)
                ]),
            ),
        )

        # If we have any includes, write them to the file
        if includes:
            fp.write("matrix:\n")
            fp.write("  include:\n")
            fp.write("\n".join(includes))
            fp.write("\n")

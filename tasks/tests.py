import io
import itertools
import os.path

import invoke
import yaml

from . import paths

TRAVIS = """
language: python

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

env:
{envlist}
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
        fp.write(
            TRAVIS.format(
                envlist="\n".join(
                    itertools.chain(
                        ["  - TOXENV={0}".format(e) for e, _ in (envs)],
                        ["  - TOXENV={0}".format(e) for e in sorted(extras)],
                    ),
                )
            )
        )

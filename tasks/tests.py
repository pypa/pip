import io
import itertools
import os.path

import invoke
import yaml

from . import paths


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

    with io.open(
            os.path.join(paths.PROJECT_ROOT, "tox.ini"), "w",
            encoding="utf8") as fp:

        # Add an environment for each of our matrix rows
        for key, items in [
                (key_format.format(**dict(a)), dict(a))
                for a in itertools.product(*axes)]:
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
        for key, config in sorted(matrix_config.get("extra", {}).items()):
            # Write out a section header for this environment
            fp.write("[testenv:{0}]\n".format(key))

            # Write out the configuration items for this environment
            _write_tox_env(fp, config)

            # Add an empty line at the end of this environment section
            fp.write("\n")

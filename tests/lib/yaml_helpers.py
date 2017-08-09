"""
"""

import pytest
import yaml


def generate_yaml_tests(directory):
    for yml_file in directory.glob("*/*.yml"):
        data = yaml.safe_load(yml_file.read_text())
        assert "cases" in data, "A fixture needs cases to be used in testing"

        # Strip the parts of the directory to only get a name without
        # extension and resolver directory
        base_name = str(yml_file)[len(str(directory)) + 1:-4]

        base = data.get("base", {})
        cases = data["cases"]

        for i, case_template in enumerate(cases):
            case = base.copy()
            case.update(case_template)

            case[":name:"] = base_name
            if len(cases) > 1:
                case[":name:"] += "-" + str(i)

            if case.pop("skip", False):
                case = pytest.param(case, marks=pytest.mark.xfail)

            yield case


def id_func(param):
    """Give a nice parameter name to the generated function parameters
    """
    if isinstance(param, dict) and ":name:" in param:
        return param[":name:"]

    retval = str(param)
    if len(retval) > 25:
        retval = retval[:20] + "..." + retval[-2:]
    return retval

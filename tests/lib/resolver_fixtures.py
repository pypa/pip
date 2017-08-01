"""
"""

import pytest
import yaml


def generate_fixture_cases(fixture_dir):
    for fixture_file in fixture_dir.glob("*/*.yml"):
        data = yaml.safe_load(fixture_file.read_text())
        assert "cases" in data, "A fixture needs cases to be used in testing"

        # Strip the parts of the fixture_dir to only get a name without
        # extension and resolver directory
        base_name = str(fixture_file)[len(str(fixture_dir)) + 1:-4]

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


def fixture_id_func(param):
    """Give a nice parameter name to the fixtured function
    """
    if isinstance(param, dict) and ":name:" in param:
        return param[":name:"]

    retval = str(param)
    if len(retval) > 25:
        retval = retval[:20] + "..." + retval[-2:]
    return retval

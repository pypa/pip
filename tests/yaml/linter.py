import re
import sys
from pprint import pprint

import yaml

sys.path.insert(0, '../../src')
sys.path.insert(0, '../..')


def check_dict(d, required=None, optional=None):
    assert isinstance(d, dict)
    if required is None:
        required = []
    if optional is None:
        optional = []
    for key in required:
        if key not in d:
            sys.exit("key %r is required" % key)
    allowed_keys = set(required)
    allowed_keys.update(optional)
    for key in d.keys():
        if key not in allowed_keys:
            sys.exit("key %r is not allowed.  Allowed keys are: %r" %
                     (key, allowed_keys))


def lint_case(case, verbose=False):
    from tests.functional.test_yaml import convert_to_dict

    if verbose:
        print("--- linting case ---")
        pprint(case)

    check_dict(case, optional=['available', 'request', 'response', 'skip'])
    available = case.get("available", [])
    requests = case.get("request", [])
    responses = case.get("response", [])
    assert isinstance(available, list)
    assert isinstance(requests, list)
    assert isinstance(responses, list)
    assert len(requests) == len(responses)

    for package in available:
        if isinstance(package, str):
            package = convert_to_dict(package)
        if verbose:
            pprint(package)
        check_dict(package,
                   required=['name', 'version'],
                   optional=['depends', 'extras'])
        version = package['version']
        assert isinstance(version, str), repr(version)

    for request, response in zip(requests, responses):
        check_dict(request, optional=['install', 'uninstall', 'options'])
        check_dict(response, optional=['state', 'error'])
        assert len(response) >= 1
        assert isinstance(response.get('state') or [], list)
        error = response.get('error')
        if error:
            check_dict(error, optional=['code', 'stderr'])
            stderr = error.get('stderr')
            if stderr:
                if isinstance(stderr, str):
                    patters = [stderr]
                elif isinstance(stderr, list):
                    patters = stderr
                else:
                    raise "string or list expected, found %r" % stderr
                for patter in patters:
                    re.compile(patter, re.I)


def lint_yml(yml_file, verbose=False):
    if verbose:
        print("=== linting: %s ===" % yml_file)
    assert yml_file.endswith(".yml")
    with open(yml_file) as fi:
        data = yaml.safe_load(fi)
    if verbose:
        pprint(data)

    check_dict(data, required=['cases'], optional=['base'])
    base = data.get("base", {})
    cases = data["cases"]
    for _, case_template in enumerate(cases):
        case = base.copy()
        case.update(case_template)
        lint_case(case, verbose)


if __name__ == '__main__':
    from optparse import OptionParser

    p = OptionParser(usage="usage: %prog [options] FILE ...",
                     description="linter for pip's yaml test FILE(s)")

    p.add_option('-v', '--verbose',
                 action="store_true")

    opts, args = p.parse_args()

    if len(args) < 1:
        p.error('at least one argument required, try -h')

    for yml_file in args:
        lint_yml(yml_file, opts.verbose)

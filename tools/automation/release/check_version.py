"""Checks if the version is acceptable, as per this project's release process.
"""

import sys
from datetime import datetime
from typing import Optional

from packaging.version import InvalidVersion, Version


def is_this_a_good_version_number(string: str) -> Optional[str]:
    try:
        v = Version(string)
    except InvalidVersion as e:
        return str(e)

    if v.local:
        return "Nope. PyPI refuses local release versions."

    if v.dev:
        return "No development releases on PyPI. What are you even thinking?"

    if v.pre and v.pre[0] != "b":
        return "Only beta releases are allowed. No alphas."

    release = v.release
    expected_major = datetime.now().year % 100

    if len(release) not in [2, 3]:
        return "Not of the form: {0}.N or {0}.N.P".format(expected_major)

    return None


def main() -> None:
    problem = is_this_a_good_version_number(sys.argv[1])
    if problem is not None:
        print("ERROR:", problem)
        sys.exit(1)


if __name__ == "__main__":
    main()

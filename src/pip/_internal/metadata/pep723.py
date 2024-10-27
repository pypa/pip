import re
from typing import List, Optional

from pip._internal.req.req_install import InstallRequirement
from pip._vendor import tomli as tomllib
from pip._vendor.packaging.requirements import Requirement

REGEX = r'(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$'


def pep723_metadata(scriptfile: str) -> dict:
    with open(scriptfile, "r") as f:
        script = f.read()

    name = 'script'
    matches = list(
        filter(lambda m: m.group('type') == name, re.finditer(REGEX, script))
    )
    if len(matches) > 1:
        raise ValueError(f'Multiple {name} blocks found')
    elif len(matches) == 1:
        content = ''.join(
            line[2:] if line.startswith('# ') else line[1:]
            for line in matches[0].group('content').splitlines(keepends=True)
        )
        return tomllib.loads(content)
    else:
        raise ValueError(f"File does not contain 'script' metadata: {scriptfile!r}")


def parse_pep723_requirements(scriptfile: str) -> List[InstallRequirement]:
    md = pep723_metadata(scriptfile)
    reqs = []

    for rq in md.get("dependencies", []):
        reqs.append(
            InstallRequirement(Requirement(rq), comes_from=None)
        )

    return reqs

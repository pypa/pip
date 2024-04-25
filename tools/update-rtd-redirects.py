"""Update the 'exact' redirects on Read the Docs to match an in-tree file's contents.

Relevant API reference: https://docs.readthedocs.io/en/stable/api/v3.html#redirects
"""

import operator
import os
import sys
from pathlib import Path
from typing import Dict, List

import httpx
import rich
import yaml

try:
    _TOKEN = os.environ["RTD_API_TOKEN"]
except KeyError:
    rich.print(
        "[bold]error[/]: [red]No API token provided. Please set `RTD_API_TOKEN`.[/]",
        file=sys.stderr,
    )
    sys.exit(1)

RTD_API_HEADERS = {"Authorization": f"token {_TOKEN}"}
RTD_API_BASE_URL = "https://readthedocs.org/api/v3/projects/pip/"
REPO_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def next_step(msg: str) -> None:
    rich.print(f"> [blue]{msg}[/]")


def log_response(response: httpx.Response) -> None:
    request = response.request
    rich.print(f"[bold magenta]{request.method}[/] {request.url} -> {response}")


def get_rtd_api() -> httpx.Client:
    return httpx.Client(
        headers=RTD_API_HEADERS,
        base_url=RTD_API_BASE_URL,
        event_hooks={"response": [log_response]},
    )


# --------------------------------------------------------------------------------------
# Actual logic
# --------------------------------------------------------------------------------------
next_step("Loading local redirects from the yaml file.")

with open(REPO_ROOT / ".readthedocs-custom-redirects.yml") as f:
    local_redirects = yaml.safe_load(f)

rich.print("Loaded local redirects!")
for src, dst in sorted(local_redirects.items()):
    rich.print(f"  [yellow]{src}[/] --> {dst}")
rich.print(f"{len(local_redirects)} entries.")


next_step("Fetch redirects configured on RTD.")

with get_rtd_api() as rtd_api:
    response = rtd_api.get("redirects/")
    response.raise_for_status()

    rtd_redirects = response.json()

for redirect in sorted(
    rtd_redirects["results"], key=operator.itemgetter("type", "from_url", "to_url")
):
    if redirect["type"] != "exact":
        rich.print(f"  [magenta]{redirect['type']}[/]")
        continue

    pk = redirect["pk"]
    src = redirect["from_url"]
    dst = redirect["to_url"]
    rich.print(f"  [yellow]{src}[/] -({pk:^5})-> {dst}")

rich.print(f"{rtd_redirects['count']} entries.")


next_step("Compare and determine modifications.")

redirects_to_remove: List[int] = []
redirects_to_add: Dict[str, str] = {}

for redirect in rtd_redirects["results"]:
    if redirect["type"] != "exact":
        continue

    rtd_src = redirect["from_url"]
    rtd_dst = redirect["to_url"]
    redirect_id = redirect["pk"]

    if rtd_src not in local_redirects:
        redirects_to_remove.append(redirect_id)
        continue

    local_dst = local_redirects[rtd_src]
    if local_dst != rtd_dst:
        redirects_to_remove.append(redirect_id)
        redirects_to_add[rtd_src] = local_dst

    del local_redirects[rtd_src]

for src, dst in sorted(local_redirects.items()):
    redirects_to_add[src] = dst
    del local_redirects[src]

assert not local_redirects

if not redirects_to_remove:
    rich.print("Nothing to remove.")
else:
    rich.print(f"To remove: ({len(redirects_to_remove)} entries)")
    for redirect_id in redirects_to_remove:
        rich.print(" ", redirect_id)

if not redirects_to_add:
    rich.print("Nothing to add.")
else:
    rich.print(f"To add: ({len(redirects_to_add)} entries)")
    for src, dst in redirects_to_add.items():
        rich.print(f"  {src} --> {dst}")


next_step("Update the RTD redirects.")

if not (redirects_to_add or redirects_to_remove):
    rich.print("[green]Nothing to do![/]")
    sys.exit(0)

exit_code = 0
with get_rtd_api() as rtd_api:
    for redirect_id in redirects_to_remove:
        response = rtd_api.delete(f"redirects/{redirect_id}/")
        response.raise_for_status()
        if response.status_code != 204:
            rich.print("[red]This might not have been removed correctly.[/]")
            exit_code = 1

    for src, dst in redirects_to_add.items():
        response = rtd_api.post(
            "redirects/",
            json={"from_url": src, "to_url": dst, "type": "exact"},
        )
        response.raise_for_status()
        if response.status_code != 201:
            rich.print("[red]This might not have been added correctly.[/]")
            exit_code = 1

sys.exit(exit_code)

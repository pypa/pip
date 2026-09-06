"""Dependency graphs for pip's offline resolver benchmarks."""

from __future__ import annotations

from pathlib import Path

from . import _support as workloads


class Scenario:
    names = [
        "single",
        "application",
        "pinned",
        "backtracking",
        "selected",
        "stress",
        "wrong-package",
        "transitive",
        "unsatisfiable",
        "nab-basic",
        "nab-constraint",
        "nab-extras",
        "nab-strategy",
        "nab-backtracking",
        "nab-unsatisfiable",
        "nab-backjump",
    ]

    def __init__(self, root: Path, graph: str) -> None:
        self.root = root
        self.wheelhouse = self.root / "wheels"
        self.wheelhouse.mkdir()
        self.constraints = []
        self.unsatisfiable = graph in {"unsatisfiable", "nab-unsatisfiable"}
        if graph in {"single", "application", "pinned"}:
            workloads.make_dependency_graph(self.wheelhouse)
            if graph == "single":
                self.requirements, self.count = (["leaf-0"], 1)
            elif graph == "application":
                self.requirements, self.count = (["application"], 31)
            else:
                self.requirements = [f"middle-{index}==2.2.0" for index in range(10)]
                self.count = 30
        elif graph == "backtracking":
            workloads.make_backtracking_graph(self.wheelhouse)
            self.requirements, self.count = (["conflicting"], 4)
        elif graph == "selected":
            workloads.make_selected_dependency_graph(self.wheelhouse)
            self.requirements, self.count = (["selected-application"], 99)
        elif graph == "stress":
            workloads.make_stress_graph(self.wheelhouse)
            self.requirements = [f"stress-{index}" for index in range(88)]
            self.count = 176
        elif graph in {"wrong-package", "transitive"}:
            builder = (
                workloads.make_wrong_package_graph
                if graph == "wrong-package"
                else workloads.make_transitive_backtracking_graph
            )
            builder(
                self.wheelhouse,
                "boto3-urllib3",
                versions=64 if graph == "wrong-package" else 256,
            )
            self.requirements, self.count = (["boto3-urllib3-root"], 4)
        elif graph == "unsatisfiable":
            for index in range(24):
                for version in ("1.0.0", "2.0.0"):
                    workloads.make_wheel(
                        self.wheelhouse, f"unsat-shared-{index}", version
                    )
                workloads.make_wheel(
                    self.wheelhouse,
                    f"unsat-branch-{index}",
                    "1.0.0",
                    requires=[f"unsat-shared-{index}==1.0.0"],
                )
            self.requirements = [
                r
                for i in range(24)
                for r in (f"unsat-branch-{i}", f"unsat-shared-{i}==2.0.0")
            ]
        elif graph in {"nab-backtracking", "nab-unsatisfiable"}:
            workloads.make_nab_pip_backtracking_family(
                self.wheelhouse, "nab-smoke-pip", 24, unsatisfiable=self.unsatisfiable
            )
            self.requirements, self.count = (["nab-smoke-pip-a"], 3)
        elif graph == "nab-backjump":
            workloads.make_nab_deep_backjump_family(
                self.wheelhouse, "nab-smoke-backjump", 6
            )
            self.requirements = [
                "nab-smoke-backjump-pivot",
                "nab-smoke-backjump-link-1",
            ]
            self.count = 14
        else:
            workloads.make_nab_smoke_fixture(self.wheelhouse)
            self.requirements, self.count = {
                "nab-basic": (["nab-smoke-basic"], 2),
                "nab-constraint": (["nab-smoke-constrained"], 1),
                "nab-extras": (["nab-smoke-extra-app[speed]"], 4),
                "nab-strategy": (
                    ["nab-smoke-strategy-app==1.0.0", "nab-smoke-strategy-direct>=1"],
                    3,
                ),
            }[graph]
            if graph == "nab-constraint":
                self.constraints = ["nab-smoke-constrained<3"]

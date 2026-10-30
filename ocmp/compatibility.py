"""
compatibility.py: Which macOS versions can this PC run?

Runs the planner once per macOS version (no downloads) and summarises
what each target would use, warn about, or refuse.
"""

import copy
from dataclasses import dataclass, field
from typing import List

from .datasets import os_data
from .efi_builder import planner


@dataclass
class Row:
    kernel: int
    supported: bool
    smbios: str = ""
    platform: str = ""
    warnings: List[str] = field(default_factory=list)
    reason: str = ""

    @property
    def name(self) -> str:
        return os_data.label(self.kernel)

    @property
    def status(self) -> str:
        if not self.supported:
            return "No"
        return "Yes, with warnings" if self.warnings else "Yes"


def check(profile, constants) -> List[Row]:
    rows = []
    for kernel in sorted(os_data.MARKETING_NAMES, reverse=True):
        c = copy.copy(constants)
        c.target_os = int(kernel)
        c.custom_smbios = ""
        try:
            plan = planner.Planner(profile, c).plan()
            rows.append(Row(int(kernel), True, plan.smbios, plan.platform, list(plan.warnings)))
        except planner.PlanError as e:
            rows.append(Row(int(kernel), False, reason=str(e)))
    return rows


def best(rows: List[Row]):
    for row in rows:                 # newest first
        if row.supported:
            return row
    return None


def report(profile, constants) -> str:
    rows = check(profile, constants)
    top = best(rows)
    lines = [f"Compatibility for: {profile.short_model()}", f"CPU: {profile.summary()}", ""]
    width = max(len(r.name) for r in rows)
    for row in rows:
        detail = f"{row.smbios}" if row.supported else row.reason.split(":")[0].split(".")[0]
        lines.append(f"  {row.name:<{width}}  {row.status:<18}  {detail}")
    lines.append("")
    lines.append(f"Newest macOS for this PC: {top.name} as {top.smbios}" if top else "This PC can't run any supported macOS.")
    return "\n".join(lines)


def summary(profile, constants) -> str:
    top = best(check(profile, constants))
    return f"Newest macOS: {os_data.name(top.kernel)} ({top.smbios})" if top else "No supported macOS for this hardware"

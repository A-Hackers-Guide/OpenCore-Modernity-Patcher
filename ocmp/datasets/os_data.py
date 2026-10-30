"""
os_data.py: macOS versions, by Darwin major version
"""

import enum


class os_data(enum.IntEnum):
    high_sierra = 17
    mojave      = 18
    catalina    = 19
    big_sur     = 20
    monterey    = 21
    ventura     = 22
    sonoma      = 23
    sequoia     = 24
    tahoe       = 25
    golden_gate = 27    # Darwin skipped 26 to match macOS 27 (checked on a real macOS 27.0.1 install)


MARKETING_NAMES = {
    os_data.high_sierra: ("macOS High Sierra", "10.13"),
    os_data.mojave:      ("macOS Mojave",      "10.14"),
    os_data.catalina:    ("macOS Catalina",    "10.15"),
    os_data.big_sur:     ("macOS Big Sur",     "11"),
    os_data.monterey:    ("macOS Monterey",    "12"),
    os_data.ventura:     ("macOS Ventura",     "13"),
    os_data.sonoma:      ("macOS Sonoma",      "14"),
    os_data.sequoia:     ("macOS Sequoia",     "15"),
    os_data.tahoe:       ("macOS Tahoe",       "26"),
    os_data.golden_gate: ("macOS Golden Gate", "27"),
}

# Newest macOS that still runs on Intel/AMD hardware
PC_MAX = os_data.tahoe

GOLDEN_GATE_DIAGNOSIS = (
    "macOS Golden Gate (27) is Apple-silicon only and can't run on any PC. "
    "Inspecting a real macOS 27.0.1 install shows: 0 Intel-capable built-in apps besides the Installer, "
    "no Intel kernel collection, and no Intel/AMD graphics or X86 power-management drivers. "
    "Apple's recovery catalog also offers no Intel Mac anything newer than 26.7. "
    "macOS Tahoe (26) is the newest macOS a PC can run."
)


def pc_supported(kernel: int) -> bool:
    return int(kernel) <= PC_MAX


def name(kernel: int) -> str:
    return MARKETING_NAMES[os_data(kernel)][0]


def label(kernel: int) -> str:
    marketing, number = MARKETING_NAMES[os_data(kernel)]
    return f"{marketing} ({number})"


def min_kernel(kernel: int) -> str:
    return f"{int(kernel)}.0.0"


def max_kernel(kernel: int) -> str:
    return f"{int(kernel)}.99.99"

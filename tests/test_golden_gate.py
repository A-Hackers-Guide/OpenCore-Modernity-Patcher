"""
macOS Golden Gate diagnosis, compatibility report and serial persistence
"""

import json
import plistlib
import struct
from pathlib import Path

import pytest

from ocmp import compatibility, constants, hardware, macos_inspector
from ocmp.datasets import os_data
from ocmp.efi_builder import build, planner

PROFILES = Path(__file__).resolve().parent.parent / "examples" / "profiles"
X86, ARM = macos_inspector.CPU_TYPE_X86_64, macos_inspector.CPU_TYPE_ARM64


def thin(cputype: int) -> bytes:
    return struct.pack("<Ii", 0xFEEDFACF, cputype) + b"\0" * 24


def fat(*cputypes: int) -> bytes:
    data = struct.pack(">II", 0xCAFEBABE, len(cputypes))
    for cputype in cputypes:
        data += struct.pack(">iiIII", cputype, 0, 0, 0, 0)
    return data


def make_app(root: Path, folder: str, name: str, binary: bytes) -> None:
    app = root / folder / f"{name}.app" / "Contents"
    (app / "MacOS").mkdir(parents=True)
    (app / "MacOS" / name).write_bytes(binary)
    (app / "Info.plist").write_bytes(plistlib.dumps({"CFBundleExecutable": name}))


def make_system(root: Path, version: str, intel: bool) -> Path:
    core = root / "System/Library/CoreServices"
    core.mkdir(parents=True)
    (core / "SystemVersion.plist").write_bytes(plistlib.dumps(
        {"ProductName": "macOS", "ProductUserVisibleVersion": version, "ProductBuildVersion": "TEST"}))
    make_app(root, "System/Applications", "Notes", fat(X86, ARM) if intel else thin(ARM))
    make_app(root, "System/Applications", "Safari", fat(X86, ARM) if intel else thin(ARM))
    (root / "System/Library/Kernels").mkdir(parents=True)
    (root / "System/Library/Kernels/kernel").write_bytes(thin(X86) + b"Darwin Kernel Version 99.0.0: test\0")
    (root / "System/Library/Extensions").mkdir(parents=True)
    if intel:
        (root / "System/Library/KernelCollections").mkdir(parents=True)
        (root / "System/Library/KernelCollections/BootKernelExtensions.kc").write_bytes(b"kc")
        (root / "System/Library/Extensions/X86PlatformPlugin.kext").mkdir()
    return root


def test_architectures(tmp_path):
    for name, data, expected in [("thin_arm", thin(ARM), {"arm64"}), ("thin_x86", thin(X86), {"x86_64"}),
                                 ("universal", fat(X86, ARM), {"x86_64", "arm64"}), ("text", b"#!/bin/sh\n", set())]:
        (tmp_path / name).write_bytes(data)
        assert macos_inspector.architectures(tmp_path / name) == expected


def test_inspector_flags_apple_silicon_only_system(tmp_path):
    result = macos_inspector.inspect(make_system(tmp_path, "27.0.1", intel=False))
    assert not result.pc_capable
    assert result.apps_checked == 2 and result.apps_with_intel == 0
    assert result.kernel_x86 == "Darwin Kernel Version 99.0.0: test"
    assert "cannot boot on a PC" in result.verdict()


def test_inspector_accepts_intel_system(tmp_path):
    result = macos_inspector.inspect(make_system(tmp_path, "26.7", intel=True))
    assert result.pc_capable
    assert "can be targeted on PCs" in result.verdict()


def test_golden_gate_is_refused_with_diagnosis():
    c = constants.Constants()
    c.target_os = os_data.os_data.golden_gate
    with pytest.raises(planner.PlanError, match="Apple-silicon only"):
        planner.Planner(hardware.HardwareProfile.load(PROFILES / "kvm-amd-host.json"), c).plan()


def test_compatibility_newest_is_tahoe():
    c = constants.Constants()
    rows = compatibility.check(hardware.HardwareProfile.load(PROFILES / "amd-ryzen5600x-rx6600.json"), c)
    assert rows[0].kernel == os_data.os_data.golden_gate and not rows[0].supported
    assert compatibility.best(rows).kernel == os_data.os_data.tahoe
    assert not [r for r in rows if r.kernel == os_data.os_data.big_sur][0].supported   # Navi 23 needs Monterey


def test_saved_serial_is_reused(tmp_path, monkeypatch):
    c = constants.Constants()
    c.data_path = tmp_path
    builder = build.BuildOpenCore(hardware.HardwareProfile.load(PROFILES / "intel-coffeelake-rx580.json"), c)
    builder.plan = planner.Planner(builder.hw, c).plan()
    saved = {"model": "iMac19,1", "serial": "C02ABCDEFGHI", "mlb": "C0212345678901234", "uuid": "UUID-1", "rom": "020000000001"}
    (tmp_path / "smbios").mkdir()
    (tmp_path / "smbios" / "iMac19_1.json").write_text(json.dumps(saved), encoding="utf-8")
    monkeypatch.setattr(builder, "_macserial", lambda *a: pytest.fail("should reuse the saved serial"))
    smbios = builder._smbios(tmp_path)
    assert smbios["SystemSerialNumber"] == "C02ABCDEFGHI"
    assert smbios["SystemUUID"] == "UUID-1"
    assert smbios["ROM"] == bytes.fromhex("020000000001")

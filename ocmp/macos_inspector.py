"""
macos_inspector.py: Can this macOS run on a PC?

Inspects a macOS system (the running one, or a mounted/copied system
volume) and reports whether Apple still ships what an Intel/AMD PC needs.
Pure Python Mach-O parsing, so it works on Windows and Linux against a
copied system folder too, not just on a Mac.

This is how macOS 27 "Golden Gate" was diagnosed: its built-in apps,
graphics drivers and kernel collections are Apple-silicon only, so it
can't be booted on x86 hardware at all.
"""

import struct
import plistlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Set

CPU_TYPE_X86_64 = 0x01000007
CPU_TYPE_ARM64  = 0x0100000C

FAT_MAGICS  = {0xCAFEBABE: ">", 0xBEBAFECA: "<"}
FAT64_MAGIC = 0xCAFEBABF
THIN_MAGICS = {0xFEEDFACF: ">", 0xCFFAEDFE: "<"}

# Kexts a PC can't do without (graphics and Intel power management)
PC_CRITICAL_KEXTS = [
    "X86PlatformPlugin.kext", "AppleIntelCPUPowerManagement.kext",
    "AMDRadeonX6000.kext", "AMDRadeonX5000.kext", "AMDRadeonX4000.kext",
    "AppleIntelKBLGraphics.kext", "AppleIntelCFLGraphicsFramebuffer.kext", "AppleIntelICLGraphics.kext",
]


def architectures(path: Path) -> Set[str]:
    """
    CPU architectures in a Mach-O file ("x86_64", "arm64"); empty if not Mach-O
    """
    try:
        with open(path, "rb") as f:
            head = f.read(8)
            if len(head) < 8:
                return set()
            magic = struct.unpack(">I", head[:4])[0]
            if magic in THIN_MAGICS:
                cputype = struct.unpack(THIN_MAGICS[magic] + "i", head[4:8])[0] & 0xFFFFFFFF
                return {_name(cputype)}
            if magic in FAT_MAGICS or magic == FAT64_MAGIC:
                endian = FAT_MAGICS.get(magic, ">")
                count = struct.unpack(endian + "I", head[4:8])[0]
                if count > 64:                  # Java class files share 0xCAFEBABE
                    return set()
                entry = 32 if magic == FAT64_MAGIC else 20
                archs = set()
                for _ in range(count):
                    data = f.read(entry)
                    archs.add(_name(struct.unpack(endian + "i", data[:4])[0] & 0xFFFFFFFF))
                return archs
    except OSError:
        pass
    return set()


def _name(cputype: int) -> str:
    return {CPU_TYPE_X86_64: "x86_64", CPU_TYPE_ARM64: "arm64"}.get(cputype, hex(cputype))


@dataclass
class Inspection:
    root: Path
    product: str = ""
    version: str = ""
    build: str = ""
    apps_checked: int = 0
    apps_with_intel: int = 0
    arm_only_apps: List[str] = field(default_factory=list)
    kernel_x86: Optional[str] = None
    intel_kernel_collection: bool = False
    critical_kexts_present: List[str] = field(default_factory=list)
    critical_kexts_missing: List[str] = field(default_factory=list)

    @property
    def pc_capable(self) -> bool:
        return self.apps_with_intel > 0 and self.intel_kernel_collection and bool(self.critical_kexts_present)

    def verdict(self) -> str:
        name = f"{self.product} {self.version} ({self.build})".strip()
        if self.pc_capable:
            return f"{name}: still ships Intel code. It can be targeted on PCs."
        reasons = []
        if self.apps_checked and self.apps_with_intel == 0:
            reasons.append(f"0 of {self.apps_checked} built-in apps contain Intel code")
        if not self.intel_kernel_collection:
            reasons.append("no Intel kernel collection (/System/Library/KernelCollections)")
        if not self.critical_kexts_present:
            reasons.append("no Intel/AMD graphics or X86 power-management drivers")
        return f"{name}: Apple-silicon only, cannot boot on a PC: " + "; ".join(reasons) + "."

    def report(self) -> str:
        lines = [
            f"macOS inspected:        {self.product} {self.version} ({self.build}) at {self.root}",
            f"Built-in apps checked:  {self.apps_checked}",
            f"  ...with Intel code:   {self.apps_with_intel}",
            f"Intel kernel:           {self.kernel_x86 or 'none'}",
            f"Intel kernel collection: {'yes' if self.intel_kernel_collection else 'no'}",
            f"PC-critical drivers:    {', '.join(self.critical_kexts_present) or 'none'}",
            "",
            "Verdict: " + self.verdict(),
        ]
        if self.kernel_x86 and not self.pc_capable:
            lines.append("Note: an x86_64 kernel alone can't boot; it needs the kernel collection and drivers above.")
        return "\n".join(lines)


def inspect(root: Path = Path("/")) -> Inspection:
    root = Path(root)
    result = Inspection(root=root)
    version_plist = root / "System/Library/CoreServices/SystemVersion.plist"
    if version_plist.exists():
        with open(version_plist, "rb") as f:
            info = plistlib.load(f)
        result.product = info.get("ProductName", "macOS")
        result.version = info.get("ProductUserVisibleVersion", info.get("ProductVersion", ""))
        result.build = info.get("ProductBuildVersion", "")

    app_dirs = [root / "System/Applications", root / "System/Applications/Utilities", root / "System/Library/CoreServices"]
    for folder in app_dirs:
        for app in sorted(folder.glob("*.app")) if folder.exists() else []:
            binary = _app_binary(app)
            if binary is None:
                continue
            archs = architectures(binary)
            if not archs:
                continue
            result.apps_checked += 1
            if "x86_64" in archs:
                result.apps_with_intel += 1
            else:
                result.arm_only_apps.append(app.stem)

    kernel = root / "System/Library/Kernels/kernel"
    if "x86_64" in architectures(kernel):
        result.kernel_x86 = _kernel_version(kernel)
    result.intel_kernel_collection = (root / "System/Library/KernelCollections/BootKernelExtensions.kc").exists()

    extensions = root / "System/Library/Extensions"
    for kext in PC_CRITICAL_KEXTS:
        (result.critical_kexts_present if (extensions / kext).exists() else result.critical_kexts_missing).append(kext)
    return result


def _app_binary(app: Path) -> Optional[Path]:
    try:
        with open(app / "Contents/Info.plist", "rb") as f:
            name = plistlib.load(f).get("CFBundleExecutable")
    except (OSError, plistlib.InvalidFileException, ValueError):
        return None
    binary = app / "Contents/MacOS" / name if name else None
    return binary if binary and binary.is_file() else None


def _kernel_version(kernel: Path) -> str:
    try:
        data = kernel.read_bytes()
    except OSError:
        return "x86_64"
    marker = data.find(b"Darwin Kernel Version")
    if marker == -1:
        return "x86_64"
    end = data.find(b"\x00", marker)
    return data[marker:end].decode("ascii", "replace")

"""
hardware.py: Detect the PC we are building OpenCore for

Works on Windows (CIM/WMI via PowerShell) and Linux (/proc and /sys).
macOS is supported only for development and reads basic sysctl values.
A profile can also be saved to and loaded from JSON, so a build can be
made on one machine for another (the equivalent of OCLP's "Target Model").
"""

import re
import sys
import json
import logging
import subprocess
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional

from .datasets import cpu_data, pci_data


@dataclass
class PCIDevice:
    vendor_id: int
    device_id: int
    name:      str = ""
    kind:      str = ""      # "gpu", "ethernet", "wifi", "bluetooth", "audio", "other"
    arch:      str = ""      # GPUs only
    location:  str = ""      # e.g. PciRoot(0x0)/Pci(0x2,0x0) when known

    @property
    def pci_id(self) -> str:
        return f"{self.vendor_id:04X}:{self.device_id:04X}"


@dataclass
class HardwareProfile:
    cpu_vendor:   str = "Intel"     # "Intel" or "AMD"
    cpu_name:     str = ""
    cpu_family:   int = 0
    cpu_model:    int = 0
    cpu_stepping: int = 0
    cpu_cores:    int = 0
    cpu_threads:  int = 0
    cpu_generation: int = 0
    is_laptop:    bool = False
    is_vm:        bool = False
    hypervisor:   str = ""          # "KVM", "VMware", "Hyper-V", "VirtualBox" ...
    manufacturer: str = ""
    model:        str = ""
    board:        str = ""
    mac_address:  str = ""
    gpus:  List[PCIDevice] = field(default_factory=list)
    nics:  List[PCIDevice] = field(default_factory=list)
    other: List[PCIDevice] = field(default_factory=list)
    source: str = ""                # where this profile came from

    # ---- derived ----

    @property
    def generation_name(self) -> str:
        return cpu_data.generation_name(self.cpu_vendor, self.cpu_generation)

    @property
    def igpu(self) -> Optional[PCIDevice]:
        for gpu in self.gpus:
            if gpu.vendor_id == pci_data.VENDOR_INTEL:
                return gpu
        return None

    @property
    def dgpus(self) -> List[PCIDevice]:
        return [g for g in self.gpus if g.vendor_id != pci_data.VENDOR_INTEL and g.arch != pci_data.GPUArch.AMD_APU]

    @property
    def apu(self) -> Optional[PCIDevice]:
        for gpu in self.gpus:
            if gpu.arch == pci_data.GPUArch.AMD_APU:
                return gpu
        return None

    def summary(self) -> str:
        kind = "Virtual machine" if self.is_vm else ("Laptop" if self.is_laptop else "Desktop")
        name = self.cpu_name or f"{self.cpu_vendor} CPU"
        return f"{name} ({self.generation_name}) - {kind}"

    def short_model(self) -> str:
        if self.is_vm:
            return f"{self.hypervisor or 'Virtual'} VM - {self.cpu_vendor} {self.generation_name}"
        placeholders = ("to be filled", "system product name", "default string", "not applicable", "system manufacturer", "o.e.m")
        def real(value: str) -> bool:
            return bool(value) and not any(p in value.lower() for p in placeholders)
        model = self.model if real(self.model) else self.board
        label = " ".join(x for x in (self.manufacturer, model) if real(x))
        return label or f"{self.cpu_vendor} {self.generation_name} PC"

    # ---- persistence ----

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "HardwareProfile":
        data = dict(data)
        for key in ("gpus", "nics", "other"):
            data[key] = [PCIDevice(**d) for d in data.get(key, [])]
        known = {f for f in cls.__dataclass_fields__}
        profile = cls(**{k: v for k, v in data.items() if k in known})
        profile.classify()
        return profile

    @classmethod
    def load(cls, path: Path) -> "HardwareProfile":
        profile = cls.from_dict(json.loads(Path(path).read_text()))
        profile.source = f"Profile: {Path(path).name}"
        return profile

    def save(self, path: Path) -> None:
        Path(path).write_text(self.to_json())

    # ---- classification ----

    def classify(self) -> None:
        if self.cpu_vendor == "AMD":
            self.cpu_generation = int(cpu_data.amd_generation(self.cpu_family))
        else:
            self.cpu_generation = int(cpu_data.intel_generation(self.cpu_family, self.cpu_model, self.cpu_stepping))
        for gpu in self.gpus:
            if not gpu.arch:
                gpu.arch = pci_data.gpu_arch(gpu.vendor_id, gpu.device_id)
        if self.cpu_threads == 0:
            self.cpu_threads = self.cpu_cores


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

PCI_CLASS_KIND = {
    0x03: "gpu",
    0x0200: "ethernet",
    0x0280: "wifi",
    0x0403: "audio",
    0x0D11: "bluetooth",
}

LAPTOP_CHASSIS = {8, 9, 10, 11, 12, 14, 18, 21, 30, 31, 32}

HYPERVISOR_HINTS = {
    "qemu": "KVM", "kvm": "KVM", "bochs": "KVM", "proxmox": "KVM",
    "vmware": "VMware", "virtualbox": "VirtualBox", "innotek": "VirtualBox",
    "microsoft corporation virtual": "Hyper-V", "hyper-v": "Hyper-V", "xen": "Xen", "parallels": "Parallels",
}


def _hypervisor_from(*strings: str) -> str:
    joined = " ".join(s.lower() for s in strings if s)
    for hint, name in HYPERVISOR_HINTS.items():
        if hint in joined:
            return name
    return ""


def _kind_for_class(pci_class: int) -> str:
    if (pci_class >> 16) == 0x03:
        return "gpu"
    return PCI_CLASS_KIND.get(pci_class >> 8, "other")


def _add_device(profile: HardwareProfile, dev: PCIDevice) -> None:
    if dev.kind == "gpu":
        profile.gpus.append(dev)
    elif dev.kind in ("ethernet", "wifi", "bluetooth"):
        profile.nics.append(dev)
    else:
        profile.other.append(dev)


class LinuxProbe:

    def probe(self) -> HardwareProfile:
        p = HardwareProfile(source="Detected (Linux)")
        self._cpu(p)
        self._dmi(p)
        self._pci(p)
        self._usb_bluetooth(p)
        p.classify()
        return p

    def _cpu(self, p: HardwareProfile) -> None:
        text = Path("/proc/cpuinfo").read_text(errors="ignore")
        first = text.split("\n\n")[0]
        fields = {}
        for line in first.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip()
        p.cpu_vendor   = "AMD" if "AMD" in fields.get("vendor_id", "") else "Intel"
        p.cpu_name     = fields.get("model name", "")
        p.cpu_family   = int(fields.get("cpu family", "0") or 0)
        p.cpu_model    = int(fields.get("model", "0") or 0)
        p.cpu_stepping = int(fields.get("stepping", "0") or 0)
        p.cpu_cores    = int(fields.get("cpu cores", "0") or 0)
        p.cpu_threads  = text.count("processor\t:") or int(fields.get("siblings", "0") or 0)
        if not p.cpu_cores:
            p.cpu_cores = p.cpu_threads
        if " hypervisor" in fields.get("flags", "") + " ":
            p.is_vm = True

    def _read(self, path: str) -> str:
        try:
            return Path(path).read_text(errors="ignore").strip()
        except OSError:
            return ""

    def _dmi(self, p: HardwareProfile) -> None:
        base = "/sys/class/dmi/id/"
        p.manufacturer = self._read(base + "sys_vendor")
        p.model        = self._read(base + "product_name")
        p.board        = self._read(base + "board_name")
        chassis = self._read(base + "chassis_type")
        if chassis.isdigit() and int(chassis) in LAPTOP_CHASSIS:
            p.is_laptop = True
        if list(Path("/sys/class/power_supply").glob("BAT*")):
            p.is_laptop = True
        hv = _hypervisor_from(p.manufacturer, p.model, self._read(base + "bios_vendor"))
        if hv:
            p.is_vm, p.hypervisor = True, hv
        elif p.is_vm:
            p.hypervisor = "KVM" if Path("/dev/kvm").exists() or "kvm" in self._read("/sys/hypervisor/type").lower() else "Unknown"
        if p.is_vm:
            p.is_laptop = False

    def _pci(self, p: HardwareProfile) -> None:
        names = self._lspci_names()
        for dev in sorted(Path("/sys/bus/pci/devices").glob("*")):
            try:
                vendor = int(self._read(str(dev / "vendor")), 16)
                device = int(self._read(str(dev / "device")), 16)
                pci_class = int(self._read(str(dev / "class")), 16)
            except ValueError:
                continue
            kind = _kind_for_class(pci_class)
            if kind == "other":
                continue
            slot = dev.name                     # 0000:00:02.0
            pcidev = PCIDevice(vendor, device, names.get(slot[5:], ""), kind, location=self._acpi_path(slot))
            if kind == "ethernet" and not p.mac_address:
                p.mac_address = self._mac_for(dev)
            _add_device(p, pcidev)

    def _usb_bluetooth(self, p: HardwareProfile) -> None:
        # Intel/Broadcom Bluetooth sit on USB; class e0 = wireless controller
        for dev in Path("/sys/bus/usb/devices").glob("*"):
            if self._read(str(dev / "bDeviceClass")) == "e0":
                try:
                    vendor = int(self._read(str(dev / "idVendor")), 16)
                    product = int(self._read(str(dev / "idProduct")), 16)
                except ValueError:
                    continue
                p.nics.append(PCIDevice(vendor, product, self._read(str(dev / "product")), "bluetooth"))

    def _mac_for(self, dev: Path) -> str:
        for net in (dev / "net").glob("*"):
            mac = self._read(str(net / "address"))
            if mac and mac != "00:00:00:00:00:00":
                return mac
        return ""

    def _lspci_names(self) -> dict:
        try:
            out = subprocess.run(["lspci", "-mm"], capture_output=True, text=True, timeout=10).stdout
        except (OSError, subprocess.SubprocessError):
            return {}
        names = {}
        for line in out.splitlines():
            parts = re.findall(r'"([^"]*)"', line)
            slot = line.split(" ", 1)[0]
            if len(parts) >= 3:
                names[slot] = f"{parts[1]} {parts[2]}"
        return names

    def _acpi_path(self, slot: str) -> str:
        # Only devices on bus 0 have a simple, reliable OpenCore device path.
        match = re.match(r"[0-9a-f]{4}:00:([0-9a-f]{2})\.([0-7])", slot)
        if not match:
            return ""
        return f"PciRoot(0x0)/Pci(0x{int(match.group(1), 16):X},0x{int(match.group(2)):X})"


WINDOWS_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$cs  = Get-CimInstance Win32_ComputerSystem
$bb  = Get-CimInstance Win32_BaseBoard
$enc = Get-CimInstance Win32_SystemEnclosure
$bat = @(Get-CimInstance Win32_Battery).Count
$pci = Get-CimInstance Win32_PnPEntity | Where-Object { $_.DeviceID -like 'PCI\VEN_*' -or ($_.DeviceID -like 'USB\VID_*' -and $_.PNPClass -eq 'Bluetooth') } |
       Select-Object Name, DeviceID, PNPClass, @{n='Location';e={(Get-PnpDeviceProperty -InstanceId $_.DeviceID -KeyName 'DEVPKEY_Device_LocationPaths').Data -join ';'}}
$mac = (Get-CimInstance Win32_NetworkAdapter | Where-Object { $_.PhysicalAdapter -and $_.MACAddress -and $_.PNPDeviceID -like 'PCI\*' } | Select-Object -First 1).MACAddress
[pscustomobject]@{
  Manufacturer = $cpu.Manufacturer; Name = $cpu.Name; Description = $cpu.Description
  Cores = $cpu.NumberOfCores; Threads = $cpu.NumberOfLogicalProcessors
  SysVendor = $cs.Manufacturer; SysModel = $cs.Model; Hypervisor = $cs.HypervisorPresent
  Board = $bb.Product; Chassis = @($enc.ChassisTypes); Batteries = $bat; Mac = $mac
  Devices = @($pci)
} | ConvertTo-Json -Depth 4 -Compress
"""


class WindowsProbe:

    def probe(self) -> HardwareProfile:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", WINDOWS_SCRIPT],
            capture_output=True, text=True, timeout=120,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
        return self.parse(json.loads(out))

    @staticmethod
    def parse(data: dict) -> HardwareProfile:
        p = HardwareProfile(source="Detected (Windows)")
        p.cpu_vendor = "AMD" if "AMD" in (data.get("Manufacturer") or "") else "Intel"
        p.cpu_name   = (data.get("Name") or "").strip()
        desc = data.get("Description") or ""
        for key, attr in (("Family", "cpu_family"), ("Model", "cpu_model"), ("Stepping", "cpu_stepping")):
            m = re.search(rf"{key} (\d+)", desc)
            if m:
                setattr(p, attr, int(m.group(1)))
        p.cpu_cores   = int(data.get("Cores") or 0)
        p.cpu_threads = int(data.get("Threads") or 0)
        p.manufacturer = data.get("SysVendor") or ""
        p.model        = data.get("SysModel") or ""
        p.board        = data.get("Board") or ""
        p.mac_address  = (data.get("Mac") or "").replace("-", ":")
        chassis = data.get("Chassis") or []
        if any(int(c) in LAPTOP_CHASSIS for c in chassis if str(c).isdigit()) or int(data.get("Batteries") or 0) > 0:
            p.is_laptop = True
        hv = _hypervisor_from(p.manufacturer, p.model)
        if hv:
            p.is_vm, p.hypervisor = True, hv
        if p.is_vm:
            p.is_laptop = False

        devices = data.get("Devices") or []
        if isinstance(devices, dict):
            devices = [devices]
        for dev in devices:
            dev_id = dev.get("DeviceID") or ""
            m = re.search(r"VEN_([0-9A-F]{4})&DEV_([0-9A-F]{4})", dev_id, re.I) or re.search(r"VID_([0-9A-F]{4})&PID_([0-9A-F]{4})", dev_id, re.I)
            if not m:
                continue
            vendor, device = int(m.group(1), 16), int(m.group(2), 16)
            pnp = (dev.get("PNPClass") or "").lower()
            name = dev.get("Name") or ""
            if pnp == "display":
                kind = "gpu"
            elif pnp == "net":
                kind = "wifi" if re.search(r"wi-?fi|wireless|802\.11|wlan", name, re.I) else "ethernet"
            elif pnp == "bluetooth":
                kind = "bluetooth"
            elif pnp == "media":
                kind = "audio"
            else:
                continue
            _add_device(p, PCIDevice(vendor, device, name, kind, location=WindowsProbe._acpi_path(dev.get("Location") or "")))
        p.classify()
        return p

    @staticmethod
    def _acpi_path(location: str) -> str:
        # "PCIROOT(0)#PCI(0200)" -> PciRoot(0x0)/Pci(0x2,0x0)
        for path in location.split(";"):
            m = re.match(r"PCIROOT\((\d+)\)((?:#PCI\([0-9A-F]{4}\))+)$", path, re.I)
            if m:
                parts = [f"PciRoot(0x{int(m.group(1)):X})"]
                for seg in re.findall(r"PCI\(([0-9A-F]{2})([0-9A-F]{2})\)", m.group(2), re.I):
                    parts.append(f"Pci(0x{int(seg[0], 16):X},0x{int(seg[1], 16):X})")
                return "/".join(parts)
        return ""


class MacProbe:
    """
    Development only: lets the app start on a Mac. Builds should use a profile.
    """

    def probe(self) -> HardwareProfile:
        def sysctl(key: str) -> str:
            return subprocess.run(["sysctl", "-n", key], capture_output=True, text=True).stdout.strip()

        p = HardwareProfile(source="Detected (macOS, development)")
        brand = sysctl("machdep.cpu.brand_string")
        p.cpu_name = brand
        p.cpu_vendor = "AMD" if "AMD" in brand else "Intel"
        p.cpu_family = int(sysctl("machdep.cpu.family") or 0)
        p.cpu_model = int(sysctl("machdep.cpu.model") or 0)
        p.cpu_stepping = int(sysctl("machdep.cpu.stepping") or 0)
        p.cpu_cores = int(sysctl("hw.physicalcpu") or 0)
        p.cpu_threads = int(sysctl("hw.logicalcpu") or 0)
        p.model = sysctl("hw.model")
        p.manufacturer = "Apple"
        p.classify()
        return p


def detect() -> HardwareProfile:
    try:
        if sys.platform == "win32":
            return WindowsProbe().probe()
        if sys.platform.startswith("linux"):
            return LinuxProbe().probe()
        return MacProbe().probe()
    except Exception:
        logging.exception("Hardware detection failed; using an empty profile")
        return HardwareProfile(source="Detection failed")

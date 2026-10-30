"""
planner.py: Decide what an EFI needs for a given PC

Pure logic, no I/O: takes a HardwareProfile and the user's settings and
returns a BuildPlan (kexts, ACPI tables, SMBIOS, quirks, warnings).
The rules follow the Dortania OpenCore Install Guide per platform.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from ..hardware import HardwareProfile
from ..datasets import cpu_data, pci_data, smbios_data, igpu_data, os_data
from ..datasets.cpu_data import Intel, AMD


class PlanError(Exception):
    pass


# Platform families the config builder understands
class Platform:
    INTEL_DESKTOP = "Intel Desktop"
    INTEL_LAPTOP  = "Intel Laptop"
    INTEL_HEDT    = "Intel HEDT"
    AMD_DESKTOP   = "AMD Desktop"
    AMD_LAPTOP    = "AMD Laptop"
    KVM           = "KVM/QEMU Virtual Machine"


@dataclass
class BuildPlan:
    platform: str
    smbios: str
    target_os: int
    kexts: List[str] = field(default_factory=list)
    acpi_ocpkg: List[str] = field(default_factory=list)        # from OpenCorePkg Docs/AcpiSamples/Binaries
    acpi_dortania: List[str] = field(default_factory=list)     # downloaded prebuilt SSDTs (name -> url in config)
    drivers: List[str] = field(default_factory=list)
    boot_args: List[str] = field(default_factory=list)
    device_properties: Dict[str, dict] = field(default_factory=dict)
    booter_quirks: Dict[str, object] = field(default_factory=dict)
    kernel_quirks: Dict[str, object] = field(default_factory=dict)
    uefi_quirks: Dict[str, object] = field(default_factory=dict)
    kernel_emulate: Dict[str, object] = field(default_factory=dict)
    kernel_block: List[dict] = field(default_factory=list)
    amd_patches: bool = False
    amd_core_count: int = 0
    secure_boot_model: str = "Default"
    update_smbios_mode: str = "Create"
    warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def add_kext(self, *names: str) -> None:
        for name in names:
            if name not in self.kexts:
                self.kexts.append(name)

    def add_arg(self, *args: str) -> None:
        for arg in args:
            if arg and arg not in self.boot_args:
                self.boot_args.append(arg)


DORTANIA_ACPI = "https://raw.githubusercontent.com/dortania/Getting-Started-With-ACPI/master/extra-files/compiled/"
DORTANIA_GUIDE = "https://raw.githubusercontent.com/dortania/OpenCore-Install-Guide/master/extra-files/"
ACPI_URLS = {
    "SSDT-EC-USBX-DESKTOP.aml": DORTANIA_ACPI + "SSDT-EC-USBX-DESKTOP.aml",
    "SSDT-EC-USBX-LAPTOP.aml":  DORTANIA_ACPI + "SSDT-EC-USBX-LAPTOP.aml",
    "SSDT-EC-DESKTOP.aml":      DORTANIA_ACPI + "SSDT-EC-DESKTOP.aml",
    "SSDT-EC-LAPTOP.aml":       DORTANIA_ACPI + "SSDT-EC-LAPTOP.aml",
    "SSDT-PLUG-DRTNIA.aml":     DORTANIA_ACPI + "SSDT-PLUG-DRTNIA.aml",
    "SSDT-AWAC.aml":            DORTANIA_ACPI + "SSDT-AWAC.aml",
    "SSDT-PMC.aml":             DORTANIA_ACPI + "SSDT-PMC.aml",
    "SSDT-RHUB.aml":            DORTANIA_ACPI + "SSDT-RHUB.aml",
    "SSDT-PNLF.aml":            DORTANIA_ACPI + "SSDT-PNLF.aml",
    "SSDT-CPUR.aml":            DORTANIA_ACPI + "SSDT-CPUR.aml",
    "SSDT-RTC0-RANGE-HEDT.aml": DORTANIA_ACPI + "SSDT-RTC0-RANGE-HEDT.aml",
    "SSDT-UNC.aml":             DORTANIA_ACPI + "SSDT-UNC.aml",
    "SSDT-EC-USBX-AMD.aml":     DORTANIA_GUIDE + "SSDT-EC-USBX-AMD.aml",
}

# Comet Lake CPUID, used to make Rocket/Alder/Raptor/Arrow Lake look supported
COMET_LAKE_CPUID = bytes.fromhex("55060A00000000000000000000000000")
CPUID_MASK       = bytes.fromhex("FFFFFFFF000000000000000000000000")


class Planner:

    def __init__(self, profile: HardwareProfile, constants) -> None:
        self.hw = profile
        self.c = constants

    def plan(self) -> BuildPlan:
        if not os_data.pc_supported(self.c.target_os):
            raise PlanError(os_data.GOLDEN_GATE_DIAGNOSIS)
        platform = self._platform()
        plan = BuildPlan(platform=platform, smbios="", target_os=int(self.c.target_os))

        self._base(plan)
        if platform == Platform.KVM:
            self._kvm(plan)
        elif self.hw.cpu_vendor == "AMD":
            self._amd(plan)
        else:
            self._intel(plan)
        self._graphics(plan)
        self._smbios(plan)
        self._networking(plan)
        self._extras(plan)
        self._user_overrides(plan)
        return plan

    # ------------------------------------------------------------------

    def _platform(self) -> str:
        if self.hw.is_vm:
            if self.hw.hypervisor not in ("KVM", "Unknown", ""):
                raise PlanError(f"{self.hw.hypervisor} virtual machines are not supported yet; only KVM/QEMU (incl. Proxmox, virt-manager, UTM-on-Linux).")
            return Platform.KVM
        if self.hw.cpu_vendor == "AMD":
            return Platform.AMD_LAPTOP if self.hw.is_laptop else Platform.AMD_DESKTOP
        gen = Intel(self.hw.cpu_generation)
        if gen in cpu_data.HEDT:
            return Platform.INTEL_HEDT
        return Platform.INTEL_LAPTOP if self.hw.is_laptop else Platform.INTEL_DESKTOP

    def _base(self, plan: BuildPlan) -> None:
        plan.add_kext("Lilu", "VirtualSMC")
        plan.drivers = ["OpenHfsPlus.efi", "OpenRuntime.efi", "ResetNvramEntry.efi"]
        if self.c.opencanopy:
            plan.drivers.append("OpenCanopy.efi")
        plan.booter_quirks = {
            "AvoidRuntimeDefrag": True,
            "DevirtualiseMmio": False,
            "EnableSafeModeSlide": True,
            "EnableWriteUnprotector": False,
            "ProtectUefiServices": False,
            "ProvideCustomSlide": True,
            "RebuildAppleMemoryMap": True,
            "SetupVirtualMap": True,
            "SyncRuntimePermissions": True,
            "ResizeAppleGpuBars": 0 if self.c.resizable_bar else -1,
        }
        plan.kernel_quirks = {
            "AppleXcpmCfgLock": not self.c.cfg_lock_unlocked,
            "DisableIoMapper": True,
            "PanicNoKextDump": True,
            "PowerTimeoutKernelPanic": True,
            "ProvideCurrentCpuInfo": False,
            "XhciPortLimit": False,
        }
        plan.uefi_quirks = {"RequestBootVarRouting": True, "ReleaseUsbOwnership": True}
        if self.c.verbose_debug:
            plan.add_arg("-v")
        if self.c.kext_debug:
            plan.add_arg("keepsyms=1", "debug=0x100")
        if self.c.target_os >= os_data.os_data.ventura and not self._has_avx2():
            plan.add_kext("CryptexFixup")
            plan.add_arg("-crypt_allow_hash_validation")
            plan.warnings.append("This CPU has no AVX2. macOS Ventura+ installs only via CryptexFixup, and some apps (and Metal on old GPUs) will not work.")

    def _has_avx2(self) -> bool:
        if self.hw.cpu_vendor == "AMD":
            return self.hw.cpu_generation >= AMD.zen
        return self.hw.cpu_generation >= Intel.haswell

    # ---- Intel ----

    def _intel(self, plan: BuildPlan) -> None:
        gen = Intel(self.hw.cpu_generation)
        laptop = plan.platform == Platform.INTEL_LAPTOP

        if gen == Intel.unknown:
            raise PlanError(f"Unrecognised Intel CPU (family {self.hw.cpu_family}, model 0x{self.hw.cpu_model:X}).")
        if gen < Intel.haswell:
            raise PlanError(f"{cpu_data.NAMES[gen]} CPUs are too old for any macOS this tool targets (Haswell or newer required).")

        plan.add_kext("SMCProcessor", "WhateverGreen", "AppleALC", "NVMeFix")
        if not laptop:
            plan.add_kext("SMCSuperIO")

        older = gen in (Intel.haswell, Intel.broadwell, Intel.skylake, Intel.kaby_lake, Intel.haswell_e, Intel.broadwell_e)
        if older:
            plan.booter_quirks.update(EnableWriteUnprotector=True, RebuildAppleMemoryMap=False, SyncRuntimePermissions=False)
        if gen >= Intel.coffee_lake and gen not in cpu_data.HEDT:
            plan.booter_quirks["DevirtualiseMmio"] = True
            plan.booter_quirks["ProtectUefiServices"] = True

        # ACPI
        ec = "SSDT-EC-USBX-LAPTOP.aml" if laptop else "SSDT-EC-USBX-DESKTOP.aml"
        if gen in (Intel.haswell, Intel.broadwell):
            ec = "SSDT-EC-LAPTOP.aml" if laptop else "SSDT-EC-DESKTOP.aml"
        plan.acpi_dortania.append(ec)
        if gen <= Intel.comet_lake or gen in cpu_data.HEDT:
            plan.acpi_dortania.append("SSDT-PLUG-DRTNIA.aml")
        if gen >= Intel.coffee_lake and gen not in cpu_data.HEDT:
            plan.acpi_dortania.append("SSDT-AWAC.aml")
        if gen == Intel.coffee_lake and not laptop:
            plan.acpi_dortania.append("SSDT-PMC.aml")
            plan.notes.append("SSDT-PMC is only needed on Z390 boards; it's harmless elsewhere.")
        if laptop:
            plan.acpi_dortania.append("SSDT-PNLF.aml")
        if gen in cpu_data.HEDT:
            plan.acpi_dortania += ["SSDT-RTC0-RANGE-HEDT.aml", "SSDT-UNC.aml"]
            plan.booter_quirks["DevirtualiseMmio"] = True
            plan.booter_quirks["SetupVirtualMap"] = False

        # Hybrid / too-new CPUs
        if gen >= Intel.rocket_lake and gen not in cpu_data.HEDT:
            plan.kernel_emulate.update(Cpuid1Data=COMET_LAKE_CPUID, Cpuid1Mask=CPUID_MASK)
            plan.kernel_quirks["ProvideCurrentCpuInfo"] = True
            plan.notes.append("CPU is spoofed as Comet Lake (Kernel > Emulate) so macOS accepts it.")
        if gen >= Intel.alder_lake and gen not in cpu_data.HEDT:
            plan.add_kext("CpuTopologyRebuild")
            plan.notes.append("Alder Lake and newer: disable E-cores in BIOS if you get boot loops; CpuTopologyRebuild helps when they're on.")

        if laptop:
            plan.add_kext("SMCBatteryManager", "VoodooPS2Controller")
            plan.notes.append("Laptop trackpads on I2C need VoodooI2C plus a custom SSDT; only PS/2 input is set up automatically.")

    # ---- AMD ----

    def _amd(self, plan: BuildPlan) -> None:
        gen = self.hw.cpu_generation
        if gen not in (AMD.bulldozer, AMD.jaguar, AMD.zen, AMD.zen3_4, AMD.zen5):
            raise PlanError(f"Unrecognised AMD CPU family 0x{self.hw.cpu_family:X}.")
        plan.amd_patches = True
        plan.amd_core_count = self.hw.cpu_cores
        if not 1 <= plan.amd_core_count <= 255:
            raise PlanError("Couldn't read the CPU's physical core count, needed for the AMD kernel patches.")
        plan.kernel_quirks.update(AppleXcpmCfgLock=False, ProvideCurrentCpuInfo=True)
        plan.kernel_emulate["DummyPowerManagement"] = True
        plan.kernel_block.append({
            "Arch": "Any", "Comment": "Exclude AppleMCEReporter (AMD panic fix)", "Enabled": True,
            "Identifier": "com.apple.driver.AppleMCEReporter", "MaxKernel": "", "MinKernel": "21.0.0", "Strategy": "Exclude",
        })
        plan.add_kext("AppleALC", "NVMeFix")
        if gen >= AMD.zen:
            plan.add_kext("AMDRyzenCPUPowerManagement", "SMCAMDProcessor")
        plan.acpi_dortania.append("SSDT-EC-USBX-AMD.aml")
        board = (self.hw.board or "").upper()
        if any(chip in board for chip in ("B550", "A520")):
            plan.acpi_dortania.append("SSDT-CPUR.aml")
            plan.booter_quirks["SetupVirtualMap"] = False
        if "TRX40" in board:
            plan.booter_quirks.update(DevirtualiseMmio=True, SetupVirtualMap=False)
        if plan.platform == Platform.AMD_LAPTOP:
            plan.add_kext("SMCBatteryManager", "VoodooPS2Controller")
        plan.notes.append(f"AMD_Vanilla kernel patches applied for {plan.amd_core_count} physical cores.")

    # ---- KVM ----

    def _kvm(self, plan: BuildPlan) -> None:
        plan.kernel_quirks.update(AppleXcpmCfgLock=False, ProvideCurrentCpuInfo=True, DisableIoMapper=True)
        plan.booter_quirks.update(DevirtualiseMmio=False, ProtectUefiServices=False)
        plan.add_kext("AppleALC")
        plan.add_arg("vmhide=on")
        plan.add_kext("RestrictEvents")       # provides vmhide
        if self.hw.cpu_vendor == "AMD" and self.hw.cpu_generation >= AMD.zen:
            plan.amd_patches = True
            plan.amd_core_count = self.hw.cpu_cores or 4
            plan.notes.append("AMD host: AMD_Vanilla patches are applied. If you use '-cpu host', set the VM's core count to match.")
        plan.notes.append("KVM: use OVMF (UEFI), q35, and '-cpu host' (or Cascadelake-Server/Haswell-noTSX on AMD hosts).")
        plan.notes.append("KVM: ACPI, Booter and Kernel settings based on the approach of Leoyzen/KVM-Opencore, updated for current OpenCore.")
        plan.update_smbios_mode = "Create"

    # ---- graphics ----

    def _graphics(self, plan: BuildPlan) -> None:
        target = plan.target_os
        supported_dgpus = [g for g in self.hw.dgpus if pci_data.gpu_supported(g.arch, target)]
        for gpu in self.hw.dgpus:
            if gpu in supported_dgpus:
                if gpu.arch in (pci_data.GPUArch.NAVI10, pci_data.GPUArch.NAVI14, pci_data.GPUArch.NAVI21,
                                pci_data.GPUArch.NAVI22, pci_data.GPUArch.NAVI23):
                    plan.add_arg("agdpmod=pikera")
                if gpu.arch == pci_data.GPUArch.KEPLER and target >= os_data.os_data.monterey:
                    plan.warnings.append("Kepler GPUs need post-install root patching on Monterey+, which can only be done from macOS.")
                continue
            note = pci_data.UNSUPPORTED_NOTE.get(gpu.arch)
            if note is None and gpu.arch in pci_data.GPU_SUPPORT:
                low, high, extra = pci_data.GPU_SUPPORT[gpu.arch]
                note = f"{gpu.name or gpu.arch} supports {os_data.name(low)} to {os_data.name(high)} only" + (f" ({extra})" if extra else "")
            plan.warnings.append(f"Disabled unsupported GPU {gpu.pci_id} {gpu.name}: {note or 'unknown GPU'}")
            if gpu.location:
                plan.device_properties[gpu.location] = {"disable-gpu-support": bytes.fromhex("01000000")}
            elif plan.platform != Platform.KVM:
                plan.add_arg("-wegnoegpu")
        self.supported_dgpus = supported_dgpus

        if self.hw.apu and plan.platform != Platform.KVM:
            if pci_data.gpu_supported(pci_data.GPUArch.AMD_APU, target):
                plan.add_kext("NootedRed")
                plan.notes.append("Ryzen APU graphics enabled via NootedRed (community kext, ChefKissInc).")
            else:
                plan.warnings.append(f"NootedRed supports up to {os_data.name(pci_data.GPU_SUPPORT[pci_data.GPUArch.AMD_APU][1])}; APU graphics will not accelerate.")

        if self.hw.cpu_vendor == "Intel" and plan.platform in (Platform.INTEL_DESKTOP, Platform.INTEL_LAPTOP):
            gen = Intel(self.hw.cpu_generation)
            igpu = self.hw.igpu
            igpu_ok = igpu is not None and igpu_data.IGPU_MAX_OS.get(gen, 0) >= target
            laptop = plan.platform == Platform.INTEL_LAPTOP
            if igpu_ok:
                props = igpu_data.properties(gen, igpu.device_id, laptop, headless=bool(supported_dgpus) and not laptop)
                if props:
                    plan.device_properties[igpu_data.IGPU_PATH] = props
            elif not supported_dgpus:
                reason = "has no macOS drivers" if igpu is None or gen not in igpu_data.IGPU_MAX_OS else \
                         f"is supported up to {os_data.name(igpu_data.IGPU_MAX_OS[gen])}"
                raise PlanError(f"No usable GPU for {os_data.name(target)}: the iGPU {reason} and there is no supported discrete GPU.")
        elif not supported_dgpus and plan.platform not in (Platform.KVM,) and not self.hw.apu:
            raise PlanError("No usable GPU: macOS needs a supported AMD GPU (Polaris, Vega, Navi 10/21/22/23) on this platform.")

    # ---- SMBIOS ----

    def _smbios(self, plan: BuildPlan) -> None:
        target = plan.target_os
        if self.c.custom_smbios:
            plan.smbios = self.c.custom_smbios
        elif plan.platform == Platform.KVM:
            plan.smbios = "iMacPro1,1" if target <= os_data.os_data.sequoia and not self.supported_dgpus else "MacPro7,1"
        elif self.hw.cpu_vendor == "AMD":
            if self.hw.apu and not self.supported_dgpus:
                plan.smbios = "MacBookPro16,3" if self.hw.is_laptop else "iMac20,1"
            else:
                plan.smbios = "MacPro7,1" if target >= os_data.os_data.monterey else "iMacPro1,1"
        elif plan.platform == Platform.INTEL_LAPTOP:
            gen = Intel(self.hw.cpu_generation)
            plan.smbios = smbios_data.INTEL_LAPTOP.get(gen, "MacBookPro16,3")
            if not smbios_data.supports(plan.smbios, target):
                plan.smbios = smbios_data.LAPTOP_TAHOE.get(gen, plan.smbios)
        else:
            gen = Intel(self.hw.cpu_generation)
            igpu_only, with_dgpu = smbios_data.INTEL_DESKTOP.get(gen, (None, "MacPro7,1"))
            plan.smbios = with_dgpu if self.supported_dgpus else (igpu_only or with_dgpu)
            if gen == Intel.comet_lake and self.hw.cpu_cores >= 10:
                plan.smbios = "iMac20,2"
            if not smbios_data.supports(plan.smbios, target):
                if gen in (Intel.coffee_lake, Intel.comet_lake):
                    plan.smbios = "iMac20,1"
                elif self.supported_dgpus:
                    plan.smbios = "MacPro7,1"

        if plan.smbios not in smbios_data.SMBIOS:
            raise PlanError(f"Unknown SMBIOS model {plan.smbios}")
        if not smbios_data.supports(plan.smbios, target):
            plan.warnings.append(f"{plan.smbios} officially supports up to {os_data.name(smbios_data.max_os(plan.smbios))}; "
                                 f"{os_data.name(target)} will need -no_compat_check and RestrictEvents.")
            plan.add_arg("-no_compat_check")
            plan.add_kext("RestrictEvents")
        if target == os_data.os_data.tahoe:
            plan.notes.append("macOS Tahoe is the last macOS for Intel Macs; only MacPro7,1, iMac20,x and MacBookPro16,x "
                              "SMBIOS models can install it, so one of those is used.")
        if plan.smbios in ("MacPro7,1", "iMacPro1,1"):
            plan.add_kext("RestrictEvents")     # hides MacPro7,1 memory/PCI warnings
        if plan.smbios == "MacPro7,1" and not self.supported_dgpus and plan.platform != Platform.KVM:
            plan.warnings.append("MacPro7,1 requires a supported discrete GPU to show a picture.")

    # ---- networking ----

    def _networking(self, plan: BuildPlan) -> None:
        if plan.platform == Platform.KVM:
            plan.notes.append("KVM: use a virtio-net or vmxnet3 network device (both have built-in macOS drivers).")
            return
        found_ethernet = False
        for nic in self.hw.nics:
            if nic.kind == "ethernet":
                kext = pci_data.ethernet_kext(nic.vendor_id, nic.device_id)
                if kext == "I225":
                    plan.add_arg("dk.e1000=0", "e1000=0")
                    if nic.location:
                        plan.device_properties.setdefault(nic.location, {})["device-id"] = bytes.fromhex("F2150000")
                    plan.notes.append("Intel I225/I226 uses Apple's built-in driver (device-id spoof + e1000=0).")
                    found_ethernet = True
                elif kext == "AppleIntelI210Ethernet":
                    found_ethernet = True   # native
                elif kext:
                    plan.add_kext(kext)
                    found_ethernet = True
                elif nic.vendor_id == pci_data.VENDOR_BROADCOM:
                    found_ethernet = True   # most Broadcom NICs are native
                else:
                    plan.warnings.append(f"No known macOS driver for Ethernet {nic.pci_id} {nic.name}")
            elif nic.kind == "wifi" and self.c.include_wifi:
                if nic.vendor_id == pci_data.VENDOR_INTEL and nic.device_id in pci_data.INTEL_WIFI_IDS:
                    plan.add_kext("itlwm")
                    plan.notes.append("Intel Wi-Fi uses itlwm; install the HeliPort app in macOS to join networks.")
                elif nic.vendor_id == pci_data.VENDOR_BROADCOM and nic.device_id in pci_data.BROADCOM_NATIVE_WIFI:
                    if plan.target_os >= os_data.os_data.sonoma:
                        plan.warnings.append("Broadcom Wi-Fi needs post-install root patching on Sonoma+ (from macOS).")
                else:
                    plan.warnings.append(f"Wi-Fi {nic.pci_id} {nic.name} is not supported by macOS")
            elif nic.kind == "bluetooth" and self.c.include_bluetooth:
                if nic.vendor_id in (pci_data.VENDOR_INTEL, 0x8087):
                    plan.add_kext("IntelBluetoothFirmware", "IntelBTPatcher", "BlueToolFixup")
                elif nic.vendor_id in (0x0A5C, 0x0489, 0x13D3, 0x0930, pci_data.VENDOR_BROADCOM):
                    plan.add_kext("BlueToolFixup")
        if not found_ethernet and not any(n.kind == "wifi" for n in self.hw.nics):
            plan.warnings.append("No supported network adapter found; macOS may need one to finish installing.")

    # ---- extras ----

    def _extras(self, plan: BuildPlan) -> None:
        if plan.platform != Platform.KVM and self.c.usb_toolbox:
            plan.add_kext("USBToolBox")
            plan.notes.append("USB: USBToolBox is included. Map your ports with the USBToolBox tool (Windows) and add the generated UTBMap.kext.")
        plan.add_arg(f"alcid={self.c.alc_layout_id}")
        if not self.c.secure_boot_model:
            plan.secure_boot_model = "Disabled"

    def _user_overrides(self, plan: BuildPlan) -> None:
        if self.c.disable_dgpu:
            plan.add_arg("-wegnoegpu")
        for arg in (self.c.extra_boot_args or "").split():
            plan.add_arg(arg)

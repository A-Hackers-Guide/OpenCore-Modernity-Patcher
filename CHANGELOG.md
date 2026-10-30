# Changelog

All notable changes to OpenCore Modernity Patcher. Versions follow [Semantic Versioning](https://semver.org); channels are described in [RELEASES.md](RELEASES.md).

## [Unreleased]

## [0.1.0-beta.1] - 2026-10-29

First public pre-release, codename **"First Light"**. Tested with `ocvalidate` and simulated hardware profiles only. **Not yet booted on real hardware.**

### Added

#### App and interface
- Windows `.exe` and Linux `.AppImage` builds from one Python/wxPython codebase.
- OCLP-style interface: main menu (two columns of icon, button and description, with Settings/Credits centred), Build log window, Install OpenCore (disk → EFI partition → live log), Create macOS Installer (download/existing → version list → USB → flash), tabbed Settings, Support, About and Credits.
- Icons drawn by the app at any size (no OCLP artwork).
- Headless command line: `--build`, `--profile`, `--save-profile`, `--target`, `--smbios`, `--output`, `--debug-opencore`.
- Settings saved between launches; data folder per OS, overridable with `OCMP_DATA_DIR`.

#### Hardware detection
- Windows: CPU family/model/stepping, cores, GPUs, NICs, Bluetooth, chassis, battery, board, MAC and PCI device paths via CIM/WMI.
- Linux: `/proc/cpuinfo`, `/sys/bus/pci`, `/sys/class/dmi`, USB Bluetooth, `lspci` names, bus-0 device paths.
- KVM/QEMU detection; VMware, Hyper-V and VirtualBox are recognised and refused with a clear message.
- Hardware profiles (JSON) to save, load and build for other machines; five example profiles.

#### Build engine
- Platforms: Intel desktop, Intel laptop, Intel HEDT, AMD desktop, AMD laptop, KVM.
- Intel Haswell → Arrow Lake: Comet Lake CPUID spoof, `ProvideCurrentCpuInfo` and CpuTopologyRebuild for Rocket Lake and newer.
- AMD Zen → Zen 5 (and 15h/16h with CryptexFixup): AMD_Vanilla patches with the core count filled in, `AppleMCEReporter` blocked, B550/A520/TRX40 quirk changes, SSDT-CPUR.
- Ryzen APU graphics through NootedRed.
- GPU support table for AMD (Polaris → Navi 23) and NVIDIA (Kepler → Blackwell); unsupported GPUs disabled automatically; `agdpmod=pikera` for Navi.
- Intel iGPU framebuffer properties per generation (display vs headless vs laptop) with verified device-id spoofs.
- Ethernet: IntelMausi, I210/I225/I226 native, RTL8111, RTL8125, Atheros E2200. Intel Wi-Fi (itlwm) and Bluetooth.
- SMBIOS selection per CPU/GPU/target with automatic upgrade when the target is too new.
- `config.plist` generated from the matching OpenCore release's `Sample.plist` (entry templates included, so new OpenCore keys are picked up), validated with `ocvalidate`.
- Serials from `macserial`; ROM from the real Ethernet MAC or a random locally administered one.
- `BuildReport.txt` with platform, SMBIOS, kexts, ACPI, warnings and notes.

#### macOS Tahoe (26)
- Full Tahoe target: SMBIOS automatically moves to MacPro7,1, iMac20,x or MacBookPro16,x.
- AMD_Vanilla patches through kernel 25.x.
- Tahoe recovery in the installer list.

#### Installing
- EFI install keeps Microsoft/Linux boot loaders, backs up an existing `EFI/OC`, and warns before touching the boot disk.
- Installer USB: Apple recovery via OpenCorePkg's `macrecovery.py`, GPT/FAT32 USB (diskpart on Windows, parted/mkfs.vfat on Linux), EFI copied alongside. Only removable, non-system disks can be erased.

#### Releases
- Three separate channels (Stable, Pre-release, Nightly) with detailed release titles and codenames; SHA-256 checksums.

### Known issues
- Not tested on real hardware.
- No post-install root patching (needs macOS).
- USB port mapping must be done with USBToolBox.

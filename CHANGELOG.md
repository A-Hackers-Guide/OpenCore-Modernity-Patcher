# Changelog

All notable changes to OpenCore Modernity Patcher. Versions follow [Semantic Versioning](https://semver.org); channels are described in [RELEASES.md](RELEASES.md).

## [Unreleased]

## [0.1.0-beta.3] - 2026-10-30

Second "First Light" pre-release: macOS Golden Gate diagnosis and three new tools.

### Added
- **macOS Golden Gate (27) diagnosis.** Checked on a real macOS 27.0.1 (26A434) install: Golden Gate is Apple-silicon only. It has no Intel kernel collection and no Intel/AMD GPU or X86 power-management drivers, only 2 of 186 built-in apps (the Installers) keep Intel code, and Apple offers no Intel Mac anything past 26.7. Golden Gate is now a known target (Darwin 27) that is refused with this explanation in the GUI, the CLI and the compatibility report. Tahoe is confirmed as the last macOS for PCs.
- **macOS inspector** (`--inspect-macos [PATH]`, *Support → Check a macOS Install*): pure-Python Mach-O parsing reports whether any macOS install can still run on PCs. Works on Windows/Linux against a copied system folder.
- **Compatibility report** (`--compat`, *Support → Compatibility Report*, and a summary in *Detect Hardware*): runs the planner for every macOS version and shows the newest one the PC can run and with which SMBIOS.
- **EFI checker** (`--check-efi PATH`, *Support → Check an Existing EFI*): checks any OpenCore EFI for outdated kexts and OpenCore, enabled-but-missing kexts/drivers/SSDTs, and runs `ocvalidate`.
- **Stable serial numbers:** SMBIOS serial, MLB, UUID and ROM are saved per model and reused on every rebuild. *Settings → SMBIOS → Generate new serial* starts over.
- Every EFI records its build info in `EFI/OC/.ocmp-build.json`.
- `--target` accepts multi-word names (`"golden gate"`, `goldengate`, `27`).

### Tests
- 16 tests (was 10): synthetic thin/universal Mach-O binaries, Apple-silicon-only vs Intel-capable system volumes, Golden Gate refusal, compatibility ordering, serial reuse.

## [0.1.0-beta.2] - 2026-10-30

First public pre-release, codename **"First Light"**. Tested with `ocvalidate` and simulated hardware profiles only. **Not yet booted on real hardware.**

> `v0.1.0-beta.1` was tagged but never published: its Windows build failed. Everything below is new in this release, plus the fixes listed here.

### Fixed
- Windows: text files (build report, settings, hardware profiles, release notes) are now always read and written as UTF-8. Before, Windows' default `cp1252` encoding crashed on characters like `→` and `®`.
- CI now runs the tests and release naming on Windows as well as Linux, so Windows-only problems are caught before a release.

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

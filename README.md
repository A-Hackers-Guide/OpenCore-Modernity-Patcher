<div align="center">

# OpenCore Modernity Patcher

**Build a bootable OpenCore EFI for your PC from Windows or Linux, with no Mac required.**

The interface works like OpenCore Legacy Patcher. The target is different: Intel and AMD PCs, laptops and KVM/QEMU virtual machines.

[![Build](https://github.com/A-Hackers-Guide/OpenCore-Modernity-Patcher/actions/workflows/build.yml/badge.svg)](https://github.com/A-Hackers-Guide/OpenCore-Modernity-Patcher/actions/workflows/build.yml)
[![Latest stable](https://img.shields.io/github/v/release/A-Hackers-Guide/OpenCore-Modernity-Patcher?label=stable&style=flat-square&color=8b5cf6)](https://github.com/A-Hackers-Guide/OpenCore-Modernity-Patcher/releases/latest)
[![Latest pre-release](https://img.shields.io/github/v/release/A-Hackers-Guide/OpenCore-Modernity-Patcher?include_prereleases&label=pre-release&style=flat-square&color=f59e0b)](https://github.com/A-Hackers-Guide/OpenCore-Modernity-Patcher/releases)
![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-0078D4?style=flat-square&logo=windows)
![Linux](https://img.shields.io/badge/Linux-AppImage-FCC624?style=flat-square&logo=linux&logoColor=black)
![macOS targets](https://img.shields.io/badge/targets-High%20Sierra%20→%20Tahoe-000?style=flat-square&logo=apple)

[Download](#-download) · [Quick start](#-quick-start) · [Supported hardware](#-supported-hardware) · [macOS Tahoe](#-macos-tahoe-26) · [Golden Gate](#-macos-golden-gate-27-why-pcs-cant-run-it) · [KVM](#-kvm--qemu-virtual-machines) · [Known limitations](#-known-limitations) · [Credits](#-credits)

</div>

> [!WARNING]
> **Early software.** Version 0.1 has only been checked with `ocvalidate`, simulated hardware profiles and a real macOS 27 install (for the Golden Gate diagnosis). It has **not yet been booted on real hardware**. Keep your current EFI and a backup of your data until releases are marked **Stable**.

---

## Contents

1. [What it does](#-what-it-does)
2. [Download](#-download)
3. [Release channels: Stable, Pre-release and Nightly](#-release-channels-stable-pre-release-and-nightly)
4. [Quick start](#-quick-start)
5. [The interface, window by window](#-the-interface-window-by-window)
6. [Supported hardware](#-supported-hardware)
7. [macOS Tahoe (26)](#-macos-tahoe-26)
   - [macOS Golden Gate (27): why PCs can't run it](#-macos-golden-gate-27-why-pcs-cant-run-it)
   - [Tools: compatibility report, macOS inspector, EFI checker](#-tools-compatibility-report-macos-inspector-efi-checker)
8. [KVM / QEMU virtual machines](#-kvm--qemu-virtual-machines)
9. [How a build is decided](#-how-a-build-is-decided)
10. [What ends up in the EFI](#-what-ends-up-in-the-efi)
11. [Command line](#-command-line)
12. [Hardware profiles](#-hardware-profiles)
13. [Where files are kept](#-where-files-are-kept)
14. [Known limitations](#-known-limitations)
15. [Troubleshooting](#-troubleshooting)
16. [Building from source](#-building-from-source)
17. [How releases are made](#-how-releases-are-made)
18. [Credits](#-credits)
19. [License](#-license)

---

## ✨ What it does

OpenCore Legacy Patcher (OCLP) helps **old Macs** run new macOS, and it runs only on macOS. This project brings the same one-window experience to **PCs**, running from **Windows and Linux**:

| Step | What happens |
|---|---|
| **Detect** | Reads your CPU, GPUs, network cards, chassis type and motherboard (WMI/CIM on Windows, `/proc` and `/sys` on Linux). |
| **Plan** | Picks the platform (Intel desktop/laptop/HEDT, AMD desktop/laptop, KVM), the SMBIOS model, kexts, ACPI tables, quirks and boot-args, following the [Dortania OpenCore Install Guide](https://dortania.github.io/OpenCore-Install-Guide/). |
| **Download** | Fetches the latest OpenCorePkg, kexts, prebuilt SSDTs and [AMD_Vanilla](https://github.com/AMD-OSX/AMD_Vanilla) patches **from their own release pages**. Nothing third-party is bundled in the app. |
| **Build** | Writes `config.plist` from the same OpenCore release's `Sample.plist`, generates serial numbers with `macserial`, assembles `EFI/`, and **validates it with `ocvalidate`**. |
| **Install** | Copies the EFI to a disk's EFI partition, keeping a backup and leaving Windows and Linux boot loaders untouched. |
| **Installer USB** | Downloads macOS Recovery straight from Apple and writes a bootable USB with your EFI on it. |
| **Compatibility report** | Shows every macOS version, High Sierra to Golden Gate, with whether your PC can run it and which Mac model it would use. |
| **macOS inspector** | Checks any macOS install for Intel support. This is how Golden Gate was diagnosed as Apple-silicon only. |
| **EFI checker** | Checks any existing OpenCore EFI: outdated kexts, missing files, `ocvalidate` results. |
| **Stable serials** | Generated serial numbers are saved and reused, so rebuilding doesn't make iMessage/FaceTime see a "new Mac". |

---

## ⬇ Download

Grab the file for your OS from **[Releases](https://github.com/A-Hackers-Guide/OpenCore-Modernity-Patcher/releases)**:

| Platform | File name pattern | Notes |
|---|---|---|
| Windows 10 / 11, x64 | `OpenCore-Modernity-Patcher-<version>-Windows-x64.exe` | Single file, no installer. |
| Linux, x86_64 | `OpenCore-Modernity-Patcher-<version>-Linux-x86_64.AppImage` | Needs glibc 2.35+ (Ubuntu 22.04, Fedora 36, Debian 12 or newer) and GTK 3. |

Every release includes `SHA256SUMS.txt`. Check your download:

```bash
sha256sum -c SHA256SUMS.txt --ignore-missing
```

On Windows (PowerShell):

```powershell
Get-FileHash .\OpenCore-Modernity-Patcher-*-Windows-x64.exe -Algorithm SHA256
```

---

## 🚦 Release channels: Stable, Pre-release and Nightly

The three channels are kept strictly separate:

| Channel | Where you find it | Tag format | Shown in app as | Who it's for |
|---|---|---|---|---|
| **Stable** | Releases page, marked **Latest** | `v1.2.0` | `Version 1.2.0` | Everyone. |
| **Pre-release** | Releases page, marked **Pre-release** (never "Latest") | `v1.2.0-alpha.1`, `v1.2.0-beta.3`, `v1.2.0-rc.1` | `Version 1.2.0-beta.3 (Pre-release)` | Testers willing to report problems. |
| **Nightly** | *Actions* tab → a workflow run → *Artifacts* (never on the Releases page) | none (every push to `main`) | `Version 1.2.0-nightly.abc1234 (Nightly)` | Developers. |

**Release names** follow one pattern, with a codename per minor version (see [`packaging/release_codenames.json`](packaging/release_codenames.json)):

| Tag | Release title |
|---|---|
| `v0.1.0-alpha.1` | OpenCore Modernity Patcher 0.1.0 Alpha 1 "First Light" (Pre-release) |
| `v0.1.0-beta.1` | OpenCore Modernity Patcher 0.1.0 Beta 1 "First Light" (Pre-release) |
| `v0.1.0-rc.1` | OpenCore Modernity Patcher 0.1.0 Release Candidate 1 "First Light" (Pre-release) |
| `v0.1.0` | OpenCore Modernity Patcher 0.1.0 "First Light" |
| `v0.2.0` | OpenCore Modernity Patcher 0.2.0 "Second Sunrise" |

The full policy is in [RELEASES.md](RELEASES.md).

---

## 🚀 Quick start

1. **Run the app** on the PC you want to put macOS on.
   - Windows: double-click the `.exe`. For disk steps, right-click → **Run as administrator**.
   - Linux: `chmod +x OpenCore-Modernity-Patcher-*.AppImage`, then run it. For disk steps run `sudo -E ./OpenCore-Modernity-Patcher-*.AppImage`.
2. Check the **Model** line on the main menu. Click **Detect Hardware** to see everything it found.
3. Open **⚙️ Settings** and pick the **Target macOS** (default: macOS Sequoia).
4. Click **Build and Install OpenCore**. Read the log, especially any `WARNING:` lines.
5. Choose **Install to disk** to copy it to an EFI partition, or **Open EFI folder** to copy it yourself.
6. Click **Create macOS Installer** → **Download macOS Installer**, pick a version and a USB stick (8 GB+). The stick is erased.
7. Before booting, set your **BIOS** as the Dortania guide describes. Typical settings: disable Secure Boot, CSM and VT-d (or keep `DisableIoMapper`); enable Above 4G Decoding and XHCI Hand-off; set SATA to AHCI.
8. Boot from the USB, choose **macOS Base System** in the OpenCore picker, and install.
9. After installing, map your USB ports with **[USBToolBox](https://github.com/USBToolBox/tool)** (it runs on Windows) and add the generated `UTBMap.kext`.

---

## 🪟 The interface, window by window

The windows, sizes and flow match OpenCore Legacy Patcher's, so OCLP users will feel at home.

| OCLP window | Here | Differences |
|---|---|---|
| Main menu (600 px, two columns) | Same layout | "Post-Install Root Patch" becomes **Detect Hardware**: root patching edits a macOS system volume and can only run inside macOS. |
| Build and Install OpenCore | Same: log view, then *Install to disk* | Extra button: **Open EFI folder**. |
| Install OpenCore → disk → volume | Same three steps | Lists disks with an EFI partition; blue = removable. Boot disks get an extra warning, and the old `EFI/OC` is backed up to `EFI-backup-ocmp`. |
| Create macOS Installer | Same: *Download* / *Use existing*, version list, disk list, flashing | Downloads **Recovery** (`BaseSystem.dmg`) from Apple instead of a full `InstallAssistant.pkg`, which can't be unpacked outside macOS. Installing then needs internet. |
| Settings (600×685, tabs) | Same structure | Tabs: Build, Hardware, Security, SMBIOS, Advanced. *Target Model* (a Mac) becomes **Target macOS** plus an SMBIOS override. |
| Support / About / Credits | Same | Links to Dortania guides, USBToolBox, AMD_Vanilla. |
| File → Reveal Log File | Same | Opens Explorer or your Linux file manager. |

Icons are drawn by the app itself. OCLP's artwork carries its branding, so it isn't used.

---

## 🧩 Supported hardware

### CPUs

| CPU | Status | Notes |
|---|---|---|
| Intel Haswell (4th gen) → Comet Lake (10th gen) | ✅ | Desktop and laptop. |
| Intel Rocket Lake (11th gen desktop) | ✅ with dGPU | iGPU unsupported; CPU spoofed as Comet Lake. |
| Intel Alder / Raptor / Arrow Lake (12th–15th gen) | ✅ with dGPU | Spoofed as Comet Lake, `ProvideCurrentCpuInfo`, CpuTopologyRebuild. Disabling E-cores in BIOS helps. |
| Intel Ice Lake laptops | ✅ | Iris Plus iGPU supported. |
| Intel HEDT (Haswell-E, Broadwell-E, Skylake-X/Cascade Lake-X) | ✅ with dGPU | iMacPro1,1 / MacPro7,1. |
| Intel Ivy Bridge and older | ❌ | Too old for any targeted macOS. |
| AMD Ryzen / Threadripper (Zen, Zen+, Zen 2, Zen 3, Zen 4, Zen 5) | ✅ with supported dGPU | [AMD_Vanilla](https://github.com/AMD-OSX/AMD_Vanilla) kernel patches with your core count filled in. |
| AMD Ryzen APU graphics (Raven, Picasso, Renoir, Cezanne, Barcelo) | 🧪 | Via the community kext [NootedRed](https://github.com/ChefKissInc/NootedRed), up to Sequoia. |
| AMD FX (15h) / Athlon (16h) | ⚠️ | No AVX2. Ventura+ needs CryptexFixup, and some apps won't run. |

### GPUs

| GPU | macOS support |
|---|---|
| AMD Polaris (RX 460–590), Vega (56/64/VII) | High Sierra → Tahoe |
| AMD Navi 10/14 (RX 5000), Navi 21 (RX 6800/6900), Navi 23 (RX 6600) | Catalina/Big Sur/Monterey → Tahoe (`agdpmod=pikera` added automatically) |
| AMD Navi 22 (RX 6700/6750) | Monterey 12.1 → Tahoe |
| AMD Navi 24 (RX 6400/6500), RDNA 3 (RX 7000), RDNA 4 (RX 9000) | ❌ no drivers; disabled automatically |
| NVIDIA Kepler (GTX 600/700) | up to Big Sur natively; Monterey+ needs root patching from macOS |
| NVIDIA Maxwell/Pascal (GTX 900/1000) | High Sierra only (Web Drivers) |
| NVIDIA Turing and newer (GTX 16, RTX 20/30/40/50) | ❌ no drivers; disabled automatically |
| Intel HD/UHD/Iris (Haswell → Comet Lake, Ice Lake) | ✅ framebuffer set automatically (headless when a dGPU is present) |

Unsupported GPUs are disabled with `disable-gpu-support` when their PCI path is known, or `-wegnoegpu` otherwise. The build stops with a clear message if no usable GPU is left.

### Networking

| Device | Driver |
|---|---|
| Intel I217/I218/I219/82579 | IntelMausi |
| Intel I210/I211 | built in |
| Intel I225-V / I226-V | built in, with device-id spoof and `e1000=0` |
| Realtek RTL8111/8168 | RealtekRTL8111 |
| Realtek RTL8125 (2.5 GbE) | LucyRTL8125Ethernet |
| Atheros/Killer E2200/E2400/E2500 | AtherosE2200Ethernet |
| Intel Wi-Fi (AX200/201/210/211, 9260/9560, 8265, 7265…) | itlwm (join networks with the **HeliPort** app) |
| Intel Bluetooth | IntelBluetoothFirmware + IntelBTPatcher + BlueToolFixup |
| Broadcom Fenvi-type Wi-Fi | built in up to Ventura; Sonoma+ needs root patching from macOS |
| KVM: virtio-net, vmxnet3 | built in |

---

## 🍎 macOS Tahoe (26)

Tahoe is a first-class target:

- **Picks a Tahoe-capable SMBIOS automatically.** Apple limits Tahoe to Intel Macs with these model IDs: **MacPro7,1**, **iMac20,1/20,2** and **MacBookPro16,1/16,2/16,4**. Older models are upgraded for you:
  - Coffee/Comet Lake desktops: iMac19,1 → **iMac20,1** (iGPU still works: same UHD 630).
  - Coffee/Comet Lake laptops: MacBookPro15,2/16,3 → **MacBookPro16,1**.
  - Ice Lake laptops: MacBookAir9,1 → **MacBookPro16,2**.
  - AMD, HEDT, Rocket/Alder/Raptor Lake: **MacPro7,1** (+ RestrictEvents to hide the Mac Pro memory/PCIe warnings).
- **AMD_Vanilla patches cover Tahoe** (kernel 25.x), with the core count filled in.
- **Recovery download:** Tahoe appears in the installer list from Apple's own board catalog.
- **Validated:** Coffee Lake + RX 580, Ryzen 5 5600X + RX 6600 and a Comet Lake laptop each produce a Tahoe EFI that passes `ocvalidate` (OpenCore 1.0.8).

Tahoe-specific limits:

- **Tahoe is the last macOS for Intel Macs.** The next macOS is Apple-silicon-only, so no PC will run it.
- Kaby Lake and older iGPUs have no Tahoe drivers. You need a supported AMD dGPU.
- Broadcom Wi-Fi and NVIDIA Kepler need root patches that only macOS itself can apply.

### 🌉 macOS Golden Gate (27): why PCs can't run it

**Short answer: Golden Gate is Apple-silicon only, so no Intel or AMD PC, laptop or VM can run it. macOS Tahoe (26) is the last macOS for PCs.**

This was checked on a real Mac running **macOS 27.0.1 (build 26A434, Darwin 27.0.0)** with the app's own inspector (`--inspect-macos`):

| What a PC needs | macOS Tahoe 26 | macOS Golden Gate 27 |
|---|---|---|
| Built-in apps with Intel (x86_64) code | all of them | **2 of 186**: only *Installer* and *Automator Installer* |
| Intel kernel collection `/System/Library/KernelCollections/BootKernelExtensions.kc` | ✅ | ❌ **missing** |
| Intel/AMD graphics drivers (AMDRadeonX6000, AppleIntel…Graphics) | ✅ | ❌ **none** |
| Intel CPU power management (X86PlatformPlugin) | ✅ | ❌ **none** |
| Intel kernel | ✅ | ⚠️ one `RELEASE_X86_64` kernel is still on disk, but it can't boot without the kernel collection and drivers |
| Newest macOS Apple's recovery catalog offers any Intel Mac | 26.x | **26.7**: no Intel Mac is offered 27 |
| Darwin version | 25 | **27**: Darwin skipped 26 to match the macOS number |

What the app does about it:

- **Golden Gate shows up in the target list**, labelled *Apple silicon only*. Selecting it shows this explanation instead of building.
- `--target "golden gate"` (or `goldengate`, `27`) fails with the same explanation instead of producing an EFI that could never boot.
- The **compatibility report** lists Golden Gate as "No" for every PC.
- **Run the inspector yourself** on any Mac or mounted macOS volume to re-check future versions: `OpenCore-Modernity-Patcher --inspect-macos /`

### 🧰 Tools: compatibility report, macOS inspector, EFI checker

All three are in **Support** (GUI) and on the command line.

**Compatibility report:** `--compat` (with `--profile` to check another machine):

```
Compatibility for: ASUS ROG STRIX B550-F GAMING
  macOS Golden Gate (27)     No     macOS Golden Gate (27) is Apple-silicon only and can't run on any PC
  macOS Tahoe (26)           Yes    MacPro7,1
  macOS Sequoia (15)         Yes    MacPro7,1
  ...
  macOS Big Sur (11)         No     No usable GPU          ← RX 6600 (Navi 23) needs Monterey+
Newest macOS for this PC: macOS Tahoe (26) as MacPro7,1
```

**macOS inspector:** `--inspect-macos [PATH]` checks a macOS system volume (default `/`) for Intel apps, Intel kernel, kernel collection and PC drivers. It parses Mach-O headers itself, so it also works on Windows or Linux against a copied or mounted system folder.

**EFI checker:** `--check-efi PATH` works on any OpenCore EFI, including hand-made ones:

```
OpenCore: 1.0.8  up to date
SMBIOS:   MacPro7,1  (newest macOS for this model: macOS Tahoe)
Kexts:
  Lilu        1.6.0   update available (1.7.2)
  NVMeFix             MISSING on disk
Problems:
  - NVMeFix.kext is enabled in config.plist but not in OC/Kexts.
Summary: 1 kext update(s) available, 1 problem(s).
```

---

## 🖥 KVM / QEMU virtual machines

Run the app **inside the Linux VM you'll convert** or **on the host** with a [profile](#-hardware-profiles), or build with `examples/profiles/kvm-amd-host.json` as a starting point.

What the KVM profile does:

- `ProvideCurrentCpuInfo`, `vmhide=on` (RestrictEvents) so macOS doesn't refuse to run as a VM, no ACPI hacks needed on Q35.
- AMD hosts automatically get AMD_Vanilla patches. Set the VM's cores to match.
- SMBIOS iMacPro1,1 (up to Sequoia without GPU passthrough) or MacPro7,1 (Tahoe, or with a passed-through AMD GPU).

Recommended VM settings (virt-manager / Proxmox / plain QEMU):

| Setting | Value |
|---|---|
| Firmware | OVMF (UEFI), Secure Boot off |
| Machine | `q35` |
| CPU | `host` (Intel hosts); `Cascadelake-Server` or `Haswell-noTSX` with AMD patches (AMD hosts) |
| Disk | SATA or virtio-blk |
| Network | virtio-net or vmxnet3 |
| Display | VMware SVGA / std VGA for basic output, or pass through a supported AMD GPU |

This profile follows the approach of [Leoyzen/KVM-Opencore](https://github.com/Leoyzen/KVM-Opencore), updated for current OpenCore. No files are copied from it.

---

## 🧠 How a build is decided

All decisions live in [`ocmp/efi_builder/planner.py`](ocmp/efi_builder/planner.py) and are pure logic: no downloads, fully unit-tested.

```
HardwareProfile ──► Planner ──► BuildPlan ──► ConfigBuilder ──► config.plist ──► ocvalidate
  (detected or        │            │              (from Sample.plist
   loaded JSON)       │            │               of the same OpenCore)
                      │            └── kexts, ACPI, drivers, quirks, boot-args,
                      │                device properties, SMBIOS, warnings, notes
                      └── rules per platform from the Dortania guide
```

Key rules:

- **Booter quirks:** older Intel (Haswell→Kaby Lake, HEDT) use `EnableWriteUnprotector`; newer and AMD use `RebuildAppleMemoryMap` + `SyncRuntimePermissions`; Coffee Lake+ add `DevirtualiseMmio` and `ProtectUefiServices`; B550/A520/TRX40 turn off `SetupVirtualMap`.
- **Kernel quirks:** `AppleXcpmCfgLock` stays on unless you tick *CFG Lock disabled in BIOS*; AMD gets `ProvideCurrentCpuInfo`, `DummyPowerManagement` and a `Kernel > Block` for `AppleMCEReporter`.
- **ACPI:** Dortania's prebuilt SSDT-EC(-USBX), SSDT-PLUG, SSDT-AWAC, SSDT-PMC, SSDT-PNLF, SSDT-CPUR, HEDT RTC/UNC, downloaded at build time.
- **iGPU:** `AAPL,ig-platform-id` per generation, headless when a supported dGPU exists, plus safe framebuffer patches and known device-id spoofs.
- **SMBIOS:** the Mac closest to your CPU/GPU that still supports the target macOS ([`smbios_data.py`](ocmp/datasets/smbios_data.py)).

---

## 📦 What ends up in the EFI

```
Build-Folder/
├── BuildReport.txt          ← platform, SMBIOS, kexts, warnings: attach this to bug reports
└── EFI/
    ├── BOOT/BOOTx64.efi
    └── OC/
        ├── OpenCore.efi
        ├── config.plist      ← validated with ocvalidate
        ├── ACPI/             ← only the SSDTs your platform needs
        ├── Drivers/          ← OpenRuntime, OpenHfsPlus, ResetNvramEntry (+ OpenCanopy)
        ├── Kexts/            ← Lilu first, then plug-ins, in load order
        ├── Resources/
        └── Tools/
```

Serial numbers come from OpenCore's `macserial` on the **first** build for each Mac model. They're saved in the data folder (`smbios/<model>.json`) and **reused on every rebuild**, so iMessage/FaceTime keep seeing the same Mac. Use **Settings → SMBIOS → Generate new serial** to start over (only before installing macOS), or type your own.

Each EFI also carries `EFI/OC/.ocmp-build.json` (app version, OpenCore version, target, SMBIOS), which the EFI checker reads.

---

## ⌨ Command line

The same app runs headless when given `--build`:

```bash
OpenCore-Modernity-Patcher --build --target tahoe
OpenCore-Modernity-Patcher --build --profile my-pc.json --target sequoia --output ./MyEFI
OpenCore-Modernity-Patcher --save-profile my-pc.json
OpenCore-Modernity-Patcher --build --smbios MacPro7,1 --debug-opencore
```

| Option | Meaning |
|---|---|
| `--build` | Build without opening the GUI. Exit code 1 if planning, downloading or `ocvalidate` fails. |
| `--profile FILE` | Build for a saved hardware profile instead of this PC. |
| `--save-profile FILE` | Detect this PC and write its profile. |
| `--target VERSION` | `high sierra` … `tahoe`, or `10.15`, `15`, `26`, or a Darwin number (`25`). |
| `--smbios MODEL` | Force a Mac model. |
| `--output DIR` | Where to write `EFI/` and `BuildReport.txt`. |
| `--debug-opencore` | Use the DEBUG OpenCore build with logging. |
| `--compat` | Show which macOS versions this PC (or `--profile`) can run. |
| `--inspect-macos [PATH]` | Check whether a macOS install (default: this Mac, `/`) can still run on PCs. |
| `--check-efi PATH` | Check an existing EFI folder for kext updates, missing files and `ocvalidate` errors. |

Set `GITHUB_TOKEN` to avoid GitHub's 60-requests-per-hour limit when building often.

---

## 🗂 Hardware profiles

A profile is a JSON snapshot of a machine. Use one to build an EFI for a PC other than the one you're on, or to share your setup in a bug report. Examples are in [`examples/profiles/`](examples/profiles):

| File | Machine |
|---|---|
| `intel-coffeelake-rx580.json` | i7-9700K, Z390, UHD 630 + RX 580, I219-V |
| `amd-ryzen5600x-rx6600.json` | Ryzen 5 5600X, B550, RX 6600, RTL8125, AX200 |
| `intel-cometlake-laptop.json` | i5-10210U laptop, UHD, AX201 |
| `kvm-amd-host.json` | QEMU Q35 on a Ryzen 9 host, virtio-net |
| `intel-alderlake-rtx3060.json` | i5-12600K + RTX 3060: **expected to fail** (no usable GPU) |

---

## 📁 Where files are kept

| OS | Folder |
|---|---|
| Windows | `%LOCALAPPDATA%\OpenCore-Modernity-Patcher\` |
| Linux | `~/.local/share/OpenCore-Modernity-Patcher/` (or `$XDG_DATA_HOME`) |

Inside: `Build-Folder/` (last EFI), `cache/` (downloads, safe to delete), `Recovery/` (macOS recovery images), `settings.json`, `ocmp.log`. Set `OCMP_DATA_DIR` to use another folder.

---

## ⚠ Known limitations

- **Not tested on real hardware yet** (see the warning at the top).
- **No root patching.** Anything OCLP fixes *after* install (Kepler, Broadcom Wi-Fi on Sonoma+, legacy Metal) has to be done from macOS.
- **USB mapping is manual.** USBToolBox.kext is included, but you need to make `UTBMap.kext` with the USBToolBox tool.
- **ACPI is generic.** Prebuilt SSDTs fit most boards. Unusual laptops may need custom SSDTs (I2C trackpads, backlight, battery).
- **Recovery-based installer.** Needs a wired network (or supported Wi-Fi) during install.
- **Hackintosh GPUs only.** NVIDIA RTX/GTX 16+ and AMD RX 7000/9000 can't be used by macOS at all.
- Only KVM/QEMU virtual machines are supported. VMware, Hyper-V and VirtualBox are refused with a message.
- Apple's macOS license allows macOS only on Apple-branded hardware. You're responsible for how you use this tool.

---

## 🛠 Troubleshooting

| Symptom | Try |
|---|---|
| "GitHub API rate limit reached" | Wait an hour, or set the `GITHUB_TOKEN` environment variable. |
| "No usable GPU" | Your GPU has no macOS drivers. Add a supported AMD card, or pick an older target if your iGPU supports one. |
| "ocvalidate reported problems" | Open an issue with `BuildReport.txt` and the log; it's a bug in the planner. |
| Disk list is empty | Run as administrator/root. The disk must be GPT with an EFI (FAT32) partition. |
| Stuck at `[EB|#LOG:EXITBS:START]` | Check BIOS settings; try *CFG Lock* off in Settings only if you unlocked it in BIOS. |
| Black screen after the Apple logo | GPU problem: try `agdpmod=pikera` (AMD Navi) or turn on *Disable discrete GPU* to test the iGPU. |
| Install says "This version of macOS is not supported" | Wrong target. Rebuild for the macOS you're installing. |

Dortania's [troubleshooting guide](https://dortania.github.io/OpenCore-Install-Guide/troubleshooting/troubleshooting.html) covers boot errors in depth.

---

## 🔨 Building from source

Requirements: Python 3.12, wxPython 4.2.

```bash
git clone https://github.com/A-Hackers-Guide/OpenCore-Modernity-Patcher.git
cd OpenCore-Modernity-Patcher
python -m venv .venv && . .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m ocmp                                       # GUI
python -m ocmp --build --profile examples/profiles/amd-ryzen5600x-rx6600.json --target tahoe
python -m pytest -q tests
```

On Linux, install wxPython from its wheel index: `pip install -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-22.04/ wxPython`.

Packaging (normally done by CI):

```bash
python packaging/make_icons.py
pyinstaller --noconfirm packaging/ocmp.spec
bash packaging/build_appimage.sh OpenCore-Modernity-Patcher-dev-Linux-x86_64.AppImage   # Linux only
```

PyInstaller can't cross-compile, so the `.exe` is built on Windows and the `.AppImage` on Linux.

### Project layout

```
ocmp/
├── __main__.py               entry point (GUI or --build)
├── constants.py              global state, paths, settings defaults
├── _version.py               version + channel (rewritten by CI from the git tag)
├── hardware.py               detection (Windows, Linux) and profiles
├── network_handler.py        GitHub releases, downloads, cache
├── disk_handler.py           list disks, mount EFI partitions, flash USB
├── macos_installer_handler.py  Apple recovery via macrecovery.py
├── settings.py               persist settings
├── datasets/                 CPU, PCI, SMBIOS, iGPU and kext tables
├── efi_builder/
│   ├── planner.py            hardware → BuildPlan (all the rules)
│   ├── config.py             BuildPlan → config.plist, AMD patch filling
│   └── build.py              download, assemble, macserial, ocvalidate
└── wx_gui/                   windows (main menu, build, install, installer, settings, help, about)
packaging/                    PyInstaller spec, AppImage script, icons, release naming
tests/                        planner, parser and patch tests
examples/profiles/            sample hardware profiles
```

---

## 🏷 How releases are made

1. Update [CHANGELOG.md](CHANGELOG.md) with a `## [x.y.z-beta.n]` or `## [x.y.z]` section.
2. Tag and push: `git tag v0.1.0-beta.2 && git push origin v0.1.0-beta.2`.
3. CI tests, builds the `.exe` and `.AppImage`, writes `SHA256SUMS.txt` and publishes the release, titled and marked per [RELEASES.md](RELEASES.md).

---

## 🙏 Credits

| Project | Authors | Used for |
|---|---|---|
| [OpenCorePkg](https://github.com/acidanthera/OpenCorePkg), Lilu, VirtualSMC, WhateverGreen, AppleALC, RestrictEvents, NVMeFix, CryptexFixup, IntelMausi, VoodooPS2, BrcmPatchRAM | [Acidanthera](https://github.com/acidanthera) | The boot loader, its tools and core kexts (downloaded) |
| [OpenCore Legacy Patcher](https://github.com/dortania/OpenCore-Legacy-Patcher) | Dortania: Dhinak G, Mykola Grymalyuk and contributors | Interface layout and app structure this project follows |
| [OpenCore Install Guide](https://dortania.github.io/OpenCore-Install-Guide/), [Getting Started With ACPI](https://github.com/dortania/Getting-Started-With-ACPI) | Dortania | Per-platform rules; prebuilt SSDTs (downloaded) |
| [AMD_Vanilla](https://github.com/AMD-OSX/AMD_Vanilla) | AMD-OSX: algrey, Shaneee, Goldfish64, CaseySJ and others | AMD kernel patches (downloaded at build time) |
| [KVM-Opencore](https://github.com/Leoyzen/KVM-Opencore) | Leoyzen | Approach for the KVM profile |
| [SMCAMDProcessor](https://github.com/trulyspinach/SMCAMDProcessor) | trulyspinach | AMD power management |
| [NootedRed](https://github.com/ChefKissInc/NootedRed) | ChefKissInc | Ryzen APU graphics |
| RealtekRTL8111, LucyRTL8125Ethernet, AtherosE2200Ethernet | Mieze | Ethernet |
| [itlwm](https://github.com/OpenIntelWireless/itlwm), IntelBluetoothFirmware | OpenIntelWireless | Intel Wi-Fi and Bluetooth |
| [CpuTopologyRebuild](https://github.com/b00t0x/CpuTopologyRebuild) | b00t0x | Hybrid Intel CPUs |
| [USBToolBox](https://github.com/USBToolBox) | dhinakg and contributors | USB mapping |
| [wxPython](https://wxpython.org), [PyInstaller](https://pyinstaller.org), [AppImage](https://appimage.org) | their authors | GUI and packaging |

This product includes software developed by Dortania and OpenCore Legacy Patcher contributors.

---

## 📄 License

[BSD 3-Clause](LICENSE) for this project's own code. The GUI follows the design of OpenCore Legacy Patcher, whose license terms are reproduced in [LICENSE-OCLP.txt](LICENSE-OCLP.txt). "OpenCore Legacy Patcher" and "Dortania" are not used to endorse or promote this project. Downloaded components keep their own licenses.

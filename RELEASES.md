# Release Policy

OpenCore Modernity Patcher ships on three channels. They never mix: a nightly is never published as a release, and a pre-release is never marked "Latest".

## Channels at a glance

| | **Stable** | **Pre-release** | **Nightly** |
|---|---|---|---|
| Purpose | Recommended for everyone | Testing before a stable release | Every change on `main`, for developers |
| Git tag | `vMAJOR.MINOR.PATCH` | `vMAJOR.MINOR.PATCH-alpha.N` · `-beta.N` · `-rc.N` | none |
| Published on | Releases page, marked **Latest** | Releases page, marked **Pre-release** | *Actions* → run → *Artifacts* (expire after 90 days) |
| In-app version label | `Version 0.2.0` | `Version 0.2.0-beta.1 (Pre-release)` | `Version 0.2.0-nightly.1a2b3c4 (Nightly)` |
| `_version.CHANNEL` | `Stable` | `Pre-release` | `Nightly` |
| Release notes banner | NOTE: Stable release | WARNING: Pre-release, may not boot | none |
| Checksums | `SHA256SUMS.txt` | `SHA256SUMS.txt` | none |

Any other tag (e.g. `v0.2`, `0.2.0`, `v0.2.0-test`) fails CI on purpose and publishes nothing.

## Pre-release stages

| Stage | Tag example | Meaning |
|---|---|---|
| **Alpha** | `v0.2.0-alpha.1` | Features still landing. Expect broken builds on some platforms. |
| **Beta** | `v0.2.0-beta.1` | Feature-complete for the version. Needs real-hardware reports. |
| **Release Candidate** | `v0.2.0-rc.1` | Ships as stable unless a blocking bug is reported. |

A version moves alpha → beta → rc → stable. Numbers restart for each stage (`beta.1`, `beta.2`, … then `rc.1`).

## Release names

```
OpenCore Modernity Patcher <MAJOR.MINOR.PATCH> [<Stage> <N>] "<Codename>" [(Pre-release)]
```

Codenames are one per minor version, kept in [`packaging/release_codenames.json`](packaging/release_codenames.json):

| Minor | Codename |
|---|---|
| 0.1 | First Light |
| 0.2 | Second Sunrise |
| 0.3 | Third Horizon |
| 0.4 | Fourth Frontier |
| 0.5 | Fifth Element |
| 1.0 | Modernity |

Examples:

| Tag | Title on the Releases page |
|---|---|
| `v0.1.0-beta.1` | OpenCore Modernity Patcher 0.1.0 Beta 1 "First Light" (Pre-release) |
| `v0.1.0-rc.2` | OpenCore Modernity Patcher 0.1.0 Release Candidate 2 "First Light" (Pre-release) |
| `v0.1.0` | OpenCore Modernity Patcher 0.1.0 "First Light" |
| `v0.1.1` | OpenCore Modernity Patcher 0.1.1 "First Light" |
| `v1.0.0` | OpenCore Modernity Patcher 1.0.0 "Modernity" |

## Asset names

```
OpenCore-Modernity-Patcher-<version>-Windows-x64.exe
OpenCore-Modernity-Patcher-<version>-Linux-x86_64.AppImage
SHA256SUMS.txt
```

`<version>` is the tag without the leading `v` (e.g. `0.1.0-beta.1`).

## When can something become Stable?

All of these must be true:

1. The previous release candidate has been out for at least 7 days with no open *blocker* issues.
2. At least one real-hardware boot report each for: an Intel desktop, an AMD desktop, an Intel laptop, and a KVM virtual machine.
3. CI is green on `main` (tests, pyflakes, both packages build).
4. `CHANGELOG.md` has a section for the exact version.

Until 0.1.0 meets these, every build is a pre-release.

## How to cut a release

```bash
# 1. Write the changelog section, e.g. "## [0.1.0-beta.2] - 2026-11-05"
# 2. Commit it, then tag and push the tag:
git tag v0.1.0-beta.2
git push origin v0.1.0-beta.2
```

CI (`.github/workflows/build.yml`) then:

1. runs `pyflakes` and `pytest`;
2. runs `packaging/release_info.py`, which classifies the tag, rewrites `ocmp/_version.py`, and writes the release title and notes (from the matching `CHANGELOG.md` section);
3. builds the `.exe` on Windows and the `.AppImage` on Linux;
4. writes `SHA256SUMS.txt`;
5. publishes the GitHub release, setting **Pre-release** and **Latest** from the channel.

To withdraw a bad release, mark it as a pre-release (or delete it) and publish a fixed patch version. Tags that were published are never moved or reused.

## Release history

| Tag | Published | Channel | Highlights |
|---|---|---|---|
| `v0.1.0-beta.5` | 2026-10-30 | Pre-release | Update kexts in an existing EFI, with backup |
| `v0.1.0-beta.4` | 2026-10-30 | Pre-release | One-click OpenCanopy (GUI boot picker) theme |
| `v0.1.0-beta.3` | 2026-10-30 | Pre-release | Golden Gate diagnosis, macOS inspector, compatibility report, EFI checker, saved serials |
| `v0.1.0-beta.2` | 2026-10-30 | Pre-release | First public release (Windows UTF-8 fix) |
| `v0.1.0-beta.1` | *never published* | n/a | Tagged, but the Windows build failed, so CI published nothing. Kept because tags are never reused. |

No stable release yet: 0.1.0 needs the real-hardware reports listed above.


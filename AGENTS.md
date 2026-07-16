# ZaeREo contributor instructions

ZaeREo is an unofficial, behavior-first port of Zaero to Quake II Rerelease.
Compatibility work follows this order:

1. load and complete every original Zaero map;
2. preserve gameplay-observable Zaero behavior and mapper contracts;
3. integrate correctly with Rerelease saves, multiplayer, input, HUD, and time;
4. preserve harmless quirks; and
5. improve defects or presentation only through a recorded decision.

The detailed authority is [docs/ZAERO_PORT_ROADMAP.md](docs/ZAERO_PORT_ROADMAP.md).
The repository has a compiling early integration DLL but is still pre-playable.
`zbase1`, `zdef1`, and `zboss` have passed only bounded legacy single-stage
DLL-load/map-spawn/client-entry/shutdown smokes. Those reports predate the
two-stage window-before-mod/map protocol and must be rerun before they count as
launch-safety evidence; no supplied map has passed completion or
gameplay-compatibility verification. Do not describe planned or static-only
behavior as live-compatible.

## Normal workflow

The supported first environment is Windows 10/11 x64, Visual Studio 2022 C++
Build Tools, PowerShell 7, Python 3.11+, Git LFS, vcpkg, Quake II Rerelease,
and—optionally, when rebuilding the content pack from its original files—an
existing Zaero installation.

Local source and game locations are configuration, never repository constants.
The shared resolver order is explicit script argument, current environment
variable, ignored schema-version-1 `.zaereo.local.json`, then safe read-only
discovery. Copy `.zaereo.local.example.json` to `.zaereo.local.json` and fill in
only local paths; never add credentials to that file. The legacy
`Q2RERELEASE_ROOT` environment variable and `q2RereleaseRoot` config key remain
warning-only aliases for the read-only engine/data root, never for a writable
install destination. Bootstrap and build both accept `-VcpkgRoot` and otherwise
resolve `VCPKG_ROOT`, `vcpkgRoot`, or a `vcpkg` command on `PATH` in that order.

The intended command loop is:

~~~powershell
./tools/bootstrap.ps1 -VcpkgRoot "C:\path\to\vcpkg"
python ./tools/import_legacy_assets.py --source "D:\Games\Zaero" --output .install/imported/zaereo --manifest .install/imported/zaereo-asset-manifest.json
./tools/build_game.ps1 -Configuration Debug -VcpkgRoot "C:\path\to\vcpkg"
./tools/verify_binary.ps1 -BinaryPath ./build/Debug/game_x64.dll
python ./tools/validate_runtime.py --root .install/imported/zaereo --manifest .install/imported/zaereo-asset-manifest.json --strict
./tools/install_dev.ps1 -EngineRoot "D:\Games\Quake II Rerelease\rerelease" -ContentRoot .install/imported/zaereo -AssetManifest .install/imported/zaereo-asset-manifest.json -Configuration Debug -WhatIf
# Inspect first; without -UserRoot, the managed install targets the current
# user's Saved Games\Nightdive Studios\Quake II\zaereo directory.
~~~

Use `-UserRoot` for an explicit writable user-data parent. Use `-GameRoot` only
as an intentional portable/disposable override whose directory already contains
`baseq2`; it is mutually exclusive with `-UserRoot`. The normal installer treats
`-EngineRoot` as read-only and refuses engine/program-root and `baseq2` writes.
Always launch Quake II Rerelease in windowed mode for development, debugging,
and automated or manual validation; never start it fullscreen. Repository launch
wrappers and shared editor configurations must pass the KEX startup argument
`-window` before video initialization, retain `v_windowmode 0` in the runtime
command, and positively verify that the created native window is windowed before
selecting the mod or map. A later switch from fullscreen is insufficient.
Automated launches must first observe a continuous three-second interval with
no selected Rerelease process, preventing a just-exited Steam/KEX handoff from
reusing stale startup state. If any visible native window is popup/non-windowed,
terminate the exact verified executable PID immediately, record a failed safety
report, and do not wait for the ordinary runtime timeout.

Windowed-only launch is a non-negotiable validation rule: no contributor may
start Quake II Rerelease fullscreen, including for a one-off manual smoke. A
post-start switch out of fullscreen does not satisfy this rule.

Developer installation, deterministic packaging, and importer-kit completion
are present. The machine-readable distribution policy records GPL-permitted code
and media distribution; publishing a release is a human-approved step, and the
manual publisher stays behind that approval. Exact-commit readiness and the
complete mode-specific packager are not fully implemented yet — that is an
engineering-readiness gap, not a rights gap. The gameplay tree is GPL and may be
pushed and tagged normally; only a public release archive waits on maintainer
approval of a draft release. A `local-full` archive is unvalidated developer
scratch and is kept out of release channels for that reason, not a licensing
one. If a roadmap command is not present, do not create a fake success path or
bypass its gate.

## Porting rules

- Port behavior into the C++17 Rerelease API 2023 substrate. Do not replace an
  upstream file wholesale with its legacy C counterpart.
- Keep upstream code easy to diff. Prefer Zaero-owned code under src/zaero and
  small reviewed hooks at native integration points.
- Translate frame counts and float seconds to typed durations. Verify all think,
  weapon, AI, damage-tick, and random-decision cadence at 40 Hz.
- Register every new field, callback, movement table, identifier, and entity
  reference with the JSON save system. Add lifecycle round-trip tests.
- Treat exact classnames, key names, flag meanings, and case-sensitive runtime
  paths as compatibility interfaces. Preserve monster_sentien spelling.
- Preserve native Rerelease game/cgame APIs, split-screen state isolation,
  expansion support, wheel behavior, bot metadata, and safe entity handles.
- Do not copy unrelated vintage Quake II drift into the current baseline.
- Test cleanup on death, disconnect, transition, free/reuse, and failed spawn.

Classify every observable delta in docs/compatibility/feature-matrix.md:

- **PARITY** reproduces legacy behavior, including relevant boundary cases.
- **ADAPT** preserves intent through a Rerelease-native implementation.
- **FIX** corrects a demonstrated defect while a regression test preserves the
  valid legacy behavior.

No behavior may disappear silently. Source-only mapper surfaces become working
implementations or explicit compatibility no-ops.

## Evidence and living documents

Every implementation change must update the affected ledgers:

- feature-matrix.md: disposition, implementation, test, and status;
- entity-matrix.md: classname, keys/flags, maps, save state, and spawn status;
- map-matrix.md: mode, progression, dependencies, smoke/play status;
- quirks.md: evidence, decision, behavioral impact, and regression test;
- decisions.md: context, alternatives, owner/date, and migration effects.

Link claims to source, map, asset, test, or generated audit evidence. A checked
box without that evidence is not completion. Generated normalized audits belong
under docs/audits; scratch output does not.

## Assets and provenance

The Zaero source and assets are GPL-released, and the Rerelease substrate is
GPL-2.0, so ZaeREo redistributes all of it under the GPL. The ported content is
bundled into `asset-full` releases; an `importer-kit` mode is also offered for
users who prefer to rebuild the pack from their own installation. When you touch
ported content, keep the original authors' copyright notices and credits intact.
Do not commit legacy `gamex86.dll`/`gamei386.so` binaries or the destructive
original `default.cfg` — they are excluded for engine-compatibility and safety
reasons, not licensing.

Use `docs/audits/assets.json` as the checked-in identity inventory, the current
import's deterministic JSON manifest as byte evidence, and the reviewed
asset-policy overlay as the per-runtime-path media policy. The
`distribution-policy.json` record maps components, modes, and
repository/source/CI/release channels to their licenses; publication of a
release still waits on maintainer approval of a draft. Preserve
pak0 < pak1 < pak2 precedence.
Generated PAKs, ZIPs, stages, and compiler output do not belong in Git;
regenerate them. Binary Zaero media is tracked via Git LFS. Do not treat LFS as a
home for generated packages.

Do not edit generated build/, .install/, dist/, vcpkg_installed/, packaged
archives, or generated audit scratch files. Regenerate an owned artifact through
its tool and commit the source plus normalized output where required.

## Validation and handoff

Run the narrowest relevant tests while iterating, then the full available build,
audit, save, asset, and map-smoke set before claiming completion. Report commands
and exact results. Gameplay changes require 40 Hz and save/load evidence; client
presentation requires split-screen isolation evidence; map work requires the
affected row in map-matrix.md.

Preserve unrelated work in a dirty/shared worktree. Inspect status and diffs
before editing, use focused patches, never discard another contributor's change,
and do not use destructive Git commands. Do not publish a release archive without
maintainer approval of a draft release; routine commits, pushes, and tags are
fine.

Remasters, decompiled/rebuilt maps, balance changes, and new protocol/engine work
are outside the 1.0 parity baseline unless an approved decision says otherwise.

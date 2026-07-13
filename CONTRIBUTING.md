# Contributing to ZaeREo

Thank you for helping preserve Zaero on Quake II Rerelease. The project has a
compiling early integration DLL but remains pre-playable, so progress claims
must distinguish static contracts, successful builds, live verification, and
roadmap intent.

Read [AGENTS.md](AGENTS.md) and the relevant sections of
[docs/ZAERO_PORT_ROADMAP.md](docs/ZAERO_PORT_ROADMAP.md) before changing code,
content, build logic, or compatibility records.

## Set up

The supported first environment is Windows 10/11 x64 with Visual Studio 2022
Desktop C++ Build Tools, PowerShell 7, Python 3.11+, Git LFS, vcpkg, Quake II
Rerelease, and—only for local importing—a legitimate Zaero installation.

Create an ignored local path file:

~~~powershell
Copy-Item .zaereo.local.example.json .zaereo.local.json
~~~

Fill in local paths only. Do not add tokens, passwords, or proprietary content.
The normal local loop is:

~~~powershell
./tools/bootstrap.ps1 -VcpkgRoot "C:\path\to\vcpkg"
python ./tools/import_legacy_assets.py --source "D:\Games\Zaero" --output .install/imported/zaereo --manifest .install/imported/zaereo-asset-manifest.json
./tools/build_game.ps1 -Configuration Debug -VcpkgRoot "C:\path\to\vcpkg"
./tools/verify_binary.ps1 -BinaryPath ./build/Debug/game_x64.dll
python ./tools/validate_runtime.py --root .install/imported/zaereo --manifest .install/imported/zaereo-asset-manifest.json --strict
./tools/install_dev.ps1 -EngineRoot "D:\Games\Quake II Rerelease\rerelease" -ContentRoot .install/imported/zaereo -AssetManifest .install/imported/zaereo-asset-manifest.json -Configuration Debug -WhatIf
~~~

Inspect the install preview before repeating it without `-WhatIf`. Without
`-UserRoot`, the installer writes below the current user's
`Saved Games\Nightdive Studios\Quake II` directory while treating `-EngineRoot`
as read-only. Pass `-UserRoot` for another writable user-data parent. Reserve
`-GameRoot` for an explicit portable/disposable Rerelease directory that already
contains `baseq2`; it is mutually exclusive with `-UserRoot`.

The shared path resolver uses explicit parameters, current environment
variables, the ignored schema-version-1 `.zaereo.local.json`, then safe
read-only discovery. Legacy `Q2RERELEASE_ROOT`/`q2RereleaseRoot` values warn and
resolve only the engine/data root. Both bootstrap and build accept
`-VcpkgRoot`; otherwise they resolve `VCPKG_ROOT`, `vcpkgRoot`, then `vcpkg` on
`PATH`. Use explicit parameters in CI and when validating path-sensitive
changes.

## Choose a focused change

Before editing:

1. identify the roadmap requirement and affected feature, entity, map, quirk,
   or decision row;
2. inspect the current Rerelease implementation and legacy evidence;
3. classify the result as PARITY, ADAPT, or FIX;
4. define the focused test that will prove it; and
5. check Git status so unrelated contributor work is preserved.

Port only the Zaero intent. Do not replace current Rerelease files wholesale
with legacy C files or remove modern save, cgame, split-screen, expansion, bot,
or safety behavior.

## Compatibility evidence

Every gameplay or map-facing pull request must update the applicable living
documents:

- docs/compatibility/feature-matrix.md;
- docs/compatibility/entity-matrix.md;
- docs/compatibility/map-matrix.md;
- docs/compatibility/quirks.md; and
- docs/compatibility/decisions.md when policy or architecture changes.

Record the evidence location, implementation link, test, disposition, and
status. For timing/state, include 40 Hz and native JSON save/load coverage. For
client state, include split-screen isolation. For entity changes, include exact
classname/key/flag behavior and lifecycle cleanup. A plan or code review alone
is not verification.

Proposed quirk fixes must include:

- the legacy source or retail observation;
- ordinary valid behavior to preserve;
- the defect and its impact;
- the chosen FIX or ADAPT behavior;
- a regression test; and
- any save, multiplayer, or migration consequence.

Balance changes, remasters, recompiled/decompiled maps, and protocol/engine
extensions are outside the 1.0 baseline unless approved in decisions.md.

## Assets and generated files

Zaero source/media redistribution is not cleared. Never commit files copied from
a local Zaero installation, original PAKs, legacy DLLs, saves, demos, or media.
Do not download them from unofficial mirrors. Importer tests should use synthetic
fixtures or locally generated ignored stages.

Do not hand-edit build/, .install/, dist/, vcpkg_installed/, generated PAK/ZIP
files, or audit scratch output. Change the source/tool, regenerate deterministically,
and commit only normalized reports that the roadmap requires. Cleared binary
source assets may enter Git LFS only after an explicit policy decision.

## Test expectations

Run the smallest relevant tests during development and all available affected
gates before opening a pull request. At minimum, report:

- exact commands and configuration;
- pass/fail/skip counts;
- map, mode, skill, and player count for runtime evidence;
- save points and lifecycle phases exercised;
- staged asset validator result for content changes; and
- any untested path with the reason.

Warnings, crashes, unknown entities/fields, placeholder spawns, case mismatches,
missing mandatory assets, or nondeterministic package output are failures.

## Commits and pull requests

- Keep commits focused and explain why observable behavior changes.
- Do not mix formatting or upstream churn into a feature port.
- Preserve applicable copyright and license notices.
- Never rewrite or discard unrelated work in a shared/dirty worktree.
- Complete the pull-request template and link the matrix rows and tests.
- Use draft pull requests while evidence or release gates remain incomplete.

While Zaero-derived code rights remain open, gameplay changes stay local/private
or use only an authorized private remote; do not push or tag the gameplay tree
publicly. A public tools-only contribution belongs in the separately reviewed,
history-clean tools distribution root and must satisfy its exact allowlist.

Maintainers may require additional review for game/cgame ABI, save schemas,
physics, security-sensitive parsers, provenance, packaging, and stable release
automation.

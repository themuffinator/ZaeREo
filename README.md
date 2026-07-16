# ZaeREo

ZaeREo is an unofficial, behavior-first port of the 1998 Zaero mission pack to
Quake II Rerelease. Its goal is a drop-in mod that eventually preserves every
Zaero map, gameplay system, mapper-facing contract, and intentional quirk while
using the Rerelease game API, saves, multiplayer, input, and presentation
facilities correctly.

> **Current status: roadmap/audit baseline complete; early gameplay integration.
> The substrate has Debug/Release/export proof and the current gameplay worktree has
> clean Debug and Release builds plus bounded legacy single-stage windowed load
> smokes (which must be rerun under the current window-before-mod/map protocol),
> but no supplied map has yet passed the live compatibility
> matrix and there is no stable release yet.**
> Do not treat the current DLL as a campaign-playable build. See the
> [port roadmap](docs/ZAERO_PORT_ROADMAP.md) and the
> [feature matrix](docs/compatibility/feature-matrix.md) for evidence-based
> progress.

## Compatibility status

| Surface | Intended target | Current status |
| --- | --- | --- |
| Platform | Quake II Rerelease, Windows x64 first | Supplied substrate is an exact per-file match for pinned official commit `8dc1fc9`; local Debug/Release/export proof exists, while engine-load/data-build certification remains open |
| Single player | 14-map campaign, cinematics through finale | Foundations and selected gameplay systems integrated; not map-verified/playable |
| Co-op | Authored starts and progression across all campaign maps | All 121 starts audited and native paths retained; full gameplay/progression matrix not implemented or live-verified |
| Deathmatch | Six ZDM maps plus campaign-map starts and item injection | All 230 starts and exact injection semantics are source/BSP/model-tested. Private legacy-v1 one-stage `q2dm1`/fixture reports record values 0–3, exact eight-item order/start/offset/native-drop state, authored suppression, partial success, and every one-member precondition; they must be rerun under the v2 window-before-mod/map protocol before they count as current runtime evidence. Full rules, saves, dedicated and live 2/4/8-client sessions remain |
| Bots | Safe coexistence with Rerelease bots | Appended Zaero item IDs use the native generic registry; custom active hazards publish native trap/laser metadata and invalid external item IDs are rejected before indexing. Live zdm1–6 bot/no-navigation sessions remain |
| Saves | Native Rerelease JSON save/load | Implemented-slice fields/callbacks registered; live lifecycle round trips and remaining systems are incomplete |
| Split screen | Isolated per-client HUD, views, zoom, and Visor | Flare/Sonic/Sniper/showorigin plus the active Visor view/HUD/copy state are client-local under static contracts, and full native Zaero wheel allocation plus 1–10 aliases are static-tested; live wheel/Visor/cross-talk matrices remain |
| Legacy content | 20 BSPs, 969 effective PAK paths, nine required loose files | Hash-audited; the ported Zaero content is GPL and is bundled into release packages (see [assets and license](#assets-and-license)) |
| Tooling | Audit, import, build, managed install, package and release | Development tools are fixture-tested; packaging is deterministic. Player install management, exact-commit readiness, and complete release modes remain incomplete |
| Remastered content | Optional post-parity overlay | Out of 1.0 scope |

The compatibility target is the supplied Zaero source and installation, not
binary compatibility with old game DLLs, demos, or saves. Exact status lives in
the [map](docs/compatibility/map-matrix.md),
[entity](docs/compatibility/entity-matrix.md), and
[quirk](docs/compatibility/quirks.md) ledgers.

## Assets and license

ZaeREo is free software distributed under the **GNU General Public License,
version 2**. See [LICENSE](LICENSE). The port stands on two GPL-released works:

- The **Quake II Rerelease game-DLL** substrate from id Software, released under
  GPL-2.0. Its pinned identity is recorded in [docs/UPSTREAM.md](docs/UPSTREAM.md).
- The original **Zaero** mission pack. Zaero's creators released both its
  **game source code and its game assets** — maps, models, textures, sounds,
  sprites, and cinematics — under the GPL. That release is what makes this port,
  and its distribution, possible.

Because both foundations are GPL, ZaeREo may freely study, modify, bundle, and
redistribute the ported Zaero content alongside the Rerelease runtime, provided
it keeps the GPL notices intact, preserves the original authors' credits, and
makes complete corresponding source available. This repository *is* that
corresponding source.

Release archives bundle the ported Zaero content directly, in `pak0.pak` plus
the required loose runtime files — the same way the sibling
[REBLIVION](https://github.com/themuffinator/REBLIVION) port ships Oblivion.
End users do not need to supply their own copy of Zaero. A local importer is
also available as a convenience for rebuilding the content pack from an existing
Zaero installation; it verifies the known retail PAK hashes, applies PAK/loose
precedence, and excludes legacy binaries and destructive configuration, but it
is a development aid, not a licensing requirement.

See [asset sources](docs/provenance/ASSET_SOURCES.md) and
[third-party notices](THIRD_PARTY_NOTICES.md) for the recorded component and
asset evidence, and [LICENSE_SCOPE.md](LICENSE_SCOPE.md) for the per-component
license map.

## Installation and launch

A stable end-user package is not published yet, because the port is still in
active development rather than because of any licensing constraint. When a
release ships it is self-contained: extract it into your Quake II Rerelease
install so the bundled `zaereo/` directory lands beside `baseq2/`, and launch
the Rerelease with the `zaereo` game module selected. The bundled `pak0.pak`
already carries this project's ported Zaero content, so there is no separate
retail-era Zaero directory to assemble first.

The managed developer installer is available for local testing today, though the
resulting build is incomplete. It refuses to target `baseq2`; legacy game DLLs
are never imported because they are not compatible with Quake II Rerelease.

The planned release defaults to the upstream-recommended per-user directory:

~~~text
%USERPROFILE%\Saved Games\Nightdive Studios\Quake II\zaereo
~~~

For development, debugging, and validation, use `tools/run_game.ps1`; it
starts a visible `-window`/`v_windowmode 0` bootstrap, positively verifies all
visible native windows owned by the selected executable, and only then attempts
foreground-gated delivery of the `zaereo`/map command. The exact handle is
foregrounded through caller/target queue attachment with a task-switch retry
before any system key is sent. A v2 report is a pass
only when the game's own session marker confirms delivery; an accepted synthetic
input sequence is not compatibility evidence. Do not substitute a direct command
line or fullscreen launch for that verifier. Future end-user instructions will
distinguish the game's mod selector from the verified developer workflow.

Stable releases will include install, update, uninstall, version, and checksum
instructions. Until one exists, GitHub source snapshots and locally generated
verification archives are development artifacts rather than finished game
packages.

### Mapper-contract scope

Zaero gameplay/content is active in the `zaereo` game module, but the legacy
meanings of colliding stock classname flags and other map-only changes to
native actors, weapons, presentation, or campaign flow are not enabled
globally. The separate mapper contract is enabled only by an audited
shipped-map identity, a conservative Zaero-owned classname signature, or the
exact worldspawn key:

~~~text
"zaero_mapper_contract" "1"
~~~

Use `"0"` to opt out explicitly. The key is case-sensitive; duplicate or
invalid values fail closed. The DLL logs the map name, classification reason,
and SHA-256 of the entity string it was actually given, and a save may load only
when those classification fields agree. This is deliberately not described as
a full-BSP verification: the Rerelease game-DLL API does not expose the
resolved BSP bytes. Full-BSP identity remains audited at import time and is an
open engine-extension requirement before this classifier can be VERIFIED.

## Development

The first supported environment is:

- Windows 10/11 x64;
- Visual Studio 2022 or Build Tools with Desktop C++ and MSBuild;
- PowerShell 7;
- Python 3.11+;
- Git and Git LFS;
- vcpkg in manifest mode;
- a legally installed Quake II Rerelease; and
- optionally, an existing Zaero installation if you want to rebuild the content
  pack from its original files rather than the tracked/bundled copy.

Copy `.zaereo.local.example.json` to the ignored `.zaereo.local.json` and set
the Rerelease, Zaero, and optional vcpkg roots. All path-aware PowerShell tools
use the same precedence: explicit parameter, current environment variable,
schema-version-1 local config, then safe read-only discovery. The legacy
`Q2RERELEASE_ROOT` environment variable and `q2RereleaseRoot` config key are
accepted with a warning as engine/data-root aliases only; they never select the
writable install destination. Bootstrap and build accept `-VcpkgRoot` and also
resolve `VCPKG_ROOT`, `vcpkgRoot`, or `vcpkg` on `PATH`.

~~~powershell
./tools/bootstrap.ps1 -VcpkgRoot "C:\path\to\vcpkg"
python ./tools/import_legacy_assets.py --source "D:\Games\Zaero" --output .install/imported/zaereo --manifest .install/imported/zaereo-asset-manifest.json
./tools/build_game.ps1 -Configuration Debug -VcpkgRoot "C:\path\to\vcpkg"
./tools/verify_binary.ps1 -BinaryPath ./build/Debug/game_x64.dll
python ./tools/validate_runtime.py --root .install/imported/zaereo --manifest .install/imported/zaereo-asset-manifest.json --strict
./tools/install_dev.ps1 -EngineRoot "D:\Games\Quake II Rerelease\rerelease" -ContentRoot .install/imported/zaereo -AssetManifest .install/imported/zaereo-asset-manifest.json -Configuration Debug -WhatIf
# Inspect the plan, then repeat without -WhatIf to use the per-user default.
./tools/run_game.ps1 -Map q2dm1 -Deathmatch -ZdmFlags 0 -ProbeDeathmatchItems -ReportOutput .install/runtime-reports/q2dm1-zdmflags0-placement.json
./tools/run_runtime_matrix.ps1 -WhatIf
./tools/run_runtime_matrix.ps1 -ScenarioFile ./tools/runtime-scenarios-dm.json -WhatIf
python ./tools/release_readiness.py --mode asset-full --channel github-release --profile playable-stable
# The wrapper starts a visible -window/v_windowmode 0 bootstrap and attempts
# delivery only after all visible native windows pass its caption/non-popup check.
# The D-045 DM matrix reruns values 0–3 and authored suppression; the separate
# `runtime-scenarios-dm-fixtures.json` matrix requires the private fixture overlay.
# The readiness evaluator writes a local record. It is expected to say
# ready=false until the port earns its playable-stable evidence; it never
# publishes on its own.
~~~

If the KEX client rejects synthetic input, add `-ManualCommandDelivery` to the
single-map wrapper or matrix. The matrix runs scenarios serially and
records that manual mode was selected, but still accepts a case only when that
case's report is `engine-confirmed`. Enter each nonce-bearing command only after
its client window is verified. Do not treat a prompted or pasted command as a
passing smoke until the report is written.

`tools/make_dm_runtime_fixture.py` can derive a local partial-placement BSP from
a locally owned `baseq2/pak0.pak` for D-045 runtime testing.
`--include-existing-member-controls` additionally emits one map for
each of the eight historical item classnames. `install_dev.ps1 -RuntimeFixtureRoot`
accepts only
`maps/zaereo_fixture_*.bsp` beneath `.install/runtime-fixtures`, refuses content
collisions and reparse points, and manages the overlay like every other owned
install byte in a generated `pak2.pak`, above project `pak0.pak` and
the importer-owned `pak1.pak`. Reinstall without `-RuntimeFixtureRoot`
immediately after the test. The derived test fixtures are development scratch and
are kept out of Git by `.gitignore`, not by any distribution restriction.

The importer and installer write to managed locations. The
installer reads `-EngineRoot` but writes the managed mod beneath
`%USERPROFILE%\Saved Games\Nightdive Studios\Quake II` by default. Pass
`-UserRoot` to select another writable user-data parent. `-GameRoot` is reserved
for an explicit portable/disposable Rerelease directory that contains `baseq2`;
it cannot be combined with `-UserRoot`. The installer refuses engine/program-root
and `baseq2` writes, refuses unmanaged overwrite, and prints the launch
arguments. A normal install builds project-owned `pak0.pak` and importer-owned
`pak1.pak`, retains the verified loose files, and validates the completed stage
against the import manifest before it is copied to the user-data mod root. For a
local packaging check, use
`./tools/package_windows.ps1 -DistributionMode asset-full -AllowDirty`;
dirty or validation-skipped artifacts are marked non-release for engineering
hygiene, not for licensing reasons. Contributor
requirements are in [CONTRIBUTING.md](CONTRIBUTING.md) and
[AGENTS.md](AGENTS.md).

## Repository layout

| Path | Purpose |
| --- | --- |
| src/ | Officially pinned Rerelease substrate reconstruction plus Zaero integration, all under GPL |
| pack/ | Tracked redistributable runtime content and configuration; large binary Zaero media is tracked via Git LFS |
| tools/ | Bootstrap, audits, importer, build, install, validation, packaging |
| tests/ | Audit fixtures and runtime/golden coverage |
| docs/audits/ | Normalized source, upstream-integration, map/entity, and asset evidence |
| docs/compatibility/ | Feature, entity, map, quirk, and decision ledgers |
| docs/provenance/ | Baseline identities and license evidence |
| editor/ | Generated mapper definitions and editor integration |
| build/, .install/, dist/ | Ignored compiler, developer-stage, and release output |

## Releases and checksums

No stable binary or asset-bearing release is published yet, because the port is
still being validated. The packager already produces deterministic
`asset-full`/`importer-kit` archives, external manifests, SHA-256 checksums, a
pinned SPDX 2.3 substrate SBOM, and the exact vcpkg license bundle. A stable
publication additionally requires the exact-commit machine-readable readiness
gate, private live evidence, a clean tagged commit, version/tag agreement, and
protected human approval of a draft GitHub release. Publishing is deliberately a
human-approved step; no workflow ships a release on its own. An `asset-full`
package bundles the ported Zaero content directly; an `importer-kit` package
omits it and rebuilds the pack from a user's existing Zaero installation for
users who prefer that. A tools-only artifact is not a playable mod release.

## Reporting problems

Use the repository issue forms. Compatibility reports should include:

- exact ZaeREo version or commit;
- map and inbound transition/spawnpoint;
- skill and mode, including player count;
- reproducible steps and expected versus observed behavior;
- a save made before the failure when safe to share; and
- console/log output.

Report security issues privately as described in [SECURITY.md](SECURITY.md).

## Credits, license, and trademarks

Zaero was created by its original team (Team Evolve) and released, source and
assets, under the GNU General Public License. Quake and Quake II were created by
id Software, and the Rerelease game DLL is likewise GPL software. ZaeREo
contributors are building this independent compatibility port on top of that
freely licensed work; the original authors' credits and notices are preserved in
the ported content, as the GPL requires.

The target baseline is the
[Quake II Rerelease game DLL](https://github.com/id-Software/quake2-rerelease-dll).
ZaeREo as a whole is distributed under the GPL v2 (see [LICENSE](LICENSE) and
[LICENSE_SCOPE.md](LICENSE_SCOPE.md)); consult [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
for component-level attribution before reuse or redistribution.

Quake, Quake II, Zaero, and related names and marks belong to their respective
owners. This project is unofficial and is not affiliated with or endorsed by id
Software, Bethesda Softworks, Nightdive Studios, or Zaero's original team.

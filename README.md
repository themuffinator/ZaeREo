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
> matrix and there is no supported public release.**
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
| Deathmatch | Six ZDM maps plus campaign-map starts and item injection | All 230 starts and exact injection semantics are source/BSP/model-tested; private windowed `q2dm1` proves values 0–3 plus exact eight-item order/start/offset/native-drop state, `zdm1` proves authored suppression, a real-brush fixture proves partial success, and eight one-member fixtures prove every precondition member. Full rules, saves, dedicated and live 2/4/8-client sessions remain |
| Saves | Native Rerelease JSON save/load | Implemented-slice fields/callbacks registered; live lifecycle round trips and remaining systems are incomplete |
| Split screen | Isolated per-client HUD, views, zoom, and Visor | Flare/Sonic/Sniper/showorigin plus the active Visor view/HUD/copy state are client-local under static contracts, and full native Zaero wheel allocation plus 1–10 aliases are static-tested; live wheel/Visor/cross-talk matrices remain |
| Legacy content | 20 BSPs, 969 effective PAK paths, nine required loose files | Hash-audited importer works locally; content is not distributed |
| Tooling | Audit, import, build, managed install, package and release containment | Development tools are fixture-tested; fail-closed distribution policy and remote containment are active, while player install management, exact-commit readiness, and complete release modes remain incomplete |
| Remastered content | Optional post-parity overlay | Out of 1.0 scope |

The compatibility target is the supplied Zaero source and installation, not
binary compatibility with old game DLLs, demos, or saves. Exact status lives in
the [map](docs/compatibility/map-matrix.md),
[entity](docs/compatibility/entity-matrix.md), and
[quirk](docs/compatibility/quirks.md) ledgers.

## Assets and legal status

The Quake II Rerelease game-DLL baseline is GPL-2.0 software. That license does
not establish permission to redistribute Zaero's commercial source additions,
maps, textures, audio, models, or cinematics. No such permission is claimed by
this repository.

Until provenance is resolved, ZaeREo independently fails closed on code and
media publication. The maximum eligible artifact is tools-only while
Zaero-derived code rights are open; an importer kit with a DLL requires code
clearance, and a distinct public asset-full release requires both code and media
clearance. A `local-full` archive is always private verification output and can
never be published or promoted into that future mode.
The importer reads a user's legitimate Zaero installation, verifies the known
retail PAK hashes, applies PAK/loose-file precedence, excludes legacy binaries
and destructive configuration, and assembles content locally. Do not upload
original PAKs, loose media, or uncleared source/binaries.
See [asset sources](docs/provenance/ASSET_SOURCES.md) and
[third-party notices](THIRD_PARTY_NOTICES.md).
While code rights are open, do not push/tag the gameplay tree to a public remote:
its history and automatic source archives are distribution channels. A public
tools-only artifact must come from the separately reviewed history-clean root
specified by the active fail-closed machine-readable distribution policy.

## Installation and launch

There is no supported end-user package yet. The managed developer installer is
available for local testing, but the resulting build is incomplete. It refuses
to target `baseq2`; legacy game DLLs are never imported because they are not
compatible with Quake II Rerelease.

The planned release defaults to the upstream-recommended per-user directory:

~~~text
%USERPROFILE%\Saved Games\Nightdive Studios\Quake II\zaereo
~~~

For development, debugging, and validation, use `tools/run_game.ps1`; it
starts a visible `-window`/`v_windowmode 0` bootstrap, positively verifies all
visible native windows owned by the selected executable, and only then injects
the `zaereo`/map command. Do not substitute a direct command line or fullscreen
launch for that verifier. Future end-user instructions will distinguish the
game's mod selector from the verified developer workflow.

Stable releases will include install, update, uninstall, version, and checksum
instructions. Until one exists, GitHub source snapshots and locally generated
verification archives are not supported game packages.

## Development

The first supported environment is:

- Windows 10/11 x64;
- Visual Studio 2022 or Build Tools with Desktop C++ and MSBuild;
- PowerShell 7;
- Python 3.11+;
- Git and Git LFS;
- vcpkg in manifest mode;
- a legally installed Quake II Rerelease; and
- a legitimate Zaero installation for local content import.

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
# The wrapper starts a visible -window/v_windowmode 0 bootstrap and only injects
# the mod/map after all visible native windows pass its caption/non-popup check.
~~~

`tools/make_dm_runtime_fixture.py` can derive an ignored, private-only
partial-placement BSP from a locally owned `baseq2/pak0.pak` for D-045 runtime
testing. `--include-existing-member-controls` additionally emits one map for
each of the eight historical item classnames. `install_dev.ps1 -RuntimeFixtureRoot`
accepts only
`maps/zaereo_fixture_*.bsp` beneath `.install/runtime-fixtures`, refuses content
collisions and reparse points, and manages the overlay like every other owned
install byte in a private generated `pak2.pak`, above project `pak0.pak` and
the importer-owned `pak1.pak`. Reinstall without `-RuntimeFixtureRoot`
immediately after the test. The derived BSP, its identity manifest, the
resulting PAK, and runtime
report must never be committed or published.

The importer and installer write only to ignored/managed locations. The
installer reads `-EngineRoot` but writes the managed mod beneath
`%USERPROFILE%\Saved Games\Nightdive Studios\Quake II` by default. Pass
`-UserRoot` to select another writable user-data parent. `-GameRoot` is reserved
for an explicit portable/disposable Rerelease directory that contains `baseq2`;
it cannot be combined with `-UserRoot`. The installer refuses engine/program-root
and `baseq2` writes, refuses unmanaged overwrite, and prints the launch
arguments. A normal install builds project-owned `pak0.pak` and importer-owned
`pak1.pak`, retains the verified loose files, and validates the completed stage
against the import manifest before it is copied to the user-data mod root. For an
asset-free local packaging check, use
`./tools/package_windows.ps1 -DistributionMode importer-kit -AllowDirty`;
this is local development output and is not publication-authorized. Dirty or
validation-skipped artifacts are also marked non-publishable. Contributor
requirements are in [CONTRIBUTING.md](CONTRIBUTING.md) and
[AGENTS.md](AGENTS.md).

## Repository layout

| Path | Purpose |
| --- | --- |
| src/ | Officially pinned Rerelease substrate reconstruction plus reviewed Zaero integration |
| pack/ | Tracked redistributable configuration contribution only; imported commercial content stays under ignored `.install/` |
| tools/ | Bootstrap, audits, importer, build, install, validation, packaging |
| tests/ | Audit fixtures and runtime/golden coverage |
| docs/audits/ | Normalized source, upstream-integration, map/entity, and asset evidence |
| docs/compatibility/ | Feature, entity, map, quirk, and decision ledgers |
| docs/provenance/ | Baseline identities and distribution evidence |
| editor/ | Generated mapper definitions and editor integration |
| build/, .install/, dist/ | Ignored compiler, developer-stage, and release output |

## Releases and checksums

No supported binaries or asset-bearing releases are currently published. The
packager already produces deterministic local importer-kit/`local-full`
archives, external manifests, SHA-256 checksums, a pinned SPDX 2.3 substrate
SBOM, and exact vcpkg license bundle, but current tooling output is not evidence
of publication rights or release readiness. Remote workflows
are read-only and the publisher fails closed before external access; those
controls must remain in place while every public mode is blocked. Stable publication
additionally requires the exact-commit machine-readable readiness gate, private
live evidence, a clean tagged commit, version/tag agreement, eligible
code/media policy, and protected human approval of a draft GitHub release. A
`local-full` package contains the user's commercial content and is permanently
ineligible for publication. Any future rights-cleared asset-bearing release is
a distinct `asset-full` artifact built from reviewed distributable inputs, not
a renamed local import. A tools-only artifact is not a playable mod release.

## Reporting problems

Use the repository issue forms. Compatibility reports should include:

- exact ZaeREo version or commit;
- map and inbound transition/spawnpoint;
- skill and mode, including player count;
- reproducible steps and expected versus observed behavior;
- a save made before the failure when safe to share; and
- console/log output, without credentials or proprietary game content.

Report security issues privately as described in [SECURITY.md](SECURITY.md).

## Credits, license, and trademarks

Zaero was created by its original developers and rightsholders. Quake and
Quake II were created by id Software. ZaeREo contributors are building this
independent compatibility port; no original creator or publisher endorsement is
implied.

The target baseline is the
[Quake II Rerelease game DLL](https://github.com/id-Software/quake2-rerelease-dll).
Repository licensing remains constrained by the provenance decisions described
above; the roadmap requires a component/path `LICENSE_SCOPE.md` before any
publication. Consult LICENSE and THIRD_PARTY_NOTICES.md before reuse or
distribution and do not infer a grant for uncleared additions from the bare
GPL-2.0 text.

Quake, Quake II, Zaero, and related names and marks belong to their respective
owners. This project is not affiliated with or endorsed by id Software,
Bethesda Softworks, Nightdive Studios, or Zaero's original publisher or
rightsholders.

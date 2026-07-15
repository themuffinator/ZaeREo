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
| Deathmatch | Six ZDM maps plus campaign-map starts and item injection | All 230 starts and exact injection semantics are source/BSP/model-tested. Private legacy-v1 one-stage `q2dm1`/fixture reports record values 0–3, exact eight-item order/start/offset/native-drop state, authored suppression, partial success, and every one-member precondition; they must be rerun under the v2 window-before-mod/map protocol before they count as current runtime evidence. Full rules, saves, dedicated and live 2/4/8-client sessions remain |
| Bots | Safe coexistence with Rerelease bots | Appended Zaero item IDs use the native generic registry; custom active hazards publish native trap/laser metadata and invalid external item IDs are rejected before indexing. Live zdm1–6 bot/no-navigation sessions remain |
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
verification archives are not supported game packages.

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
./tools/run_runtime_matrix.ps1 -WhatIf
./tools/run_runtime_matrix.ps1 -ScenarioFile ./tools/runtime-scenarios-dm.json -WhatIf
python ./tools/release_readiness.py --mode local-full --channel private-local-filesystem --profile local-full-private
# The wrapper starts a visible -window/v_windowmode 0 bootstrap and attempts
# delivery only after all visible native windows pass its caption/non-popup check.
# The matrix consumes private-only reviewed scenarios and creates no output under -WhatIf.
# The D-045 DM matrix reruns values 0–3 and authored suppression; the separate
# `runtime-scenarios-dm-fixtures.json` matrix requires the private fixture overlay.
# The readiness evaluator writes an ignored local record. It is expected to say
# ready=false while the active policy blocks every public mode; it never publishes.
~~~

If the KEX client rejects synthetic input, add `-ManualCommandDelivery` to the
single-map wrapper or private matrix. The matrix runs scenarios serially and
records that manual mode was selected, but still accepts a case only when that
case's report is `engine-confirmed`. Enter each nonce-bearing command only after
its client window is verified. Do not treat a prompted or pasted command as a
passing smoke until the report is written.

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
controls must remain in place while every public mode is blocked. The local
readiness evaluator fingerprints the policy, audited/ledger inputs, source state,
and requested mode/channel/profile, but intentionally produces a blocked record
until exact-candidate manifests, test evidence, and rights/channel gates exist.
Stable publication additionally requires that exact-commit machine-readable
readiness gate, private
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

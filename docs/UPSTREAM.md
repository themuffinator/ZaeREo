# Quake II Rerelease upstream record

## Current identity status

The implementation base is a **hash-recorded supplied substrate, not a pinned
upstream commit**. The project used a locally supplied copy of the Quake II
Rerelease game-DLL source. Its bytes are identified reproducibly, but the copy
did not retain Git metadata or a downloaded archive checksum that proves which
official commit produced it.

| Field | Recorded value |
| --- | --- |
| Official project | <https://github.com/id-Software/quake2-rerelease-dll> |
| Official commit | **Unresolved**; no commit ID has been verified for the supplied tree |
| Supplied reference location | `E:\_SOURCE\_CODE\quake2-rerelease-dll-main\rerelease` on the audit workstation; evidence only, never a build constant |
| Acquisition/import date | Not recorded |
| First ZaeREo identity audit | 2026-07-13 |
| Normalized identity record | `docs/provenance/baselines.json`, entry `quake2_rerelease` |
| Files / bytes | 144 files / 2,635,282 bytes |
| Aggregate SHA-256 | `74b79d4f853fb521a866aaa5b1510c1c46afb63a73370b907b10143146629bf5` |
| Aggregate algorithm | SHA-256 of each UTF-8 path, NUL, decimal size, NUL, per-file SHA-256, and LF, ordered by UTF-8 path bytes |
| License observed | GNU General Public License, version 2.0; retain upstream notices and see `LICENSE` and `THIRD_PARTY_NOTICES.md` |

The directory name ending in `-main`, file timestamps, API version numbers, and
similarity to the official repository are not commit evidence. Do not describe
this baseline as pinned until D-002 is closed with a verified official identity.

## API and data-build compatibility

The supplied `game.h`, whose individual SHA-256 is
`66defbd069c38c4a1740c5087a3f6f2343d603b956ca0d6e1d89e8ad46d0843f`,
declares:

- game API version 2023;
- cgame API version 2022; and
- protocol version 2023.

The supplied tree includes the base game, CTF, Xatrix, Rogue, and bot sources,
plus the original Visual Studio project and its `fmt`/`jsoncpp` vcpkg manifest.
Those facts identify the source interface; they do not identify a particular
Quake II Rerelease executable or data build. No engine/data-build compatibility
range is certified yet. Runtime DLL load, stock/expansion smoke tests, and the
rights-safe base `mapdb.json` merge remain separate roadmap gates.

## Relationship between the baseline and `src/`

`docs/provenance/baselines.json` describes the untouched supplied reference,
not the evolving `src/` directory. At this record's initial audit, a mechanical
comparison found 113 unchanged paths, 30 modified paths, 14 added Zaero-owned
paths, and the supplied in-tree `vcpkg.json` relocated/replaced by the pinned
root manifest. This is already an early gameplay integration; it is not the
minimal Phase-1 substrate diff.

The current patch inventory is organized by integration seam:

- build/layout: `src/game.vcxproj`, `src/game.vcxproj.filters`, the root
  `vcpkg.json`, output/staging paths, static dependency settings, and the added
  `src/zaero/g_zaero_*` project entries;
- mapper/entity and physics hooks: `g_func.cpp`, `g_misc.cpp`, `g_phys.cpp`,
  `g_spawn.cpp`, `g_target.cpp`, `g_trigger.cpp`, `g_turret.cpp`, and
  `g_utils.cpp`;
- items, weapons, HUD, and client lifecycle hooks: `g_cmds.cpp`, `g_combat.cpp`,
  `g_items.cpp`, `p_client.cpp`, `p_hud.cpp`, `p_view.cpp`, and `p_weapon.cpp`;
- AI/monster hooks: `g_ai.cpp`, `g_monster.cpp`, the currently modified stock
  monster modules, and shared declarations in `bg_local.h`/`g_local.h`;
- save/export/version hooks: `g_main.cpp`, `g_save.cpp`, and the project export
  configuration; and
- Zaero-owned implementations: the fourteen current files under `src/zaero/`.

This inventory is descriptive, not a waiver for broad upstream edits. Regenerate
and review the exact comparison whenever a hook or baseline changes. The
roadmap's compatibility ledgers remain authoritative for the behavior and test
status of each integration.

## Reproducing the supplied-tree identity

Set the four evidence roots explicitly and regenerate into scratch files first:

~~~powershell
python ./tools/audit_source_delta.py `
  --zaero-root $env:ZAERO_SOURCE_ROOT `
  --legacy-root $env:Q2_LEGACY_SOURCE_ROOT `
  --rerelease-root $env:Q2_RERELEASE_SOURCE_ROOT `
  --assets-root $env:ZAERO_LEGACY_ROOT `
  --json-output .audit-work/source-delta.json `
  --markdown-output .audit-work/source-delta.md `
  --baselines-output .audit-work/baselines.json
~~~

The `quake2_rerelease` aggregate in the scratch manifest must equal the value
above before the supplied reference is considered the same input. Review the
full per-file manifest and case-collision list before replacing a checked-in
normalized report. A matching aggregate proves byte identity only; it still
does not prove an official commit.

## Closing D-002 and refreshing upstream

To close the unresolved identity gate:

1. acquire the official repository or a publisher-provided archive in an
   isolated worktree and retain its URL, commit/tag, acquisition date, and
   archive checksum where applicable;
2. find and verify the exact official commit corresponding to the supplied
   144-file tree, or record that no exact official match exists;
3. record the verified commit/archive identity and pristine comparison location
   in this file and the machine-readable baseline record;
4. generate an exact diff from that immutable baseline, classify every existing
   integration seam, and reconstruct the minimal Phase-1 substrate separately
   from later gameplay work; and
5. run Debug/Release builds, both API export/load checks, stock and expansion
   smoke tests, save checks, dependency/SBOM checks, and the complete applicable
   repository test suite before accepting a refresh.

Update this record, the baseline manifest, D-002, notices, and the changelog as
one reviewed change. Never overwrite `src/` from a moving branch or infer a pin
from an archive directory name.

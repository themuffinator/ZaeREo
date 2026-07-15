# Quake II Rerelease upstream record

## Current identity status

The implementation base is a **hash-recorded supplied substrate with an exact
official Git content match**. The supplied directory did not retain Git
metadata, so its historical acquisition commit is unknowable; however, every
one of its 144 paths and blobs is byte-identical to the `rerelease/` subtree of
the immutable official commit selected below. That commit is the pinned
reconstruction baseline for builds and diffs.

| Field | Recorded value |
| --- | --- |
| Official project | <https://github.com/id-Software/quake2-rerelease-dll> |
| Selected official commit | `8dc1fc9794c01ece06881e703851b768fb3994de` (`Update 1 changes`, 2023-10-03) |
| Official `rerelease/` tree | `7c3a380c5114dab4e7b7511a5c9c96390b72a1cd` |
| Supplied reference location | Private audit-workstation evidence only; resolve a current source input through `Q2_RERELEASE_SOURCE_ROOT` or an explicit audit argument, never a build constant |
| Original supplied-copy acquisition date | Not recorded; no date is inferred |
| Official mirror verification date | 2026-07-14 |
| First ZaeREo identity audit | 2026-07-13 |
| Normalized identity records | `docs/provenance/baselines.json` entry `quake2_rerelease` and `docs/provenance/upstream-match.json` |
| Files / bytes | 144 files / 2,635,282 bytes |
| Aggregate SHA-256 | `74b79d4f853fb521a866aaa5b1510c1c46afb63a73370b907b10143146629bf5` |
| Aggregate algorithm | SHA-256 of each UTF-8 path, NUL, decimal size, NUL, per-file SHA-256, and LF, ordered by UTF-8 path bytes |
| License observed | GNU General Public License, version 2.0; retain upstream notices and see `LICENSE` and `THIRD_PARTY_NOTICES.md` |

`tools/identify_upstream.py` scanned all 191 commits in the acquired official
mirror. Those commits contain nine distinct `rerelease/` trees; only one tree
matches the supplied aggregate and it occurs in three commits. The selected
commit is the exact match at official `refs/heads/main`. The other two are merge
commits with the same subtree and remain recorded in the normalized report.
The directory name ending in `-main`, timestamps, API numbers, or similarity
were not used as evidence.

## API and data-build compatibility

The supplied `game.h`, whose individual SHA-256 is
`66defbd069c38c4a1740c5087a3f6f2343d603b956ca0d6e1d89e8ad46d0843f`,
declares:

- game API version 2023;
- cgame API version 2022; and
- protocol version 2023.

The supplied tree includes the base game, CTF, Xatrix, Rogue, and bot sources,
plus the original Visual Studio project and its `fmt`/`jsoncpp` vcpkg manifest.
Those facts identify the source interface and official DLL source commit; they
do not identify a particular Quake II Rerelease executable or data build. No
engine/data-build compatibility range is certified yet. Runtime DLL load,
stock/expansion smoke tests, and the rights-safe base `mapdb.json` merge remain
separate roadmap gates.

## Relationship between the baseline and `src/`

`docs/provenance/baselines.json` describes the untouched supplied reference,
not the evolving `src/` directory. The current mechanical comparison finds 110
unchanged paths, 33 modified paths, 34 added Zaero-owned paths, and one removed
in-tree `vcpkg.json` (replaced by the pinned root manifest). This is already an
early gameplay integration; it is not the minimal Phase-1 substrate diff. The
reproducible current comparison and all 68 classified differences are retained in
`docs/audits/upstream-integration.json`/`.md`; CI rejects an unclassified path or
a stale classification.

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
- Zaero-owned implementations: the current 34 files under `src/zaero/`.

This inventory is descriptive, not a waiver for broad upstream edits. Regenerate
and review the exact comparison whenever a hook or baseline changes. The
roadmap's compatibility ledgers remain authoritative for the behavior and test
status of each integration.

## Reproducing the supplied-tree and official identity

Set the four evidence roots explicitly and regenerate into scratch files first:

~~~powershell
python ./tools/audit_source_delta.py `
  --zaero-root $env:ZAERO_SOURCE_ROOT `
  --legacy-root $env:Q2_LEGACY_SOURCE_ROOT `
  --rerelease-root $env:Q2_RERELEASE_SOURCE_ROOT `
  --assets-root $env:ZAERO_LEGACY_ROOT `
  --json-output .audit-work/source-delta.json `
  --markdown-output .audit-work/source-delta.md `
  --baselines-output .audit-work/baselines.json `
  --rerelease-upstream-match docs/provenance/upstream-match.json

git clone --mirror https://github.com/id-Software/quake2-rerelease-dll.git .audit-work/quake2-rerelease-dll.git
python ./tools/identify_upstream.py `
  --repository .audit-work/quake2-rerelease-dll.git `
  --verified-on 2026-07-14 `
  --json-output .audit-work/upstream-match.json
~~~

The `quake2_rerelease` aggregate in the scratch manifest must equal the value
above before the supplied reference is considered the same input. The upstream
matcher then requires every ordered per-file record to match, not merely the
aggregate. Review both reports and the case-collision list before replacing a
checked-in normalized record. If the local baseline changes, the baseline
generator rejects this upstream-match record instead of carrying the old commit
forward.

## D-002 closure and future upstream refreshes

D-002 is closed for identity: the supplied bytes have an exact official
reconstruction commit and immutable tree. The deterministic substrate
dependency/SBOM/license evidence is also implemented separately. This does not
close the remaining Phase 1 clean-clone build, engine-load, stock/expansion
smoke, or clean-integration-diff gates.

For a future upstream refresh:

1. acquire/fetch the official repository in an isolated ignored mirror and
   retain its URL, selected commit/tag, and verification date;
2. generate a new per-file baseline and upstream-match report; never overwrite
   the current pin merely because a branch moved;
3. generate an exact diff from the immutable old and proposed new baselines and
   classify every integration seam;
4. update this record, `baselines.json`, `upstream-match.json`, D-002's migration
   note, notices, and changelog together; and
5. run Debug/Release builds, both API export/load checks, stock and expansion
   smoke tests, save checks, dependency/SBOM checks, and the complete applicable
   repository test suite before accepting the refresh.

Never overwrite `src/` from a moving branch or infer a pin from an archive
directory name.

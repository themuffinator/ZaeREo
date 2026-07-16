# ZaeREo: Zaero to Quake II Rerelease Port Roadmap

- Document status: audited roadmap baseline with record-level traceability and
  runtime-v2 safety gates implemented; gameplay execution remains gated by the
  phase exit criteria below
- Audit date: 2026-07-15
- Roadmap revision: 1.3
- Target platform: Quake II Rerelease game DLL API 2023, Windows x64 first
- Recommended game directory: `zaereo`

## 1. Purpose

ZaeREo is a behavior-first port of the 1998 Zaero mission pack to Quake II
Rerelease. The goal is not merely to make the original BSP files load. The
finished port must reproduce the gameplay systems, mapper-facing contracts,
content flow, presentation, and intentional oddities on which Zaero relies,
while adopting the Rerelease engine's native interfaces and quality-of-life
features.

The project is progressive: every milestone should produce a build that is
more useful and more testable than the previous one. Compatibility comes before
remastering. Once parity is demonstrated, assets and presentation may be
improved without replacing the verified original-content baseline.

This document is both:

1. an inventory of the observable differences between the supplied Zaero
   source/content and legacy Quake II; and
2. the implementation, repository, validation, and release plan for carrying
   those differences into Quake II Rerelease.

It is not a claim that the historical retail DLL has been reverse-engineered.
The authoritative inputs are the supplied source, maps, configuration, and
assets listed below. Any retail-only behavior discovered later belongs in the
compatibility ledger and must receive a reproducible test.

Roadmap completion is deliberately separate from port completion. This
document is complete when every mechanically discovered delta has an explicit
classification route, phase, ownership slot, proof obligation, and release
gate. A feature is complete only under Section 16 and the living matrices. The
generated audit reports are authoritative for exact files, symbols, paths,
classnames, keys, counts, and hashes; this document supplies the reviewed
behavioral interpretation and dependency order.

## 2. Required outcome

A stable release is complete only when all of the following are true:

- A clean checkout can bootstrap dependencies and build `game_x64.dll` without
  relying on an undocumented developer machine.
- The mod installs as a drop-in Rerelease game directory and does not overwrite
  the base game.
- All 20 shipped BSPs load without unknown classnames, missing mandatory assets,
  fatal errors, or entity-count/sound-index exhaustion.
- The complete single-player episode, including its cinematic chain, unit
  boundaries, objectives, keys, final boss, outro, and save/load behavior, is
  completable.
- Authored co-op and deathmatch behavior works, including Zaero item injection,
  `zdmflags`, the six dedicated deathmatch maps, and campaign-map DM starts.
- Zaero's custom weapons, inventory, deployables, monsters, AI, movers,
  triggers, HUD/view effects, commands, and map fields have parity tests.
- JSON save/load, 40 Hz simulation, split-screen clients, the Rerelease weapon
  wheel, and current collision/render conventions are handled deliberately.
- Original quirks are either reproduced, intentionally adapted, or fixed with a
  documented compatibility decision. Nothing important disappears accidentally.
- Runtime assets are assembled reproducibly from a versioned manifest with
  deterministic precedence, hashes, case checks, and a documented provenance
  decision.
- A public playable stable release uses an eligible importer-kit or distinct
  asset-full artifact; tools-only is non-playable and local-full is permanently
  private.
- CI, developer installation, editor definitions, packaging, checksums, manual
  GitHub publication, and rollback/recovery procedures are documented and
  exercised.

## 3. Compatibility policy

### 3.1 Priority order

When two goals conflict, use this order:

1. load and complete every original Zaero map;
2. preserve gameplay-observable Zaero behavior and authored scripting;
3. integrate correctly with Rerelease save, multiplayer, input, HUD, and timing;
4. preserve harmless historical quirks;
5. improve defects, visuals, or ergonomics only behind a recorded decision.

### 3.2 Three disposition labels

Every discovered difference must be assigned one of these labels in
`docs/compatibility/feature-matrix.md`:

| Label | Meaning |
| --- | --- |
| `PARITY` | Reproduce it, including behavior on boundary cases. |
| `ADAPT` | Preserve player/map intent using a Rerelease-native implementation. |
| `FIX` | Correct a proven defect; document the legacy result and add a regression test. |

An item may not be silently dropped because its code appears unused. Map data,
save fields, configuration aliases, editor definitions, or third-party maps may
still depend on it. Source-only mapper surfaces should normally become harmless
compatibility implementations or explicit no-ops.

### 3.3 Baseline and enhancement separation

The repository should always retain a buildable, original-asset compatibility
baseline. High-resolution replacements, PBR materials, navigation data, revised
audio, localization, and reauthored maps are overlays that can be disabled.
Do not make a remastered asset the only way to validate original behavior.

## 4. Evidence and audit boundaries

### 4.1 Supplied inputs

| Input | Local audit path | Role |
| --- | --- | --- |
| Zaero C source | `ZAERO_SOURCE_ROOT` / ignored local config | Primary evidence for custom game behavior |
| Legacy Quake II game source | `Q2_LEGACY_SOURCE_ROOT` / ignored local config | Reference used to isolate Zaero changes from the original game |
| Zaero installation | `ZAERO_LEGACY_ROOT` / ignored local config | Shipped maps, media, configuration, documentation, and binary layering |
| Quake II Rerelease source | `Q2_RERELEASE_SOURCE_ROOT` / ignored local config | Target API and implementation baseline |
| REBLIVION repository | Explicit audit-tool argument | Repository, build, install, editor, PAK, and release-workflow reference |

These are resolver names, not repository constants. The original audit
workstation paths are private provenance evidence and must not be added to
commands, examples, policy, or source. Machine-readable manifests and source-tree hashes are recorded under
`docs/provenance/` and `docs/audits/`. D-002 is now closed for the Rerelease
source identity: `tools/identify_upstream.py` verified every supplied path/blob
against official commit `8dc1fc9794c01ece06881e703851b768fb3994de` and Git
subtree `7c3a380c5114dab4e7b7511a5c9c96390b72a1cd`; the normalized scan is
`docs/provenance/upstream-match.json`. This reconstructs the supplied bytes but
does not invent their lost original acquisition date or certify an engine/data
build. Regenerate the per-file baseline and official match before any baseline
change.

### 4.2 Audit method

The planning audit used four complementary comparisons:

- a recursive source-tree and text diff between legacy Quake II and Zaero;
- parsing every BSP entity lump and collecting classnames, keys, spawnflags,
  map transitions, and multiplayer starts;
- parsing the directory tables of `pak0.pak`, `pak1.pak`, and `pak2.pak` plus
  the loose installation files;
- mapping each custom or changed system to the Rerelease API 2023 source.

The audit is implemented by committed scripts rather than one-off notes:

- `tools/audit_source_delta.py`
- `tools/audit_bsp_entities.py`
- `tools/audit_dm_injection.py`
- `tools/audit_assets.py`
- `tools/audit_flymove.py`
- `tools/audit_release_surfaces.py`
- `tools/audit_stock_precaches.py`
- `tools/audit_visor_trace_order.py`
- `tools/identify_upstream.py`
- `tools/audit_upstream_integration.py`
- `tools/audit_repository.py`
- `tools/audit_identifier_surface.py`
- `tools/audit_save_surface.py`
- `tools/validate_distribution_policy.py`
- `tools/validate_runtime.py`

Their normalized reports are committed under `docs/audits/` and updated
only when an input baseline or an intentional compatibility decision changes.

### 4.3 Inventory closure and traceability

The phrase “all differences” has three layers, all of which must stay linked:

1. **Mechanical delta:** the 104-path source union and every common-file
   function delta are listed; all 14,933 BSP entity records were parsed and
   their normalized per-map/classname/key-value counts retained; and all 132
   exact map classnames plus all 978 effective runtime paths are retained in
   generated JSON/Markdown reports under `docs/audits/`.
2. **Behavioral classification:** the 77 rows in
   `docs/compatibility/feature-matrix.md`, 50 entity-contract rows, and 57 known
   quirks classify the gameplay, mapper, system, and defect consequences of
   that mechanical evidence by observable surface. The Appendix A source-area
   crosswalk routes common-file areas into those surfaces; a symbol may span more
   than one row and receives its final disposition when its behavior is
   reviewed. Rows may be split when testing reveals more than one observable
   contract, but may not disappear without a decision record.
3. **Target/release mapping:** Sections 8–16 assign each class of behavior to a
   Rerelease integration point, implementation phase, verification matrix,
   risk gate, repository artifact, and definition of done.
4. **Record-level closure (Phase 0 gate):** broad source-area categories are
   not sufficient proof that every record is routed. The committed
   `tools/audit_traceability.py` produces two deterministic normalized outputs:

   - `docs/audits/source-delta-coverage.json`/`.md` must contain every
     `source-delta.json` path record, each lexical added/removed/changed
     function or global record, and every Zaero-only/legacy-only path. Each
     record must link to one or more feature/entity/quirk/decision IDs, a
     `PARITY`/`ADAPT`/`FIX` outcome or a narrow `SOURCE_AGE`/`NON_RUNTIME`/
     `TOOLING_ONLY` disposition, a reason, phase, implementation seam, and
     test/evidence link. A source-age/no-runtime record still needs a reviewed
     target decision; “covered by area” is invalid.
   - `docs/audits/bsp-contract-coverage.json`/`.md` must contain every exact
     BSP classname plus each observed key and spawnflag value. It must identify
     its entity/feature/decision row or an explicit native-no-delta exemption,
     map applicability/classifier, key/flag semantics, save/lifecycle surface,
     spawn status, and proof link. The 50 handwritten entity rows may group
     surfaces but may not leave any of the 132 names or their mapper contracts
     implicit in raw audit output.

   The tool validates ledger IDs, source/BSP input hashes, per-classname mapper
   input, duplicate records, required routing fields, and zero uncovered records.
   The current reports cover 948 source records (102 paths, 556 functions, and
   290 globals) and 1,752 BSP records (132 classnames, 946 keys, and 674
   spawnflag values), with zero uncovered. Private audit regeneration reads the
   local game inputs; public CI verifies checked-in report self-consistency and
   ledger/count integrity. A changed source or BSP baseline cannot merge without
   regenerated coverage, and a future new record fails closed rather than being
   covered by an implicit area.

CI must regenerate or validate the audit reports and reject unexplained drift.
When a count in prose conflicts with generated evidence, the generated report
wins and this roadmap plus the affected ledgers must be updated in the same
change. This prevents both raw text differences and subtle source-version drift
from being mistaken for untracked Zaero requirements.

### 4.4 REBLIVION reference patterns and deliberate divergence

The private `REBLIVION` repository was reviewed as an architectural reference,
not as a source or policy to copy wholesale. Its useful patterns are a dedicated
Rerelease DLL target, separated `src`/`pack`/`editor`/`tools` concerns,
generated editor definitions, an HTML release readme, deterministic staging,
and explicit developer versus release scripts. ZaeREo adopts those structural
ideas only where they preserve Zaero's own evidence and provenance gates.

The following REBLIVION behaviors are expressly not inherited:

| Reference pattern | ZaeREo decision and reason |
| --- | --- |
| Default, writable Steam-install path and direct mod-directory updates | Resolve an explicit read-only engine root and a managed per-user root; reject engine/program-root and `baseq2` writes except an explicit disposable portable override. |
| Junction/link convenience and ad-hoc cleanup in the game tree | Use manifest-owned copies under the managed root, path/reparse checks, and an explicit uninstall/restore contract. |
| Direct client launch with `+set game` | Development and validation must use the verified wrapper: visible `-window` bootstrap, every exact-PID top-level window check, then mod/map injection. |
| Automatically publishable nightly/release flow | Keep publishing behind a deliberate human step: a maintainer approves a draft release once the readiness record passes; no workflow ships on its own. |
| Shipping bundled content | Bundle the ported GPL Zaero content directly in the `asset-full` package (REBLIVION-style); offer `importer-kit` as a convenience for users who supply their own copy. `local-full` stays out of releases as unvalidated developer scratch. |

Future comparisons may add a reference pattern to this table, but must state
whether it is adopted, adapted, or rejected and link the resulting tool,
decision, and test. A reference repository never overrides this roadmap's
behavior-first compatibility order or rights policy.

## 5. Executive audit findings

### 5.1 Scale

- The Zaero source tree contains 100 files versus 78 in the supplied legacy
  `game` tree. Their logical union contains 104 paths: 74 common, 26 Zaero-only,
  and four legacy-only. The directory comparison emits 102 non-identical path
  records and 14,887 insertions/6,981 deletions; many apparent deletions are
  baseline age, license-header, or header-layout drift rather than Zaero
  features.
- Zaero adds dedicated modules for the autocannon, AI, boss, camera, Handler,
  Hound, items, Sentien, spawning, triggers, and weapons. It also contains
  debug/test animation and monster tooling.
- There are 20 shipped maps: 14 campaign maps and 6 dedicated deathmatch maps.
  Their entity lumps contain 14,933 entity records and 132 distinct classnames.
- The current Rerelease baseline already recognizes 105 of those exact
  classnames. Twenty-seven map-facing classnames need Zaero implementations.
  A [reproducible worktree audit](compatibility/entity-matrix.md) now resolves
  all 132 without placeholders. This is a registry snapshot, not a Phase 2
  exit: each entity still requires its behavior, lifecycle, save, asset, and map
  evidence.
  Several recognized stock classnames still require modified Zaero semantics.
- The maps contain 121 co-op starts across all 14 campaign maps and 230
  deathmatch starts across all 20 maps. Co-op and deathmatch are therefore
  first-class compatibility targets, not optional post-release extras.
- The three PAKs contain 971 directory entries before override resolution.
  Layering `pak0 < pak1 < pak2` produces 969 effective paths. Nine additional
  runtime files are intentionally loose in the installation.

### 5.2 Roadmap execution snapshot

The roadmap and audit scaffold now exist, and some later code has already been
prototyped. That does not waive earlier gates or make a phase complete. The
current honest checkpoint is:

| Phase | Current evidence | Gate still preventing closure |
| --- | --- | --- |
| 0 | Generated source/BSP/asset reports, policy/schema records, matrices, fail-closed distribution decision, exact official Rerelease match, reviewed private evidence tree, repository audit, and read-only workflow/manual-publisher containment exist | The configured GitHub gameplay repository is currently public despite D-003 and the machine policy; that external exposure must be resolved by an authorized owner. Remaining supplied Zaero/legacy origin records and any future tools-only history root also need closure. |
| 1 | Pinned official Rerelease substrate, project, shared path resolver, safe per-user developer install, bootstrap/build wrappers, Windows workflows, local Debug/Release/export proof, deterministic pinned-schema substrate SBOM/license harvesting, and a complete classification of all 68 current `src/` differences exist | Fresh-clone CI certification, reconstruction/certification of the minimal substrate-only integration, stock baseline DLL API engine-load/stock-map smoke, and a fresh v2 two-stage window-before-mod/map Release smoke remain. The retained v1 one-stage Release report is historical D-015 evidence, not a launch-safety gate. |
| 2 | Importer, validators, deterministic PAK/ZIP tooling, managed per-user developer installer with overwrite/`baseq2`/program-root guards, config/mapdb scaffold, custom fields/save conventions, 132/132 registry coverage including ZBoss/marker, direct/Handler-created Hound, Handler, and Sentien, the D-010 no-redistribution world-music mapping, generated 30-changelevel target/destination closure with D-011's inert-orphan disposition, plus bounded private legacy one-stage `zbase1`/`zdef1`/`zboss`/`zdm6` DLL-load/map-spawn/client-entry/shutdown observations exist | The legacy sampled logs are not v2 launch-safety, current registry/resource, playability, or complete behavior/entity evidence. Rerun them with the two-stage harness; zdm6 additionally needs acoustic silence or deathmatch. Music still needs live audible/transition/volume/server proof; all valid campaign transitions still need geometry, save, co-op, and completion proof. Canonical PAK/import ownership, install-manager lifecycle, cross-layer reference/case closure, rights-safe mapdb merge, classifier, live JSON round trips, and all-map behavior remain. |
| 3 | Static contracts cover several movement types, map behaviors, stock-class extensions, simple world entities, the exact source-only no-toggle `trigger_laser` contract with generation-safe target dispatch, retained post-trigger physics lifetime guards, D-044's identity-locked one-line FlyMove classification/seven float32 goldens and unmodified shared native solver, the exact Zaero-gated bit-2 `func_plat` feet boundary, mass-400 FALLFLOAT `misc_explobox` airborne-client pushing, rotating-door zero-damage defaults, and the complete train/path-corner mapper surface including native flag isolation | Live mover/rider/save/map fixtures plus help/freeze and always-windowed corner/wedge/stair/repeated-plane/projectile/monster/player/expansion collision fixtures remain |
| 4 | Static implementations exist for the item foundation, Push, Flare, Sonic Cannon, Sniper Rifle, IRED, Plasma Shield, EMP, A2K, Autocannon interactions, active Visor duration/camera/view/HUD/input/lifecycle with the D-021 trace-order FIX, exact `use weapon 1`–`10` multiselect, opt-in aliases, full native wheel ownership, private `showorigin` HUD, kill guard, 25 monster obituaries, seven custom MOD paths, shared-state-safe Zaero health-count sounds, and the saved Rocket/BFG/Flare projectile-dodge throttle with Blaster exclusion | Visor and all other systems still require live behavior, collision, save and split-screen matrices; localization keys, live health concurrency/custom-count behavior, and remaining live behavior also remain |
| 5–10 | Static Handler/Hound/Sentien/ZBoss/finale slices, D-041's scoped damage-reaction integration, D-042's 22-placement Hover radial-dodge integration/Q-013 reset FIX, D-043's identity-locked 22-helper/19-file stock-precache classification and native Handler/Infantry route, D-045's source/BSP-locked injection plus private historical one-stage values 0–3/suppression, exact `q2dm1` identity/start/offset/native-drop probe, real-brush partial-placement fixture, and all eight one-member controls, plus sampled legacy v1 registry/resource observations, exist | No campaign, monster-set, finale, multiplayer, soak, or stable-release phase has passed; every retained runtime observation must be rerun under D-046 before it counts as current launch or gameplay evidence. DM injection still lacks pickup/respawn/save, dedicated/2/4/8-client and native-mode isolation; all other affected resource/audio, combat, lifecycle, save and completion matrices remain live-unverified |

Implementation status is maintained in the living matrices, not by editing the
phase prose into a retrospective. Only the exit criteria below close phases.

Because gameplay prototypes already exist beyond Phase 1, the clean-substrate
gate is recovered without pretending the gameplay worktree contains only
version/build changes and without deleting useful work. First review every
currently untracked/tracked path for secrets, generated output, and
ignore/attribute correctness; then capture the approved
tree as an immutable evidence commit/tree. Do not
push it publicly while D-003 forbids that channel. Reconstruct the pristine pinned
substrate and minimal Phase-1 integration in an isolated worktree or from a
known baseline commit; retain exact-commit Debug/Release, export/load, stock
smoke, and upstream-diff reports proving that reconstructed milestone. Then run
the immutable gameplay evidence commit from a clean isolated checkout against
Debug and Release, both exported APIs and DLL/mod-directory load, and the
identical stock-smoke scenarios, then retain a documented machine-readable patch
inventory from that certified baseline to the gameplay evidence commit. If the
reconstructed substrate is not an existing commit, identify
it with a written Git tree object or local evidence commit plus toolchain hash so
every report still has immutable input identity. Phase 1 closes only when both
evidence sets agree. A gameplay-tree diff that already contains later Zaero work
is not expected to satisfy the minimal-diff criterion by itself, and no history
rewrite or publication of either evidence ref is required.

### 5.3 Architectural conclusion

This is not safely implemented by dropping the old C files into the Rerelease
tree. The Rerelease game module is C++17, runs at 40 Hz rather than the legacy
10 Hz behavior cadence, serializes games as JSON, has a 2023 import/export API,
supports split-screen clients and a separate cgame presentation layer, and
includes wheel, bot, navigation, expansion-pack, and protocol changes.

Port behavior in small Rerelease-native modules. Keep upstream files close
enough to their baseline to make future merges reviewable, and put Zaero-owned
code under an obvious `src/zaero/` boundary wherever callbacks and shared game
structures permit it.

## 6. Zaero difference inventory

This section is the initial parity backlog. The committed feature matrix must
eventually give every row an owner, implementation link, test, status, and
`PARITY`/`ADAPT`/`FIX` disposition.

### 6.1 Map-facing classnames absent from the Rerelease baseline

The following 27 exact classnames occur in shipped BSP entity data and must
resolve:

| Group | Classnames |
| --- | --- |
| Weapons/ammunition | `weapon_flaregun`, `weapon_sniperrifle`, `weapon_soniccannon`, `ammo_flares`, `ammo_ired`, `ammo_a2k`, `ammo_empnuke`, `ammo_plasmashield` |
| Inventory/keys | `item_visor`, `key_energy`, `key_landing_area`, `key_lava`, `key_slime` |
| Monsters/defences | `monster_autocannon`, `monster_autocannon_floor`, `monster_handler`, `monster_hound`, `monster_sentien`, `monster_zboss` |
| World objects | `func_barrier`, `misc_commdish`, `misc_crate`, `misc_crate_medium`, `misc_ired`, `misc_seat`, `misc_securitycamera` |
| Boss scripting | `target_zboss_target` |

Name spelling is part of the ABI. In particular, retain the historical
`monster_sentien` spelling rather than correcting it.

### 6.2 Source-exposed compatibility entities

The Zaero spawn table adds 18 entries relative to legacy Quake II:

`sound_echo`, `misc_ired`, `trigger_laser`, `monster_autocannon`,
`monster_autocannon_floor`, `monster_sentien`, `misc_securitycamera`,
`monster_hound`, `monster_handler`, `misc_commdish`, `load_mirrorlevel`,
`misc_crate`, `misc_crate_medium`, `misc_crate_small`, `monster_zboss`,
`func_barrier`, `misc_seat`, and `target_zboss_target`.

Four do not appear as exact classnames in the shipped maps but remain part of
the Zaero mapper contract:

- `sound_echo` and `load_mirrorlevel` deliberately free themselves in the
  supplied source; preserve them as documented compatibility no-ops unless
  retail testing proves otherwise.
- `trigger_laser` has no `use` callback: it requires a target, auto-starts after
  0.1 seconds, defaults `wait` to four seconds, traces 2,048 units, and reacts
  only to monster/player hits. Spawnflag bit 1 rearms it; without that bit it
  frees itself after the first qualifying hit. It needs a functional port,
  editor definition, and synthetic proof because no shipped BSP places it.
- `misc_crate_small` is the 32-unit pushable-crate variant.

The hidden, always-owned `weapon_push` is another source-only gameplay surface
and must be registered even though maps do not place it.

### 6.3 Map parser, field, and scripting changes

| Surface | Legacy Zaero behavior to preserve |
| --- | --- |
| `spawnflags2` | A second flags field appears 2,621 times: bit 1 `MIRRORLEVEL`, bit 2 `NOT_COOP`, and bit 4 `NOT_SINGLE`. Parse, save, filter, and expose it to editors. The shipped values are 0 (2,316), 1 (300), 2 (1), and 4 (4). The legacy deathmatch path also tests `NOT_SINGLE`; preserve/test that non-obvious filtering rather than normalizing it silently. |
| Mirror metadata | `mirrortarget` and `mirrorlevelsave` keys occur in map data. The supplied source parses/ignores or leaves the mirror system dormant. Retain the keys and record a no-op/parity decision; do not reject them as unknown. |
| `active` and sliding doors | Used by Zaero machines, cameras, doors, and toggled objects. On doors, bit 1 enables use-as-activation-toggle and bit 2 means initially enabled; the use path toggles touch eligibility rather than simply opening. `door_openclose` also preserves its message across repeated use, and `door_blocked` performs no damage path when `dmg <= 0`. Preserve auto-trigger/message behavior, initial state, transitions, animations, blocking, and saves. |
| `mangle` | Used for remote camera orientation. Preserve parsing separately from normal entity angles. |
| `mteam` | A monster/team relationship used by the custom AI and Handler/Hound behavior. Preserve target selection and friendly interaction rules. |
| `model2`/`model3`/`model4` | Additional linked models used by multipart/custom entities. Parse, index, link, and save them without assuming stock single-model state. |
| `aspeed` | Angular speed used by rotating trains/movers and custom objects; preserve acceleration units and orientation across saves. |
| Explicit `mins`/`maxs` | Mapper-supplied bounds used by custom solids/objects. Parse safely and verify reordered/invalid bounds. |
| Random `func_timer` | A semicolon-delimited target list means choose one target randomly rather than firing the literal name. Shipped examples occur in `ztomb2`, `ztomb4`, and `zdm6`. |
| Toggle `trigger_push` | Adds bit 2 start-off and bit 4 no-sound plus a `use` toggle. At least five shipped fan/push volumes depend on this behavior; validate messages/non-client touches while off. |
| Accelerating `func_rotating` | Zaero adds acceleration/deceleration and stateful toggle behavior. Translate timing to duration types and verify rider/contact behavior. |
| Low-trigger `func_plat` | Zaero reuses spawnflag bit 2 as `PLAT_LOW_TRIGGER_2`: `Touch_Plat_Center` accepts only a player whose feet are within eight units of the lowered platform top. Eleven shipped platforms across eight maps use it. Rerelease already uses bit 2 as `SPAWNFLAG_PLAT_NO_MONSTER`; [D-036](compatibility/decisions.md#d-036--func_plat-bit-2-low-trigger-collision) now dispatches the exact inclusive boundary only on Zaero-classified maps and retains native behavior elsewhere under static tests. Live touch/movement/save and D-018 classifier closure remain. |
| Rotating doors | Zaero removes the legacy default `dmg 2` from `func_door_rotating`; 12 of the 32 shipped rotating doors omit or explicitly zero damage. [D-038](compatibility/decisions.md#d-038--func_door_rotating-zero-damage-default) now preserves zero/missing and positive authored values only on Zaero-classified maps while retaining the native default elsewhere under static tests. Live block/reversal/movement/team/save proof remains. |
| Rider physics | `MOVETYPE_RIDE` lets the floor autocannon follow moving platforms/trains. |
| Pushable physics | `MOVETYPE_FALLFLOAT` supports crates and seats; `MOVETYPE_BOUNCEFLY` supports custom projectiles/effects. |
| Falling explosive barrels | Zaero changes stock `misc_explobox` to `MOVETYPE_FALLFLOAT`, mass 400, and a client-only `barrel_touch` that does not require the pusher to be grounded and moves through `SV_movestep`. [D-037](compatibility/decisions.md#d-037--misc_explobox-fallfloat-and-push-contract) now gates those spawn/touch/start differences, preserves their 40 Hz speed, and retains native STEP/mass-50 behavior elsewhere under static tests. Thirty-one placements in five maps still require live water, airborne-push, slope, explosion, save, and native-map-fallback proof. |
| Damage modes/flags | Custom code relies on `DAMAGE_IMMORTAL`, `FL_DONTSETOLDORIGIN`, `FL_BFGMISSFIRE`, and transient barrier/EMP/flash state. |
| Mission help | Thirty-nine `target_help` entities in ten maps supply objectives. Preserve F1/help display, cross-level state, save/load, and per-client presentation. |
| Changelevels | Preserve `*` unit boundaries, `$spawnpoint` suffixes, cinematic/image chains, and exact target strings. Catalog suspicious data rather than silently repairing it. |
| World music | Worldspawn `sounds` values 1 through 11 select legacy CD/music tracks. [D-010](compatibility/decisions.md#d-010--music-values-111) now preserves explicit native `music`, passes values 2–11 through Rerelease's own numeric base-soundtrack contract, and logs value 1/invalid requests before selecting silence. Zaero ships no music and ZaeREo packages none. Static evidence locks all 20 map values, no-media provenance, transitions, volume/loop isolation, and native fallback; a historical legacy-v1 one-stage zdm6 report records the exact value-1 log and must be rerun under D-046. Acoustic silence, audible 2–11, transitions, client volume, cinematic, and server proof remain. |
| Enhanced `misc_viper` | Supports smoke, solid/custom bounds, and `model2`–`model4` linked presentation while retaining the ordinary `func_train_find`/`train_use` route. The supplied source has no separate train-destination variant: preserve exact smoke-flag consumption before train logic and linked-model motion without inventing one. |
| Trains and path corners | `train_next` accepts per-corner speed/accel/decel and uses raw-origin destinations for `misc_viper`; `path_corner_touch` turns toward the next goal before waiting and suppresses the teleport event. [D-039](compatibility/decisions.md#d-039--train-and-path-corner-colliding-mapper-semantics) now implements those scoped paths plus the source-only 10 Hz smooth bits 2/4 and train rotation bits 8/16/32/64 while preserving native/Rogue meanings elsewhere. Static evidence locks all 375 corners, 28 trains, seven Vipers, five nonzero zdef4 node speeds, 96 waits, four teleports, zero shipped smooth/rotation uses, and four zero `aspeed` values. Live route/orientation/rider/save and classifier proof remains. |
| Cosmetic `target_explosion` | Zaero flag 1 selects an animated A2K-style effect/sound but retains ordinary target-explosion damage and target firing; it is not an EMP. |
| Monster count flag | Zaero uses monster spawnflag 16 for “do not count,” including composite-spawn edge cases. The compatibility spine now translates that low authored bit to Rerelease `AI_DO_NOT_COUNT` before native accounting; the two shipped placements are statically covered, while live composite-spawn accounting remains a gate. |
| Spawn killboxes | Custom monster/player killbox helpers avoid killing a live player in one path and may remove the spawning monster instead. Zaero monster trigger/target-spawn paths now use a gated player-safe helper that clears non-player blockers but self-removes the spawning monster on a live-player overlap; live obstruction and save/load fixtures remain required. |

Map-specific compatibility must be data-driven where practical. A test should
fail when a map introduces an unrecognized key/classname rather than relying on
console-log inspection.

### 6.4 Player weapons, ammunition, and usable inventory

| Feature | Observable Zaero contract |
| --- | --- |
| Push | Hidden, always-owned `weapon_push` reaches about 64 units, applies two damage and roughly 512 kick, interacts specially with players, monsters, and `MOVETYPE_FALLFLOAT` objects, then returns to the prior weapon. It is excluded from ordinary keep/select behavior. |
| Flare Gun | Fires a bouncing flare at speed 600. Its approximately `8000 / speed` lifetime, 256-unit illumination/blinding cone, 0.1-second distance/facing checks, monster alert/evasion/flash response, player blend, and multiplayer compensation damage (up to ten per 100 ms flare check) for `gl_polyblend 0` are gameplay. `zdmflags` bit 1 disables that compensation damage. |
| IRED | `ammo_ired` is both inventory and deployable laser trip mine. Placement accepts a world surface within 64 units; it arms after about one second, expires after about 180 seconds, detects beam-end movement, uses a 150-damage/384-radius explosion plus five 15-damage shrapnel pieces, and limits deployed mines to 25 by detonating the oldest. Map-authored `misc_ired` adds toggling and a back-wall check. |
| Sonic Cannon | Charges for up to five seconds, consuming as many as 100 cells. Release combines a line hit and radial blast scaling up to approximately 1,000 damage and 500 radius. EMP interference can reset/misfire it. Quad plays its sound but the supplied fire path does not multiply the damage. The dedicated Rerelease implementation, per-client saved clocks, delayed effects, idle hum, obituary and null-safe EMP hook are now statically verified; live 40 Hz, split-screen, save and real-EMP fixtures remain. |
| Sniper Rifle | Uses three slugs, has an approximately three-second charge/reload, zooms to FOV 15 in single player and 30 in deathmatch, does 250/400 damage/kick in single player and 150/300 in deathmatch, bypasses armor, passes through Plasma Shields, and uses a custom impact effect. The supplied code excludes it from generic cycling in places. |
| A2K | The Armageddon 2000 is a use-as-weapon item with a maximum carry of one. Activation consumes the item, holds gunframe 19, and starts a five-second duration (`50` legacy frames, `200` target ticks) in the firing client's `a2kFramenum` state; the port stores a duration/deadline, not the literal target tick count. That player is absolutely immune during the countdown even to `DAMAGE_NO_PROTECTION`; there is no intermediate explosion entity. Death cancels the pending event. At detonation, the temporary `A2K Explosion` is created and a 2,500-damage/512-radius primary event is followed by a visibility-gated outer pass to 1,024 units, so qualifying targets can be hit twice; self damage is halved. Quad state at blast time multiplies damage and both radii by four. Lock HUD seconds, exact time/radius boundaries, death/save phases, self/double hits, and Quad-at-blast with golden tests. |
| EMP Nuke | A use-as-weapon item creates a no-line-of-sight EMP field with roughly 1,024 radius and 30-second lifetime. It disrupts an explicit matrix of energy weapons, monster attacks, IRED, Plasma Shield, and Sonic Cannon behavior rather than all weapons; its owner is exempt from the owner's own field check. |
| Visor | A nominal 30-second usable remote-camera view (`300` legacy frames, `1,200` target ticks, represented as a duration). It cycles active `misc_securitycamera` entities, freezes the still-solid real player, and preserves third-person presentation through a `VisorCopy`. The source copy is solid/non-damageable, but D-021 proves its trace winner changes with mover-driven link order and selects a scoped non-solid-copy FIX without weakening the real player. The view uses required camera `message` and `mangle`, displays tracking target and timer, applies a ±15-degree yaw swing over 6.4 seconds (`64` legacy frames, `256` target ticks), flashes static for 0.2 seconds, can be dropped with remaining duration, and cancels on damage/death/putaway. Picking up a dropped Visor can add its remaining duration to a partially consumed one and exceed 30 seconds. |
| Plasma Shield | Places an oriented, stationary sprite barrier about 50 units ahead. It has 4,000 health, lives about ten seconds, uses power-armor-like mitigation (making effective durability much higher), loops audio/animation, is prevented by EMP, and is penetrated by the Sniper Rifle. It has no conventional owner damage attribution and even owner shots collide. Preserve the original multiplayer sound quirk unless deliberately adapted. |
| Custom keys | Airfield Pass (`key_landing_area`), Laboratory (`key_lab`), Clearance Pass (`key_clearancepass`), Energy, Lava, and Slime keys use standard key/coop semantics with custom models/icons/messages. The two source-exposed keys not used by the supplied maps still belong to the mapper/item contract. |
| Obituaries and presentation | Zaero adds 25 monster-specific death messages plus custom MOD handling for Sniper, Tripbomb, Flare, `gl_polyblend`, A2K, Sonic Cannon, and Autocannon. Its `IsFemale` test uses the first character of `skin` rather than the legacy `gender` key and removes neutral handling. Preserve the observable SP/co-op/DM/self/friendly-fire results while adapting safely to Rerelease localization and formatting. |

Zaero extends persistent ammo limits: Flares 30, IRED 30, A2K 1, EMP 50,
and Plasma Shields 20. A Pack raises IRED to 100, A2K to 1, EMP to 100,
and Plasma Shields to 40 in addition to its stock-ammo effects, but notably does
not raise or grant Flares. Verify Backpack, Bandolier, death/respawn, co-op
inventory, level transitions, and save/load.

The 1.1 configuration maps `use weapon 1` through `use weapon 10` to a
multi-selection table that combines stock and Zaero weapons. Preserve these
commands/aliases while also registering stable Rerelease wheel IDs, icons,
ammo relationships, availability predicates, and cgame strings.

The single-player/co-op starting loadout is also changed: Push and Blaster are
owned, and the player receives the Flare Gun with three flares. Confirm exact
deathmatch starting inventory separately.

Placed ammunition also gains Zaero spawnflag behavior: one flag caps the
post-pickup inventory at the entity's quantity, and another schedules a
15-second respawn even outside ordinary deathmatch rules. Preserve the exact
bit meanings in the generated entity definition. The old code newly permits
dropping the active grenade-ammo stack to zero and its no-ammo fallback does not
know custom weapons; retain observable drop behavior but integrate fallback
safely with the complete Rerelease item list.

### 6.5 Monsters, defences, and interactive objects

| Feature | Required behavior surface |
| --- | --- |
| Autocannon | Ceiling and floor variants, multipart rendering, four styles covering three attack types (styles 3/4 both HyperBlaster), berserk/start-off/use flags, constrained tracking arcs, deploy/active states, damage/death, and mover riding for the floor variant. The implementation preserves its deliberate non-`SVF_MONSTER` classification, 10 Hz decisions, generation-safe multipart riders, EMP suppression and retail style-4 frame result; static source/map/ELF contracts pass, while live mover/combat/save proof remains. |
| Hound | 175-health leap/bite monster with spawnflag-8 schooling/swarm behavior, custom movement ranges, team behavior, pain/death, and wake/target logic. |
| Handler | Begins as a combined Handler/Hound creature whose lethal damage is clamped until separation, releases a Hound using the intended health proportion, then becomes an infantry-derived Handler. Monster totals and spawn flags account for the future Hound. |
| Sentien | 900-health ranged monster whose hovering presentation uses grounded STEP/walkmonster locomotion, with bullet/blast and laser attacks, defensive fend/shield behavior, pain, and death effects. Preserve the shipped spelling and precaches. |
| ZBoss | Multi-attack final boss with skill health 3,000/4,500/6,000/8,000, rockets/flares, grapple/drag behavior, plasma attack, staged state/taunts, EMP responses, damage quartering only when the direct inflictor itself is monster-classified, death barrage, and one-shot `target_zboss_target` scripting. A dedicated module now implements the complete static frame/state surface, typed/saved pressure/cooldown state, marker consumption, and generation-owned child cleanup under D-025. Pain retaliation occurs on the 42nd qualifying callback; the separate below-25%-health EMP path uses a 30–35 second cooldown isolated from Hound schooling. Live phase, save, damage, co-op, encounter, and outro proof remains a release gate. |
| Security camera | `message` is required and initial active state derives solely from the presence of `targetname`; preserve subsequent active/use state, frames 0–59 at 10 Hz as a six-second animation loop, 0.2-second green-shell pain feedback, target message, remote-view orientation, save state, and Visor enumeration. |
| Barrier | Invisible, immortal blocking volume that reveals itself briefly on touch/damage and influences weapon traces through transient barrier state. |
| Crates/seats | Three crate sizes plus a seat use pushable/fall-float physics, damage, collision, and mass-dependent interaction with Push. |
| Comm dish | One-shot use-triggered animated communications dish. The supplied callback does not fire ordinary entity targets. |
| IRED world entity | Mapper-placeable/toggleable trip mine, including spawn flags and persistence. |
| Laser trigger | A source-only mapper-facing trace trigger with no `use` callback: require a target, auto-start after 0.1 seconds, default `wait` to four seconds, trace 2,048 units, react only to monsters/players, and either rearm under bit 1 or free after the first hit. Preserve callback/save identity and prove it with synthetic fixtures. |

Zaero also changes stock monster/system behavior. The implementation audit must
track these separately from wholly new monsters:

- Handler transformation depends on reusable stock-infantry precache/spawn
  logic. [D-043](compatibility/decisions.md#d-043--stock-monster-precache-extraction-and-sound-index-strategy)
  and the [generated call graph](audits/stock-precaches.md) prove that this is
  the only cross-file consumer among Zaero's 22 extracted helpers in 19 stock
  files. The Rerelease baseline already exposes the needed
  `InfantryPrecache`; the port reuses it and a Zaero-owned Hound precache rather
  than cloning unrelated stock files.
- Custom monsters and some projectiles consult EMP state.
- Flying AI gains strafe/schooling/team behavior and uses added AI flags/fields.
- Hover behavior includes an active dodge/strafing path. D-042 now scopes the
  exact callback to Zaero `monster_hover`, preserves its 37-direction search,
  strict typed one-second state and direct 3D impulse, and explicitly resets
  Q-013's expired/clipped state; live projectile/collision/save proof remains.
- Monster flash/blind handling is shared with Flare Gun behavior.
- Team and target-response rules are modified for `mteam` and paired creatures.
- Shared `check_dodge` state adds `AI_DODGETIMEOUT` and saved
  `monsterinfo.dodgetimeout`, with skill-dependent throttling. Rockets, BFG, and
  Flare invoke it; Blaster deliberately does not. Skill 0 first passes only a
  25-percent random gate; skill is capped at 3 for the timeout arithmetic. The
  initial boundary is `level.time + (4 - skill) * 1.1`, after which the flagged
  throttle is `level.time + skill * 4`. Preserve that flag-clear/rearm ordering,
  10 Hz decision intent on the 40 Hz target, and save/load during each window.
- `M_ReactToDamage` accepts non-monster Autocannons, retains `AI_SOUND_TARGET`
  when a player attacks, applies `mteam`, and can select the reacting monster
  itself through `attacker->enemy`. D-041 now layers the intended deltas onto
  native Tesla/medic/target-anger/cooldown/ignore-shot behavior and preserves
  Rerelease's self-selection guard; live combat/save proof remains.
- The final boss grapple changes player movement/view state and therefore needs
  multiplayer, save/load, death, disconnect, and teleport cleanup tests.

The stock-monster diff has a small intentional core surrounded by version drift:

| Area | Observed Zaero change | Port classification |
| --- | --- | --- |
| Selective EMP | Aborts/misfires Boss2 and Jorg machineguns plus Infantry, Supertank, and Tank machineguns; Makron BFG has a redundant check. Global wrappers cover selected energy projectiles. Actor/Gunner/Soldier hitscan and monster shotguns/grenades remain active. | Preserve this explicit affected/unaffected matrix first. |
| Hover | Adds a roughly one-second radial fly-strafe dodge; its reset contains an assignment/comparison typo. | [D-042](compatibility/decisions.md#d-042--hover-fly-strafe-and-expired-state-reset) preserves the exact Zaero-only callback/search/impulse through a dedicated saved Rerelease state and fixes the stale comparison; static contracts pass for all 22 placements, with live seeded/collision/expiry/save proof remaining. |
| Infantry | Adds the Handler-to-Infantry conversion entry point and is the sole stock precache helper reused from another Zaero source file. | [D-043](compatibility/decisions.md#d-043--stock-monster-precache-extraction-and-sound-index-strategy) reuses the Rerelease baseline's existing `InfantryPrecache` for Handler and conversion; live resource/audio/conversion proof remains. |
| Chick | Removes the third pain sound and chooses between two sounds 50/50, likely due sound pressure. | Preserve for initial parity; expanded sound capacity is not permission to redesign audio. |
| Monster movement | Adds FALLFLOAT ledge/water handling and flare evasion. The flare selector uses the first enumerated flare, overwrites a goal, and contains a precedence expression that is always false. | Port observable selection/motion, then classify safety/logic fixes. |
| Other stock monsters | Adds 21 more precache helper surfaces across 18 files, but the identity-locked call graph finds no cross-file consumer; the same files can still contain unrelated EMP, flash, audio, cadence, or source-version deltas. | Keep native Rerelease spawn-local resource paths and do not clone organizational extractions. Independently classify every observable non-precache delta. |
| Muzzle offsets/protocol | Restores older base offsets and omits later expansion offsets/constants. | Treat as source-version drift; keep Rerelease tables unless a Zaero visual test demands an override. |

All differing old monster files also omit upstream GPL headers. That is not a
runtime feature and must not be repeated; preserve applicable copyright/license
notices in the port.

Initial golden-test anchors from the custom-monster source are:

- Hound melee produces two or four 30–34-damage strikes; leap starts around
  400 horizontal plus 200 vertical velocity and can apply 40–49 impact damage
  above the speed threshold. Long-range jump selection has no upper distance
  bound and only a low random chance beyond 100 units.
- Handler starts at 175 health and clamps a lethal hit until separation. Release
  derives a 175-scaled Hound health value and leaves the same remaining health
  on the converted Infantry body, effectively duplicating encounter durability.
- Sentien is a 900-health, −425-gib, mass-500 grounded STEP/walkmonster whose
  model presents as hovering. Its burst helper accepts
  five damage but fires hard-coded two-damage/four-kick shots. Its persistent
  laser does eight base damage, locks aim on its first frame, and scales damage
  and turn speed by skill. Fend briefly holds a frame and reduces incoming
  damage to 85 percent. Its normal monster lifecycle removes it in deathmatch.
- Ceiling Autocannon style 1 fires four-damage bullets; style 2 fires
  100-direct/120-radius rockets at speed 650; styles 3/4 fire 20-damage
  hyperblaster shots at speed 1,000. Floor cannons reject style 1. Range is
  about 2,048 with constrained yaw/pitch; default health is 100. Death applies
  150/384 radial damage, historically ignores its current enemy, and reports
  the Tripbomb MOD.
- ZBoss has skill health 3,000/4,500/6,000/8,000, gib threshold −700, and mass
  1,000. Its dedicated source-shaped flare/rocket, seven-shot bouncing plasma,
  grapple, EMP, damage-reduction, one-shot marker, and death-barrage paths now
  have static contracts; each still needs deterministic live and save tests and
  must not be simplified into a generic Rerelease boss attack.

### 6.6 Stock gameplay and engine-facing modifications

The source diff is broader than its `z_*.c` files. Port and test the intent of
changes in these legacy subsystems:

| Area | Zaero delta to isolate |
| --- | --- |
| Spawn/save fields | Custom entity/client/level fields, extra movement and AI state, callback pointers, mirror metadata, `spawnflags2`, EMP/Visor/boss state, and item maxima. |
| Item system | New item registrations, use-as-weapon inventory, hidden/cycle flags, Pack limits, model/icon/sound precaches, death/drop behavior, and DM injection. |
| Client lifecycle | Default Push ownership, persistent inventory, respawn/death cancellation of views/effects, weapon-number commands, help state, and camera-player copy cleanup. |
| Weapon core | Custom animation/state machines, zoom/view handling, armor/trace flags, EMP queries, barrier penetration, projectiles, muzzle/effects, and Quad scaling. |
| Damage/combat | Immortal-but-reactive entities, no-armor sniper damage, team relationships, barrier traversal, flash/EMP state, grappling, and radial visibility rules. |
| Physics/movers | Ride, fall-float, bounce-fly, accelerating rotation, toggled pushes, active doors/objects, ground ownership, and save restoration. |
| AI | Schooling/formation helpers, fly strafing, custom attack checks, blind/flash response, reusable stock monster precaches, team logic, and new monster callbacks. |
| Player view/HUD | Sniper zoom, Visor view redirection/copy, blend/static/tracking/timer presentation, boss/grapple effects, and custom status/inventory strings. |
| Triggers/targets | Random timer targets, toggle push, custom laser, boss target, camera/comm-dish targets, and compatibility no-ops. |
| Server configuration | `zdmflags`, Zaero DM item injection, item/weapon aliases, episode start command, map list, and legacy config migration. |
| Resource indexing | Large custom sound/model/image sets plus conditional caching code. Rerelease cached-index helpers and expanded limits replace legacy workarounds. |

Do not copy unrelated vintage Quake II changes merely because the two trees
differ. For each change outside a Zaero-owned module, classify it as:

- Zaero feature dependency;
- deliberate Zaero bug fix/quirk;
- upstream version drift already superseded by Rerelease; or
- debug/dead code that is not part of a release build.

### 6.7 Commands and cvars

Preserve Zaero's additions without regressing the larger Rerelease command/cvar
surface:

- `zdmflags` is the sole clearly gameplay-specific server cvar.
- `gl_polyblend` is read from user info by the Flare Gun damage workaround;
  modern parity mode needs a safe per-client equivalent or a documented
  adaptation.
- `printsoundrejects` exists only with the conditional legacy sound-cache
  feature and should become a development diagnostic, not a public requirement.
- `gamedir` was queried by the old module; use the native target API/config
  instead of recreating a stale engine cvar.
- `showorigin` is a production client command that displays origin data using
  Zaero HUD stats. Preserve it as a useful compatibility/developer command after
  reallocating the conflicting stat slots.
- `linesize`, `testitem`, and `anim` are test-mode-only commands; keep them out
  of player Release builds.
- Version 1.1 removes the old `zwepas` toggle and implements alternate selection
  through `use weapon 1`–`10` plus config aliases `zwepas_on`/`zwepas_off`.
  Preserve the actual 1–10 syntax and aliases without rebinding users by default.
- While the Visor is active, preserve the legacy gameplay-command lock:
  cancellation/Visor-only use and inventory cycling remain available. D-008
  adapts chat by allowing `say`, `say_team`, and `steam` to continue through
  native Rerelease lobby routing rather than suppressing or reimplementing it
  in the game DLL.
- The old `give` path assembles multiword names in a fixed unchecked buffer.
  Use safe Rerelease parsing while retaining accepted item names.
- The old `kill` behavior allows an immediate respawn after a five-second
  cooldown. Compare with native Rerelease behavior and classify it rather than
  overwriting the modern client path wholesale.

Legacy-source absences such as later `maxspectators`, password/flood/filter/map
list cvars are source-version drift. Do not remove their Rerelease equivalents.

### 6.8 Deathmatch-specific behavior

`zdmflags` is a server-info cvar with default 0:

- bit 1 (`ZDM_NO_GL_POLYBLEND_DAMAGE`) disables Flare Gun compensation damage
  to players who disabled `gl_polyblend`;
- bit 2 (`ZDM_ZAERO_ITEMS`, historically named as a positive flag) disables
  automatic Zaero-item addition to maps that contain none.

In deathmatch, when bit 2 is clear and none of the eight Zaero item classnames
already exists, the game tries to place one of each near successive DM starts:

`weapon_soniccannon`, `weapon_sniperrifle`, `weapon_flaregun`, `ammo_ired`,
`ammo_a2k`, `ammo_flares`, `ammo_empnuke`, and `ammo_plasmashield`.

The search/placement order, four-attempt fallback, 128-unit radial traces,
bouncing spawn state, all-or-none precondition, and console count are observable
quirks. Port them first for parity; a later deterministic/fair-spawn mode may be
offered under a separate cvar.

[D-045](compatibility/decisions.md#d-045--zdmflags-and-deathmatch-item-injection)
now implements this in `src/zaero/g_zaero_dm.cpp` through native Rerelease item
lifecycle. “All-or-none” is explicitly the existing-member precondition, not a
transaction: blocked geometry can leave 0–7 successful additions and the exact
console count remains observable. The normalized
[source/BSP audit](audits/dm-injection.md) proves all 20 supplied maps already
contain at least one member and therefore suppress auto-injection, including
six maps with incomplete sets. Static values 0–3, order/wrap/partial failure,
save-callback surface and D-018 isolation tests pass. Historical legacy-v1
one-stage eligible stock `q2dm1` reports record aggregate counts
8/8/disabled/disabled for values 0–3, and an authored `zdm1` report records
existing-member suppression. A structured Debug probe records all eight exact
identities/order, successive start ordinals 1–8 on
first attempts, 128/16-unit initial offsets, final origins, and live native
Toss/trigger/Touch_Item/IR state; bit-2 and authored controls record zero.
A deterministic private fixture with four starts inside real collision brushes
records the other four placements at set indices 0/2/4/6 and wrapped ordinals
1/6/11/16. Eight additional private maps each contain one valid start and
exactly one historical member; all eight structured value-0 runs record zero
additions. These pre-v2 reports must be rerun under D-046 before they count as
current runtime evidence. Multiplayer, pickup/respawn/drop/save,
dedicated/server-info, and native-mode fixtures remain before SYS-012 is
verified.

### 6.9 Campaign and map inventory

| Unit | Maps | Boundary/flow |
| --- | --- | --- |
| Logos and introduction | `elogo.cin`, `intro.cin`, `zlogo.cin` | Start chain before `zbase1` |
| Base | `zbase1`, `zbase2` | Boundary from `zbase1` to `*zdef1` |
| Defence | `zdef1`–`zdef4` | Boundary from `zdef1` unit to `*zwaste1` |
| Wasteland | `zwaste1`–`zwaste3` | Boundary to `*ztomb1` |
| Tomb | `ztomb1`–`ztomb4` | Boundary to `*zboss` |
| Finale | `zboss` | `outro.cin+victory.pcx` completion chain |
| Deathmatch | `zdm1`–`zdm6` | Dedicated arenas; `zdm6` also exercises random timer targets and toggle pushes |

~~~mermaid
flowchart LR
    Intro["elogo + intro + zlogo"] --> B1["zbase1"]
    B1 <--> B2["zbase2"]
    B1 -->|"unit boundary"| D1["zdef1"]
    D1 <--> D2["zdef2"]
    D1 <--> D4["zdef4"]
    D4 <--> D3["zdef3"]
    D1 -->|"unit boundary"| W1["zwaste1"]
    W1 <--> W2["zwaste2"]
    W1 <--> W3["zwaste3"]
    W1 -->|"unit boundary"| T1["ztomb1"]
    T1 <--> T2["ztomb2"]
    T1 <--> T3["ztomb3"]
    T1 <--> T4["ztomb4"]
    T1 -.->|"preserved unreferenced artifact"| Missing["tomb1 (no supplied BSP)"]
    T1 -->|"unit boundary"| Boss["zboss"]
    Boss --> Outro["outro + victory"]
~~~

Internal transitions use named `$spawnpoint` suffixes and must be preserved.
[D-011](compatibility/decisions.md#d-011--ztomb1-target-for-absent-tomb1-bsp)
now classifies the `ztomb1` changelevel to absent `tomb1`: generated closure of
all 30 changelevels proves entity 522 is both the sole missing destination and
the sole record with no activation or other target reference. Because
`target_changelevel` is invisible/use-only and no production code names its
`mainexit` targetname, it is unreachable from every valid inbound state and is
preserved unchanged as an inert mapper artifact. Do not add an alias, rewrite
the BSP, or create an importer data patch. A map revision that adds either the
reference or destination must fail the audit and reopen the decision.

Entry to `zboss` has a separate player-state contract. On a positive-health
entry, `PutClientInServer` calls `InitClientPersistant`, retains only current
health, and resets inventory to Push, Blaster, Flare Gun, and three flares.
Preserve the inbound finale reset without applying it to an ordinary reload or
native map. Test first entry, mid-boss reload, death/respawn, level travel,
co-op, and split-screen clients independently.

Create a Rerelease `mapdb.json` episode entry and `zaerostart.cfg` whose start
command preserves the exact logo/introduction order:
`gamemap "*elogo.cin+intro.cin+zlogo.cin+zbase1"`. Generate/merge the episode
against the pinned full Rerelease map database so selecting the mod does not
erase native map metadata. Do not install the old `default.cfg` or loose
`autoexec`: both use `unbindall` and would trample a Rerelease user's controls.
Translate their useful Zaero aliases and weapon-number behavior into a
mod-specific configuration that can be executed explicitly.

### 6.10 Source-only and non-runtime material

The supplied source includes seven project-enumerated animation/frame/monster
test modules plus integration hooks guarded by `_DEBUG` and `_Z_TESTMODE`.
Only the supplied Debug configuration defines `_Z_TESTMODE`; its Release
configuration defines `NDEBUG` and not `_DEBUG`/`_Z_TESTMODE`. The separate
two-site `_SHANETEST` animated-rocket experiment is defined by neither supplied
configuration, and both boss grapple-cable rendering branches are literal
`#if 0` blocks whose selected fallback is `TE_MEDIC_CABLE_ATTACK`. Under
[D-015](compatibility/decisions.md#d-015--debug-and-test-tools), these are
archaeological/developer material rather than missing release features.

The machine-readable [Release-surface policy](provenance/release-surface-policy.json)
identity-locks all 15 relevant source/project files and the exact guarded
commands, classnames, configuration paths, symbols, and compiled-out branches.
The normalized [audit](audits/release-surfaces.md) proves the current port has
zero forbidden source/project hits. `tools/audit_release_surfaces.py` also
fails closed on ASCII or UTF-16 signatures in a produced DLL and on forbidden
members or embedded DLL signatures in a deterministic ZIP. Its grapple denial
is scoped only to `src/zaero/g_zaero_zboss.cpp`, so the native Rerelease
protocol and CTF constants remain valid. Revision 2 approves D-045's narrowly
scoped read-only `sv zaereo_dm_probe` only under `_DEBUG`: placement metadata
lives outside edicts/saves, the server dispatch/declaration is absent from
Release, and both command/output signatures join the binary denylist. Any
future developer-tool restoration requires the same explicit non-Release flag,
policy revision, and regression tests; it cannot arrive as an accidental
mapper/game ABI. Static/DLL proof does not replace live evidence. The retained
2026-07-15 schema-valid **legacy v1** Release report records that the audited
DLL loaded, initialized/spawned `zbase1`, reached native client begin, and shut
down cleanly. Because it selected the mod/map before native-window verification,
it does not close Q-039/SYS-018 or any current launch-safety gate, and makes no
map-playability claim.

Conditional `CACHE_SOUND` code was intended to work around legacy sound-index
limits but was not enabled by either supplied project configuration. The
[D-043 audit](audits/stock-precaches.md) now locks its global `gi.soundindex`
interception, in-place caller-buffer lowercasing, level-list/name allocations,
return-zero rejection at the 256-entry ceiling, and the Rerelease-native 2,048
limit. The port therefore uses scoped cached-index mechanisms and does not
emulate the original missing-sound failures in `zdef1`, `zdef4`, `ztomb1`, or
`ztomb3`. Per-map referenced-index counts and audible verification remain open;
the larger ceiling and sampled spawn logs alone are not acoustic proof.

Old demos and saves use incompatible protocols/formats and are archival inputs,
not runtime compatibility targets. A stable release is not required to replay
the four legacy `.dm2` files or load the four legacy save directories.

### 6.11 Known-defect and quirk ledger seed

These findings require explicit decisions before code cleanup:

| Finding | Initial disposition |
| --- | --- |
| IRED/EMP phase-out code compares rather than assigns `SVF_NOCLIENT` in one path. | Reproduce expected visible behavior in a test, then `FIX` the obvious state bug if no retail quirk depends on it. |
| Barrier trace helper has a path without a final return value. | `FIX` undefined behavior while preserving tested trace results. |
| A2K has overlapping radial/visible damage paths and unusual self-damage. | D-028 preserves source-origin/bbox falloff, integer damage, half self damage, and both ordered passes under static golden contracts; retain `PARITY` pending live boundary/multiplicity capture. |
| Quad multiplies A2K damage and radii, while Sonic Cannon plays Quad audio without multiplying damage. | A2K now samples Quad at blast and scales damage plus the inner radius before deriving the outer radius; Sonic preserves one discharge sound and unscaled equations. Retain `PARITY` pending live comparison. |
| Flare damage compensates for a client rendering preference. | `PARITY` by default; retain the historical opt-out flag and document it. |
| Visor camera cycling can loop indefinitely when all cameras are inactive, restores WALK rather than the prior movement type, and has a broken player-copy skin-change path. | `FIX` lifecycle/safety bugs while preserving ordinary camera presentation. |
| Plasma Shield uses the generic ammo cap despite a contradictory dead pickup-specific maximum and has no ordinary owner attribution. | [D-029](compatibility/decisions.md#d-029--plasma-shield-collision-durability-and-placer-identity) retains 20→40 limits, no gameplay owner, owner-shot collision, independent lifetime, and generation-checked non-collision placer metadata under static contracts; live pickup/drop/death/collision/save proof remains. |
| IRED shrapnel has a possible null trace-plane dereference. | `FIX` memory safety without changing valid impacts. |
| Sentien's bullet helper ignores a requested damage argument and hardcodes two damage. | `PARITY` unless retail comparison proves the helper call was intended. |
| Autocannon destruction attributes its blast as Tripbomb damage and ignores its current enemy. | The port preserves both under dedicated MOD/source contracts; live radius and obituary capture remains before verification. |
| Fly-strafe assigns with a comparison operator in one AI path and may persist. | `FIX` only after an AI sequence test captures ordinary motion. |
| Hound schooling stores a radius list/distance in fields on every nearby edict; ZBoss reuses `zDistance` for its EMP cooldown. A Hound within 2,000 units can therefore corrupt the boss timer. | Separate transient schooling data from boss time for safety, but retain a focused legacy-quirk test and document the `FIX`. |
| Schooling averages yaw arithmetically (so 359° and 1° average to 180°), includes non-schooling Hounds, and “minimum distance” copies a neighbor's heading rather than separating. | Begin with `PARITY` because formation motion is visible; offer corrected steering only after captures. |
| Handler release duplicates remaining health into the converted Handler and detached Hound; the detached Hound has `noclass`/zero max health and can miscount kills when the Handler is not counted. | Preserve encounter durability, but normalize stable identity/count/save bookkeeping as an `ADAPT`. |
| Sentien's persistent laser helper is switched off but not freed at death/gib. | `FIX` entity leak while preserving the beam shutdown event. |
| ZBoss one-shot marker can be used without a live enemy, but the firing path dereferences the enemy unconditionally and the marker calls unvalidated targets. | D-025 implements exact live-boss/type/null validation and guarded marker consumption; live valid-marker behavior/free-reuse remains. |
| ZBoss attack interruption can overwrite its live hook pointer, and detonated plasma retains collision/touch through its blast visual. | D-025 generation-owns/cleans hooks and makes plasma contact terminal while preserving the visual; live lifecycle/save proof remains. |
| `DAMAGE_ARMORMOSTLY` has no known caller and can produce an invalid result. | Retain no ABI dependence; quarantine or correct before any new use. |
| Random timer target parsing and old `give` parsing use unchecked buffers. | `FIX` bounds while preserving accepted syntax and selection behavior. |
| FALLFLOAT ground/water state and rotating START_ON reset contain suspicious assignments. | Reproduce map scenarios and classify before rewriting physics. |
| Player death clears inventory before an old co-op key-preservation path can retain keys, and power-armor state is not fully cleared. | Use Rerelease co-op/key semantics only after parity/softlock tests; explicitly clear stale power state. |
| Ammo spawn flags add out-of-DM timed respawn/cap semantics; Pack omits Flares and no-ammo fallback ignores custom weapons. | Preserve placed-item behavior and Pack omission; integrate custom fallback through Rerelease selection. |
| Health pickup temporarily mutates the shared global item sound. | [D-040](compatibility/decisions.md#d-040--health-pickup-sound-concurrency) now selects the exact count-derived sound locally after explicit native noise, retains native maps, and never writes shared item metadata. Static 447-placement/interleaving contracts pass; live simultaneous/custom-count proof remains. |
| `target_explosion` flag 1 is named EMP-style but is only an A2K-like cosmetic explosion; it still applies ordinary damage/targets. | Preserve cosmetic-only semantics; do not create an EMP field. |
| The 1.1 readme describes `use weapon 0`–`9`, but the DLL accepts 1–10 and the updated config binds key 0 to `use weapon 10`. | Treat source plus shipped config (1–10) as authoritative; document the readme error. |
| `ZDM_ZAERO_ITEMS` bit name reads opposite to its effect. | [D-045](compatibility/decisions.md#d-045--zdmflags-and-deathmatch-item-injection) preserves external values 0–3 and replaces the executable symbol with `ZAERO_DMFLAG_DISABLE_ITEM_INJECTION`; source/BSP/contracts plus historical legacy-v1 `q2dm1` counts record the inversion, while a v2 rerun and live server-info query/config persistence/dedicated proof remain. |
| Mirror-level fields/system appear dormant. | Preserve parsing/save ABI and compatibility no-ops; do not invent missing gameplay. |
| Some original levels exceeded old sound limits. | `ADAPT` to native Rerelease indexing; absence of missing audio is intended. |
| Original `default.cfg` unbinds all controls. | `ADAPT` into an explicit, non-destructive `zaero.cfg`. |
| A `ztomb1` transition names an absent `tomb1`. | D-011 preserves the sole unreferenced/missing changelevel as an inert artifact; generated 30/29/1 closure and use-only dispatch tests prohibit a silent rewrite or alias. |
| `VisorCopy` is a solid, non-damageable duplicate overlapping the still-solid player and may absorb traces. | D-021's identity-locked source/link audit proves equal-hit ownership changes when a mover relinks the frozen player. Use a tested `FIX`: keep the real player solid/vulnerable and make only the visual copy non-solid; live attacker/projectile/mover verification remains. |
| Picking up a dropped Visor can add its remaining time to a partially consumed Visor and exceed the nominal 30 seconds (`300` legacy frames = `1,200` target ticks, represented as a duration). | Typed carrier/drop fields now preserve exact fresh/equality/partial/stacked/reset arithmetic and native grant/death/co-op integration under static tests; retain `PARITY` pending live pickup/drop/active/save captures. |
| `M_ReactToDamage` can choose the reacting monster itself through `attacker->enemy`. | [D-041](compatibility/decisions.md#d-041--zaero-monster-damage-reaction-and-self-target-safety) preserves normal player/Autocannon/`mteam`/sound/buddy paths atop native lifecycle and keeps the Rerelease self guard as a tested `FIX`; live combat/save proof remains. |
| Hover fly-strafe timeout compares with `AS_STRAIGHT` instead of assigning it. | [D-042](compatibility/decisions.md#d-042--hover-fly-strafe-and-expired-state-reset) retains the radial movement and strict deadline but explicitly clears the dedicated state on expiry, collision, or invalid lifecycle as Q-013 `FIX`; live 40 Hz/collision/save proof remains. |
| `SV_Physics_Step` omits the post-`G_TouchTriggers` `inuse` guard. | [D-035](compatibility/decisions.md#d-035--step-physics-trigger-free-lifetime-safety) retains the native guard and equivalent FallFloat guards under static order tests; live ordinary/free/free-reuse fixtures remain. |
| `SV_FlyMove` removes duplicate-plane suppression globally. | [D-044](compatibility/decisions.md#d-044--global-sv_flymove-duplicate-plane-delta) classifies the exact one-condition removal as source-age drift. Seven identity-locked float32 goldens show its only legacy difference is a repeated-plane residual dead-stop; retain the shared Rerelease 0.99 near-duplicate/1.01 overclip solver and require live caller-isolation clips. |
| Shared projectile dodge throttles Rocket/BFG/Flare but deliberately not Blaster. | [D-033](compatibility/decisions.md#d-033--projectile-dodge-timing-and-rerelease-coexistence) preserves the firing-time trace, both typed skill windows, exact hooks and stock isolation under static tests; live seeded cadence and mid-window save proof remain. |

Add every discovered defect to `docs/compatibility/quirks.md` with evidence,
retail comparison if available, decision, owner, and regression test.

## 7. Content and asset audit

### 7.1 Original package layers

The legacy installation uses last-package-wins precedence:

| Layer | Bytes | Entries | SHA-256 |
| --- | ---: | ---: | --- |
| `pak0.pak` | 95,910,332 | 958 | `1de0161318cb946dbaad1ad6ac9abe375d3aa1da57f3571fdee3e5549cb0fafd` |
| `pak1.pak` | 4,931 | 1 | `3806e4cc59564e5a081518adf04fc608d79159b1e31d073b6699f0a3a34b4973` |
| `pak2.pak` | 12,001,303 | 12 | `e0b043599386f5b39701919f334de37d21011dd254630e17504dece497fec82e` |

`pak1` updates `default.cfg`. `pak2` adds the six deathmatch maps and updates
`maps.lst`; those two names are the only overridden PAK paths. Resolve package
precedence before importing into an ignored `.install/imported/` working tree,
and keep an origin/layer column in the importer manifest. Tracked `pack/`
contains only redistributable project-owned runtime definitions while D-003
remains open, including text-only Rerelease `.mat` material descriptors.
Generated `_glow.png` maps are derived from local Zaero pixels, so they remain
ignored import-owned output. The effective legacy PAK view contains 969 unique
paths before generated local derivatives.

[D-047](compatibility/decisions.md#d-047--legacy-pak-layer-to-runtime-ownership-semantics)
defines the output contract: preserving `pak0 < pak1 < pak2` means preserving
the source-layer audit and each final effective byte/path, not necessarily
shipping three copied commercial PAKs. A local import may therefore collapse
the already-resolved legacy effective view into an import-owned `pak1.pak`
beside a project-owned `pak0.pak`, but only with deterministic source-origin
records, explicit project/import collision policy, exact `default.cfg` and
`maps.lst` override tests, loose-file precedence tests, and fail-closed
cross-layer case/reference validation. The current installer/package records
the physical project/import/generated layers, compares the complete staged
import byte set against the importer manifest, and rejects direct member/loose
and file/directory-prefix collisions. Source-override, engine loose-precedence,
cross-layer reference, and lifecycle proofs remain. The checked-in audit test
locks the exact `default.cfg` and `maps.lst` source winners before their distinct
Rerelease handling. SYS-016 is not verified.

`pak0` includes:

- 548 WAL textures, grouped mainly under `z1`–`z4`;
- 161 WAV sounds;
- 119 PCX images, 46 TGA images, and 60 skybox images;
- 57 MD2 models;
- 14 campaign BSPs;
- the `elogo.cin` and `zlogo.cin` videos;
- configuration/map-list files; and
- four legacy demos, four legacy save files, and sixteen screenshots.

`pak2` contributes six deathmatch BSPs, four WAL textures, one WAV sound, and
the updated map list.

### 7.2 Required loose files

The installation deliberately leaves nine runtime files outside the PAKs. The
original documentation says the plasma sprites are loose for programming
reasons, so packaging must test both loose and packed behavior before changing
that arrangement:

| Directory | Files |
| --- | --- |
| `sprites/` | `plasma1.sp2`, `plasma1_0.pcx`–`plasma1_3.pcx`, `plasmashield.sp2`, `plasmashield_0.pcx` |
| `video/` | `intro.cin` (49,817,132 bytes), `outro.cin` (16,606,854 bytes) |

The two large videos are especially important to installation size, Git hosting,
and release testing. Keep them in the manifest even if the selected release
format leaves them loose next to the generated PAK.

### 7.3 Content taxonomy

The asset tree contains Zaero-specific:

- item models for custom ammunition, keys, Plasma Shield, and Visor;
- monster models for ZBoss, Handler/Hound, and Sentien;
- object models for autocannons, cameras, communications dish, crates, IRED,
  seats, shrapnel, wall/barrier effects, explosions, and flares;
- custom first- and third-person weapon models;
- monster, item, weapon, autocannon, and extensive world/voice sound sets;
- four major texture families (`z1`, `z2`, `z3`, `z4`), tool textures, skies,
  HUD/icons, cinematics, victory art, and map media.

No original `.map` source files were found in the supplied PAKs; the authoritative
levels are the 20 BSPs. Editor definitions support new/community work. Do not
silently decompile and treat reconstructed map source as original or use a
recompile as the 1.0 compatibility baseline.

The checked-in baseline inventory is `docs/audits/assets.json` (with a reviewed
Markdown rendering), while every local import produces a deterministic JSON
manifest. The future sole reviewed per-path policy overlay is
`docs/provenance/asset-policy.json`, keyed by normalized path or a narrowly
defined category rule. It does not exist at this audit checkpoint and is an
explicit Phase 2/provenance gate; no prose or distribution-policy record may be
treated as its substitute. Together, the release-time manifest and that overlay
must carry at least:

`runtime_path`, `source_container`, `source_path`, `source_sha256`,
`effective_sha256`, `size`, `category`, `references`, `license_status`,
`shipping_status`, and `notes`. Exact-path rules override category defaults;
unmatched paths fail closed. A CSV rendering may be generated for review, but
must not become a second source of truth. Schema validation rejects duplicate,
orphaned, overbroad, expired, or evidence-free policy entries.

The validator must reject duplicate normalized paths, case-only collisions,
path traversal, missing references, unexpected overrides, invalid PAK limits,
and differences between the staged directory and the manifest.

### 7.4 What belongs in a canonical completed runtime

In an `asset-full` release—or after a local import—the completed runtime
contains:

- effective maps, models, skins, sprites, images, textures, sounds, skyboxes,
  and cinematic/victory media;
- the mode-specific generated PAK set (`pak0.pak` for cleared project data and,
  after importer completion, local import-owned `pak1.pak`) plus any files
  deliberately verified as loose;
- `zaerostart.cfg`, the episode `mapdb.json` contribution, credits/notices, and
  a release README;
- `game_x64.dll` and a separate optional symbols archive.

Do not copy into the runtime:

- `gamex86.dll` or `gamei386.so` from the legacy engine;
- installer/uninstaller metadata, icons, or machine-generated logs unless used
  deliberately by the new installer;
- the destructive original `default.cfg`;
- the destructive loose `autoexec`;
- legacy demos, saves, screenshots, or retail installer state;
- source PAKs, object files, PDBs, compiler intermediates, or nested release ZIPs.

Preserve the original readmes and changelog in a provenance/reference area when
redistribution rights permit it. Otherwise record their hashes and explain how a
developer with the original installation can inspect them.

Do not confuse that completed runtime with a public artifact while rights gates
are open. The only possible public artifact is whichever tools-only/importer-kit
mode Section 11.2 proves eligible. Neither contains Zaero media; the importer
kit contains a DLL only after project-code distribution is cleared and becomes
locally playable only after the user supplies and imports a legitimate Zaero
installation. A tools-only artifact contains independently cleared tool source,
but neither the DLL nor gameplay/Zaero-derived source, and remains a non-playable
acquisition/validation artifact unless the user obtains gameplay code through a
separate lawful path.

### 7.5 Provenance and public-distribution basis

The Quake II Rerelease game DLL is GPL-2.0 software, and Zaero's original team
released both the Zaero game source and its assets under the GPL. All the
foundational inputs are therefore GPL, and ZaeREo redistributes them under the
GPL. To keep the distribution clean:

1. preserve each input's copyright notices and the original authors' credits;
2. record every third-party component and its license in
   `THIRD_PARTY_NOTICES.md`;
3. keep the overall project under a compatible GPL license (GPL-2.0);
4. publish `LICENSE`, `THIRD_PARTY_NOTICES.md`, and
   `docs/provenance/ASSET_SOURCES.md`; and
5. ship complete corresponding source with any released DLL (this repository).

Represent the result in `docs/provenance/distribution-policy.json`, not by
scraping prose. It is distinct from the per-runtime-path media overlay
`asset-policy.json` and has a versioned schema (initially
`zaereo.distribution-policy/v1`), policy ID/revision, review timestamp, and
records for:

- components: stable ID, kind (`tool`, `substrate-source`, `zaero-code`,
  `media`, `definition`, or `dependency`), exact paths or narrow globs, holder,
  SPDX expression/no-grant status, distribution status (`unknown`, `denied`,
  `permitted`), evidence references, reviewer, jurisdiction/scope, and
  expiry/revisit condition;
- channels: public Git tree/history/source archives, Actions logs/artifacts/
  caches, release assets, corresponding-source bundles, and editor gamepacks,
  each with an explicit status and component coverage; and
- modes/profiles: exact component and per-file allowlists, required policy
  predicates, prohibited content, permitted channels, and whether the result is
  playable or stable-eligible.

The top-level `code_distribution_permitted` and
`media_distribution_permitted` values are validated summaries of the covered
component records, not overrides; both derive to `true` from the GPL component
decisions. `public_distribution_enabled` stays `false` until a maintainer turns
on a validated release, so publishing is always a deliberate human step.
`release_readiness.py`, the packager, workflows, and publisher consume this JSON
schema directly.

There are three public capability states plus one private mode: the primary
`asset-full` artifact bundles the DLL with the ported Zaero content; an
`importer-kit` ships the DLL and rebuilds the content pack from a user's own
installation for users who prefer that; a `tools-only` kit ships just the
automation; and `local-full` is developer-only. `local-full` stays out of
release channels because it is unvalidated developer scratch, not for any rights
reason. The remaining gate on a public build is engineering readiness plus human
approval, not a rights clearance.

Artifact contents are not the only publication surface. A GitHub tag/release
also exposes repository history and automatic source archives; Actions can
retain source-bearing caches, logs, DLLs, and packages. All of that is GPL and
may be public — keep the notices and credits attached. When a release ships a
DLL, that exact binary release also supplies or durably links the GPL-2.0
corresponding source and complete notices for the covered target code, which is
straightforward because this repository *is* that corresponding source.

The one input the project does not redistribute is the Quake II Rerelease
soundtrack and base game data: those are Nightdive/id commercial content, not
GPL Zaero assets, so ZaeREo relies on the user's own Rerelease installation for
them (see §7.3 and D-010) and never copies them into its output.

## 8. Mapping to Quake II Rerelease

### 8.1 Baseline strategy

Import a pinned, clean Rerelease DLL source baseline into `src/` and commit a
machine-readable baseline record before Zaero changes. Keep the stock, Xatrix,
Rogue, CTF, bot, and cgame support intact. Zaero is an additional game-content
layer, not a replacement for Rerelease architecture.

Use small integration seams, following the already established
`g_zaero_*` naming convention rather than creating a second `z_*` family:

- conceptual `src/zaero/g_zaero_items.cpp` and `g_zaero_weapons.cpp` modules for
  owned item/weapon logic, split into focused files such as the current
  `g_zaero_sniper.cpp`, `g_zaero_sonic.cpp`, and `g_zaero_emp.cpp` as they grow;
- `src/zaero/g_zaero_entities.cpp` and focused entity modules;
- one module per substantial monster/defence;
- `g_zaero_ai.cpp` and `g_zaero_physics.cpp` only for genuinely shared custom
  behavior;
- `g_zaero_compat.cpp` for no-ops, aliases, legacy-field parsing, and quirks;
- `g_zaero_cgame.cpp` or narrow cgame changes for Zaero presentation;
- minimal registration hooks in upstream spawn, item, save, and export tables.

Do not create a parallel second copy of core combat, physics, or client code.
Where Zaero changes a shared invariant, add a narrow hook or typed helper and
keep the upstream path as its default.

Maintain `docs/UPSTREAM.md` as the operational sync contract. It records the
official repository URL and commit (or explicitly identified archive plus tree
hash while D-002 is open), import date, API/data-build compatibility, pristine
reference location, applied layout/build-only transformations, local patch
inventory by integration seam, and licenses/notices. “Pinned” may be used only
after that identity is verified; until then the accurate term is
“hash-recorded supplied substrate.”

An upstream refresh occurs in an isolated branch/worktree: acquire and verify
the new pristine tree, regenerate the baseline diff and project-source list,
reapply the smallest Zaero seams, review every conflict and API/enum/limit/save
change, then run Debug/Release/export, stock/base/Xatrix/Rogue/CTF/bot, all
Zaero static and private runtime, save migration, packaging, and editor/mapdb
tests. Update the baseline record, `UPSTREAM.md`, decisions, notices, and
changelog together. Never overwrite `src/` from a moving archive or accept a
large generated diff without classifying it.

### 8.2 Mandatory mechanical translations

| Legacy assumption | Rerelease implementation requirement |
| --- | --- |
| 10 Hz server frames and integer `framenum` deadlines | Express time using `gtime_t` and duration literals. Preserve durations, not frame counts. Audit every custom think, animation, debounce, countdown, charge, timeout, and random interval. |
| Legacy monster move callbacks execute at 10 Hz | Use the Rerelease legacy-move throttling behavior where parity demands it; opt into high-tick behavior only with measured tests. Avoid making AI/projectiles four times faster. |
| C arrays, `vec3_t` helpers, and integer booleans | Port to the Rerelease C++ vector/format/string conventions without changing arithmetic order until golden tests pass. |
| Raw `gi.*index` calls and legacy resource ceilings | Use cached model/sound/image indexes and Rerelease limits. [D-043](compatibility/decisions.md#d-043--stock-monster-precache-extraction-and-sound-index-strategy) rejects the supplied-but-disabled global 256-sound interceptor in favor of native 2,048-index capacity and scoped cached precaches; verify referenced-index and audible closure on every map. |
| Pointer-oriented binary save tables | Register every custom think/use/touch/pain/die/blocked callback and every custom field with the Rerelease save macros/JSON serializer. The generated `audit_save_surface.py` inventory fails closed when a current Zaero-owned field or callback/mmove leaves that registration mechanism; still test live and dormant entities. |
| One local player's view/HUD | Make view state client-local, split-screen safe, and serialized. Route Visor, sniper zoom, help, timer, blend/static, boss/grapple state, and weapon display through appropriate game/cgame data. |
| Statusbar/inventory-only weapon selection | Add stable item/wheel IDs, wheel configstrings, icons, ammo and quantity metadata, and cgame UI while preserving `use weapon N` aliases. `audit_identifier_surface.py` must fail closed on append position, enum/value collision, item-ID/classname registry drift, compile-time bounds, and wheel capacity. |
| Old protocol/effect enums | Select Rerelease temp events, render effects, entity-event semantics, collision contents/masks, and multicast scopes explicitly. Verify visual intent rather than copying numeric values. |
| Single legacy content set | Avoid ID/classname conflicts with integrated base, Xatrix, Rogue, and CTF content. Reuse native facilities only when behavior and saves remain Zaero-compatible. |
| Engine-owned info strings and client slots | Use Rerelease info-key, client-index, entity-instance, and split-screen APIs; never assume one client per connection or index zero. |

### 8.3 System mapping checklist

#### Spawn and map parsing

- Register every exact Zaero classname and alias.
- Extend the typed spawn-field table for `spawnflags2`, `active`, `mangle`,
  `mteam`, and retained mirror keys.
- Apply single/co-op filters before spawn while preserving ordinary
  `spawnflags` filtering.
- Include custom entities in inhibited/spawn counts and save restoration.
- Generate editor definitions from the same registration metadata where
  possible.

Keep two orthogonal scopes rather than one global `level.is_zaero` switch:

1. **Zaero gameplay/content active** means the `zaereo` game module may register
   and run its items, weapons, damage types, HUD, EMP hooks, and DM injection on
   stock/community maps.
2. **Zaero mapper-contract semantics** alone enables conflicting interpretations
   of stock classnames/keys/flags (platform/train/push/door/barrel/Viper, for
   example) and any reviewed behavior that is intrinsically a supplied-map
   contract: stock projectile dodge/audio/ammo ordering, Hover dodge wiring,
   stock-actor obituary prose, and the `zboss` entry/finale handoff. Native
   meanings remain the default on every other map. Custom Zaero entities/items
   remain content-active without enabling those native-map adaptations.

The target mapper classifier accepts the audited shipped BSP identity set
(canonical name plus full BSP hash), an explicit documented worldspawn/mapdb
opt-in for community or remastered maps, and only conservative signatures based
on unambiguous Zaero-specific evidence. It never infers compatibility merely
from a conflicting stock flag. The current DLL implementation has no resolved
file-read API, so it must not claim the full-BSP check: it matches canonical
retail names only alongside the audited SHA-256 of the exact entity string that
`SpawnEntities` received, or uses an unambiguous Zaero-owned classname
signature. A canonical name alone is rejected. The full BSP SHA-256 remains in
the generated audit and requires an engine extension before it can be enforced
at runtime. The presently implemented exact worldspawn key is the
case-sensitive `"zaero_mapper_contract" "1"`; `"0"` explicitly opts out and a
duplicate or malformed key fails closed. MapDB opt-in, diagnostic overrides,
and reviewed remaster-hash enrollment remain open work.

Record the map name, observable entity-string identity, and classification
reason (`shipped-entity-lump`, `explicit-metadata`, `signature`, or
`explicit-metadata-disabled`) in logs and level-save state; loading rejects a
mismatched or pre-classifier save rather than silently changing mapper meaning.
Fixtures cover the generated 20-map entity identity manifest and save fields;
still add runtime classifier fixtures for same-name/wrong-BSP, stock/base/
Xatrix/Rogue/ambiguous-community maps, explicit metadata, and save/load. A
stock DM injection fixture must prove custom items function while native mover
flags remain native. D-018 owns the full-hash API, remaining override policy,
and MapDB/remastered enrollment closure.

#### Items and weapons

- Allocate stable internal item IDs; do not depend on accidental source order.
- Register models, pickup/use/drop callbacks, ammo types, maxima, wheel data,
  icons, descriptions, precaches, and default ownership.
- Translate each weapon's timing and animation with Rerelease helpers such as
  weapon animation time/gun-rate handling.
- Audit prediction, recoil, muzzle origin, handedness, view model, death/respawn,
  infinite-ammo modes, Quad/Double interactions, and expansion modifiers.
- Treat A2K, EMP, IRED, Visor, and Shield as persistent state machines rather
  than one-shot functions.
- The old Zaero fork removed the ordinary `weapmodel`/VWep encoding and stock
  third-person weapon precaches, likely for vintage resource/protocol pressure.
  Keep Rerelease's remote-player weapon presentation for stock weapons and map
  each Zaero weapon to an available third-person model or a documented safe
  fallback; test other clients' views rather than copying the removal.

#### AI and monsters

- Convert move/frame tables without altering frame event order.
- Route move changes through `M_SetAnimation` rather than assigning legacy
  `currentmove` pointers directly.
- Register all move/endfunc/attack/pain/death callbacks for save serialization.
- Reconcile custom schooling/strafe logic with Rerelease AI flags and enhanced
  monster behavior; begin with Zaero-compatible defaults.
- Validate target acquisition in single player, co-op, split-screen, teams,
  notarget, invisibility, flashes, EMP, and scripted targets.
- Make composite entities and boss-owned hooks/projectiles robust across save,
  owner death, target death, disconnect, changelevel, and entity reuse.
- Preserve the Autocannon's original non-monster server classification unless a
  behavior test justifies changing it; add targeted bot threat metadata rather
  than casually setting `SVF_MONSTER`.

#### Physics and combat

- Add custom movement types through deliberate switch cases in movement,
  ground checking, pushers, collision, and save code.
- Preserve mass, friction, gravity, bounce, rider ownership, water, teleport,
  moving-platform, and world-boundary behavior.
- Give custom damage modes typed flags rather than colliding legacy integer bits.
- Confirm shield/barrier/sniper traces against Rerelease contents masks and
  expansion projectile behavior.

#### Presentation

- Decide which effects are authoritative game events and which belong in cgame.
- Define split-screen ownership for Visor view copies, zoom, blends, overlays,
  tracking text, mission help, inventory, and timer display.
- Retain readable fallback presentation when a player disables optional screen
  effects; do not base damage on a modern client preference without explicitly
  retaining the parity mode.
- Add localization keys for new item names/messages while keeping original
  English strings available for map compatibility.

#### Saves and transitions

- Serialize every added scalar, duration, entity handle, item reference, enum,
  move reference, callback, per-client view state, and level/global flag.
- Never serialize raw pointers to entities or static strings when a stable handle
  or identifier is required.
- Test saves before/after every unit boundary and during every complex system.
- Version Zaero save fields and provide clear failure for incompatible
  development saves; do not promise legacy binary-save import.

### 8.4 Behavior that Rerelease already supersedes

Do not port old-engine workarounds when the target already solves the constraint:

- low sound/model index ceilings;
- 10 Hz network/server mechanics;
- legacy demo and binary-save formats;
- vintage map-specific base-game hacks that are not used by Zaero maps;
- old platform DLL entry points and project files;
- duplicate stock/Xatrix/Rogue behavior already integrated in the Rerelease
  baseline.

The acceptance test is still behavior. For example, the correct result of
removing a sound-cache workaround is that all intended sounds play, not merely
that the code compiles.

### 8.5 Concrete Rerelease constraints found in the target source

- Preserve both exports: game API 2023 and cgame API 2022. Keep the Rerelease
  `PreInit`, JSON save, `CanSave`, `Pmove`, slot/social-ID, bot, `RunFrame`,
  `PrepFrame`, visibility, and shadow-data paths rather than restoring API 3.
- `gclient_t` and `edict_t` have engine-visible prefixes guarded by integrity
  checks. Add Zaero-private fields only after those prefixes and include them in
  the correct game/level/client/edict JSON schema.
- Map legacy `game.serverflags` progression data to Rerelease
  `game.cross_level_flags`. Do not reuse the engine-facing
  `globals.server_flags`, which now carries loading/intermission status.
- Save callback names are global identifiers. Use Zaero-prefixed names and the
  Rerelease `THINK`/`TOUCH`/`USE`/`PAIN`/`DIE`/monster/mmove declaration
  wrappers; duplicate names across translation units make save initialization
  fail.
- The thin cgame API handles HUD/layout/wheel/configstrings/centerprint and
  muzzle offsets, but does not expose arbitrary new protocol temp-event parsers.
  Prefer existing supported events, render entities, and layouts. Any truly new
  protocol effect would require a separately scoped engine change.
- Zaero used HUD stats 16–21, which collide with Rerelease/CTF assignments.
  Reserve verified free shared stats (initial audit suggests 54–59), add
  compile-time bounds/collision checks, and replace hard-coded Visor layout
  numbers with named constants.
- The item list is capped at 256 and each weapon/ammo/powerup wheel at 32.
  The generated `audit_identifier_surface.py` report now proves the current
  append-only item/ammo/powerup/MOD/stat/configstring and AI-bit ranges,
  independent `spawnflags2`, the explicit intentionally-colliding mapper-flag
  inventory, native replacements for legacy protocol identifiers, registry
  classnames, current 17-ammo/24-weapon/25-powerup wheel counts, and static
  bounds; compiled stock/expansion and live UI validation remain required.
- Item saves use classnames. Treat those strings as stable save identifiers even
  when internal numeric item IDs change.
- Rerelease may deny ordinary saves while dead or in intermission. Decide and
  test whether active Visor/camera/boss-grapple states are saveable; if they are,
  they must round-trip completely rather than being cancelled implicitly.
- Rerelease reserves ordinary spawnflag bits for co-op filtering. Keep Zaero
  `spawnflags2` in its own typed field and apply its historic filters separately.
- Default Rerelease co-op behavior includes squad respawn, instanced items, and
  different player collision. These can alter keys, puzzles, drops, and item
  availability. Establish tested ZaeREo defaults or document intentional native
  behavior instead of accepting defaults accidentally.
- Co-op slot restoration uses social IDs, and item visibility uses Rerelease
  instancing/visibility state. Extend these paths; do not replace them with
  legacy client or key-pickup code.
- Mark appropriate Zaero missiles, flares, mines, shrapnel, and hooks with the
  native projectile/trap flags and masks so `PROJECTILECLIP`, bots, and collision
  behave correctly.
- Beam linkage no longer populates `old_origin` automatically. Set endpoints
  explicitly for IRED/laser/boss effects.
- Translate legacy `RF_FRAMELERP` intent to the renamed Rerelease
  `RF_NO_ORIGIN_LERP` semantics deliberately, especially for Hound movement.
- Start new monsters with legacy/path-corner navigation behavior and tested
  fallback when navigation is absent. Native pathfinding and bot awareness are
  later, individually gated enhancements.
- The Visual Studio project uses an explicit source list. Every new source/header
  must be added to both the project and filters, with a CI check that no intended
  module is omitted.
- Quarantine `z_mtest` and its raw file-loading behavior as development-only;
  the Rerelease import surface does not provide a matching arbitrary VFS/file
  interface for release code.
- Replace raw static resource-index integers with
  `cached_soundindex`/`cached_modelindex`/`cached_imageindex`. Rerelease clears
  and restores these around map spawn/load; copying Zaero's raw globals would
  create stale indexes after JSON load.
- Apply API conversions intentionally: use `traceline` for zero-extents traces,
  pass portal/filter/reliability/duplicate-key arguments where required, use
  `WriteEntity` rather than hand-written entity shorts, and retain the engine's
  UTF-8/split-screen Info functions.
- Use the native monster muzzle-flash helper for Autocannon/ZBoss where it
  expresses the same event; it selects the correct service message and supports
  extended flash IDs.
- Keep game/level/client/edict save-schema structures standard-layout and
  trivially managed. Do not embed arbitrary `std::string`/`std::vector` members
  into memory that is tag-allocated, zeroed, or schema-serialized; use supported
  fixed/tag-owned/savable representations.
- Dynamic cgame layout messages remain tightly bounded even though the static
  statusbar has more space. Individual configstrings are 96 bytes and the
  dynamic layout passed to cgame is 1,024 bytes. Bound and escape Visor/camera
  target text, and test long/map-authored messages and 16-bit inventory wire
  quantities.
- Harden save initialization early: duplicate serialized callback/mmove names
  must produce a safe diagnostic even before strict-save cvars are available.
  Whole-file legacy imports make such collisions particularly likely.
- Adapt callbacks at typed boundaries: Rerelease touch, pain/death MOD, and
  dodge signatures carry additional/typed context. Never silence mismatches by
  casting old function pointers.

Rerelease's monster cadence deserves a dedicated audit: animation frame
callbacks advance at a legacy-like 10 Hz, but each frame's AI function can be
invoked on all 40 Hz ticks while only movement distance is scaled. Zaero's Hound
schooling functions perform target scans, random decisions, speed decay, list
rebuilds, and animation changes inside those AI functions. A direct port would
run those side effects four times too often. Split each custom frame function
into a cadence-gated decision update and a high-tick movement path/cache; audit
every non-stock Zaero frame function individually. Enabling a generic
high-tick-rate AI flag is not a substitute.

The finale also has presentation logic outside the entity table. Leaving
`zboss` starts a five-second white fade in the supplied code; the Rerelease's
ordinary changelevel fade is shorter and black. Reproduce the Zaero white fade
explicitly and test its timing, save/intermission lockout, cinematic handoff,
and split-screen presentation. The old `fact1` secret-level special case is
base-game source drift and should stay on the audit list, but it is not a Zaero
map requirement unless the project later promises general legacy-map behavior.

## 9. Repository architecture and target tree

### 9.1 Present and planned target tree

~~~text
ZaeREo/
├── .github/
│   ├── CODEOWNERS
│   ├── dependabot.yml
│   ├── ISSUE_TEMPLATE/
│   ├── pull_request_template.md
│   └── workflows/
│       ├── ci-windows.yml
│       ├── nightly-windows.yml
│       ├── package-windows.yml
│       └── release-windows.yml
├── .vscode/
│   ├── extensions.json
│   ├── launch.json              # launches run_game.ps1; never a direct game target
│   └── tasks.json
├── .install/                     # generated developer stage, ignored
├── build/                        # generated compiler output, ignored
├── dist/                         # generated releases, ignored
├── docs/
│   ├── ZAERO_PORT_ROADMAP.md
│   ├── UPSTREAM.md
│   ├── audits/                   # normalized generated audit reports
│   ├── compatibility/
│   │   ├── decisions.md
│   │   ├── entity-matrix.md
│   │   ├── feature-matrix.md
│   │   ├── map-matrix.md
│   │   └── quirks.md
│   ├── provenance/
│   │   ├── ASSET_SOURCES.md
│   │   ├── asset-policy.json
│   │   ├── baselines.json
│   │   ├── dependency-policy.json
│   │   ├── distribution-policy.json
│   │   ├── release-surface-policy.json
│   │   ├── upstream-integration-policy.json
│   │   ├── upstream-match.json
│   │   └── schemas/
│   │       ├── README.md
│   │       ├── asset-policy.schema.json
│   │       ├── dependency-policy.schema.json
│   │       ├── distribution-policy.schema.json
│   │       ├── import-ownership.schema.json
│   │       ├── install-ownership.schema.json
│   │       ├── local-config.schema.json
│   │       ├── release-manifest.schema.json
│   │       ├── release-readiness.schema.json
│   │       ├── runtime-smoke.schema.json
│   │       └── spdx-schema-2.3.json
│   └── release-readme.html
├── editor/
│   ├── entities.json             # generator source of truth
│   ├── common/
│   ├── netradiant-custom/
│   ├── trenchbroom/
│   └── README.md
├── pack/                         # redistributable runtime source only
│   ├── README.md
│   ├── mapdb.json               # Zaero fragment input; never active full DB
│   ├── zaero.cfg
│   └── zaerostart.cfg
├── references/                   # manifests/docs; licensed source only
├── src/
│   ├── zaero/
│   ├── bots/ ctf/ rogue/ xatrix/
│   ├── game.sln
│   └── game.vcxproj
├── tests/
│   ├── audit/
│   ├── build/
│   ├── compatibility/
│   ├── content/
│   ├── editor/
│   ├── fixtures/
│   ├── release/
│   └── runtime/                  # live harness/fixtures as they are added
├── tools/
│   ├── audit_assets.py
│   ├── audit_bsp_entities.py
│   ├── audit_common.py
│   ├── audit_dm_injection.py
│   ├── audit_flymove.py
│   ├── audit_release_surfaces.py
│   ├── audit_repository.py
│   ├── audit_identifier_surface.py
│   ├── audit_save_surface.py
│   ├── audit_source_delta.py
│   ├── audit_stock_precaches.py
│   ├── audit_traceability.py
│   ├── audit_upstream_integration.py
│   ├── audit_visor_trace_order.py
│   ├── bootstrap.ps1
│   ├── build_game.ps1
│   ├── check_project_sources.py
│   ├── complete_importer_kit.ps1
│   ├── collect_licenses.py
│   ├── create_evidence_snapshot.py
│   ├── generate_editor_defs.py
│   ├── generate_sbom.py
│   ├── generate_version.py
│   ├── import_legacy_assets.py
│   ├── identify_upstream.py
│   ├── install_dev.ps1
│   ├── make_dm_runtime_fixture.py
│   ├── make_pak.py
│   ├── make_release_zip.py
│   ├── manage_install.ps1
│   ├── merge_mapdb.py
│   ├── package_windows.ps1
│   ├── publish_github_release.ps1
│   ├── release_readiness.py
│   ├── release_manifest.py
│   ├── render_release_readme.py
│   ├── run_game.ps1
│   ├── run_runtime_matrix.ps1
│   ├── runtime-scenarios.json
│   ├── validate_distribution_policy.py
│   ├── validate_runtime.py
│   ├── verify_binary.ps1
│   └── zaereo_paths.ps1
├── .editorconfig
├── .gitattributes
├── .gitignore
├── .zaereo.local.example.json   # path-only template; local copy is ignored
├── AGENTS.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── LICENSE_SCOPE.md             # path/component scope; no implied Zaero grant
├── README.md
├── SECURITY.md
├── THIRD_PARTY_NOTICES.md
├── VERSION
└── vcpkg.json
~~~

This is the target contract, not a claim that every entry exists today. The
repository/editor/VS Code scaffold, official upstream match, current-integration
classification, distribution and local-config schemas, path resolver, audit
snapshot, and remote containment now exist. Notable planned gaps include the
reviewed path-level `asset-policy.json`, package/import/readiness schemas,
version generation, live verification of the config-driven wrapper and
runtime matrix, the install manager, release-readiness/README rendering, and the live
runtime suite. Each gap is assigned below to the relevant feature phase or the
Phase-9 release gate; an empty or unverified placeholder does not close it.

Every machine-consumed policy/config/ownership/release record declares its
schema ID and version and validates before use. Schemas are authored, reviewed
files; incompatible changes take a new major/schema ID with an explicit
migration and backward-read policy. Tests reject unknown major versions,
ambiguous duplicate keys, unrecognized policy fields where fail-closed behavior
is required, and a producer/consumer version mismatch. A Markdown example is
never the schema.

Keep generated builds, imported commercial content, and installations outside
tracked `pack/`. `pack/` is the redistributable source-controlled contribution;
`.install/imported/` is a disposable private import, `.install/zaereo/` is a
managed developer stage, and `dist/` contains generated release archives and
checksums. A future rights-cleared asset-source layout must be introduced by a
recorded D-003/D-004 decision rather than silently changing this boundary.

### 9.2 Required root-file contracts

#### `AGENTS.md`

The tracked file must tell human and automated contributors:

- project intent and the compatibility priority order;
- authoritative input paths are developer-specific and must never be hardcoded
  into committed build logic;
- how to bootstrap, build, validate, stage, and run;
- that Rerelease-native ports are required instead of wholesale legacy-file
  replacement;
- how to classify `PARITY`, `ADAPT`, and `FIX` decisions;
- that all new callbacks/fields need save registration and round-trip tests;
- that all timing is duration-based and must be checked at 40 Hz;
- that exact map classnames/keys and original case-sensitive runtime paths are
  compatibility interfaces;
- how assets, provenance, Git LFS, generated PAKs, and licensed references are
  handled;
- which generated directories must not be edited or committed;
- required focused and full validation before completion;
- that every repository-provided launch configuration invokes the windowed
  `tools/run_game.ps1` verifier rather than launching the game directly;
- rules for updating the feature/entity/map/quirk matrices with code changes;
- safe Git practices in a shared/dirty worktree; and
- scope boundaries for remastering/maps plus code, media, repository/source,
  Actions, and release publication channels.

Keep the file operational and short enough to be read every session. Detailed
feature lore belongs in `docs/compatibility/` and is linked from `AGENTS.md`.

#### `README.md`

The README is the public landing page, not a second roadmap. It needs:

- a one-paragraph description and explicit unofficial-project attribution;
- current status with the newest playable milestone and known blockers;
- compatibility/support table;
- legal/provenance summary and asset-acquisition mode;
- end-user install, launch, start-episode, update, and uninstall steps;
- developer prerequisites and the shortest build/test loop;
- repository layout;
- release/download and checksum guidance;
- issue-report instructions that request map, skill/mode, save, and logs;
- credits, upstream links, license, and trademark disclaimer.

Never claim full compatibility in the README until the release gates in this
roadmap pass.

#### `.gitignore`

Ignore at least:

- Visual Studio (`.vs/`, `x64/`, `src/x64/`, objects, libraries, DLLs, PDBs,
  ILKs, executables, user files);
- vcpkg (`vcpkg_installed/` and local downloads/buildtrees if present);
- `build/`, `.install/`, and `dist/`;
- Python virtual environments, `__pycache__`, pytest/mypy caches;
- generated PAK/ZIP/checksum/staging files and audit scratch output;
- `.zaereo.local.json` and any local path/launch overrides;
- editor logs, map compiler `.prt/.lin` output, crash dumps, and runtime saves.

Keep `.vscode/tasks.json`, `launch.json`, and `extensions.json` tracked while
ignoring other personal editor state. Launch configurations call the repository
windowed verifier and contain no personal paths; a shared direct-game debugger
is prohibited because it cannot establish the native-window safety result. Do
not ignore source assets or committed audit reports.

#### `.gitattributes`

- normalize text intentionally (LF is recommended for code/config/Markdown;
  preserve CRLF only for scripts proven to require it);
- mark binary formats as binary;
- use Git LFS for committed large binary source assets such as BSP, CIN, MD2,
  WAV, WAL, PCX, TGA, and SP2, after confirming the hosting policy;
- never place a generated PAK in LFS merely to avoid designing a reproducible
  build; and
- keep diff/merge rules explicit for JSON, project files, and manifests.

Track a matching `.editorconfig` for charset, final newline, indentation, and
line-ending defaults across C++, Python, PowerShell, JSON, YAML, XML/project,
and Markdown files. Formatters may make mechanical changes only in focused
commits; imported upstream/source evidence is excluded unless deliberately
normalized and rehashed.

#### Contribution, security, and ownership files

- `CONTRIBUTING.md` defines setup, small-change workflow, compatibility evidence,
  test expectations, generated-file updates, commit/PR conventions, and how to
  propose a quirk fix or remaster.
- `SECURITY.md` lists supported releases and a private vulnerability-reporting
  route. Treat PAK/BSP/import paths and release extraction as untrusted input:
  reject traversal, oversized/overlapping directories, malformed offsets, and
  symlink escapes.
- `CODEOWNERS` may require review for save schema, game/cgame ABI, packaging,
  provenance/licenses, and stable workflows.
- Dependency automation may update actions and tool libraries, but vcpkg/Python/
  action baseline changes must run the full build/audit suite rather than merge
  solely because a bot opened them.

#### License, notices, and versioning

- Preserve the Rerelease GPL-2.0 notices and do not casually copy REBLIVION's
  different licensing choice.
- The project code license is GPL-2.0, matching both the Rerelease substrate
  and the GPL-released Zaero source.
- The root `LICENSE` is the GPL-2.0 text that covers the whole project,
  including the GPL-released Zaero additions and the Rerelease substrate.
  `LICENSE_SCOPE.md` maps the per-component licenses (all GPL/MIT) to
  paths/components; update it with D-003 when a component's license changes.
- Put media/source-specific notices plus harvested runtime dependency notices
  (including statically linked `fmt` and `jsoncpp`, applicable compiler runtime,
  and packaged tools) in `THIRD_PARTY_NOTICES.md` and the SBOM.
- Make `VERSION` the single authored source for package and DLL display version.
  Generate build metadata/display constants from it; keep the stable engine game
  identifier `zaereo` separate from the release version. Validate the vcpkg
  manifest version, archive/tag, internal/external manifests, HTML README,
  changelog section, and DLL-reported display version against `VERSION`.
- Use SemVer once public compatibility promises begin; pre-1.0 milestones may
  use `0.x.y`.
- Keep user-visible behavior changes and compatibility decisions in
  `CHANGELOG.md`.

Release packaging renders `docs/release-readme.html` from a template with the
actual version, distribution mode, support status, readable save schemas, and
known limitations; a stable archive must not retain a “Development build”
banner. Release notes extract only the matching changelog section plus required
legal/known-issue text rather than attaching the entire changelog.

Current gap: `VERSION` is `0.1.0-dev.0`, the vcpkg manifest says
`0.1.0-dev`, runtime `GAMEVERSION` is only the stable product identifier, and
the HTML is permanently worded as a development build. Until generation and
the consistency test exist, package metadata must be treated as development
output rather than a release version claim.

Public documentation is part of the executable interface. Before Phase 0/1
closure, literal command/link tests must keep `README.md`, `AGENTS.md`,
`CONTRIBUTING.md`, `CHANGELOG.md`, `pack/README.md`, `ASSET_SOURCES.md`,
`THIRD_PARTY_NOTICES.md`, and the rendered release README aligned with scripts
and D-003. In particular: examples resolve vcpkg through the shared precedence,
use the canonical import
manifest, preview an explicit disposable/per-user destination, and never rely on
Steam-root discovery; contribution/release prose cannot suggest a public
gameplay push or guarded publisher while publication is disabled; provenance and
notices cover repository/source/CI channels through `distribution-policy.json`;
packaging prose does not claim the missing cross-layer PAK-member/loose check;
and the mode/version renderer emits only applicable completion/install-manager,
source/license-scope, ownership, and warning text. A command that no shipped
tool accepts, or a promised safety gate with no test, fails documentation CI.

### 9.3 REBLIVION patterns to reuse deliberately

The sibling project demonstrates a useful separation of `src`, `pack`,
`editor`, `docs`, `references`, `tools`, developer stage, and release output.
Reuse its practical ideas:

- PowerShell discovery of MSBuild through `vswhere`;
- pinned vcpkg dependencies;
- a single build wrapper used by local and automated flows;
- a separate disposable developer installation;
- a sorted Python PAK builder;
- mapdb plus start-configuration episode integration;
- VS Code tasks as conveniences over scripts, not an alternative build system;
- generated editor support for multiple editors;
- nightly packaging and a human-readable release README.

Strengthen those patterns for ZaeREo: keep the pristine upstream baseline
recorded, separate package from publish, make stable publication draft/explicit,
test deterministic ZIPs as well as PAKs, guard dirty trees and target paths,
mark nightlies as prereleases, add asset/provenance manifests, and make runtime
validation much deeper. Do not copy REBLIVION's license, full content database,
generated archives, or project-specific assets without an independent reason.

## 10. Developer environment and workflows

### 10.1 Supported first environment

The first reproducible target should match the available Rerelease project:

- Windows 10/11 x64;
- Git and Git LFS;
- Visual Studio 2022 or Build Tools with Desktop C++, MSBuild, and an explicitly
  pinned MSVC toolset and Windows SDK recorded in the toolchain/baseline
  documentation (do not leave `WindowsTargetPlatformVersion` floating for a
  release);
- PowerShell 7 where available (Windows PowerShell compatibility documented);
- Python 3.11+ for deterministic audits/PAK/editor generation;
- vcpkg manifest mode with pinned baseline and `fmt`/`jsoncpp` dependencies;
- a legally installed Quake II Rerelease for runtime tests; and
- for importer mode, a legitimate Zaero installation selected by parameter or
  environment variable.

The initial toolchain candidate observed on the audited machine is Visual
Studio 2022/MSBuild `17.14.23.42201`, v143 MSVC tools `14.44.35207` (compiler
`19.44.35222`), Windows SDK `10.0.26100.0`, PowerShell `7.5.8`, Python `3.11.3`,
Git `2.50.0.windows.1`, Git LFS `3.6.1`, and vcpkg
`2025-09-03-4580816534ed8fd9634ac83d46471440edd82dfe` with manifest baseline
`4334d8b4c8916018600212ab4dd4bbdc343065d1`. Phase 1 must certify and pin this
set or record a reviewed replacement; “latest installed” and mutable CI image
labels are not release pins.

Pin tool versions in documentation/CI. `tools/bootstrap.ps1` should discover
`vswhere`/MSBuild, verify Python/Git LFS/vcpkg, restore dependencies, and print
actionable errors. It must not modify global PATH, copy game assets into tracked
locations, or guess personal installation paths without confirmation.

All wrappers must use one tested path resolver. In particular, bootstrap accepts
an explicit `-VcpkgRoot`, then `VCPKG_ROOT`, then `vcpkgRoot` from the ignored
local JSON, then safe PATH/discovery—and returns/records the resolved path so
`build_game.ps1` consumes the same result. A bootstrap success followed by a
build failure because the two scripts chose different vcpkg roots is a release
blocking defect. CI records the Visual Studio image, MSVC, SDK, PowerShell,
Python, vcpkg commit, and dependency versions in build metadata.

Keep three content locations unambiguous. The target CLI/config/environment keys
are `-EngineRoot` / `q2RereleaseEngineRoot` /
`Q2RERELEASE_ENGINE_ROOT` for the read-only executable/data installation,
`-UserRoot` / `q2RereleaseUserRoot` / `Q2RERELEASE_USER_ROOT` for the writable
Nightdive user-data parent, and `-ZaeroLegacyRoot` / `zaeroLegacyRoot` /
`ZAERO_LEGACY_ROOT` for the retail Zaero input. `-GameRoot` remains only an
explicit disposable-development/portable override. During one documented
migration window, the current `q2RereleaseRoot` key may be accepted as an alias
for the engine root with a warning; it is never inferred to be writable, and an
absent user root still resolves to the per-user Saved Games default. Remove the
alias only with a config-schema version change and migration note.

Implemented Phase 1 foundation (2026-07-13): `bootstrap.ps1`,
`build_game.ps1`, and `install_dev.ps1` now share `tools/zaereo_paths.ps1` and
the versioned local-config schema. Focused tests cover argument, environment,
config, legacy-alias, and discovery precedence; bootstrap and build consume the
same resolved vcpkg root; and installer dry-run/live tests use the separated
engine/user roots. Steam discovery is read-only, never makes a program directory
writable, and an explicit portable `-GameRoot` remains the only supported
beside-`baseq2` override. Fresh-clone/CI certification and the broader runtime
matrix remain Phase 1 exit work.

Use that split with a documented path precedence for every script:

1. explicit command-line parameter;
2. the corresponding `Q2RERELEASE_ENGINE_ROOT`, `Q2RERELEASE_USER_ROOT`,
   `ZAERO_LEGACY_ROOT`, and `VCPKG_ROOT` variables;
3. ignored `.zaereo.local.json` based on the tracked example; then
4. safe read-only discovery with a clear printed result.

CI always supplies explicit values. Local configuration contains paths only,
never GitHub tokens or other secrets; publication uses `gh`'s credential store
or Actions' scoped token.

Linux/macOS game-DLL support can follow after the Windows baseline. Keep Python
audits and asset packaging cross-platform from the start.

### 10.2 Standard commands

The supported build/import loop is:

~~~powershell
./tools/bootstrap.ps1 -VcpkgRoot "C:\path\to\vcpkg"
python ./tools/import_legacy_assets.py --source "D:\Games\Zaero" --output .install/imported/zaereo --manifest .install/imported/zaereo-asset-manifest.json
./tools/build_game.ps1 -Configuration Debug -VcpkgRoot "C:\path\to\vcpkg"
./tools/verify_binary.ps1 -BinaryPath ./build/Debug/game_x64.dll
python ./tools/validate_runtime.py --root .install/imported/zaereo --manifest .install/imported/zaereo-asset-manifest.json --strict
./tools/install_dev.ps1 -EngineRoot "D:\Games\Quake II Rerelease" -UserRoot "D:\Disposable\Quake2User" -ContentRoot .install/imported/zaereo -AssetManifest .install/imported/zaereo-asset-manifest.json -Configuration Debug -WhatIf
# Inspect the preview, then repeat the preceding install command without -WhatIf.
./tools/run_game.ps1 -EngineRoot "D:\Games\Quake II Rerelease" -UserRoot "D:\Disposable\Quake2User" -Map q2dm1 -Deathmatch -ZdmFlags 0 -ProbeDeathmatchItems -ReportOutput .install/runtime-reports/q2dm1-zdmflags0-placement.json
./tools/run_runtime_matrix.ps1 -ScenarioFile ./tools/runtime-scenarios-dm.json
# Optional private D-045 partial-geometry proof; all outputs remain ignored.
python ./tools/make_dm_runtime_fixture.py --source-pak "D:\Games\Quake II Rerelease\baseq2\pak0.pak" --source-member maps/q2dm1.bsp --fixture-name zaereo_fixture_dm_partial --output-root .install/runtime-fixtures/zaereo_fixture_dm_partial --manifest-output .install/runtime-fixtures/zaereo_fixture_dm_partial-manifest.json --include-existing-member-controls
./tools/install_dev.ps1 -Configuration Debug -SkipBuild -RuntimeFixtureRoot .install/runtime-fixtures/zaereo_fixture_dm_partial
./tools/run_game.ps1 -Map zaereo_fixture_dm_partial -Deathmatch -ZdmFlags 0 -ProbeDeathmatchItems -ReportOutput .install/runtime-reports/zaereo-fixture-dm-partial.json
./tools/run_runtime_matrix.ps1 -ScenarioFile ./tools/runtime-scenarios-dm-fixtures.json
./tools/install_dev.ps1 -Configuration Debug -SkipBuild # immediately restore normal content
./tools/build_game.ps1 -Configuration Release -VcpkgRoot "C:\path\to\vcpkg"
python ./tools/audit_release_surfaces.py --policy ./docs/provenance/release-surface-policy.json --zaero-root "D:\Sources\Zaero" --port-root ./src --binary ./build/Release/game_x64.dll
python ./tools/audit_dm_injection.py --zaero-root "D:\Sources\Zaero" --port-root ./src --bsp-audit ./docs/audits/bsp-entities.json --json-output ./docs/audits/dm-injection.json --markdown-output ./docs/audits/dm-injection.md
./tools/package_windows.ps1 -Configuration Release -DistributionMode importer-kit
~~~

`-VcpkgRoot` may be omitted when the same value is supplied by `VCPKG_ROOT`,
the ignored local configuration, or safe discovery. `-UserRoot` may be omitted
for the per-user Saved Games default; it is explicit above to keep the example
disposable and auditable.

PowerShell scripts must support explicit paths, `-WhatIf` for destructive/copy
or remote-mutation operations where useful, non-interactive CI, and non-zero
exit codes. Python tools use `--dry-run` where they can otherwise write. A
repository-local configuration file may store paths but must be ignored;
provide a tracked example file containing no machine-specific values.

### 10.3 Build script contract

`tools/build_game.ps1` should:

1. resolve the repository root independent of current directory;
2. find MSBuild using `vswhere`;
3. verify/restore the pinned vcpkg manifest;
4. build `src/game.sln` for Debug or Release x64 with parallel compilation;
5. fail on errors and surface warnings cleanly;
6. copy nothing into the user's game unless an install command is requested;
7. direct DLL/symbol/intermediate output into ignored `build/` configuration
   directories rather than the repository root, and report the exact paths; and
8. support the same arguments locally and in CI.

Treat new warnings in Zaero code as errors after the mechanical port stabilizes.
Add sanitizers/static analysis where the Windows toolchain permits it, especially
for old undefined behavior, array bounds, entity lifetime, and format strings.

### 10.4 Developer installation

`install_dev.ps1` stages a self-contained `zaereo/` directory from:

- the selected build output;
- the tracked redistributable `pack/` contribution plus a hash-verified ignored
  `ContentRoot` when full local content is requested;
- generated `pak0.pak`;
- deliberately loose assets;
- mapdb/start configuration; and
- a development provenance/version marker.

The supported/default destination is
`%USERPROFILE%\Saved Games\Nightdive Studios\Quake II\zaereo`, following the
upstream Rerelease recommendation. Treat the read-only engine/data installation
root and the writable user-data/mod root as separate inputs. That split interface
is implemented: `-EngineRoot` identifies the read-only installation and
`-UserRoot` selects a writable user-data parent, defaulting per user. The legacy
`-GameRoot` parameter is retained only as an explicit disposable/portable
development override and requires a sibling `baseq2`; it is never selected by
discovery. Installing into a Steam/GOG/Microsoft Store program directory is not
the default release contract.

The installer must refuse `baseq2`, any program-root overwrite without an
explicit development override, and any target outside the selected writable
mod root. It removes only files listed in its own previous-stage manifest and
never deletes arbitrary user files. Support `-NoPak` loose-content mode for
debugging and `-Link` mode only when privileges and behavior are clear.

For private derived-BSP tests only, `-RuntimeFixtureRoot` accepts a strict child
of `.install/runtime-fixtures` containing only
`maps/zaereo_fixture_[a-z0-9_]+.bsp`. It rejects root/directory/file reparse
points and any collision with imported or tracked content, and records the
managed fixture count. This is not a packaging input: the fixture BSP,
identity manifest, PAK, and report remain ignored/private-local-only. A normal
install without the argument must remove the overlay before other testing.

All project launchers and validation runs force windowed mode and never start
fullscreen. The KEX `-window` startup argument is authoritative before video
initialization; changing a cvar after startup is not acceptable. The verifier
uses a required two-stage protocol:

1. launch a visible bootstrap with `-window`, `v_windowmode 0`, explicit
   dimensions, and no `game`, `map`, or equivalent mod/map command;
2. enumerate every visible top-level window belonging to each exact newly
   launched executable PID, reject any popup/non-windowed one, and require a
   captioned non-popup window; then
3. acquire foreground only for that exact verified handle through the caller's
   attached input queue with a task-switch retry, send the selected
   `zaereo`/mode/map command through system keyboard input, and retain a
   `zaereo.runtime-smoke/v2` report proving the ordering.

The wrapper requires a continuous three-second process-free interval before
launching, so a just-exited Steam/KEX handoff cannot reuse stale startup state.
Any visible popup/non-windowed observation or failed post-verification command
delivery causes immediate termination of the exact verified executable PID and
a distinct failed safety report; it never waits for the ordinary timeout or
attempts an in-process mode switch. Timeout cleanup re-enumerates all exact
newly launched selected-executable PIDs, terminates each, and records any
residual PID; a residual makes a v2 result fail. A legacy one-stage report that passed
`+set game`/`+map` on the initial command line is historical runtime evidence
only and cannot satisfy this gate.

### 10.5 Config-driven launch and runtime harness

The first bounded slice of `run_game.ps1` is implemented as the supported local
single-map single-player/deathmatch smoke wrapper. It uses the shared path
resolver, requires a managed developer install and three-second process
quiescence, launches a visible `-window`/`v_windowmode 0` bootstrap without a
mod/map selector, enumerates every visible Win32 top-level window owned by the
exact process, immediately aborts the PID on any popup/non-windowed style, and
only then foreground-gates system input for the selected Zaero command to the
verified window. It follows
the real process through the Steam bootstrap, brackets only the current console
session, re-enumerates and shuts down exact observed PIDs on failure, and writes
a strict private-local v2 hash report including `command_delivery`, the
focus-stage diagnostic, and any `residual_process_ids`. The `launch_protocol`, `engine-confirmed`
command-delivery marker, and zero residual IDs are mandatory
for a passing v2 report; v1 reports remain retained historical evidence but do
not meet the sequencing gate.
When a KEX client rejects synthetic keyboard input, `-ManualCommandDelivery`
prints the nonce-bearing command only after that same window check. The developer
enters it in the verified client; the wrapper treats delivery as pending until
the engine writes the matching marker, so manual operation cannot relabel a
missed command as a pass. The private matrix forwards that option serially to
each scenario and records the selected delivery mode plus every case's actual
launch-protocol, command-delivery result, and focus-stage diagnostic; it still rejects a report that says
`passed` without an engine-confirmed, zero-residual, fully bracketed v2 result.
`-Deathmatch` selects deathmatch and `-ZdmFlags 0` through `3` records the exact
server setting; nonzero `-ZdmFlags` is rejected outside deathmatch. The report
records mode, flags, and the final legacy-compatible `0` through `8` “Zaero
entities added” count when the session emits one. On Debug builds,
`-ProbeDeathmatchItems` invokes the D-015-contained read-only server probe after
the wait and requires structured item order, start/attempt/entity identity,
128/16-unit initial placement, final origin, generation-safe liveness, and
native Toss/trigger/Touch_Item/IR state to parse consistently. It is rejected
outside deathmatch and fails against a Release DLL because the command is
deliberately absent. The v2 schema makes the launch-protocol and command-
injection evidence mandatory for every current passing report; retained v1
reports are archival evidence only and must not be validated as current runs.
Static, schema, parser, and synthetic `-WhatIf` contracts live under
`tests/runtime/`.
`make_dm_runtime_fixture.py` supplies one narrow live geometry fixture by
selectively reading a legitimate local `baseq2` PAK, retaining the selected
BSP's geometry byte-for-byte, replacing only its ignored entity lump, and
choosing blocked starts inside actual solid collision brushes. Its manifest
records source/output identities and the expected partial result without an
absolute local path. `--include-existing-member-controls` adds eight separate
maps with exactly one historical member apiece. The installer overlay is
path/collision/reparse scoped, and reinstalling without it restores ordinary
content.
Retained private results loaded/spawned `zbase1`, `zdef1`, and `zboss` and exited
cleanly on 2026-07-14; they establish only sampled registry/resource closure,
including the newly registered ZBoss. They are not map-pass claims. The current
`run_runtime_matrix.ps1` is the non-interactive orchestration layer: it consumes
the strict private-only `runtime-scenarios.json`, calls this wrapper, and emits
private raw reports plus normalized JSON/JUnit aggregation. It fails the matrix
when any wrapper report is absent, malformed, or failed; no retained v1 result
can be promoted through the matrix. The optional `-ManualCommandDelivery` mode
does not relax that check: it exists only for a developer to enter the printed
per-case command into the already verified window when the supported KEX client
rejects system input.
Both layers read paths from the same explicit/environment/ignored-config
precedence as the build and installer and never encode a developer username or
store path.

The tracked VS Code launch entry and its matching task invoke this wrapper with
the selected read-only engine root, writable user root, and map. They
intentionally do not expose a direct Quake executable debug target: the
wrapper owns the pre-video `-window` switch and must observe a captioned,
non-popup native game window before selecting the mod/map. Attach a local
debugger only to a process that the verified wrapper has already started.

The launch wrapper must accept configuration, map/start-chain, skill, mode,
client count, dedicated/listen mode, extra cvars, writable user-data root,
timeout, and log/result paths. It stages first unless explicitly told to reuse a
verified stage, constructs arguments as an array rather than a shell string,
uses a fresh named profile for automated runs, and reports the executable,
content manifest, DLL hash, command arguments, process exit, crash dump, and
console-log location. Interactive client launch may stay attached; automated
client launch remains visible because it must prove the native window before
selecting the mod/map. Dedicated/headless server scenarios are a separate
non-client lane: they cannot satisfy any windowed-client safety or presentation
gate and must say so in their result.

The current matrix wrapper consumes a reviewed JSON scenario file for the
supported map/single-player-or-deathmatch/`zdmflags` cases, invokes the same
launch wrapper, retains raw reports below `.install/runtime-matrix`, and emits
normalized JUnit plus JSON results under `build/test-results/`. Fixtures declare
required game content by hash, never by committed path. Public CI skips
such cases with an explicit reason when the large game content is not fetched
into the runner; a private runner executes
them as described in Section 13.10. Skill, start-chain, client-count, listen,
dedicated, and extra-cvar expansion remain explicit future matrix requirements;
the current runner does not claim those scenarios.

## 11. Packaging, release, and automation design

### 11.1 Deterministic PAK builder

Adapt the useful REBLIVION pattern but make determinism a tested contract:

- normalize runtime paths to forward slashes;
- sort entries by normalized path;
- reject duplicate/case-colliding names and traversal;
- preserve bytes exactly;
- use fixed metadata where the PAK format permits;
- write to a temporary file and atomically replace;
- emit a content manifest and SHA-256;
- rebuild twice in CI and compare hashes.

If loose sprites/videos remain required, the package manifest must say so;
“everything is in the PAK” must never be assumed by installer code.

Final validation has two levels: an outer archive manifest hashes files such as
`pak0.pak`, while a cross-layer runtime manifest expands every PAK member beside
every loose runtime path, records its layer/origin/effective hash, and rejects
traversal, duplicates, case collisions, or an unexplained loose-versus-PAK
override. Reopen the staged PAKs and compare member bytes to that manifest; do
not treat a PAK as an opaque single file for runtime reference closure.

### 11.2 Release modes and archive layouts

The runtime packaging pipeline has four mutually exclusive manifest modes.
Artifact metadata, filenames, manifests, and publication checks must record the
selected mode; changing a filename cannot change eligibility. Until the
independent code-rights gate is resolved, the only possible public artifact is
an explicitly cleared tools-only acquisition kit:

~~~text
zaereo-vX.Y.Z-tools-only.zip
└── zaereo-tools/
    ├── tools/
    │   ├── import_legacy_assets.py
    │   ├── make_pak.py
    │   └── validate_runtime.py
    ├── ACQUIRE_AND_BUILD.txt
    ├── MANIFEST.json
    ├── BUILD-METADATA.json
    ├── SBOM.spdx.json
    ├── licenses/
    ├── LICENSE.txt
    ├── LICENSE_SCOPE.md
    ├── THIRD_PARTY_NOTICES.md
    └── VERSION.txt
~~~

This artifact contains only independently authored/redistributable acquisition
and validation instructions/tools—no DLL, Zaero-derived source, media, or
installable game directory. The readiness policy decides whether this
artifact is ready; it is not presented as a playable mod release. It is a
narrow, optional artifact — the primary end-user mode is `asset-full`.

When a user prefers to supply their own Zaero copy, the `importer-kit` runtime
artifact ships the DLL and rebuilds the content pack from that installation:

~~~text
zaereo-windows-x64-vX.Y.Z-importer-kit.zip
└── zaereo/
    ├── game_x64.dll
    ├── pak0.pak                 # cleared config/start data; no copied base mapdb
    ├── tools/
    │   ├── complete_importer_kit.ps1
    │   ├── import_legacy_assets.py
    │   ├── zaero_material_assets.py
    │   ├── manage_install.ps1
    │   ├── make_pak.py
    │   ├── merge_mapdb.py
    │   ├── data/zaereo-mapdb.fragment.json
    │   └── validate_runtime.py
    ├── IMPORT_ASSETS.txt
    ├── MANIFEST.json
    ├── BUILD-METADATA.json
    ├── SBOM.spdx.json
    ├── licenses/
    ├── README.html
    ├── LICENSE.txt
    ├── LICENSE_SCOPE.md
    ├── THIRD_PARTY_NOTICES.md
    └── VERSION.txt
~~~

Completing that kit locally verifies the three retail PAK hashes, creates a
separate local `pak1.pak` from the effective imported content plus generated
glow maps, and retains the nine required loose files. Completion never
downloads content and never turns the locally completed directory into a
publishable artifact.

Private integration and parity verification use a deliberately marked
`local-full` mode:

~~~text
zaereo-windows-x64-vX.Y.Z-local-full-private.zip
└── zaereo/
    ├── game_x64.dll
    ├── pak0.pak                 # package-owned cleared project data
    ├── pak1.pak                 # local import-owned effective retail content
    ├── tools/
    │   ├── manage_install.ps1
    │   ├── make_pak.py
    │   ├── merge_mapdb.py
    │   ├── zaero_material_assets.py
    │   ├── data/zaereo-mapdb.fragment.json
    │   └── validate_runtime.py
    ├── .zaereo-install/import-ownership.json
    ├── sprites/                 # only if verified loose requirement remains
    ├── video/                   # likely intro.cin and outro.cin
    ├── README.html
    ├── MANIFEST.json
    ├── BUILD-METADATA.json
    ├── SBOM.spdx.json
    ├── licenses/
    ├── LICENSE.txt
    ├── LICENSE_SCOPE.md
    ├── THIRD_PARTY_NOTICES.md
    └── VERSION.txt
~~~

`local-full` artifacts are developer-only scratch and stay out of release
channels. The publishing script and stable workflow must reject a
manifest whose mode is `local-full`; renaming the file, copying its contents,
or passing a generic force flag must not bypass that check.
The canonical ownership split still applies inside this developer archive:
project data remains package-owned `pak0.pak`; imported effective media
remains `pak1.pak` plus the nine verified loose files under the separate import
ownership manifest. The packager must not fold those bytes into `pak0` or erase
their provenance.

The primary `asset-full` mode bundles the ported GPL content directly. It is
built from the reviewed redistributable source/asset manifest—not promoted from
a user's local import—and uses a distinct filename and metadata mode:

~~~text
zaereo-windows-x64-vX.Y.Z-asset-full.zip
└── zaereo/
    ├── game_x64.dll
    ├── pak0.pak
    ├── tools/                    # merge subset for the Rerelease base DB, which is not bundled
    │   ├── manage_install.ps1
    │   ├── make_pak.py
    │   ├── merge_mapdb.py
    │   ├── data/zaereo-mapdb.fragment.json
    │   └── validate_runtime.py
    ├── sprites/                 # only if verified loose requirement remains
    ├── video/                   # only verified cleared loose media
    ├── README.html
    ├── MANIFEST.json
    ├── BUILD-METADATA.json
    ├── SBOM.spdx.json
    ├── licenses/
    ├── LICENSE.txt
    ├── LICENSE_SCOPE.md
    ├── THIRD_PARTY_NOTICES.md
    └── VERSION.txt
~~~

The asset-full builder fails unless every included path is covered by current
code/media policy, the manifest records `asset-full`, and the stable readiness
record names the same version and commit. `local-full` and `asset-full` may have
similar runtime trees, but their provenance and publication status are never
interchangeable.

Every archive's mode-specific `LICENSE_SCOPE.md`, SBOM, and `licenses/`
directory describe exactly the components in that mode and contain the
harvested dependency copyright texts; the manifest and checksum cover them.
Tools-only must name the actual license/no-grant status of its independent tools
and must not inherit a bare GPL text as an implied license for unrelated bytes.
For an eligible public mode, publish
`SHA256SUMS.txt`, the external artifact/readiness manifest, and the separately
versioned editor gamepack for playable importer-kit/asset-full releases. A
tools-only release includes editor definitions only if those files are
independently cleared and explicitly part of the tools product. A symbols archive may be published only for a
code-cleared importer-kit or asset-full release; local-full may retain symbols
privately, and tools-only never includes or publishes PDB-derived material. Do
not put PDBs, source PAKs, legacy DLLs, or nested ZIPs in the player archive.

Each public DLL archive also has an exact-version companion
`zaereo-source-vX.Y.Z.zip` (or a verified durable equivalent) containing the
preferred form of the covered source, build/project files, package/build tools,
`vcpkg.json` and baseline identity, applicable patches, notices/license texts,
`LICENSE_SCOPE.md`, manifest, and build instructions for that same commit. It
contains no imported media. The package test proves the binary/source commit,
version, dependency baseline, and file scope agree; an automatic GitHub source
archive is accepted only if the test proves it is complete corresponding source
for the exact binary and the distribution policy permits that repository/ref.

The Phase-1 substrate implementation of deterministic `generate_sbom.py` and
`collect_licenses.py` is present. It pins the official SPDX 2.3 JSON Schema and
generator version; verifies the exact vcpkg closure/baseline/versions; records
the compiler and static runtime; copies the actual dependency copyright bytes;
sorts records; uses the source commit epoch; and is included in current local
package stages. Synthetic and live-install tests cover unknown dependencies,
missing/tampered license bytes, version/policy drift, official-schema validity,
and two-build byte equality. Phase 9 must extend the same policy/SBOM to every
mode-specific packaged Python/PowerShell tool and artifact-manifest path before
publication readiness. An unknown component, missing copyright file,
inconsistent license expression/scope, or SBOM/manifest path mismatch fails
packaging and readiness.

`zaero.cfg` and `zaerostart.cfg` should normally occur once inside the cleared
project PAK. The active full `mapdb.json` occurs once in the locally generated
import-completion layer, or in asset-full only when its base bytes are separately
redistributable; the Zaero fragment must not masquerade as the full active file.
If target engine testing requires one to be loose, move it rather than
duplicating it. The stage validator rejects ambiguous loose-versus-PAK
overrides.

Current-script state/gap: the local packager and developer installer now stage
project `pak0.pak` separately from an effective importer-owned `pak1.pak`,
reject project/import path collisions, retain the required loose files, and
write mode-specific runtime ownership records. Private generated runtime
fixtures use a distinct `pak2.pak`; they cannot be mistaken for imported media.
The packager still exposes only importer-kit and local-full paths, always stages
the DLL, gives local-full no required `-local-full-private` filename suffix, and
does not yet implement the tools-only or asset-full packaging paths or the
local-full release-channel exclusion. These local ownership records are not proof
of the unimplemented source-override, loose-precedence, cross-layer reference,
or install/update/rollback lifecycle matrix.
Remote containment landed on 2026-07-13: package/nightly/stable workflows are
read-only verification jobs with no cache, artifact, release, or credential
publication path; checkout credentials are not persisted; and the manual
publisher is a deliberately manual, human-approved step. The manually dispatched stable workflow first
accepts only an exact stable SemVer tag, requires its annotated-tag object and
commit to match the checkout, verifies object connectivity, a clean worktree,
and ancestry from `origin/main`, then validates the distribution policy and a
current `importer-kit`/`gameplay-release-assets`/`playable-stable` readiness
record with `--require-ready`. It performs no dependency install, build, or
package if any of those gates fail. If a future approved policy and complete
evidence allow it to continue, it pins the vcpkg commit exactly and rechecks the
package version, source commit, manifest, and checksum while retaining every
output on the runner. Their deterministic archives remain local development
evidence only. Remote mutation must stay technically absent until the mode
schema, packager, publisher, workflows and tests implement this section end to
end and the relevant rights gates are independently permitted.
The release manifest still treats each PAK as one outer file, but
`validate_runtime.py --stage` now compares importer `pak1` members plus the
required loose paths to the import manifest and rejects all project/import/
generated member collisions. Exact legacy `default.cfg`/`maps.lst` source-winner
fixtures, engine lookup proof for the loose files, and cross-layer reference
validation remain publication gates.
For every mode, a package dependency-closure test executes each bundled entry
point in an extracted offline archive and proves every imported script/module,
data file, schema, runtime, and license is present and allowlisted; no tool may
work only because it reaches back into the source checkout.

Immediate Phase-0 containment precedes any other release work. That containment
is implemented: scheduled/dispatchable remote publication is absent, every
`-Publish` path fails before external access, checkout credentials are not
persisted, and gameplay-tree workflows upload no DLL, package, cache, artifact,
or log. These controls remain mandatory until machine-readable code/media policy
and exact-commit readiness authorize a reviewed mode and channel. Local/private
execution must have explicitly covered retention and audience and may expose
only reviewed normalized evidence. No current workflow may create or mutate a
GitHub release on its own; publishing stays a human-approved step, and prose
saying “gated” is not a technical control.

### 11.3 Manual GitHub release script

Keep packaging and publication separable:

- `package_windows.ps1` builds, validates, stages, packages, and checksums;
- `publish_github_release.ps1` publishes already-validated artifacts.

The publication script must:

1. require an explicit version/tag and read/compare `VERSION`;
2. evaluate repository/ref/history and channel policy before creating a tag:
   confirm the distribution policy records the GPL basis and that the release
   carries the required notices and complete corresponding source;
3. verify the tag format, expected branch/commit, and a clean worktree;
4. run every profile-applicable CI gate: tools-progress runs tool unit/security/
   offline dependency-closure and deterministic package validation, while every
   DLL-bearing mode additionally requires Debug/Release, both exports, load, and
   applicable runtime proof;
5. ensure the archive was created from the current commit;
6. recompute checksums and inspect the ZIP allowlist, SBOM and license bundle;
7. produce release notes from the matching `CHANGELOG.md` section;
8. authenticate/check `gh`, repository identity, remotes, existing tag/release
   state, and protected environment;
9. create a draft by default. A local `-Publish` may target only a policy-eligible
   prerelease channel; it can never publish/promote a stable release. Stable
   promotion requires the protected stable workflow's environment approval (or
   a verifiable workflow attestation that a local caller cannot forge);
10. upload the eligible archive, checksum, external manifest/readiness record,
    and SBOM/license evidence exactly once. Playable importer-kit/asset-full
    modes also upload the editor gamepack; tools-only includes it only when
    separately cleared. Upload symbols and exact corresponding-source evidence
    only for code-cleared DLL modes;
11. allow replacement/recovery only for an unpublished draft. Hard-reject
    overwrite of an already published stable tag or asset; replace a bad stable
    with a new version;
12. enforce mode-specific policy: tools-only has no DLL, gameplay/Zaero-derived
    source, or media (only its independently licensed tool source);
    importer-kit requires code permission and no media; asset-full requires
    both permissions and reviewed distributable inputs; local-full is always
    rejected;
13. reject dirty, required-test-skipped, profile-required-build-skipped,
    wrong-commit, incomplete-source, and otherwise non-publishable manifests.
    A tools-progress record explicitly marks game build/export `not-applicable`
    rather than “skipped.” A stable playable tag rejects
    tools-only, which is eligible only as an explicitly labelled
    progress/prerelease artifact from its separate distribution root; and
14. print the release URL and artifact hashes.

A `-WhatIf`/dry-run path should perform every validation except remote mutation.
Do not combine nightly publication and stable releases in an ambiguous script.

### 11.4 GitHub Actions

#### Pull-request and main CI

These jobs run in a repository/channel recorded by D-003. The gameplay tree is
GPL and may be public; CI is read-only with respect to releases (it never
publishes on its own), and policy still allowlists cache and artifact
contents independently:

- pin third-party actions by full commit SHA; human-readable version comments
  may accompany the SHA but are not the trust boundary;
- checkout with LFS when the selected asset strategy requires it;
- restore pinned vcpkg/Python caches only when their keys, contents, audience,
  and retention avoid leaking secrets or credentials;
- build Debug and Release x64 plus verify both exports for DLL-bearing profiles;
  tools-only CI instead runs the complete independently allowlisted tool test,
  security, offline dependency-closure, and deterministic package suite;
- for gameplay/DLL profiles, run source, BSP, entity, asset, case, PAK
  determinism, and save-registration tests. The tools-only profile runs
  only its allowlisted synthetic parser/import/PAK/security fixtures and carries
  no large gameplay inputs or media-derived audit reports;
- package the selected profile without publication;
- upload only policy-allowlisted normalized logs/manifests and short-lived test
  artifacts; releasing DLLs/packages remains a human-approved step rather than an
  automatic CI upload, and large media stays in LFS rather than loose artifacts;
- fail if profile-applicable generated reports are stale; tools-only compares
  only synthetic/independently cleared tool evidence present in its clean root.

Dependency updates must change the vcpkg baseline/lock evidence and action SHAs
in a reviewed change, regenerate an SBOM/license inventory, and update
`THIRD_PARTY_NOTICES.md` when obligations change. Cache keys include the exact
manifest/baseline/tool version; caches are performance aids, never accepted as
unverified build inputs. Dependabot may propose updates but cannot bypass the
full profile-applicable build/audit/package suite or license review.

Workflow path filters are part of the gate, not an optimization that may skip
policy work. Changes to `CHANGELOG.md`, `LICENSE*`, `THIRD_PARTY_NOTICES.md`,
`docs/provenance/**`, distribution/readiness schemas, editor gamepack inputs,
release templates, `VERSION`, packaging/publishing workflows, or their tools and
tests must run the applicable package, policy, SBOM/license, and readiness jobs.
CI has a test proving each release-sensitive path is covered.

#### Nightly

- run the full package path on a schedule and manual dispatch;
- mark artifacts clearly as untested/nightly;
- use prereleases if publishing to GitHub Releases;
- retain a bounded number of builds;
- never move the stable tag or overwrite stable assets.

#### Stable release

- trigger from a protected version tag or explicit workflow dispatch;
- require all release gates and a protected environment approval;
- call the same scripts used locally;
- consume the locally/CI-created draft for final human inspection, then require
  protected-environment approval before promotion; a generic local script flag
  cannot substitute for that approval;
- publish only the provenance-eligible distribution mode recorded in the
  manifest; and
- generate provenance/attestation/SBOM metadata where practical.

### 11.5 Editor support

Generate and validate definitions for at least TrenchBroom and a NetRadiant
variant, using REBLIVION's editor layout as inspiration. Definitions need:

- every exact custom classname, model preview, bounding box, color, and category;
- `spawnflags2` and ordinary spawn flags without conflating their namespaces;
- custom keys (`active`, `mangle`, `mteam`, mirror metadata);
- item/key descriptions, ammo relationships, and game-mode notes;
- entity-specific flags for cameras, IRED, autocannons, Handler, barrier,
  trigger push/laser, crates, and boss targets;
- Zaero texture paths and compiler/tool textures;
- launch/compile profiles that point at `zaereo` without hardcoded personal paths.

Treat editor files as generated artifacts when possible and validate them
against the spawn table so runtime and documentation cannot drift.

The distributable editor artifact is a versioned gamepack archive, not loose
FGD files alone. It contains the editor-specific game descriptor/config, Zaero
definitions, icons/metadata, texture/tool declarations, optional compile-profile
templates, README, version, manifest, and checksum. It references a
user-selected base game and mod root; it does not bundle the packaged runtime
maps/textures or unreviewed compiler binaries.

The pinned stock-Rerelease definition set is itself a distribution input. Its
hash, origin, license/status, and inclusion channel must be covered by
`distribution-policy.json` and the editor SBOM. If redistribution is permitted,
the archive may carry generated combined stock-plus-Zaero definitions. If it is
unclear or denied, ship only the cleared Zaero delta plus a local generator that
requires the user-selected stock definition set, verifies its supported hash,
and writes the combined files locally; neither those inputs nor the locally
combined output become release assets. In both cases generation must append the
Zaero delta without hiding stock/expansion entities, build twice identically,
install into a disposable editor profile, and open one stock plus one synthetic
Zaero map before release. NetRadiant Custom/VibeRadiant layout variants may be
emitted from the same `editor/entities.json` source, never maintained as
independent hand-edited contracts.

### 11.6 Update, uninstall, rollback, and release recovery

Implement one `manage_install.ps1` contract for player packages:

~~~powershell
./tools/manage_install.ps1 -Action Install -Package "<archive-or-completed-kit>" `
  -UserRoot "<writable-data-root>" -EngineRoot "<read-only-data-root>" -WhatIf
# Allowed actions: Install, Repair, Update, Rollback, Uninstall,
# and PurgeImportedContent. PortableRoot is an explicit alternative to UserRoot.
~~~

The complete action set also includes `Rollback`. `-Package` is required for
`Install`, `Repair`, `Update`, and `Rollback`; `Uninstall` and
`PurgeImportedContent` trust only the verified on-disk ownership manifests and
must not accept a release archive as authority.

`-UserRoot` defaults to `%USERPROFILE%\Saved Games\Nightdive Studios\Quake II`;
`-PortableRoot` is an explicit mutually exclusive override. The manager refuses
`baseq2`, engine/program roots without that override, traversal, reparse-point
escapes, wrong product/mode, and any collision with an unmanaged or differently
owned file. It never guesses a Steam library for player installation.
`-EngineRoot` follows the shared resolver and is read-only; importer completion
or a data-build update requires it to hash/read a supported pristine base
mapdb. If it is absent or unsupported, the manager offers only the documented
no-mapdb/console-start completion and makes no menu-coexistence claim.
The manager requires no elevation, creates no registry entries or shortcuts,
and performs no implicit network download/self-update; `Update` consumes an
explicit already-verified package. Any future shell integration needs its own
reviewed ownership and rollback records.

Every install commits `.zaereo-install/package-ownership.json` last. Its
versioned schema records product/install ID, package version and mode, source
artifact/manifest/readiness hashes, destination identity, tool/schema version,
and for every package-owned file its normalized relative path, SHA-256, size,
component/policy ID, and operation. Imported content has a separate
`.zaereo-install/import-ownership.json` containing all three input PAK hashes,
the nine loose-input hashes, supported data-build/mapdb input hash, importer and
schema versions, generated `pak1.pak` plus member-manifest hash, generated mapdb
hash/location, and every locally generated/retained loose path and hash. Import
completion writes this manifest atomically only after validating all outputs.

Operations obey these ownership rules:

- `Install` stages and validates every byte beside the destination before any
  mutation. A journaled atomic commit (temporary files, per-file replace/backup,
  ownership manifest last) either completes or restores the previous tree.
- `Repair` restores missing package-owned paths. `Repair`, `Update`, and
  `Uninstall` replace/remove an existing path only when its bytes match the
  prior ownership hash; a modified owned path causes a reported conflict rather
  than data loss. An explicitly confirmed repair may first preserve a conflicting
  file to a user-selected backup, never silently overwrite it.
- `Update` validates the new package/policy first, preserves all unowned and
  import-owned paths, journals replacement of matching old-owned bytes, removes
  only matching obsolete package-owned paths, and commits the new ownership
  manifest last. It rejects a version decrease. Same-version repair and
  interrupted rerun are idempotent.
- `Rollback -Package <prior>` requires separate confirmation, verifies the
  prior artifact, readiness record, policy, and ownership chain exactly like an
  update, then uses the same journal. It refuses by default when it detects saves
  newer than the prior readable schema; an explicitly acknowledged rollback
  first preserves those saves and reports them unsupported rather than altering
  or claiming compatibility with them.
- `Uninstall` removes only still-matching package-owned files and then its empty
  owned directories/manifest. Saves, profiles, configuration, logs, screenshots,
  and import-owned content remain.
- `PurgeImportedContent` is separate, prominently confirms that local commercial
  outputs will be removed, verifies the import manifest and current hashes, and
  removes only matching import-owned paths. It never broadens uninstall scope.

Mode transitions are explicit ownership migrations, never ordinary renames:
importer-kit to importer-kit preserves and revalidates local `pak1`; completed
importer-kit to asset-full requires either a clean install or separately
confirmed verified purge/archive of import-owned bytes so stale `pak1` cannot
override cleared assets; asset-full to importer-kit requires successful
legitimate local completion before removing asset-full-owned media; and a
private local-full install is a permanently separate lineage that cannot update
or “promote” into a public mode. Tools-only is non-installable. Cross-mode tests
exercise every permitted/refused direction and mixed ownership conflict.

Phase 2 implements importer completion, the two ownership schemas, safe clean
install/repair/uninstall, and crash/interruption recovery. Phase 9 adds certified
cross-version update/rollback and release-candidate fixtures. Tests kill the
manager at each journal boundary, rerun it, corrupt/modify each ownership class,
mix package and import content, change the Rerelease data build, and prove that
only matching owned bytes change in both per-user and explicit portable roots.
A rollback never claims compatibility with saves created by a newer schema
unless that direction has a passing test.

A failed draft may be deleted and recreated only before publication, with an
audit note. Published stable tags and assets are immutable; a bad stable release
is marked withdrawn and replaced by a new patch version rather than silently
overwritten. Retain the source commit, build metadata, external/internal and
ownership manifests, checksums, release notes, symbols, and validation logs
needed to reproduce or diagnose every release. Compromised artifacts or
credentials use the private `SECURITY.md` route, immediate draft/release
withdrawal where appropriate, token rotation, a new version/tag, and a public
advisory. Never reuse a compromised tag.

### 11.7 Rerelease data-version and mapdb merge policy

The tracked `pack/mapdb.json` is a Zaero-only development fragment, not a
shippable replacement for the Rerelease database. A release package must never
mask stock/expansion episodes by installing that fragment as though it were the
complete database, nor redistribute the selected base database merely because
it can read it locally.

The deterministic `merge_mapdb.py` stage follows these rules:

1. take the full `mapdb.json` from an explicitly selected, supported Rerelease
   data installation and verify its recorded data-build hash/version;
2. parse and preserve unknown fields, the relative order of all upstream arrays,
   and every existing episode/map entry. Canonicalize object-key order, encoding,
   and whitespace only; never sort episode/map arrays whose order may drive the
   New Game menu;
3. merge the tracked Zaero fragment by stable IDs at an explicitly selected and
   runtime-tested menu position, rejecting duplicate IDs, conflicting map
   ownership, malformed start chains, missing maps/media, and case-only paths;
4. write only to the generated local stage, with an atomic output and report
   identifying the upstream hash, insertion position, and each added record;
5. prove that removing the Zaero records reconstructs the upstream database with
   all values, unknown fields, and array order preserved; and
6. support a no-mapdb fallback in which `exec zaerostart.cfg` remains usable but
   no menu-coexistence claim is made.

The default importer-kit carries only the Zaero fragment (or its cleared
equivalent). Local completion must invoke this merge only after its operator
selects a hash-verified Rerelease data build and a reviewed menu position; the
current completion wrapper deliberately does not guess either input. The merged
database is import/generated-owned, recorded in `import-ownership.json`,
preserved by package repair/update/uninstall, and regenerated from the newly
selected pristine base—not patched in place—when the supported data build
changes. An `asset-full` release may include a combined database only if
`distribution-policy.json` separately permits redistribution of the exact base
definition/database bytes (Nightdive's commercial data, not GPL Zaero content);
otherwise it uses the same local merge even though the Zaero content is GPL. The
public package never carries a copied base database by default.

The supported-data-build matrix belongs in the release manifest. A Rerelease
data update is a baseline change: rerun deterministic/inverse/order tests plus
menu, map, cinematic, music, and stock-episode smoke before adding its hash.
Never copy a stale full database from REBLIVION or another mod.

`tools/merge_mapdb.py` now implements the mechanical local stage: it reads the
selected loose base file or exact `mapdb.json` PAK member, verifies that member's
SHA-256 and a nonempty data-build identifier, and requires explicit
episode/map insertion indices, a validated imported content root, and output/
report paths below `.install`. It rejects duplicate or case-colliding episode/
map identities, unsafe/missing referenced BSP/cinematic paths, malformed start
chains, and output escapes while preserving legitimate exact duplicate upstream
map entries; it writes canonical JSON atomically and proves that removing the
exact added records reconstructs the canonical base document. Its
private report records both input hashes, the positions, records, output hash,
and inverse proof. No supported Rerelease base hash or menu position has passed
the required live menu regression yet, so this tool does not establish
stock-menu coexistence on its own.

## 12. Progressive implementation roadmap

There are deliberately no calendar promises here. Estimate each phase only
after its predecessor supplies working measurements. A phase closes when its
exit criteria pass on a clean machine, not when its code has merely been merged.

### Phase 0 — Freeze evidence, policy, and naming

Goal: make the existing worktree reproducible before further gameplay changes.

Work:

- Record hashes/manifests for all four supplied source/content baselines and the
  selected Rerelease upstream commit or archive.
- Generate and review source-delta, BSP-entity, map-flow, asset-layer, and
  case-collision reports.
- Regenerate and review the record-level source/function/global and
  BSP-classname/key/spawnflag coverage reports defined in Section 4.3. Keep
  public-CI structural validation and local game-content regeneration;
  zero uncovered records is a hard failure.
- Inventory the complete candidate gameplay tree; review every tracked and
  untracked path for secrets, generated bytes, ignore/LFS
  policy, and intended
  repository scope, then capture an immutable evidence commit/tree
  before using “head,” clean-checkout, or exact-commit claims.
- Record the GPL basis for code and media redistribution.
- Establish the schema registry and validate the asset/distribution-policy
  records; reserve versioned IDs and phase owners for local config, ownership,
  release manifest, and readiness schemas.
- Record repository/remotes/history/source-archive/Actions channels in D-003;
  the gameplay tree is GPL and may be public.
- Keep release publication behind a deliberate human step until the
  machine-readable readiness gate is implemented: a maintainer approves a draft
  release rather than a workflow shipping automatically. CI stays read-only with
  respect to releases in the meantime.
- Choose the product/game directory (`ZaeREo`/`zaereo` recommended), repository
  license, version convention, supported first OS, and upstream-sync model.
- Create `AGENTS.md`, the public README skeleton, notices/provenance documents,
  compatibility matrices, quirk ledger, issue templates, and contribution rules.
- Decide Git LFS versus local-importer policy before committing binary content.

Exit criteria:

- Every input is identified by hash and origin.
- All 20 BSPs and all 969 effective PAK paths plus nine loose files appear in
  generated reports.
- The 132-classname inventory and exact 27 missing map-facing names are locked.
- Every source-delta and BSP mapper-contract record has a validated coverage
  entry with an explicit disposition, ledger/decision ID, implementation seam,
  lifecycle/save applicability, and test/evidence link; no `SOURCE_AGE`,
  `NON_RUNTIME`, or native-no-delta exemption lacks a reason.
- Code and media are recorded as GPL-distributable; the `asset-full`,
  `importer-kit`, and `tools-only` modes are the publication paths, and
  `local-full` stays developer-only.
- Existing nightly/stable/manual paths cannot publish a release until the
  readiness gate and a maintainer's draft approval exist; a negative integration
  test proves the containment.
- Released DLL modes ship complete GPL-2.0 corresponding source and notices, and
  the public tree carries the GPL notices and the original authors' credits.
- The approved gameplay tree has an immutable commit/tree ID after a
  retained secret/generated-file review; reports distinguish that
  identity from the audit checkpoint's one-file initial `HEAD`.
- No secret or generated build artifact has entered Git accidentally.

Playable output: none; this is the reproducibility gate.

### Phase 1 — Establish the clean Rerelease substrate

Goal: certify the target baseline/toolchain beneath the existing prototypes
before adding further Zaero gameplay code.

Work:

- Import the pinned Rerelease DLL tree into `src/` without semantic edits.
- Preserve game API 2023, cgame API 2022, integrated expansion/bot code, project
  output naming, and engine-visible struct layouts.
- Relocate/update the solution paths cleanly and keep the upstream snapshot easy
  to diff.
- Pin vcpkg; implement bootstrap and Debug/Release build scripts.
- Add pinned-schema SBOM generation and exact dependency-license harvesting
  with deterministic synthetic fixtures; later phases extend the inventory as
  packaged tools/content are introduced.
- Make bootstrap/build/install share the documented explicit/env/local-config/
  discovery resolver; pin the toolchain candidate, default installs to the
  per-user Saved Games root, and require an explicit flag for portable/program
  roots. Validate the split local-config schema and migration alias. Remove
  unsafe silent program-root discovery from the supported path.
- Add Windows CI, formatting/static checks, project-file completeness checks,
  and an empty/mod-directory load smoke test.
- Enforce D-015 with an identity-locked legacy-source policy plus fail-closed
  current source/project, produced Release DLL, and package-member deny scans;
  preserve native Rerelease grapple constants through path-scoped rules.
- Add `GAMEVERSION`/display version through a minimal Zaero integration commit,
  without gameplay.

Exit criteria:

- Fresh-clone Debug and Release x64 builds succeed locally and in CI.
- The stock baseline DLL loads in the Rerelease from `zaereo` and exports both
  required APIs.
- An automated upstream diff contains only the documented build/layout/version
  integration.
- No warnings indicate ABI prefix corruption, missing source files, or vcpkg
  drift.
- Resolver tests prove `-VcpkgRoot`, environment, ignored config and safe
  discovery select the same checkout across bootstrap/build; a successful
  bootstrap cannot be followed by a missing-`VCPKG_ROOT` build failure.
- Installer dry-run/live tests prove per-user default, explicit disposable
  override, no implicit Steam/program-root mutation, and refusal of `baseq2`.
- The substrate SBOM and license bundle reproduce byte-for-byte and fail on an
  unknown dependency, missing copyright text, or manifest/scope mismatch.
- The D-015 validator proves the produced Release DLL/package contains none of
  the legacy test commands, entities, configs, modules, animated-rocket strings,
  or Zaero ZBoss grapple experiment, followed by a v2 two-stage windowed Release
  DLL-load/map-spawn/client-entry/shutdown smoke.

Current D-015 closure (2026-07-15): the identity-locked policy and normalized
audit cover 15 source/project files, seven project-enumerated debug modules,
three guarded commands, two `_SHANETEST` sites, and two literal grapple blocks.
Six fail-closed tests cover the current source/project, scoped native grapple
allowance, ASCII/UTF-16 DLL strings, ZIP members/embedded binaries, and embedded
PAK directory names. Revision 2 additionally contains D-045's read-only probe
under `_DEBUG` and denies both signatures. The current produced Release DLL
passes its 11-string deny scan, and four local deterministic packages pass their
member, DLL, and PAK scans with a generated private-local result. The retained
v1 single-stage `zbase1` Release smoke loads DLL SHA-256
`273ac734dc2ee0199e1aa88bd745d657b53c2e181419e13fd0cbaf7af2cf2fc0`,
initializes, spawns, reaches native client begin, and shuts down with no
non-windowed observation, safety abort, timeout, fatal output, dump, or process
leak (report SHA-256
`b0ca47bc40779ef6e4ee83cf3e656c20f51f97ab9dec8988abb514a9ab8c7bd4`).
It remains historical binary/load evidence only: because it selected the
mod/map before native-window proof, it no longer closes D-015/Q-039/SYS-018.
Rerun it under the v2 protocol; it still does not claim map compatibility.

Playable output: stock Rerelease behavior under the new mod directory, useful
only as an installation/build smoke test.

### Phase 2 — Build the content and compatibility spine

Goal: make every original map/resource inspectable with deterministic failures.

Work:

- Implement the licensed-content import/canonicalization path and deterministic
  PAK builder.
- Add the Zaero mapdb fragment and rights-safe local merge, non-destructive
  config, exact cinematic start chain, version marker, developer installation,
  importer completion, and the package/import ownership manifests plus core
  install/repair/uninstall manager from Section 11.6.
- Create the typed Zaero state containers, duration/cadence helpers, stable item
  and entity identifier conventions, save registration conventions, and
  `spawnflags2` parser/filter.
- Replace the current single map-origin switch with separate gameplay/content
  activation and mapper-contract classification; implement the audited hash,
  explicit metadata, conservative signature, reason logging, and save contract
  defined in Section 8.3/D-018.
- Register exact custom classnames. Functional source no-ops may be real no-ops;
  incomplete gameplay entities must be loudly marked development-only, never
  silently omitted or accepted by release validation.
- Parse retained fields (`active`, `mangle`, `mteam`, mirror metadata, model2–4,
  `aspeed`, explicit mins/maxs) and report their per-class use.
- Reserve non-colliding HUD stats, item IDs, wheel capacity, damage MODs, effects,
  and configuration strings with compile-time checks.
- Add the asset-reference/case/closure validator and an all-map spawn-registry
  test.

Exit criteria:

- The staged package is byte-for-byte reproducible and matches both its outer
  archive manifest and expanded PAK-member/loose runtime manifest; negative
  override/case/duplicate fixtures fail.
- All 20 BSP entity lumps parse; production validation reports zero unknown
  classnames/fields and zero accidental placeholder spawns.
- Every content path resolves with correct case/precedence, including loose
  sprites/videos.
- `spawnflags2` single/co-op filtering has unit tests for every bit combination.
- Classifier fixtures prove all original maps opt in, stock/mission-pack/
  ambiguous maps do not false-positive, explicit community metadata is stable
  across saves, and stock-map DM injection leaves native mover meanings intact.
- A minimal custom field/callback/entity survives a JSON save round trip, proving
  the chosen extension pattern.
- Local completion records the exact imported/generated ownership and supported
  base-mapdb hash; clean install, repair, uninstall, interrupted rerun, and
  modified/unmanaged-file tests change only matching owned bytes while preserving
  saves, configuration, and imported content.

Playable output: map-tour/developer builds only. Maps may be visually inspected,
but gameplay compatibility is not claimed.

### Phase 3 — Port map semantics, movers, and simple world entities

Goal: reproduce the mapper-facing substrate shared across the campaign.

Work:

- Port `MOVETYPE_FALLFLOAT`, `MOVETYPE_RIDE`, `MOVETYPE_BOUNCEFLY`, and the
  legacy freeze state through Rerelease physics/masks/entity handles.
- Restore lifetime validation after step-physics trigger touches. Under D-044,
  retain the unmodified shared Rerelease `SV_FlyMove`/step-slide path: the
  identity-locked source audit and seven float32 goldens classify Zaero's
  one-line global exact-duplicate comparison removal as source-age drift.
- Port accelerating/decelerating `func_rotating`; exact per-corner train
  speed/accel/decel and raw-origin Viper destinations; path-corner pre-wait
  turning and suppressed teleport events; active/touch/message/zero-damage
  sliding and rotating doors; bit-2 low-trigger platforms; toggle/no-sound
  `trigger_push`; and random-target `func_timer`. Keep unused smooth path bits
  and train rotation/aspeed paths as synthetic/community-map ABI tests rather
  than claiming the shipped campaign exercises them.
- Implement crates/seats, mass-400 FALLFLOAT `misc_explobox` with client-only
  airborne pushing, comm dish, barrier, simple camera world state, map IRED
  shell, boss target marker, and intentional compatibility no-ops.
- Correct `trigger_laser` as a synthetic source-only entity: required target,
  no use callback, 0.1-second auto-start, default wait four, 2,048-unit
  monster/player-only trace, and bit-1 rearm or one-hit free.
- Port custom damage/flag plumbing without yet attaching every weapon/monster.
- Preserve mission help, cross-level flags, named spawnpoints, unit boundaries,
  and active/use state.
- Register all entity fields and callbacks with JSON save; add targeted fixtures
  for riders, pushers, toggles, random targets, and dormant timers.

Current static closure includes the exact `func_plat` bit-2 collision dispatch,
`misc_explobox` spawn/push delta, rotating-door damage default, and complete
train/path-corner mapper surface: all 11 platforms, 31 barrels, 12 missing/zero
rotating doors, 375 corners, 28 trains and seven Vipers are inventoried;
platform equality at eight units activates; barrel push speed is
tick-independent and accepts airborne clients; zero-damage doors still enter
their shared reversal path; all five zdef4 speed nodes, 96 waits and four
teleports are locked; source-only smooth/rotation flags retain their 10 Hz
decisions over 40 Hz physics; and non-Zaero maps retain native meanings. This
is not live mover, map-completion, water/contact, blocking, rider, orientation,
or save/load evidence; those Phase-3 exit gates remain open.

D-044 additionally locks legacy, Zaero, Rerelease and current physics sources,
proves Zaero changes only the exact-duplicate comparison inside global
`SV_FlyMove`, and executes unobstructed, wall, corner, stair, three-plane wedge,
exact-repeat projectile, and near-repeat monster float32 goldens. Only the exact
repeat distinguishes legacy from Zaero: the removed suppression turns a tiny
negative residual into a dead-stop, while Rerelease recognizes the repeat via
its native 0.99 gate. This closes the static disposition, not the live BSP/
caller-isolation fixtures.

Exit criteria:

- Entity test maps demonstrate each movement type, flag, target path, and use
  transition at 40 Hz.
- Save/load works while movers accelerate, a floor object rides a train, a
  low-trigger platform moves, an explosive barrel falls/floats/is pushed, a
  zero-damage door blocks, a barrier is revealed, a timer is dormant, and a
  toggle trigger is off.
- The three shipped random-timer definitions select only their semicolon-listed
  targets and no buffer overflow is possible.
- All 11 low-trigger platforms, 31 explosive barrels, 12 missing/zero-damage
  rotating doors, five nonzero per-corner speeds, 96 waits and four teleport
  corners pass their shipped-map fixtures; stock/Rogue meanings remain native.
- Synthetic trigger_laser and unused path/train flag fixtures prove the complete
  mapper ABI without turning source-only behavior into a shipped-map claim.
- A trigger that frees a stepped entity cannot cause post-free work, and live
  corner/wedge/stair/repeated-plane projectile/monster/player/expansion clips
  confirm D-044 without forking the shared `SV_FlyMove` path.
- Map-flow tests preserve exact `*unit`, `$spawnpoint`, help, and cross-level
  semantics.

Playable output: environmental/puzzle smoke routes; combat is not yet complete.

### Phase 4 — Port player inventory, weapons, camera, and presentation

Goal: complete all player-owned Zaero state machines before enemy integration.

Suggested dependency order:

1. stable item registrations, ammo maxima, Pack/Bandolier behavior, custom keys,
   default loadout, Push, aliases, wheel, HUD stats, and save schemas;
2. Flare Gun and flash/blind presentation;
3. Sniper Rifle, zoom, no-armor trace, shield penetration contract;
4. Sonic Cannon charge/release;
5. IRED placement, beam, cap, timeout, shrapnel, and map variant;
6. Plasma Shield collision/mitigation/lifetime;
7. EMP field and an explicit affected-system matrix;
8. A2K activation consumption, held gunframe, client countdown/immunity, HUD,
   death cancellation, detonation-only helper and dual/Quad blast arithmetic;
9. Security Camera and Visor targetname state, lifecycle, overlays, yaw sway,
   tracking, control, additive dropped duration, and copy/collision decision;
10. monster/custom-MOD obituaries and Rerelease-safe presentation/localization;
11. shared saved projectile-dodge timeout for Rocket/BFG/Flare, with Blaster
    deliberately excluded, ready for monster integration.

For each, port the original arithmetic/order first, translate time explicitly,
use Rerelease projectile/trap/linking conventions, and add deterministic golden
tests before correcting defects.

Exit criteria:

- Every item can be spawned, picked up, selected through aliases/wheel, used,
  dropped where allowed, carried across a level, lost/retained on death as
  intended, and round-tripped through a save.
- Weapon damage, cost, timing, charge, radius, kick, zoom, Quad, EMP, barrier,
  shield, water, sky, and owner interactions match the recorded matrices.
- IRED/Shield/EMP/A2K save correctly during every lifecycle phase and clean up
  safely on owner death/disconnect/changelevel.
- A2K immunity includes no-protection damage only before the exact blast frame;
  death cancels it, Quad is sampled at blast, and the helper exists only after
  detonation.
- Visor works with zero, one, all-inactive, and multiple cameras without hangs;
  targetname controls initial camera state, duration stacking and trace-copy
  behavior match D-021, cancellation restores complete prior state, and HUD
  stats do not collide.
- A golden table covers all 25 monster obituary mappings and all seven custom
  MOD paths; representative live self/team/mode/gender/localization cases pass.
  Projectile-dodge cadence/call sites and saved timeout are exact.
- Player-specific views/effects work for two local split-screen clients.

Playable output: weapon/item test maps and multiplayer firing range.

### Phase 5 — Make the Base unit playable

Goal: ship the first honest campaign milestone (`zbase1` and `zbase2`).

Work:

- Port the Handler composite creature, reusable infantry precache/transition,
  released Hound accounting, `mteam`, monster totals, and save lifecycle.
- Finish crate/seat/comm-dish/security-camera behavior used by the two maps.
- Audit all Base-unit `active`, mirror metadata, help, items, triggers,
  changelevels, secrets, co-op starts, and spawnpoint transitions.
- Validate the complete start cinematic chain into `zbase1`.
- Capture per-map health/monster/secret/objective baselines by skill and mode.

Exit criteria:

- A new single-player game can watch/skip supported cinematics, complete both
  Base maps on skills 0–3, and cross into `zdef1`.
- Saves work before/after Handler release, camera view, objectives, and the unit
  boundary.
- Two-player co-op can complete the unit with correct keys/items, death,
  respawn, reconnect, and transition positions.
- There are no unknown entities, required-asset failures, stuck progression
  states, or four-times-fast AI decisions.

Playable output: milestone `0.5-base` (version name illustrative), clearly
labelled as partial campaign support.

### Phase 6 — Port the main enemy set and middle campaign

Goal: complete Defence, Wasteland, and Tomb gameplay systems.

Work:

- Port Hound melee/leap and schooling with a separate 10 Hz decision cadence
  and 40 Hz motion path. Capture its radius-2,000 peer list, sight range,
  speed/yaw averaging, leader decay/randomization, first-neighbor quirks, and
  separation from ZBoss cooldown storage.
- Port ceiling/floor Autocannons, styles, arcs, state, mover riding, damage, and
  destruction.
- Port Sentien's grounded hover locomotion, bullet/laser/fend/shield, pain,
  death, EMP, and team logic.
- Integrate stock-monster precache refactors only where Handler/custom spawns
  require them. D-043's generated audit now closes the static classification:
  only Infantry crosses a source boundary, the Rerelease baseline already owns
  that helper, Handler/Hound use cached native indexes, and the disabled legacy
  256-sound interceptor is not ported. Complete all-map referenced-index,
  audible, Handler conversion, and native-expansion isolation proof. Port
  genuine Zaero stock-AI changes such as Hover dodge/strafe and EMP/flash
  interactions behind compatible defaults. D-042's static Hover slice covers
  all 22 supplied placements without changing native Daedalus; complete its
  seeded live direction/collision/expiry/save matrix.
- Complete shared projectile-dodge integration and `M_ReactToDamage` behavior
  for players, monsters, non-monster Autocannons, `AI_SOUND_TARGET`, `mteam`,
  and attacker-enemy indirection; reject pathological self-selection through
  the documented FIX without changing ordinary reactions.
- Complete Landing/Energy/Lava/Slime key flows, map IREDs, barrier, tomb
  timer/push/mover behavior, and all unit transitions.
- Audit every custom monster frame AI function for 40 Hz side effects and every
  callback/mmove for save registration.

Exit criteria:

- `zdef1`–`zdef4`, `zwaste1`–`zwaste3`, and `ztomb1`–`ztomb4` are completable
  on skills 0–3 from both fresh starts and carried campaign state.
- Monster counts, scripted awakenings, team relationships, schooling,
  autocannon riders, EMP responses, and keys match recorded expectations.
- Rocket/BFG/Flare-versus-Blaster dodge cadence and saved timeout pass on stock
  and custom monsters; the full reaction matrix passes without self-enemies.
- School tests cover yaw wraparound, non-schooling neighbors, peer loss,
  obstacles, save/load, leader selection, and a Hound within range of ZBoss
  without corrupting boss time.
- Saves round-trip during every attack/pain/death state, Hound school update,
  Sentien fend, moving Autocannon, map IRED, and critical puzzle.
- The inert `tomb1` changelevel has D-011's generated, tested no-patch
  disposition; valid Tomb routes still pass their live matrix.
- Co-op progression reaches `zboss` without item-instancing or squad-respawn
  softlocks.

Playable output: milestone `0.7-campaign`, all campaign content except verified
finale parity.

### Phase 7 — Port ZBoss and the finale

Goal: complete the campaign end to end.

Work:

- Complete and live-verify the implemented ZBoss health-by-skill, target logic,
  rockets/flares/plasma, grapple/drag, EMP reactions, damage scaling,
  taunts/state, 42nd-qualifying-pain retaliation, separate below-25%-health EMP
  path, isolated typed/saved 30–35-second cooldown, death barrage, and one-shot
  target markers. Static contracts and a retained legacy v1 load/spawn sample
  are present; neither substitutes for phase, damage, lifecycle, save, co-op,
  encounter, or current launch-safety proof.
- The positive-health inbound `zboss` player reset now retains health only,
  reinitializes persistence, grants Push, Blaster, Flare Gun and three flares,
  and uses the Rerelease fresh-body lifecycle to distinguish first entry from
  reload and death for each local/network client. Static contracts pass; live
  first-entry/reload/death/level-travel/co-op/split-screen proof remains.
- Make boss-owned entities robust to target/owner death, co-op target switches,
  disconnect, save/load, and entity-slot reuse.
- The five-second white finale fade and exact authored
  `outro.cin+victory.pcx` handoff now have a Zaero-owned typed-duration path
  through native per-client screen blends and `gamemap`. Static color,
  duration, gating and chain contracts pass; live fade frames, cinematic,
  victory art, skip/return/menu and co-op/split-screen proof remain.
- Validate final objective/intermission/achievement-compatible behavior without
  relying on a custom protocol opcode.

Exit criteria:

- The campaign is completable from a new game through victory on skills 0–3.
- Saves at each boss phase and while grappled restore safely and deterministically.
- Pain callbacks 41/42/43, the below-25% branch, seeded 30–35-second cooldown,
  Hound proximity, and every boss runtime helper pass boundary and save tests.
- Fresh inbound entry, reload, death/respawn, co-op and split-screen inventory
  resets retain only the intended health/loadout and never reset the wrong client.
- The boss cannot strand co-op/split-screen players after a target death,
  disconnect, or transition.
- Fade color/duration, death targets, outro, victory art, return/menu state, and
  credits behavior match the compatibility decision.

Playable output: milestone `0.8-complete`, full single-player campaign beta.

### Phase 8 — Multiplayer, co-op, deathmatch, bots, and native integration

Goal: harden all authored multiplayer paths and coexist with Rerelease features.

Work:

- Test and decide defaults for instanced items, squad respawn, player collision,
  key ownership, and social-ID slot restoration.
- Test two-, three-, and four-player network co-op plus two-local-client
  split-screen combinations across every unit.
- Complete all six `zdm` maps, campaign-map DM starts, spawn safety, item
  respawn/drop behavior, kill MODs/messages, spectator/intermission paths, and
  `zdmflags`.
- Validate custom-item auto-injection on stock/community maps both when no
  custom item exists and when exactly one exists.
- Add correct bot item/weapon/trap/projectile metadata and safe behavior with and
  without navigation. Treat sophisticated custom-weapon bot tactics/native
  monster navigation as separately measurable enhancements.
- Verify dedicated server, mixed input clients, reconnect, map rotation, and
  server-info cvars.

Current implementation evidence: D-045 provides the exact numeric bits,
eight-item precondition/order, wrapping start walk, four-attempt 16/128-unit
placement sweep, interim Bounce state, partial-success count, native item/save
lifecycle, and mapper-classification isolation. The normalized audit proves all
20 supplied maps suppress the positive path because each has at least one set
member. Five private legacy v1 single-stage Debug reports record eligible stock
`q2dm1` aggregate counts 8/8/disabled/disabled for values 0–3 and record that
authored `zdm1` suppresses injection. Three structured reports further record
the exact eight identities/order, successive first-attempt starts,
128/16-unit offsets, final origins and live native item state, plus zero records
for bit-2 and authored suppression. A fourth structured private report uses a
deterministic locally derived BSP with four starts inside real collision brushes
and records the other four placements at historical set indices 0/2/4/6 and
wrapped ordinals 1/6/11/16. Eight further legacy v1 structured reports each
contain exactly one historical member and record zero additions. They must be
rerun through the v2 protocol before they count as current windowed runtime
evidence or close a live single-member suppression case. This
does not close live multiplayer, server-info persistence, pickup/respawn/save,
dedicated, or native-mode work above.

The private v2 scenario inventories now make the reruns executable rather than
implicit: `tools/runtime-scenarios-dm.json` schedules `q2dm1` values 0–3 and
authored `zdm1` suppression, while
`tools/runtime-scenarios-dm-fixtures.json` schedules the partial-placement map
and every one-member fixture after its explicit private overlay is installed.
They remain Debug-only probe runs and inherit D-046's window-before-mod/map,
engine-confirmed-delivery, cleanup, and non-public-evidence requirements.

D-013's 1.0 safety slice is now implemented: all sixteen appended Zaero items
continue through the native generic bot item-ID/state registry, bot-facing
item/weapon entrypoints reject null or terminal IDs before indexing the expanded
table, and the active Flare, IRED bomb/beam/shrapnel, EMP center, Sentien beam,
and ZBoss hook/plasma expose native trap or laser-field metadata. This changes
no legacy collision, damage, or timing behavior. Static registry/bounds/trap
endpoint/free-unregister contracts pass; live navigation/no-navigation ZDM
sessions remain required before bot compatibility is verified.

Exit criteria:

- Authored co-op has no progression, key, item, view, transition, or save
  softlocks through the complete episode.
- `zdm1`–`zdm6` pass timed 2/4/8-client and bot smoke sessions without crashes,
  leaks, missing resources, invalid inventory, or stuck camera states.
- Both `zdmflags` bits and all four combinations have tests.
- A non-Zaero DM map receives exactly the historic eight-item injection when
  eligible, and none when ineligible.
- Split-screen views/HUD/wheels/Visor/zoom/blends are isolated per player.

Playable output: milestone `0.9-multiplayer`, release-candidate feature set.

### Phase 9 — Fidelity, hardening, and 1.0 release

Goal: turn feature completeness into a supportable, reproducible engineering
candidate and, when rights permit, a playable public release.

Work:

- Close every feature/entity/map/quirk matrix row with evidence and a test.
- Perform full original-versus-port timing/damage/AI captures for boundary cases.
- Run clean-machine, clean-profile, upgraded-profile, dedicated-server, and
  offline/importer installation tests.
- Profile entity counts, save size/time, CPU, network state, resource indexes,
  and long-running projectile/monster lifetimes.
- Run static analysis and defect-focused review of every legacy-derived buffer,
  pointer, callback, random choice, entity handle, trace result, and format call.
- Finalize editor definitions, localization/fallback strings, README,
  changelog, credits, notices, license, support matrix, and troubleshooting.
- Generate and independently validate the exact mode-specific SBOM, harvested
  licenses, `LICENSE_SCOPE.md`, and corresponding-source bundle.
- Exercise dry-run and draft GitHub release, independently verify archive
  contents/checksums, and archive audit artifacts.

Engineering/private readiness criteria:

- All gates in Sections 13 and 16 pass from a clean checkout.
- No compatibility row is “unknown”; deferred enhancements are explicitly
  outside 1.0 rather than untracked.
- No blocker/critical defect is open; accepted lower-severity quirks are
  documented.
- A private `local-full` candidate has completed the entire live matrix and its
  exact commit/manifests/readiness evidence are retained. This proves technical
  readiness only and never authorizes publication.

Additional playable-public-release criteria:

- The public-distribution/provenance gate permits an importer-kit or the
  distinct `asset-full` mode for the exact artifact. A tools-only publication
  may accompany progress but cannot satisfy the playable 1.0 gate.
- An importer-kit candidate is completed with legitimate local content, then
  installed and completed by someone other than its packager; an asset-full
  candidate receives the equivalent independent install/completion test.
- The mode-specific SBOM/license scope and harvested texts match the payload;
  every DLL has verified exact corresponding source for the same commit,
  version, dependency baseline, and build instructions.
- The draft's mode, inputs, code/media policy, checksums, readiness record and
  protected approval agree before promotion to stable.

Playable output: ZaeREo 1.0 only when the additional public criteria pass.
Otherwise the phase may produce a technically complete private candidate and a
non-playable tools-only progress artifact, but not a public playable 1.0 claim.

### Phase 10 — Post-parity enhancements

Only after the 1.0 baseline remains continuously testable:

- remastered textures/materials/models/sounds and optional cinematic upgrades;
- Rerelease-native localization and accessibility improvements;
- navigation generation and richer bot/custom-monster tactics;
- additional platforms/toolchains;
- mapper SDK/examples and community-map compatibility;
- opt-in fixes or balance modes for historic quirks;
- source-map restoration only where provenance permits and geometry/entity
  behavior can be regression-tested against original BSPs.

Each enhancement must be an overlay or separately versioned decision, with an
original-compatibility mode retained.

## 13. Verification strategy and release gates

### 13.1 Static and generated checks

Every pull request should run:

- source-baseline drift and project-file completeness checks;
- format/compiler/static-analysis checks;
- spawn registry versus BSP classname/key matrix;
- item ID/classname, HUD stat, wheel-slot, configstring, damage MOD, callback,
  and mmove uniqueness/capacity checks;
- JSON schema coverage for added state;
- asset manifest/hash/case/reference/override validation;
- deterministic PAK and ZIP reproduction;
- mapdb/config/episode-chain validation;
- forbidden-artifact and license-header scan.

### 13.2 Behavioral golden tests

Build small deterministic fixtures with fixed random seeds and record:

- exact damage, armor, health, knockback, radius/LOS, ammo, and timing for every
  weapon/item at minimum/maximum/Quad/EMP boundaries;
- projectile velocity, lifetime, bounce, contents masks, owner immunity, sky,
  water, barrier/shield, and cleanup;
- monster frame-event order, decision cadence, movement distance, targeting,
  team response, pain/death, EMP/flash, and skill scaling;
- mover acceleration, deceleration, rider offsets, block behavior, toggles,
  save restoration, and random-target selection;
- inventory limits, Pack/Bandolier, pickup/drop/death/respawn, wheel/alias
  selection, and co-op instancing;
- camera/Visor/zoom/help/fade/HUD behavior per client.

Where the old DLL can be run legally and repeatably, capture its console/state
results in a controlled legacy engine. Otherwise derive the expected result
from source with a documented hand calculation and retail play observation.
Never make an undocumented screenshot the sole oracle.

### 13.3 Per-map automated smoke

For each of the 20 BSPs:

1. start the correct game mode and skill;
2. load from a clean game and, where relevant, via its inbound spawnpoint;
3. enumerate spawned/inhibited/free entities and resources;
4. fail on unknown classname/key, missing asset, invalid model/sound/image index,
   NaN, callback/save error, or console error;
5. run a bounded simulation interval;
6. write a normalized report of counts, objectives, starts, custom entities,
   and transitions.

The smoke suite complements, but does not replace, real completion runs.

### 13.4 Single-player matrix

- Full new-game runs on skills 0, 1, 2, and 3.
- Fresh-map developer starts for each BSP, clearly distinguished from valid
  carried inventory/cross-level state.
- Every secret, objective/help update, key, cinematic, spawnpoint, unit boundary,
  death/reload, finale, and victory path.
- Saves immediately before/after transitions and during all complex systems.
- Long idle/timeout cases for IRED, EMP, Shield, Visor, movers, schools, and boss.

### 13.5 Save matrix

At minimum, save/load:

- each custom weapon idle, activating, firing/charging, and deactivating;
- armed/arming/expiring IREDs; active EMP; Shield; A2K countdown;
- Visor entering/tracking/cycling/exiting plus player copy;
- accelerating/blocked movers, rider cannon, random timer, active/inactive
  camera, revealed barrier, toggled trigger;
- Handler before/during/after release; Hound leap/school; Sentien attacks/fend;
  each boss attack, grapple, pain, death phase;
- every map and unit transition, co-op checkpoint, and cross-level flag.

Also load a save after rebuilding the same version to detect callback-name or
item-classname instability. Development save compatibility across schema
changes follows this policy:

- pre-1.0 saves are supported only by the exact artifact unless a milestone
  explicitly promises otherwise; incompatible development schemas fail with a
  clear version diagnostic rather than partially loading;
- 1.0 introduces an explicit ZaeREo save-schema version independent of package
  SemVer. Stable item classnames, serialized callback/mmove names, and field
  meanings are compatibility identifiers;
- patch/minor releases within a supported major line must read saves from every
  earlier supported schema in that line. Renames require aliases/migrations;
  removals retain a safe reader until the support window closes;
- unknown newer schemas are never overwritten or “best effort” loaded.
  Downgrade loading is unsupported unless a fixture proves it;
- retain sanitized/synthetic golden saves for every released schema and run all
  forward migrations in CI plus the private runtime lane; and
- every migration is deterministic, idempotent where retried, preserves unknown
  target-native data where possible, logs its source/target version, and has a
  rollback/recovery note. The release manifest states the readable schema range.

### 13.6 Co-op and split-screen matrix

- Two, three, and four network players; reconnect and restored slots.
- Two local players, and local plus remote combinations supported by the engine.
- Friendly fire on/off, player collision modes, instanced items on/off, squad
  respawn on/off, and key sharing.
- Simultaneous Visor/zoom/help/wheel/inventory effects.
- Player death/disconnect while owning a mine, shield, EMP, camera copy, school
  target, boss hook, or boss aggro.
- Full episode progression and transitions; all 121 authored co-op starts
  validated for placement/availability.

### 13.7 Deathmatch matrix

- `zdm1`–`zdm6` with 2, 4, and 8 clients/bots where supported.
- Campaign maps in deathmatch, covering all 230 authored starts.
- Item respawn, dropped items, infinite ammo, Quad, damage MODs, kill messages,
  intermission, timelimit/fraglimit, spectators, map rotation.
- `zdmflags` values 0, 1, 2, and 3.
- Eligible stock map, map containing one custom item, and map containing the full
  custom set for injection's all-or-none behavior.
- Players with/without the legacy blend preference equivalent.

### 13.8 Assets, audio, and presentation

- Reference closure for every entity/item/animation frame and every map at
  runtime.
- No unintended case dependence on Windows; validate as if the filesystem were
  case-sensitive.
- Sound-index headroom and audible sampling of previously affected levels
  (`zdef1`, `zdef4`, `ztomb1`, `ztomb3`).
- Music values 1–11, logos, intro/outro, victory art, missing-music fallback,
  cinematic skip, and volume/subtitle behavior.
- Original aspect ratios/palettes/transparency, sprite orientation, model skins,
  animation frames, effect colors, dynamic lights, and white finale fade.

### 13.9 Performance and robustness

- Four-hour dedicated-server soak and repeated map rotation.
- Entity churn with maximum IREDs, projectiles, shields, camera copies, schools,
  and boss effects.
- No stale entity handles, invalid callback names, unbounded camera loop,
  resource-index growth, PAK nondeterminism, or save-state growth.
- CPU/network comparison at 40 Hz, especially schooling, radius scans, Visor,
  laser traces, EMP scans, and boss attacks.
- Malformed map keys/long timer targets/long item commands fail safely.
- Clean shutdown/unload/reload and repeated developer installation.

### 13.10 Private runtime lane for live gates

Public CI uses synthetic fixtures and may validate hashes/manifests, but cannot
claim map or campaign parity without running the legitimate content. Maintain a
separate Windows self-hosted or otherwise private runner for live gates:

- provision the Rerelease executable/data and Zaero installation outside the
  repository through runner administration; workflows receive only approved
  root paths, verify recorded hashes, and import into an ephemeral managed
  workspace;
- never expose that runner or its content-bearing secrets to fork pull requests,
  arbitrary branches, or unreviewed workflow code. Run only protected commits
  after explicit approval, with least-privilege GitHub permissions and no
  publication credential in the gameplay job;
- execute the same build/package wrappers plus the scenario-driven runtime
  harness; use fresh profiles, bounded timeouts, clean stages, and deterministic
  seeds where possible;
- upload only normalized counts, pass/fail records, hashes, timings, sanitized
  console excerpts, crash stacks, and synthetic screenshots approved for
  distribution. Never upload the Rerelease base game data, saves containing
  embedded base game data, full logs that dump asset content, or the completed
  local package; and
- wipe ephemeral imports/stages after the job and periodically audit the runner,
  credentials, logs, retention, and installed baseline hashes.

Manual retail comparison can augment this lane, but records the build/version,
platform, setup, observer, expected/actual result, and reproducibility. “Passed
on a developer machine” without a retained normalized result cannot close a
VERIFIED row.

### 13.11 Machine-readable release readiness

The initial [generator/validator](../tools/release_readiness.py) and pinned
`release-readiness.schema.json` now write an ignored
`dist/release-readiness.json`. They validate the active distribution policy and
mode/profile relationship, fingerprint `VERSION`, baseline/upstream/audit/
ledger/runtime-scenario inputs, record source cleanliness and policy identity,
and reject a hand-promoted `ready: true` record that contradicts the policy. The
output is deliberately non-publishing and must remain below `dist/`; current
records are expected to be `ready: false` because the port has not yet earned
its playable-stable evidence, not for any rights reason.

Extend that evaluator, without adding an override, to consume the current
commit, baseline/data-build hashes, build/export/test results, compatibility
ledgers, map completion matrix, live-run reports, asset/provenance mode,
save-schema range, editor/package checks, and known-issue policy. It is
generated output, signed or attested where practical, and cannot be hand-
authored to waive a gate. Both the internal/external release manifests and
readiness record validate against their pinned schemas before any policy
evaluation.

Every remote publication names a mode, channel, and readiness profile. The
validator has distinct, non-promotable profiles:

- `tools-progress`: the tools automation only; exact per-file
  tool/license/channel allowlist, no DLL/gameplay source/media/object-bearing
  cache, deterministic/security tests for the acquisition tools, exact manifest/
  SBOM/checksums, and prominent non-playable/prerelease labeling. Gameplay/map
  completion is deliberately not a gate for this profile.
- `playable-candidate`: a code-cleared importer-kit or code/media-cleared
  asset-full nightly/draft; all applicable build, corresponding-source,
  provenance, package/import-completion, ownership, and candidate test gates
  pass, but it remains explicitly non-stable while any 1.0 gate is open.
- `playable-stable`: the full 1.0 gate below. A reduced tools/candidate record
  cannot be relabelled, copied, or promoted into this profile.

`local-full-private` may produce a private engineering record but is not a
publication profile. Stable publication requires `playable-stable` to prove,
for the exact commit and artifact hashes:

- every 1.0-required feature/entity/quirk row is `VERIFIED`, every map/mode gate
  is closed, and no required proof link/result is missing or stale;
- Debug/Release/export, deterministic package, clean install/update/uninstall,
  stock-regression, private live campaign/co-op/DM, save-schema, editor, soak,
  security, and provenance checks all passed within the release candidate;
- no blocker/critical issue is open and every accepted limitation is linked to
  the changelog/release notes; and
- the selected distribution mode is legally eligible and matches the internal
  and external manifests.

`publish_github_release.ps1` and the stable workflow consume this file and fail
closed. Generic `-Force`, `-AllowDirty`, or workflow rerun switches cannot turn
a non-ready artifact into a stable release. The distribution mode/provenance/
channel decision, permanent `local-full` prohibition, clean and exact source
commit, tag/version identity, archive checksum and per-file allowlist, critical
security results, corresponding-source/license obligations, and every required
feature/entity/quirk/map/mode gate are non-waivable. A reviewed decision record
may waive only a gate explicitly classified as optional/deferred for the chosen
profile, must remain visible in the readiness document, and can never change a
`ready: false` playable-stable result to true.

## 14. Dependencies, risks, and mitigations

| Risk | Impact | Mitigation and gate |
| --- | --- | --- |
| GPL notices or credits get dropped from ported content | The GPL requires notices and attribution to travel with the work | Preserve per-file copyright headers and the original authors' credits; the packager harvests notices and ships complete corresponding source with any DLL. |
| A release accidentally bundles non-GPL content | Shipping the Rerelease soundtrack or base game data would redistribute Nightdive/id commercial content | Package allowlists and the soundtrack/base-data boundary (§7.5, D-010) keep only GPL Zaero content in releases; rely on the user's own Rerelease install for its media. |
| Supplied source differs from the final retail DLL | Source parity may not equal player-observed parity | Preserve retail installation/version evidence; capture focused retail behavior where uncertainty matters; label inferred tests. |
| Wrong or unpinned Rerelease baseline | Future updates become unreviewable and API behavior moves underneath the port | Import a pristine commit/archive first, record hashes, keep upstream sync notes, and gate baseline changes through the full suite. |
| 10 Hz logic runs four times per second too often at 40 Hz | AI, damage ticks, random choices, charge, and effects diverge | Audit every think/frame callback and probability; split decision cadence from motion; use duration/golden tests. |
| Legacy raw pointers/functions cannot survive JSON save | Corrupt or unloadable saves, stale entities, crashes | Stable callback/mmove names, complete schemas, entity handles, cached resource indexes, and lifecycle-phase round-trip tests. |
| Custom fields/flags collide with integrated expansion/Rerelease state | Maps filter or behave incorrectly | Typed namespaces, compile-time uniqueness checks, BSP per-class matrices, and no numeric copy without target-source review. |
| Rerelease co-op defaults change authored puzzles | Keys/items/players can softlock progression or duplicate rewards | Test instancing, squad respawn, collision, reconnect, and key policy on every unit; select explicit ZaeREo defaults. |
| Visor/camera/grapple redirects player state | Split-screen leakage, input lock, disconnect/save failures | Per-client handles and cleanup state machine; zero/all-inactive cameras; local/remote/death/disconnect tests. |
| Old undefined behavior hides intended quirks | “Cleanup” changes play, while literal ports remain unsafe | Capture expected valid cases first, then fix memory/UB defects under quirk-ledger decisions. |
| Asset path case/override/loose-file assumptions | Missing media on other platforms or in packaged build | Canonical manifest, last-layer origin, case-collision checks, reference closure, and test staged archive rather than source tree. |
| Zaero-only mapdb replaces the target data build | Stock/expansion episodes disappear or future data updates conflict | Deterministically merge a tracked fragment locally from the user's hash-verified target data unless policy clears the exact base bytes; preserve upstream order/unknown fields, prove reversible semantics, and retain console-start fallback. |
| Program-directory installation or unmanaged update | Elevation, game repair, or deletion can damage the mod/user files | Default to the upstream per-user Saved Games root, separate engine/content roots, and mutate only manifest-owned files. |
| Videos and binary assets stress Git/release hosting | Clone bloat or hosting rejection | Decide LFS/importer mode before commit; never version generated PAKs/ZIPs; verify artifact limits and checksums. |
| Custom effects need protocol support cgame cannot provide | Visual behavior blocked without engine changes | Prefer existing events/entities/layouts; make any engine fork an explicit, independently reviewed scope decision. |
| Integrated base/mission-pack/bot behavior regresses | The DLL loses Rerelease value and DM injection on ordinary maps breaks | Retain native client/bot/expansion paths, add stock-map smoke, and isolate Zaero hooks behind class/game checks. |
| Scope expands into remastering before parity | No stable baseline and difficult bug attribution | Keep Phase 10 overlays after 1.0; original content and compatibility mode remain continuously testable. |
| Release automation mutates GitHub incorrectly | Lost/overwritten tags or misleading artifacts | Package separately, dry-run, clean-tree/current-commit checks, draft default, explicit publication, protected stable workflow. |
| Private live runner leaks licensed content or credentials | Legal/security incident and untrustworthy evidence | Protected-commit approval only, least privilege, external hash-verified inputs, sanitized normalized outputs, no publication token, ephemeral stages, and periodic audit. |

### Critical path

The effective dependency chain is:

`provenance/baseline → clean Rerelease build → spawn/save/time spine → assets and
map semantics → player systems → Handler/Base unit → remaining monsters/units →
ZBoss/finale → multiplayer hardening → release gates`.

Editor polish, additional platforms, enhanced navigation, bots' tactical use of
custom weapons, and remastered assets can proceed in parallel only when they do
not alter this chain or consume unverified runtime contracts.

## 15. Decision register

Record resolved choices in `docs/compatibility/decisions.md`. These are the
initial decisions that cannot be left implicit:

| ID | Decision | Recommended starting position | Due |
| --- | --- | --- | --- |
| D-001 | Product/game directory | `ZaeREo` / `zaereo` | Phase 0 |
| D-002 | Rerelease baseline | Official pinned upstream commit; archive hashes if unavailable | Phase 0 |
| D-003 | Source license and media distribution | Zaero source and assets are GPL-released; `distribution-policy.json` records code and media as GPL-distributable; publishing a release is a human-approved step; `local-full` stays developer-only | Phase 0 |
| D-004 | Git binary strategy | LFS for the GPL canonical source assets (or the importer for importer-kit); never generated PAKs | Phase 0 |
| D-005 | Compatibility bug policy | Default to parity, fix memory safety/undefined behavior with tests | Phase 0 |
| D-006 | Rerelease co-op defaults | Choose from map tests; do not inherit accidentally | Before Phase 5 |
| D-007 | Flare `gl_polyblend` compensation | Historic parity mode with documented server control; evaluate safer default before 1.0 | Phase 4/8 |
| D-008 | Visor command/chat restrictions | Preserve gameplay lock and Visor-only use/inventory commands; route chat through native Rerelease lobby handling | Live multiplayer/split-screen command matrix |
| D-009 | Loose sprites/videos | Keep loose until packed behavior is verified on target | Phase 2 |
| D-010 | Music tracks 1–11 | Reuse target-native numeric 2–11 without distributing media; preserve value 1/invalid as logged silence | Phase 2/7 live audio matrix |
| D-011 | `ztomb1` absent `tomb1` target | Preserve exact sole orphan/missing changelevel as inert; no alias or data patch | Reopen on a supported map revision that references/supplies it |
| D-012 | New protocol/engine fork | Avoid for 1.0 unless a required effect is impossible through supported APIs | Phase 4 |
| D-013 | Bot/navigation scope | Safe metadata/fallback for 1.0; advanced tactics/pathing post-parity | Phase 8 |
| D-014 | Legacy demos/saves | Archive evidence only; no playback/load promise | Phase 0 |
| D-015 | Source debug/test tools | Developer-only; identity-locked source/project policy plus path-scoped source, Release DLL, and ZIP deny gates; revision 2 contains D-045's read-only `_DEBUG` probe and forbids both signatures from Release | Static source/DLL/four-package scans pass; the retained v1 Release smoke is historical only. Close after an equivalently clean v2 two-stage window-before-mod/map load/spawn/client/shutdown rerun, then reopen for any new developer surface |
| D-016 | Stable release publication | Manual/draft approval using CI-equivalent scripts | Phase 9 |
| D-017 | Remastered content | Optional overlay after 1.0, never replaces parity baseline | Phase 10 |
| D-018 | Zaero semantics on stock classnames | Separate content/gameplay activation from hash/metadata/signature-proved mapper semantics; retain native stock meanings elsewhere | Phase 2/3 |
| D-019 | Autocannon style-4 idle overread | Preserve the shipped false result with bounded data, not undefined memory access | Phase 6 |
| D-020 | Selective EMP matrix and BFG latch | Explicit attack-type hooks, saved non-colliding latch, and source-order/audio tests; never a blanket weapon disable | Phase 4/6/7 |
| D-021 | Visor copy collision | FIX link-order-dependent absorption: keep the real player solid/vulnerable and the visual copy non-solid | Live hitscan/projectile/mover/save/multiplayer matrix |
| D-022 | Hound schooling transient state | Keep school scans local while preserving visible peer/yaw/proximity quirks | Phase 5/6 |
| D-023 | Handler split identity/accounting | Preserve duplicated durability with stable identities and pre-reserved native counts | Phase 5 |
| D-024 | Sentien locomotion/laser lifecycle | Preserve grounded hover and mitigation; generation-check and free the persistent beam | Phase 6 |
| D-025 | ZBoss child/projectile lifecycle | Preserve source attacks with generation-checked hooks/projectiles and single terminal damage | Phase 7 |
| D-026 | ZBoss inbound persistence | Apply the exact fresh-entry loadout per client without corrupting loadgame/death lifecycle | Phase 7 |
| D-027 | Finale fade/handoff | Five-second per-client white blend with continued world work and authored native handoff | Phase 7 |
| D-028 | A2K deadline/radius boundaries | Typed per-client five-second deadline plus source-shaped dual damage walker; no countdown entity | Phase 4 |
| D-029 | Plasma Shield collision/durability/placer identity | Preserve ownerless source collision and mitigation; generation-check non-collision placer metadata | Phase 4 |
| D-030 | Visor duration representation/incremental gate | Typed carrier/drop duration drives the active elapsed-time lifecycle; D-021 is resolved | Live pickup/drop/active-state/save matrix |
| D-031 | Weapon-number multiselect/native wheel | Follow source/config 1–10 semantics, isolate the exact alternate table from native weapon chains, and retain the native wheel in parallel | Phase 4 |
| D-032 | Player HUD/lifecycle/obituary presentation | Preserve client-local showorigin, native five-second kill lifecycle, exact safe obituary fallbacks and Zaero skin-first gender while isolating stock maps | Phase 4/8 |
| D-033 | Projectile-dodge timing/native coexistence | Preserve Zaero's exact firing-time Rocket/BFG/Flare trace and saved two-stage throttle on classified maps; retain native proximity dodge elsewhere | Phase 4/6 |
| D-034 | trigger_laser mapper/lifetime contract | Preserve exact no-use auto-start/rearm/free behavior and generation-check the entity after target dispatch | Phase 3 |
| D-035 | Step-physics trigger-free safety | Retain Rerelease post-trigger lifetime validation and mirror it in custom FallFloat | Phase 3 |
| D-036 | func_plat bit-2 low-trigger collision | Apply Zaero's inclusive eight-unit feet boundary on classified maps and preserve native no-monster semantics elsewhere | Phase 3 |
| D-037 | misc_explobox FALLFLOAT/push contract | Gate mass-400 FALLFLOAT and airborne client SV_movestep pushing while retaining native barrels elsewhere | Phase 3 |
| D-038 | func_door_rotating zero-damage default | Preserve missing/zero and positive Zaero damage values while retaining native Rerelease defaults elsewhere | Phase 3 |
| D-039 | Train/path-corner colliding mapper semantics | Scope node speed/smooth/teleport/Viper/rotation behavior and retain native/Rogue train bits elsewhere | Phase 3 |
| D-040 | Health pickup sound concurrency | Select Zaero's 2/10/25/default sound per pickup without shared item mutation; retain explicit/native paths | Phase 4 live concurrency matrix |
| D-041 | Zaero monster damage reaction/self-target safety | Layer Autocannon, mteam, tank and retained-sound deltas onto native reaction; preserve the self guard and expansion lifecycle | Phase 6 live combat/save matrix |
| D-042 | Hover fly-strafe/expired-state reset | Preserve the exact Zaero-only radial dodge in a dedicated saved state; FIX the comparison typo and retain native Hover/Daedalus flight elsewhere | Phase 6 live seeded/collision/expiry/save matrix |
| D-043 | Stock-monster precache extraction/sound-index strategy | Reuse the existing native Infantry helper only for Handler/conversion, keep other stock spawns native, use cached indexes, and omit the disabled 256-sound interceptor | Phase 5–6 all-map resource/audio and Handler conversion matrix |
| D-044 | Global SV_FlyMove duplicate-plane delta | Retain the unmodified shared Rerelease 0.99 near-duplicate/1.01 overclip solver; do not import Zaero's one-line exact-repeat residual dead-stop globally or through a map fork | Phase 3 live windowed clip/caller-isolation matrix |
| D-045 | zdmflags and deathmatch item injection | Preserve external bits 1/2 and the exact eight-item precondition/order/wrapping-start/placement/partial-count pass through native item lifecycle; keep it independent of mapper classification | Phase 8 v2 reruns for values 0–3, eligible/ineligible including all eight one-member controls, exact open placement/native-drop state and real-brush partial placement; then multiplayer/save/dedicated/server-info and native-mode isolation |
| D-046 | Two-stage visible window-before-mod/map runtime launch | Bootstrap visibly with `-window`/`v_windowmode 0`, inspect every exact-PID top-level window, then use caller-queue-attached/task-switch-retried foreground-gated system input for the mod/map only after a captioned/non-popup result and record residual-PID cleanup | Private v2 reruns of Release/campaign/DM/fixture smokes; command-delivery proof on every supported KEX distribution |
| D-047 | Legacy PAK layer to runtime ownership semantics | Retain audited `pak0 < pak1 < pak2` source precedence and final effective paths/bytes while allowing a deterministic import-owned effective `pak1` beside project-owned `pak0` | Override/origin/loose/case/reference/collision and package/install lifecycle proof |
| D-048 | Release-readiness evidence | Generate schema-valid readiness records that fingerprint policy, source state, ledgers, and requested mode; publishing additionally needs human approval of a draft | Add package/SBOM/build/live evidence collectors |
| D-049 | Rerelease material and glow-map asset generation | Keep checked-in text `.mat` descriptors project-owned while generating `_glow.png` maps only from verified local imports as private import-owned output | Visual lookup proof, tuning review, and ownership lifecycle checks |

Every decision record needs context, alternatives, behavioral impact, evidence,
date/owner, and tests or migration consequences.

## 16. Definition of done

### 16.1 A feature is done when

- its source/map/asset evidence is linked;
- every contributing source-delta and mapper-contract coverage record is linked
  to the same feature/entity/quirk/decision disposition;
- `PARITY`, `ADAPT`, or `FIX` is recorded;
- Rerelease-native implementation is reviewed;
- all new fields, callbacks, moves, resources, IDs, UI strings, multiplayer
  ownership, and cleanup paths are registered;
- deterministic focused tests cover ordinary and boundary behavior;
- save/load and 40 Hz behavior are tested where state/time exists;
- relevant map/entity/editor/README matrices are updated;
- no new compiler/static/runtime/resource warning remains.

### 16.2 A map is done when

- it loads from the intended inbound transition and a supported fresh start;
- all entities/fields/assets resolve and all scripted targets can fire;
- objectives, keys, secrets, monsters, items, sounds, movers, transitions, and
  finale/cinematic paths work;
- it is completable in intended single-player and authored co-op modes;
- its authored deathmatch starts work where applicable;
- representative mid-map and pre/post-transition saves round-trip;
- its normalized smoke report is committed and stable.

### 16.3 A playable public release is done when

These are stricter than private engineering readiness. A `local-full` candidate
may supply normalized technical evidence but is never the published artifact;
a tools-only archive is not installable/playable and cannot satisfy this
definition.

- clean checkout/bootstrap/build/package succeeds in CI and on a second machine;
- full single-player, co-op, split-screen, and deathmatch gates pass;
- all 20 map rows and every in-scope feature/entity/quirk row are `VERIFIED`;
  any approved `DEFERRED` enhancement is explicitly excluded from the release
  by a compatible decision and readiness record;
- the release uses the bundled `asset-full` mode or the `importer-kit` mode for
  the exact artifact; the mode is neither tools-only nor `local-full`;
- deterministic PAK/ZIP hashes and archive allowlist pass;
- install, start, update, and uninstall are verified without touching `baseq2`;
- README, changelog, version, license, notices, credits, editor package, known
  issues, and support instructions match the artifact;
- the `asset-full` build is independently installed and tested, or an
  `importer-kit` is independently completed from an installation and then
  installed/tested;
- symbols/audit reports/checksums are retained for diagnosis;
- the Git tag, source commit, manifest, package version, and release notes agree.

## 17. Audit appendices

### Appendix A — Source-tree delta summary

The supplied trees contain:

- 100 Zaero files and 78 legacy `game` files;
- 74 common relative paths;
- 26 Zaero-only paths and 4 legacy-only paths;
- two common paths byte-identical and 72 textually modified; review classifies
  46 common production source/header paths as carrying potential semantic
  deltas while the remainder are predominantly removed license headers or
  source-age layout drift;
- 57,566 C/header lines versus 46,874, with 10,494 lines in the 24 new
  `z_*.[ch]` files; and
- within common C files, a lexical function audit finds 50 added, 200 changed,
  and 12 removed definitions. Functions in Zaero-only modules are separately
  covered by the module/feature inventories rather than being conflated with
  common-file deltas.
- the same common-file lexical audit finds five added, 20 changed, and 12
  removed simple global declarations; complex declarations remain path-routed
  rather than being misrepresented as compiler-accurate semantic analysis.

Zaero-only paths:

~~~text
readme.txt
zaero.dsp
z_acannon.c
z_ai.c
z_anim.c / z_anim.h
z_boss.c / z_boss.h
z_camera.c
z_debug.c / z_debug.h
z_frames.c / z_frames.h
z_handler.c / z_handler.h
z_hound.c / z_hound.h
z_item.c
z_list.c / z_list.h
z_mtest.c
z_sentien.c / z_sentien.h
z_spawn.c
z_trigger.c
z_weapon.c
~~~

Legacy-only paths are `g_chase.c` and old generated/project artifacts
`game.001`, `game.dsp`, and `game.plg`. Zaero's absence of `g_chase.c` and many
shared-file changes must be classified against source age before being treated
as an intentional feature.

The old build is a Visual Studio 6 Win32 DLL configuration with a fixed image
base to make raw pointer saves viable. Release uses `NDEBUG`; debug enables
`_DEBUG`/`_Z_TESTMODE`. None of those ABI/build assumptions belongs in the
Rerelease target.

The 46 semantically changed common files are:

~~~text
g_ai.c       g_cmds.c     g_combat.c    g_func.c       g_items.c
g_local.h    g_main.c     g_misc.c      g_monster.c    g_phys.c
g_save.c     g_spawn.c    g_svcmds.c    g_target.c     g_trigger.c
g_turret.c   g_utils.c    g_weapon.c
m_berserk.c  m_boss2.c    m_boss31.c    m_boss32.c    m_brain.c
m_chick.c    m_flash.c    m_flipper.c   m_float.c      m_flyer.c
m_gladiator.c m_gunner.c  m_hover.c     m_infantry.c   m_insane.c
m_medic.c    m_move.c     m_mutant.c    m_parasite.c   m_soldier.c
m_supertank.c m_tank.c
p_client.c   p_hud.c      p_view.c      p_weapon.c
q_shared.c   q_shared.h
~~~

The 200 changed shared functions cluster as follows:

| Shared source area | Changed definitions | Zaero-relevant themes | Primary ledger routes |
| --- | ---: | --- | --- |
| `g_ai` | 5 | target visibility/reaction and custom flight | AI-012–AI-014, SYS-001, Q-013/Q-046 |
| `g_cmds` | 12 | alternate weapon slots, item visibility/use, camera command gating | PLY-012, PLY-016–PLY-018, SYS-013 |
| `g_combat` | 5 | armor/power armor, immortal damage, teams, EMP, reaction | MAP-018, PLY-005–PLY-007, PLY-009, AI-014, Q-003/Q-043/Q-046 |
| `g_func` | 29 | acceleration, doors, trains, rotating, timers, platforms | MAP-006, MAP-008–MAP-009, MAP-017–MAP-019, Q-020/Q-021 |
| `g_items` | 10 | ammo maxima, custom pickups/drops, item hiding/precaches | PLY-001–PLY-015, PLY-020, Q-008/Q-023–Q-025 |
| `g_main` | 4 | frame/exit/intermission behavior and DM flow | SYS-005, SYS-009, SYS-011–SYS-012, SYS-019 |
| `g_misc` | 5 | viper attachments, crates/barrels, path corners/player head | MAP-011, MAP-017, MAP-020, AI-008 |
| `g_monster` | 11 | fire helpers, cadence, trigger spawn, custom state | MAP-016, AI-011, AI-013, AI-015, SYS-001 |
| `g_phys` | 5 | dispatch, toss/step/fly/push and new movement types; D-044 retains the baseline shared plane solver | MAP-010, MAP-017, MAP-020, AI-001, AI-008, Q-021/Q-041/Q-047/Q-048 |
| `g_save` | 9 | raw legacy save ABI and added fields | SYS-002 and every stateful MAP/PLY/AI row |
| `g_spawn` | 3 | field parsing, worldspawn and mode filtering; D-045 moves the exact DM injection body into a Zaero-owned module with one post-team hook | MAP-001–MAP-005, MAP-014–MAP-015, SYS-012 |
| `g_svcmds` | 1 | reduced old server-command surface | SYS-015 source-version-drift guard |
| `g_target` | 4 | delayed explosion and custom blaster/spawner behavior | MAP-012–MAP-013, MAP-016, AI-005, AI-011, Q-026 |
| `g_trigger` | 2 | toggle/silent push | MAP-007 |
| `g_turret` | 2 | driver/breach fire integration | AI-011, SYS-015 |
| `g_utils` | 4 | entity free/use targets, angles, monster-safe killboxes | MAP-016, AI-014, SYS-002 |
| `g_weapon` | 8 | projectiles, dodge, barrier/EMP/custom effects | PLY-002, PLY-005, PLY-007, PLY-009, AI-011, AI-016, Q-002/Q-043/Q-049 |
| stock monster sources | 34 | 22-helper/19-file precache call graph, EMP/flash, Hover changes, audio and version drift | AI-003, AI-011–AI-013, AI-015, D-043; `docs/audits/stock-precaches.md` separates organizational helpers from behavior |
| `p_client` | 16 | loadout, persistence, death/respawn, camera/weapon state and obituaries | PLY-008, PLY-013, PLY-017–PLY-019, SYS-002, SYS-009–SYS-010, SYS-013 |
| `p_hud` | 4 | help, stats, scoreboard, finale intermission | MAP-013, PLY-005, PLY-008, PLY-016, SYS-013, SYS-019 |
| `p_view` | 7 | zoom/camera/blend/sound/effects/view | PLY-002, PLY-005, PLY-008, SYS-013, SYS-019, Q-044–Q-045 |
| `p_weapon` | 16 | all base fire paths plus custom integration/selection | PLY-001–PLY-009, PLY-012, PLY-015, AI-011, Q-043 |
| `q_shared` | 4 | parser/string-comparison source-version changes | Q-020 and SYS-015 source-version-drift guard |

The exact function-level report belongs in `docs/audits/source-delta.md` and is
a Phase 0 generated input. The largest shared file changes are `g_items.c`
(+662/−97), `g_func.c` (+332/−49), `p_client.c` (+303/−356),
`g_local.h` (+302/−136), `g_cmds.c` (+239/−101), `p_weapon.c`
(+191/−194), `g_save.c` (+135/−140), and `q_shared.h` (+37/−259).

Zaero adds four movement types, eight AI flags, `AS_FLY_STRAFE`,
`DAMAGE_IMMORTAL`, `DAMAGE_ARMORMOSTLY`, five ammo tags, and seven damage MODs
(Sniper Rifle, Tripbomb, Flare, A2K, Sonic Cannon, Autocannon, and the
`gl_polyblend` punishment). Allocate typed Rerelease values; do not preserve
the old numbers.

Zaero also defines `EF_BOOMER`, `MZ_BOOMERGUN`, `CHAN_WEAPON2`,
`TE_PLASMATRAIL`, `MASK_SHOT_NO_WINDOW`, and HUD stats 16–21. Several numeric
values collide with later Quake II/Rerelease meanings, and the Boomer effect/
muzzle values appear unused by Zaero game code. Map behavior to native
Rerelease effects/channels/masks and reserve new IDs only when actual use proves
necessary.

The 16 production item additions are the ten player systems listed in
Section 6.4 plus the six custom keys. Test mode adds `weapon_linedraw`,
`weapon_test`, and `item_test`.

#### Runtime-only helper lifecycle ledger

These identities do not belong in the BSP classname count, but they are save,
callback, ownership, resource, and entity-slot ABI. SYS-002 cannot close until
every row survives its applicable create/active/cleanup phases and an entity
slot free/reuse round trip without stale handles:

| Runtime identity | Owner/relationship to preserve | Required lifecycle proof |
| --- | --- | --- |
| `ired` | Player-deployed or map-authored mine root | Placement/arming/trigger/expiry/cap detonation, target firing, owner disconnect/death, callbacks and saves in every phase |
| `laser trip bomb laser` | IRED beam/helper linked to its mine | Endpoint movement, obstruction, parent-first/child-first cleanup, generation reuse and save restoration |
| `shrapnel` | Five independent IRED blast children | Bounce/touch/invalid-plane safety, water/sky/free timeout, attribution and mid-flight save |
| `sconnanExplode` | Delayed Sonic Cannon explosion/effect | Shooter/target invalidation, presentation/damage ordering, timed free and save |
| `flare` | Flare Gun projectile owned by the firing client | Bounce/light/blind/expiry, sky/water, owner loss, touch/think registration and save |
| `A2K Explosion` | Detonation-time effect only; never the countdown owner | Exact creation boundary, radial/outer passes, animation/free and post-spawn save |
| `EMPNukeCenter` | Player-created EMP field with generation-safe owner exemption | Overlap queries, owner loss/free-reuse, expiry, callback and save phase restoration |
| `PlasmaShield` | Stationary deployed shield with no conventional damage owner | Placement, mitigation, Sniper/EMP interaction, animation/sound, expiry/destruction and save |
| `laser_yaya` | Persistent Sentien laser child | Acquire/aim/stop, parent pain/death/gib cleanup, stale-handle protection and save |
| `autocannon base` | Multipart cannon child/rider | Parent motion/damage/death, child-first/parent-first cleanup, generation reuse and save |
| `autocannon turret` | Multipart cannon child/rider | Style/frame/use/motion, parent destruction, generation reuse and save |
| `bosshook` | ZBoss grapple projectile linked to boss and victim | Hit/miss/drag/release, target death/disconnect/teleport, boss death, free-reuse and save |
| `plasmaball` | ZBoss plasma projectile | Flight/touch/EMP/owner loss, attribution, free and mid-flight save |
| `VisorCopy` | Generation-owned non-solid visual duplicate linked to a still-solid/vulnerable player under D-021 FIX | Live hitscan/projectile/mover collision, view stop on every exit, disconnect/death/free-reuse and active save cleanup |
| detached `noclass` Hound | Handler-created monster with legacy identity/count anomalies | Split health/count/no-count, stable target identity, parent/child death order and all-phase save |

Confirmed baseline drift that must not regress Rerelease includes removed
legacy chase/spectator code, IP filtering, chat flood control, `playerlist`,
`sv_maplist`, later expansion protocol constants, later muzzle offsets, config
string capacity, third-person VWep encoding, and security/server commands.
Preserve native Rerelease facilities and layer only the behavior Zaero needs.

### Appendix B — Map dependency overview

All maps use custom content; the generated entity matrix remains authoritative.
This table highlights the custom combat/world dependencies that order the
campaign phases:

| Map | Custom monsters/defences | Other notable custom world dependency | Security cameras |
| --- | --- | --- | ---: |
| `zbase1` | Handler ×1 | Crate, seat, all major player systems | 4 |
| `zbase2` | Handler ×2 | Comm dish, camera/Visor flow | 4 |
| `zdef1` | Hound ×4, Sentien ×5 | Heavy `mteam`/mirror metadata | 6 |
| `zdef2` | Autocannon ×4, Sentien ×3 | Medium crate | 6 |
| `zdef3` | Autocannon ×2 | Toggle push/active machinery | 6 |
| `zdef4` | Autocannon ×3, Sentien ×6 | Landing-area key, medium crate | 5 |
| `zwaste1` | Autocannon ×2, Hound ×7, Sentien ×3 | School/team behavior | 9 |
| `zwaste2` | Autocannon ×1, Handler ×2, Sentien ×4 | Crate | 9 |
| `zwaste3` | Handler ×2, Sentien ×4 | School/team behavior | 9 |
| `ztomb1` | Hound ×7, Sentien ×5 | Energy/Lava/Slime keys | 5 |
| `ztomb2` | Autocannon ×1 | Slime key, random timer | 7 |
| `ztomb3` | Floor Autocannon ×2, Hound ×2 | Map IRED ×2, Energy key | 6 |
| `ztomb4` | Sentien ×1 | Barrier, Lava key, random timer | 0 |
| `zboss` | ZBoss ×1 | Boss targets ×5, finale fade/outro | 0 |
| `zdm1`–`zdm6` | None authored | Custom item/camera systems; `zdm6` timer/push | 3–9 each |

Every dedicated DM map places the Zaero weapons/ammunition and Visor/cameras
directly; auto-injection is primarily for non-Zaero maps.

### Appendix C — Rerelease ownership map

| Zaero surface | Primary Rerelease integration points |
| --- | --- |
| Classnames/fields/filtering | Spawn registry and typed spawn-field parser |
| Global/client/entity state | Private structs plus game/level/client/edict JSON schemas |
| Functions/mmoves | Save declaration wrappers and globally unique stable names |
| Items/ammo/keys | Item IDs/list, pickup/use/drop, persistent maxima, wheel/configstrings, bots |
| Weapons/projectiles | Weapon timing/state machinery, combat/traces, projectile masks/events |
| Monsters | `MMOVE_T` frame tables, monster cadence, AI/movement, precaches, save registry |
| Movement types/movers | Physics dispatch, ground/pusher handling, collision/linking, saves |
| Visor/zoom/help/fade | Per-client game state, playerstate stats/layout, cgame screen/status paths |
| Cinematics/maps/music | mapdb, start config, changelevel/intermission, packaged media |
| Co-op/DM | item instancing/visibility, social-ID slots, spawn selection, server cvars |
| Bots/nav | item/weapon IDs, trap/projectile metadata, native pathfinding with fallback |
| Packaging | tracked redistributable `pack/` contribution, ignored imported `ContentRoot`, deterministic stage/package manifests, release scripts |

### Appendix D — Required living documents

The roadmap is not a substitute for implementation evidence. Maintain:

- `docs/audits/source-delta.md` — per-file/function mechanical lexical delta;
- `docs/audits/source-delta-coverage.json` and `.md` — generated one-to-many
  source path/function/global to disposition/ledger/implementation/test
  crosswalk, including reviewed non-runtime/source-age records;
- `docs/audits/upstream-integration.json` plus
  `docs/provenance/upstream-integration-policy.json` — exhaustive current
  `src/` differences from the pinned Rerelease baseline and their reviewed
  integration categories;
- `docs/audits/bsp-entities.json` — exact class/key/value/count report;
- `docs/audits/bsp-contract-coverage.json` and `.md` — generated 132-classname
  and observed key/spawnflag to entity/feature/decision/native-exemption/save/
  lifecycle/test crosswalk;
- `docs/audits/assets.json` — layers, hashes, references, case and effective paths;
- `docs/audits/visor-trace-order.json` and `.md` — identity-locked
  legacy area-link/trace/mover proof and the D-021 FIX disposition;
- `docs/audits/stock-precaches.json` and `.md` — identity-locked 22-helper/
  19-file call graph, native/port Handler dependency route, legacy/Rerelease
  sound limits, and D-043 disposition;
- `docs/audits/flymove.json` and `.md` — identity-locked one-condition
  legacy/Zaero delta, native shared-helper/call-graph proof, seven executable
  float32 collision goldens, and D-044 disposition;
- `docs/audits/dm-injection.json` and `.md` — identity-recorded source bits,
  cvar, eight-item order/search/placement/partial-count contract, native port
  lifecycle/hook proof, 20-map/230-start inventory, and D-045 disposition;
- `docs/audits/release-surfaces.json` and `.md` plus
  `docs/provenance/release-surface-policy.json` — D-015 identity locks, supplied
  configuration/guard evidence, path-scoped current-source denial, and the
  local-only produced DLL/package validation contract;
- `docs/compatibility/feature-matrix.md` — every gameplay/system difference;
- `docs/compatibility/entity-matrix.md` — classname, keys, flags, maps, code, saves;
- `docs/compatibility/map-matrix.md` — mode, flow, objectives, starts, status/tests;
- `docs/compatibility/quirks.md` — anomaly evidence and decisions;
- `docs/compatibility/decisions.md` — architectural/behavioral decisions;
- `docs/UPSTREAM.md`, `docs/provenance/baselines.json`,
  `docs/provenance/upstream-match.json`, `docs/provenance/ASSET_SOURCES.md`,
  `docs/provenance/asset-policy.json`,
  `docs/provenance/dependency-policy.json`, and the independently versioned
  `docs/provenance/distribution-policy.json` component/mode/channel gate;
- the reviewed `docs/provenance/schemas/` suite for asset/distribution policy,
  local config, release manifests/readiness, and package/import ownership;
- `LICENSE_SCOPE.md` and the generated exact-install ownership manifests;
- generated private runtime reports and `dist/release-readiness.json` for a
  release candidate; and
- `CHANGELOG.md` and player-facing known issues.

The project has reached parity only when these reports agree with code and
runtime evidence, not when a checklist is closed by assertion.

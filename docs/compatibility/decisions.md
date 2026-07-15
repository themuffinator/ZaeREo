# Compatibility and architecture decision register

This register makes policy explicit before implementation obscures the choice.
ACTIVE decisions bind current work. INTERIM decisions bind current work safely
but must be revisited at the stated gate. OPEN decisions are not authority to
guess. SUPERSEDED entries remain as history and link their replacement.

The initial decisions are derived from the 2026-07-13 roadmap audit. Repository
maintainers own ACTIVE/INTERIM policy collectively until a named owner accepts a
record.

| ID | Topic | Status | Current position | Revisit |
| --- | --- | --- | --- | --- |
| D-001 | Product/game directory | ACTIVE | ZaeREo / zaereo | Only with an install migration plan |
| D-002 | Rerelease baseline | ACTIVE | Pin official commit `8dc1fc9794c01ece06881e703851b768fb3994de`, whose `rerelease/` subtree exactly matches all supplied bytes | Any proposed upstream refresh |
| D-003 | Source/media distribution | INTERIM | Gate code/media and distribution channel independently; no public gameplay-repo push/tag while code is open; tools-only needs a history-clean distribution root; local-full is always private | When rights evidence is obtained |
| D-004 | Git binary strategy | INTERIM | No legacy assets; LFS only for cleared canonical source binaries; never generated packages | Before first binary source commit |
| D-005 | Compatibility bug policy | ACTIVE | Parity first; tested FIX for safety/undefined behavior | Per quirk |
| D-006 | Rerelease co-op defaults | OPEN | Decide from all-map tests | Before Phase 5 |
| D-007 | Flare blend compensation | INTERIM | Preserve historical behavior and zdmflags opt-out | Phase 4 and before 1.0 |
| D-008 | Visor command/chat restrictions | ACTIVE | Preserve gameplay control lock and Visor-only use/inventory commands; route chat through the native Rerelease lobby path | Live multiplayer/split-screen command matrix |
| D-009 | Loose sprites/videos | INTERIM | Keep nine files loose until target behavior is verified | Phase 2 packaging proof |
| D-010 | Music values 1–11 | ACTIVE | Reuse Rerelease's numeric base-soundtrack contract for 2–11; log and preserve value 1/invalid values as silence | Live all-map audio/transition matrix |
| D-011 | ztomb1 absent tomb1 target | ACTIVE | Preserve the sole unreferenced/missing changelevel as an inert mapper artifact; no alias or data patch | Reopen only if a supported map revision references `mainexit` |
| D-012 | New protocol/engine fork | ACTIVE | Avoid for 1.0 unless required parity is impossible through supported APIs | Any engine-fork proposal |
| D-013 | Bot/navigation scope | INTERIM | Safe metadata/fallback for 1.0; advanced tactics post-parity | Phase 8 |
| D-014 | Legacy demos/saves | ACTIVE | Evidence only; no playback/load promise | Only with a separate compatibility project |
| D-015 | Source debug/test tools | ACTIVE | Developer-only, disabled and excluded from releases | Post-parity |
| D-016 | Stable publication | ACTIVE | CI-equivalent package, clean tree, checksums, human-approved draft/manual release | Each stable release |
| D-017 | Remastered content | ACTIVE | Optional overlay after 1.0; never replaces original parity baseline | Post-1.0 enhancement |
| D-018 | Zaero semantics on stock classnames | ACTIVE | Separate content/gameplay activation from hash/metadata/signature-proved mapper semantics; retain native meanings elsewhere | Classifier plus live stock/Zaero map fixture evidence |
| D-019 | Autocannon style-4 idle overread | ACTIVE | Preserve the shipped ELF's false result in a bounded fifth table entry | Only if repeatable retail Windows behavior contradicts the shipped ELF |
| D-020 | Selective EMP matrix and BFG state | ACTIVE | Explicit attack-type hooks, generation-safe owner exemption, saved non-colliding BFG latch, and Zaero-gated audio ordering; never blanket-disable weapons | Live full affected/unaffected matrix |
| D-021 | Visor copy collision | ACTIVE | FIX the link-order-dependent trace absorber: keep the real player solid/vulnerable and make only the visible copy non-solid | Live hitscan/projectile/mover/save/multiplayer matrix |
| D-022 | Hound schooling transient state | ACTIVE | Use local scans; preserve visible formation quirks without shared edict scratch state | Live schooling/save and ZBoss-isolation matrix |
| D-023 | Handler split identity/accounting | ACTIVE | Preserve duplicated durability with stable Handler/Hound identities and pre-reserved native counting | Live split/count/death-order/save matrix |
| D-024 | Sentien locomotion/laser lifecycle | ACTIVE | Preserve grounded hover behavior and shared mitigation while generation-checking and freeing the persistent beam | Live attack/fend/beam/save matrix |
| D-025 | ZBoss child/projectile lifecycle | ACTIVE | Preserve boss timing/damage/state while generation-checking children, releasing interrupted grapple victims, and making the plasma blast terminal | Live grapple/plasma/death/save matrix |
| D-026 | ZBoss inbound player persistence | ACTIVE | Preserve eligible positive-health inbound state, force a safe fresh/local reset for invalid arrivals, and never reset during ordinary local spawn | Live fresh/inbound/dead/disconnected/co-op matrix |
| D-027 | Finale white fade and handoff | ACTIVE | Freeze gameplay at boss-driven intermission, render per-client white fade, then hand off through native command state | Live fade/client/outro/victory/menu sequence |
| D-028 | A2K deadline and radius boundaries | ACTIVE | Typed per-client deadline and exact source-shaped dual damage walker; no countdown entity | Live timing/damage/save matrix |
| D-029 | Plasma Shield collision, durability, and placer identity | ACTIVE | Preserve the ownerless pusher bbox and legacy mitigation; use generation-checked non-collision placer metadata | Live collision/damage/EMP/save matrix |
| D-030 | Visor duration representation and incremental gate | ACTIVE | Typed carrier/drop time now drives the active elapsed-time camera lifecycle; D-021 is resolved | Live pickup/drop/active-state/save matrix |
| D-031 | Weapon-number multiselect and native wheel coexistence | ACTIVE | Follow source/config 1–10 semantics through exact alternates while retaining the native wheel | Live command/wheel/split-screen selection matrix |
| D-032 | Player HUD, lifecycle, and obituary presentation | ACTIVE | Use private saved HUD state, retain native death lifecycle, and preserve exact safe Zaero obituary fallbacks with stock isolation | Live HUD/death/obituary/localization/split-screen matrix |
| D-033 | Projectile-dodge timing and Rerelease coexistence | ACTIVE | Use Zaero's exact firing-time trace/timeout on classified maps and retain the native proximity scanner everywhere else | Live skill/call-site/save/stock-isolation matrix |
| D-034 | trigger_laser contract and target-callback lifetime | ACTIVE | Preserve the exact no-use auto-start mapper surface and stop safely if target dispatch frees or replaces the laser | Synthetic live hit/rearm/free/reuse/save matrix |
| D-035 | Step-physics trigger-free lifetime safety | ACTIVE | Retain Rerelease's post-trigger free guard and mirror it in Zaero FallFloat rather than importing the legacy omission | Live ordinary/free/free-reuse physics matrix |
| D-036 | func_plat bit-2 low-trigger collision | ACTIVE | Dispatch Zaero's inclusive eight-unit player-feet boundary on classified maps and retain native bit-2 no-monster semantics elsewhere | Live all-placement touch/move/monster-use/save matrix and D-018 classifier closure |
| D-037 | misc_explobox FALLFLOAT and push contract | ACTIVE | Gate Zaero's mass-400 FALLFLOAT spawn and airborne client `SV_movestep` push while retaining the native Rerelease barrel elsewhere | Live water/contact/slope/explosion/save matrix and D-018 classifier closure |
| D-038 | func_door_rotating zero-damage default | ACTIVE | Leave missing/zero damage non-damaging on Zaero maps while retaining authored positive and native Rerelease default values | Live zero/positive block/move/team/save matrix and D-018 classifier closure |
| D-039 | Train and path-corner colliding mapper semantics | ACTIVE | Scope Zaero node speed/smooth/teleport/Viper/rotation behavior while retaining native/Rogue train bits elsewhere | Live shipped routes, synthetic smooth/rotation, rider/team/save matrix and D-018 classifier closure |
| D-040 | Health pickup sound concurrency | ACTIVE | Select Zaero's count-derived sound per pickup without shared item mutation; retain explicit/native paths | Live custom-count, simultaneous pickup, split-screen, and D-018 classifier matrix |
| D-041 | Zaero monster damage reaction and self-target safety | ACTIVE | Layer Autocannon, mteam, tank-exclusion and retained-sound deltas onto native reaction; preserve the Rerelease self guard and expansion lifecycle | Live player/monster/Autocannon/mteam/sound/save matrix |
| D-042 | Hover fly-strafe and expired-state reset | ACTIVE | Preserve the scoped radial 3D dodge through a dedicated saved state and Rerelease slide movement; explicitly FIX the stale-state comparison typo | Live seeded dodge/direction/collision/expiry/save and stock/Daedalus matrix |
| D-043 | Stock-monster precache extraction and sound-index strategy | ACTIVE | Reuse the Rerelease-native Infantry helper only where Handler needs it; retain native stock spawns and cached indexes, never the disabled 256-sound interceptor | All-map resource-reference/audible and Handler spawn/conversion matrix |
| D-044 | Global SV_FlyMove duplicate-plane delta | ACTIVE | Retain the unmodified Rerelease shared near-duplicate/overclip solver; do not import Zaero's one-line global exact-plane comparison change | Live windowed corner/wedge/stair/projectile/monster and stock/expansion isolation matrix |
| D-045 | zdmflags and deathmatch item injection | ACTIVE | Preserve numeric bits 1/2 and the exact eight-item precondition/order/search/placement pass through native Rerelease item lifecycle; never use mapper classification as the content gate | Rerun the historical v1 values 0–3, eligible/ineligible including all eight one-member controls, exact open placement/native-drop state, and real-brush partial placement under D-046; then pickup/respawn/save, dedicated/multiplayer/server-info and native-mode isolation |
| D-046 | Window-before-mod/map runtime launch | ACTIVE | Visible two-stage bootstrap, exact-PID full window enumeration, then caller/target-queue-attached/task-switch-retried foreground-gated mod/map delivery with residual-PID cleanup | Private v2 cross-distribution client reruns |
| D-047 | Legacy PAK layer/runtime ownership semantics | INTERIM | Preserve source-layer audit and effective bytes, permit deterministic resolved import `pak1` beside project `pak0` only under strict ownership/collision proof | Phase 2 import/package/install lifecycle matrix |

## D-001 — Product and game directory

- **Status/date/owner:** ACTIVE; 2026-07-13; repository maintainers.
- **Context:** The mod needs a stable player-facing name and an isolated
  Rerelease game directory.
- **Decision:** Use ZaeREo as the product/repository name and zaereo as the
  runtime directory. Never install into baseq2.
- **Alternatives:** Reuse zaero, which risks confusion/collision with a legacy
  installation; choose another name, which weakens project continuity.
- **Behavioral impact:** Launch/config/package paths use zaereo; exact legacy
  classnames and cvars remain unchanged.
- **Evidence:** User-defined project identity and roadmap Sections 1, 9, and 12.
- **Tests/migration:** Install refusal for baseq2; archive-root allowlist;
  launch smoke. A future rename requires install/update/uninstall migration.

## D-002 — Rerelease baseline identity

- **Status/date/owner:** ACTIVE; opened 2026-07-13, resolved 2026-07-14;
  repository maintainers.
- **Context:** The supplied Rerelease tree had no retained Git metadata, so its
  original acquisition commit cannot be inferred from its directory name.
- **Decision:** Pin official commit
  `8dc1fc9794c01ece06881e703851b768fb3994de`; its `rerelease/` Git tree
  `7c3a380c5114dab4e7b7511a5c9c96390b72a1cd` matches all 144 supplied paths,
  sizes, and SHA-256 values and the aggregate
  `74b79d4f853fb521a866aaa5b1510c1c46afb63a73370b907b10143146629bf5`.
  Preserve the supplied per-file baseline and generated official-match report.
- **Alternatives:** Unpinned moving copy, rejected because API/layout drift would
  be unreviewable; vendored archive with hashes, acceptable only when commit
  provenance cannot be recovered.
- **Behavioral impact:** Determines API 2023 substrate, reproducible builds,
  upstream diffs, and future merge policy.
- **Evidence:** `docs/provenance/upstream-match.json`,
  `docs/provenance/baselines.json`, and `docs/UPSTREAM.md`. The matcher scanned
  191 official commits/nine distinct subtrees; exactly one subtree matched (in
  three commits), with the official main commit selected.
- **Tests/migration:** `tests/audit/test_identify_upstream.py`; baseline
  enrichment rejects a mismatched tree. A proposed baseline change regenerates
  both records and runs the complete build/load/smoke/dependency suite.

## D-003 — Source and media distribution

- **Status/date/owner:** INTERIM; 2026-07-13; repository maintainers.
- **Context:** GPL-2.0 terms for the Rerelease DLL do not establish rights for
  Zaero's commercial source additions or media.
- **Decision:** Treat project-code and media publication as independent,
  machine-readable fail-closed permissions. While code rights are unresolved,
  publish no Zaero-derived source or DLL; at most, publish an independently
  cleared tools-only acquisition kit from a separate reviewed repository or
  history-free/orphan distribution ref containing only allowlisted cleared
  files. Do not push, tag, or create a public release from the gameplay tree:
  GitHub's tag/source archives would publish the excluded source regardless of
  ZIP contents. If code is cleared but media is not, an
  importer kit may contain the DLL and clean configuration/tools but no Zaero
  media. A distinct `asset-full` artifact requires both permissions. The
  developer-only `local-full` mode always contains user-provided commercial
  content and is permanently non-publishable regardless of future clearance;
  it can never be promoted by renaming its archive or manifest mode. Never commit or
  publish original PAKs, loose files, legacy binaries, extracted media, or
  uncleared source merely because they are locally available.
- **Alternatives:** Treat GPL coverage of the Rerelease substrate as permission
  for Zaero additions, rejected because it does not establish those rights;
  asset-bearing/importer-DLL publication without independent evidence,
  rejected; stop local engineering, unnecessary because hash-verified private
  compatibility work can proceed according to each contributor's lawful access.
- **Behavioral impact:** Users provide a legitimate installation for media;
  public tools-only CI uses only cleared files/synthetic fixtures, while the
  gameplay tree remains local/private until its channel is cleared; the public artifact capability advances
  only from tools-only to importer-kit to a separately constructed asset-full
  mode as evidence permits. Tools-only remains non-playable; importer-kit becomes
  locally playable only after the user completes a validated legitimate import.
- **Evidence:** THIRD_PARTY_NOTICES.md and
  docs/provenance/ASSET_SOURCES.md.
- **Tests/migration:** Structured provenance records
  `code_distribution_permitted` and `media_distribution_permitted` with holder,
  scope, channel (repository, source archive, Actions artifact/cache, binary,
  media), evidence, review date and conditions. Package/publisher/readiness
  tests independently enforce both, plus repository/history identity,
  stage/archive denylists and importer hashes. Once a GPL-covered DLL may be
  distributed, the exact release/tag must also provide or durably link the
  corresponding source and notices required for that binary; a bare GPL text
  must not be represented as licensing uncleared Zaero additions.
  Revisit only with holder, scope, permission text, attribution, license
  compatibility, and distribution review.

## D-004 — Git binary strategy

- **Status/date/owner:** INTERIM; 2026-07-13; repository maintainers.
- **Context:** Original media is large and uncleared; generated PAKs/ZIPs are
  reproducible outputs rather than source.
- **Decision:** Commit no original legacy binary content. If a category is later
  cleared, store canonical source binaries in Git LFS after hosting policy
  review. Never put generated PAKs, ZIPs, DLLs, PDBs, or stages in LFS.
- **Alternatives:** Normal Git blobs or source PAKs, rejected for history size,
  hosting limits, provenance, and irreproducible layering; importer-only forever,
  remains valid.
- **Behavioral impact:** Development imports locally; releases regenerate from a
  manifest.
- **Evidence:** Package sizes/hashes in ASSET_SOURCES.md and roadmap Section 7.
- **Tests/migration:** Attributes/ignore checks, repository-object allowlist,
  deterministic package comparison. Revisit before any binary source commit.

## D-005 — Compatibility and defect policy

- **Status/date/owner:** ACTIVE; 2026-07-13; repository maintainers.
- **Context:** Literal vintage code contains visible quirks, version drift,
  undefined behavior, and memory-safety hazards.
- **Decision:** Assign PARITY, ADAPT, or FIX to every observable delta. Default
  to PARITY. Fix undefined behavior and safety only after tests lock valid
  behavior. Preserve native Rerelease facilities rather than vintage drift.
- **Alternatives:** Blind literal port or blanket modernization, both rejected
  because each loses either safety/native integration or compatibility.
- **Behavioral impact:** Quirk fixes can be intentional without silently
  redesigning gameplay.
- **Evidence:** Roadmap compatibility priority and quirks.md.
- **Tests/migration:** Every FIX links ordinary and invalid-case regression
  tests plus player-visible changelog/migration impact where applicable.

## D-006 — Rerelease co-op defaults

- **Status/date/owner:** OPEN; opened 2026-07-13; Unassigned.
- **Context:** Native item instancing, squad respawn, player collision, key
  ownership, and social-slot restoration can change authored Zaero puzzles.
- **Required decision:** Select explicit ZaeREo defaults from all-unit
  two-to-four-player and split-screen tests.
- **Alternatives:** Inherit current engine defaults, rejected as accidental;
  force legacy semantics, unsafe until softlock/quality behavior is measured.
- **Behavioral impact:** Inventory, key progression, respawn positions, reconnect,
  and transition survival.
- **Evidence:** 121 authored co-op starts across all 14 campaign maps.
- **Tests/migration:** Phase 5 Base tests, then full Phase 8 co-op matrix. Record
  server cvar/save compatibility before changing a released default.

## D-007 — Flare blend-compensation damage

- **Status/date/owner:** INTERIM; 2026-07-13; Unassigned implementation owner.
- **Context:** Legacy Flare damages players who disabled gl_polyblend, and
  zdmflags bit 1 opts out.
- **Decision:** Preserve the behavior in compatibility mode and keep the numeric
  server opt-out while evaluating a safe modern per-client signal/default.
- **Alternatives:** Remove damage, safer but not parity; trust a stale renderer
  cvar, potentially unavailable/unsafe; server-forced visual, possibly beyond
  supported APIs.
- **Behavioral impact:** Competitive damage and client preference interaction.
- **Evidence:** Supplied Zaero Flare/cvar source and 1.1 configuration behavior.
- **Tests/migration:** Per-client on/off, damage tick cap, zdmflags 0–3,
  split-screen and dedicated server. Revisit before 1.0 release notes.

## D-008 — Visor control and chat policy

- **Status/date/owner:** ACTIVE; resolved 2026-07-14; Visor slice/repository
  maintainers.
- **Context:** Legacy Visor freezes gameplay controls and permits only a narrow
  command allowlist, suppressing chat too. KEX Rerelease routes chat through
  its native lobby path outside the legacy game-DLL command handler.
- **Decision:** Preserve the gameplay lock, putaway cancellation, Visor-only
  textual/index use, selected-Visor inventory use, and inventory cycling.
  Allow `say`, `say_team`, and `steam` to continue through native Rerelease
  lobby/chat routing. Do not intercept or emulate lobby chat in game code.
- **Alternatives:** Literal allowlist including chat suppression; permit chat
  while retaining gameplay lock; remove lock, rejected as gameplay-changing.
- **Behavioral impact:** Remote-view vulnerability and multiplayer communication.
- **Evidence:** Supplied `g_cmds.c`, Rerelease KEX lobby routing in
  `g_cmds.cpp`, and the active command gate in `src/g_cmds.cpp`.
- **Tests/migration:** Static command-order and allowlist contracts pass.
  Live chat delivery, gameplay-command suppression, wheel/index input, death,
  damage, disconnect, save, and two-local-client isolation remain.

## D-009 — Loose sprites and cinematics

- **Status/date/owner:** INTERIM; 2026-07-13; asset/import owner Unassigned.
- **Context:** Seven plasma sprite files and intro/outro are deliberately loose
  in the legacy installation; documentation cites programming reasons.
- **Decision:** Preserve all nine as loose staged files until packed loading,
  animation, case, and cinematic behavior are verified on the target.
- **Alternatives:** Pack immediately for neatness; rejected without behavioral
  proof. Keep loose permanently; acceptable if target testing requires it.
- **Behavioral impact:** Asset lookup, archive layout, startup/finale playback.
- **Evidence:** PKG/DOC plus hashes in ASSET_SOURCES.md.
- **Tests/migration:** Loose/packed A/B runtime, manifest closure, animation,
  cinematic skip and case-sensitive stage. Packaging changes require upgrade
  cleanup of the old form.

## D-010 — Music values 1–11

- **Status/date/owner:** ACTIVE; 2026-07-14; World music slice/repository
  maintainers.
- **Context:** Zaero passes worldspawn `sounds` directly to numeric
  `CS_CDTRACK`. The 20 supplied maps author 1, 3, 4, 5, 6, 8, 9, or 11; only
  `zdm6` uses 1. The supplied Zaero PAKs contain no music files, so there is no
  Zaero soundtrack to import or redistribute. Rerelease's own game DLL retains
  numeric `sounds`, its base maps use the same numeric configstring contract,
  and an audited legitimate Rerelease installation contains `track02.ogg`
  through `track21.ogg` but no `track01.ogg`. Track 1 was the classic CD data
  track and therefore yields no music. The game DLL API exposes no portable
  asset-existence query and must not inspect an engine/program root.
- **Decision:** When a Rerelease `music` string is explicitly authored, keep its
  native precedence. Otherwise, on a Zaero-classified map, pass values 2–11
  unchanged through the target-native numeric contract, map 0 to silence
  without noise, and map 1 or any out-of-domain value to `0` with a map-named
  console explanation. This preserves `zdm6` silence while making the fallback
  observable. Do not ship, copy, rename, or package soundtrack media: 2–11 are
  supplied by the player's legitimate Rerelease installation. Keep native
  numeric behavior unchanged on every non-Zaero map and leave music volume and
  loop policy to the Rerelease client/configstrings.
- **Alternatives:** Ship Zaero or copied Rerelease music, rejected because no
  Zaero music is supplied and Rerelease media is not project redistributable;
  arbitrarily map value 1 to an audible track, rejected because it changes the
  authored silent result; pass 1 silently, rejected because the required
  fallback would be invisible; use explicit `music/trackNN.ogg` paths, rejected
  because numeric selection is already the target-native map contract; hard
  fail on unavailable/invalid values, rejected because ambience must not block
  map loading.
- **Behavioral impact:** Nineteen supplied maps select their authored base-game
  track number, and `zdm6` remains silent with one explanatory load message.
  Each worldspawn replaces the previous selection, explicit community-map
  `music` strings still win, client volume is untouched, and stock/expansion
  maps are byte-for-byte on their existing selection path.
- **Evidence:** Identity-locked supplied `g_spawn.c` SHA-256
  `60cf870a254e8f80aa5a2a28eb81b7522534f84c7221002247dfae9c091cc75b`;
  direct entity-zero extraction from all 20 BSPs; checked-in
  `docs/audits/assets.json` proving no music extension/path; official pinned
  Rerelease `g_spawn.cpp` numeric/string branches; read-only installed base
  content audit (`baseq2/pak0.pak` SHA-256
  `bfc341d7508b275413511bea5fc092ccc7aa5ab1989e657516894bd5f0fc883c`)
  showing base maps use numeric values and music tracks begin at 02; MAP-015,
  E-042, and Q-057.
- **Tests/migration:**
  `tests/compatibility/test_zaero_world_music.py` locks the source identity,
  exact per-map values/domain, no-Zaero-music provenance, 0/1/2–11/invalid
  resolution, logging, sequential replacement, explicit-string precedence,
  native fallback, and absence of volume/loop mutation. A historical legacy-v1
  one-stage zdm6 report on Debug DLL SHA-256
  `f4b7c260700ca92f46601fd01e1e800590b32573fb7a11dc47dab72f70d66732`
  recorded the exact value-1 fallback line; the schema-valid ignored report is
  SHA-256
  `68ab47b74486949b81290252ee907e9e85e50526aca82cfdf985744aa0438d59`.
  It must be rerun under D-046 and does not acoustically prove silence. Live audible sampling of every 2–11
  value, captured zdm6 silence, synthetic invalid fallback, sequential
  map/cinematic/server transitions, client volume/loop behavior, dedicated
  server, and D-018 classifier fixtures remain. No saved field or save
  migration is introduced. Release notes must state that ZaeREo supplies no
  music and uses the installed Rerelease soundtrack.

## D-011 — ztomb1 target for absent tomb1 BSP

- **Status/date/owner:** ACTIVE; 2026-07-14; Campaign integration/repository
  maintainers.
- **Context:** ztomb1 entity 522 is a `target_changelevel` at
  `-720 -3008 -376`, with targetname `mainexit` and destination `tomb1`.
  `maps/tomb1.bsp` is absent from every supplied layer. A complete generated
  audit of all 30 changelevels proves this entity is also the only one with no
  activation reference: 29 have exactly one `target`/`pathtarget`/`deathtarget`
  reference, while entity 522 has no reference through any activation,
  killtarget, or combat-target key. The supplied and Rerelease spawn paths make
  `target_changelevel` invisible and use-only; no touch or think callback can
  fire it. No supplied or production source names `mainexit`. Named inbound
  spawnpoints change player placement, not the immutable entity target graph.
- **Decision:** Preserve entity 522 and its exact `tomb1` string as an inert
  mapper artifact. Do not rewrite ztomb1, add a `tomb1` alias/BSP, synthesize an
  activation path, or special-case `mainexit`. The intended Tomb routes remain
  ztomb1's referenced exits to ztomb2/3/4 and `*zboss`; this orphan cannot
  block them. Keep the audit fail-closed: if a supported map revision adds any
  activation reference or supplies a `tomb1` destination, reopen D-011 and
  classify that revision rather than inheriting this conclusion silently.
- **Alternatives:** Correct `tomb1` to `ztomb1`, rejected because no evidence
  identifies that destination and it could create an unintended self-reload;
  add an alias or duplicate BSP, rejected because it invents content and can
  alter save/unit behavior; delete the entity, rejected because exact harmless
  map data is a compatibility interface; patch only during import, rejected
  because there is no reachable defect to fix; hard-fail on every missing
  destination, rejected because this proven orphan is harmless while such a
  rule would prevent the map from loading.
- **Behavioral impact:** None on valid play: no entity can call the orphan's
  use callback. ztomb1's four internal exits and referenced unit exit to zboss
  remain unchanged. Developer-forced entity mutation is outside compatibility
  scope and no longer masquerades as an unresolved campaign risk.
- **Evidence:** ztomb1 BSP SHA-256
  `b19a7d4ec771d99e1fef9c754d4da89c51dc14f99e157a5eb2464c3a506c00eb`;
  generated `docs/audits/bsp-entities.json/.md` target/destination closure;
  supplied `g_target.c` SHA-256
  `25b0bab6a361b6682fdcea59c4b2e2f306b85a079f7ea52d7b869bfecb046af0`
  and `g_utils.c` SHA-256
  `9f38a328cd489960933de750600781b4e89224bb37b38a97d021d45db3c1fcb9`;
  pinned Rerelease `SP_target_changelevel` and `G_UseTargets`; MAP-014, E-043,
  and Q-032.
- **Tests/migration:**
  `tests/audit/test_audit_reports.py` proves activation-reference and BSP
  closure generation on synthetic present/referenced and missing/orphan cases.
  `tests/compatibility/test_zaero_campaign_flow.py` locks all source/BSP
  identities, the 30/29/1 counts, entity 522 as the sole orphan and sole
  missing BSP, exact empty reference set, use-only spawn path, targetname
  dispatch, and absence of a production `mainexit` special case. Full live
  ztomb1–4 fresh/carried/co-op route and save coverage remains for MAP-014, but
  no valid route can exercise this entity. No code, map patch, package overlay,
  saved field, or migration is introduced.

## D-012 — Protocol or engine fork

- **Status/date/owner:** ACTIVE; 2026-07-13; repository maintainers.
- **Context:** Custom visuals may tempt new engine protocol opcodes, multiplying
  distribution and interoperability scope.
- **Decision:** Use supported game/cgame events, entities, stats, layouts, and
  effects for 1.0. An engine fork requires proof that required parity is
  impossible otherwise and a separate reviewed scope decision.
- **Alternatives:** Fork preemptively, rejected; omit required presentation,
  rejected if gameplay/presentation contract cannot be represented.
- **Behavioral impact:** Keeps the mod drop-in compatible with Quake II
  Rerelease.
- **Evidence:** Target API/cgame audit and roadmap architectural conclusion.
- **Tests/migration:** Stock-engine load and protocol smoke. A future fork must
  define client/server compatibility, distribution, install, and rollback.

## D-013 — Bots and navigation

- **Status/date/owner:** INTERIM; updated 2026-07-15; Native bot integration.
- **Context:** Rerelease bots need correct item/weapon/trap/projectile metadata,
  while advanced tactics and navigation authoring are larger parity-neutral
  work.
- **Decision:** 1.0 provides safe metadata and graceful behavior with or without
  navigation. Every appended Zaero item continues through the native generic
  item-ID/state registration path; the external bot item/weapon entrypoints
  reject the null and terminal item sentinels before indexing the expanded
  inventory/item table. The Flare, IRED bomb/laser/shrapnel, EMP center,
  Sentien beam, and ZBoss hook/plasma publish the native trap or laser-field
  metadata, so the bot bridge receives active state, velocity, and laser
  endpoints without changing their source-compatible gameplay. Advanced
  custom-weapon tactics and generated navigation are post-parity enhancements.
- **Alternatives:** No bot integration, rejected because native paths must not
  crash; full tactical/nav scope before parity, rejected as critical-path drift.
- **Behavioral impact:** Bots can coexist safely and receive generic pickups
  plus explicit danger metadata, but may not use every system optimally at 1.0.
- **Evidence:** [Native bot exports](../../src/bots/bot_exports.cpp),
  [native state bridge](../../src/bots/bot_utils.cpp), scoped Zaero hazard
  producers, the upstream-integration audit, and Phase 8 scope.
- **Tests/migration:** [Static item/boundary/trap contracts](../../tests/compatibility/test_zaero_bot_integration.py)
  pass. Still run 2/4/8-client bot smokes on zdm1–6 and a no-navigation
  fallback; publish known tactical limitations.

## D-014 — Legacy demos and saves

- **Status/date/owner:** ACTIVE; 2026-07-13; repository maintainers.
- **Context:** Four demos and four save artifacts use incompatible legacy
  protocol/raw-pointer formats.
- **Decision:** Preserve identity as audit evidence only. ZaeREo does not promise
  playback or load compatibility.
- **Alternatives:** Protocol/save emulation, rejected as unrelated to map and
  gameplay parity; ship artifacts, rejected for provenance and runtime scope.
- **Behavioral impact:** Players begin new Rerelease games and make native JSON
  saves.
- **Evidence:** PKG and target protocol/save audit.
- **Tests/migration:** Runtime/archive denylist and native save suite. Any future
  converter is a separately scoped tool.

## D-015 — Debug and test tools

- **Status/date/owner:** ACTIVE; 2026-07-15; repository maintainers.
- **Context:** Legacy source has _DEBUG/_Z_TESTMODE entities/commands plus
  disabled experiments that were not in the shipped Release DLL.
- **Decision:** The legacy tools are not 1.0 gameplay requirements. A narrowly
  scoped read-only evidence surface may exist only behind the project's
  existing `_DEBUG` configuration when a current roadmap requirement cannot be
  observed through native commands; it must add no edict/save/protocol state,
  player command, or Release mapper/game ABI and must be absent from Release.
- **Alternatives:** Port now, rejected as risk/scope; delete historical evidence,
  rejected; expose publicly, rejected because it changes the mapper/game ABI.
- **Behavioral impact:** Release players cannot spawn experimental tools.
- **Evidence:** The identity-locked [D-015 policy](../provenance/release-surface-policy.json)
  and normalized [Release-surface audit](../audits/release-surfaces.md) prove the
  supplied Debug-only `_Z_TESTMODE` definition, the absent `_SHANETEST` define,
  both literal ZBoss `#if 0` grapple branches, and the current port's zero
  forbidden source/project hits. The deny is scoped to the Zaero ZBoss path so
  native Rerelease grapple protocol/CTF declarations remain valid. Policy
  revision 2 additionally denies both signatures of D-045's `_DEBUG`-only,
  read-only `sv zaereo_dm_probe`; it records private placement evidence outside
  edicts/saves and has no Release declaration or dispatch.
- **Tests/migration:** [Fail-closed source/project, ASCII/UTF-16 DLL, and ZIP
  contracts](../../tests/release/test_release_surfaces.py) pass. The validator
  passes against the produced Release DLL and four local deterministic packages,
  including their embedded DLL and PAK directories. The DM probe satisfies the
  required explicit `_DEBUG` guard, policy revision, source/schema tests, and
  binary deny scan. The 2026-07-15 retained private Release report
  `.install/runtime-reports/zbase1-release-surface-smoke.json` (SHA-256
  `b0ca47bc40779ef6e4ee83cf3e656c20f51f97ab9dec8988abb514a9ab8c7bd4`)
  is a historical schema-v1 single-stage report and loads Release DLL SHA-256
  `273ac734dc2ee0199e1aa88bd745d657b53c2e181419e13fd0cbaf7af2cf2fc0`.
  It initializes, spawns `zbase1`, observes native client begin, and shuts down
  with every lifecycle marker true in an 868×517 captioned/non-popup window;
  no non-windowed window, safety abort, timeout, stderr, fatal signature, dump,
  or residual process occurred. It preserves binary/load evidence but does not
  close SYS-018/Q-039 after the window-before-mod/map rule: rerun as v2 before
  reopening verified status. It does not claim map playability. Any further
  utility requires the same review.

## D-016 — Stable release publication

- **Status/date/owner:** ACTIVE; 2026-07-13; repository maintainers/release owner.
- **Context:** Publishing and packaging are distinct risk boundaries.
- **Decision:** Reuse the CI-equivalent deterministic package path, require a
  clean current commit/version/tag plus a commit-bound machine-readable release-
  readiness artifact, generate checksums, and create a human-approved draft/
  manual GitHub release. Stable promotion requires a protected environment
  approval and retained legally provisioned private live evidence. Nightlies
  are prereleases and may package only the provenance-eligible capability.
- **Alternatives:** Automatic stable publication or mutable assets, rejected;
  manual one-off packaging, rejected because it diverges from CI.
- **Behavioral impact:** Releases are reproducible, reviewable, and recoverable.
- **Evidence:** Roadmap Sections 11 and 13.10–13.11, strengthened REBLIVION workflow review,
  `tools/package_windows.ps1`, `tools/publish_github_release.ps1`, and the
  current nightly/stable workflow scaffold.
- **Tests/migration:** `tests/release/` locks deterministic archives, manifests,
  path/provenance gates, draft-first publication, and non-mutating dry runs.
  Add exact-commit readiness, protected approval, private live report, and
  independent code/media policy enforcement. A clean-machine install, draft
  independent playthrough, and tag/version agreement remain mandatory before
  any stable promotion.

## D-017 — Remastered content

- **Status/date/owner:** ACTIVE; 2026-07-13; repository maintainers.
- **Context:** Visual/audio remastering can obscure original parity and has its
  own provenance/performance risks.
- **Decision:** Remasters are optional post-1.0 overlays. The original-content
  compatibility baseline remains available and continuously tested.
- **Alternatives:** Replace original baseline, rejected; prohibit improvements
  forever, unnecessary after parity is stable.
- **Behavioral impact:** Players can distinguish fidelity bugs from enhancements
  and can disable overlays.
- **Evidence:** Project intent and roadmap Phase 10.
- **Tests/migration:** Overlay on/off comparison, asset provenance, performance,
  original path fallback, and independent versioning.

## D-018 — Zaero semantics on stock classnames

- **Status/date/owner:** ACTIVE; 2026-07-13; map behaviors/repository
  maintainers.
- **Context:** Zaero changes stock `func_timer`, `trigger_push`,
  `func_rotating`, `func_door`, `func_door_rotating`, `func_plat`,
  `func_train`, `path_corner`, `misc_explobox`, `misc_viper`, and
  `target_explosion`. `trigger_push` bit 2 means START_OFF in Zaero but
  PUSH_PLUS in the Rerelease baseline; `func_plat` bit 2 means the eight-unit
  low trigger but means `SPAWNFLAG_PLAT_NO_MONSTER` in Rerelease; Zaero train
  bits 8/16/32/64 collide with Rerelease move-teamchain/fix-offset/use-origin
  meanings. Viper and explosion bit 1 also acquire Zaero-only meanings.
  Applying any legacy meaning globally would regress stock and expansion maps.
- **Decision:** Replace the single `level.is_zaero` concept with two orthogonal
  scopes. Zaero content/gameplay activation permits registered items, weapons,
  damage/EMP/HUD hooks, and DM injection on stock/community maps. A narrower
  mapper-contract classification alone dispatches conflicting stock-classname
  semantics and separately reviewed supplied-map adaptations of native actors,
  weapon timing/presentation, obituary prose, and campaign flow; keep native
  Rerelease behavior on all other maps. The mapper scope
  accepts the audited canonical-name-plus-BSP-hash set, an explicit documented
  worldspawn/mapdb opt-in, or conservative unambiguous Zaero signatures—never a
  conflicting stock flag by itself. Record its map identity and reason in logs
  and saves, reject/migrate mismatches explicitly, and keep diagnostic overrides
  visible. Parse only semicolon timer targets into bounded, saveable slots;
  retain literal targets unchanged. Store Zaero rotation phase separately from
  native mover state and scale the legacy degrees-per-second-squared rates by
  the actual frame duration. `aspeed` is not applied to `func_rotating` because
  the supplied Zaero implementation does not read it there. Gate sliding-door
  `active`/message/zero-block damage, rotating-door zero-default damage,
  low-trigger platforms, train/path behavior, mass-400 FALLFLOAT explosive
  barrels, multipart viper flags/models, and the cosmetic-only target explosion
  on the same classification; retain each native Rerelease path otherwise.
- **Implementation checkpoint (2026-07-15):** `level.zaero_content_active` is
  always active for this game module, while `level.zaero_mapper_contract` alone
  gates the colliding stock-classname paths and reviewed map-only native hooks
  (ammo spawn flags, monster spawn/dodge/reaction, stock weapon ordering,
  obituary, Hover, and `zboss` behavior). The generated retail manifest uses
  a canonical map name plus SHA-256 of the entity string passed by the engine;
  a canonical name alone no longer grants mapper semantics. This is an
  intentionally narrower claim than the required full-BSP hash: the Rerelease
  game import supplies no resolved-file reader. The full BSP hashes remain in
  `docs/audits/bsp-entities.json`, and an engine resolver is required before
  the `shipped-hash` target is complete. Until then, an exact case-sensitive
  worldspawn `zaero_mapper_contract` value of `1` opts in, `0` opts out, and
  malformed/duplicate values fail closed; Zaero-owned classname signatures are
  the remaining conservative path. MapDB opt-in and diagnostic overrides are
  not implemented. Map name, entity-string digest, content state, mapper state,
  and reason are registered in JSON saves; pre-classifier or mismatched loads
  reject explicitly.
- **Alternatives:** Reinterpret bits globally, rejected because it breaks
  PUSH_PLUS; infer meaning independently on each entity from `targetname` or
  `wait`, rejected as an ambiguous mapper heuristic; patch the supplied BSPs,
  rejected because drop-in map compatibility is the goal.
- **Behavioral impact:** Supplied, explicitly opted-in, and conservatively
  signature-identified Zaero maps receive
  their timer, push, angular mover, doors, low platforms, trains/path corners,
  explosive barrels, multipart-viper, and cosmetic explosion contracts while
  base, mission-pack, and custom Rerelease maps retain their native meanings.
- **Evidence:** Supplied Zaero `g_func.c`/`g_trigger.c`; five shipped push
  volumes, three semicolon timers, fourteen rotating brushes, 318 sliding
  doors, seven vipers, and 35 target explosions in the BSP audit; Rerelease
  `g_func.cpp`/`g_trigger.cpp`/`g_misc.cpp`/`g_target.cpp` flag assignments. Zaero's
  `func_rotating` never reads `aspeed`; all four shipped `aspeed` keys belong to
  `func_train` and are explicitly zero. The audit also finds 11 bit-2 platforms
  across eight maps, 12 of 32 rotating doors with missing/zero damage, 31
  explosive barrels across five maps, five nonzero per-corner speeds in
  `zdef4`, 96 waiting and four teleport path corners, no shipped path smooth
  bits, and no shipped train rotation bits. Source-only flag paths remain
  synthetic/community-map contracts rather than invented campaign requirements.
- **Tests/migration:** Deterministic target bounds/selection, flag separation,
  and 40 Hz rotation curves are in
  `tests/compatibility/test_stock_map_behaviors.py`; active-door, multipart
  viper, cosmetic-explosion, shipped-key-pattern, native-fallback, and
  generation-safety contracts are in
  `tests/compatibility/test_stock_world_extensions.py`. Before verification,
  add live delayed-use/save round trips, all five push volumes, rotating rider
  and contact fixtures, exact train/path/low-platform/barrel/door cases, live
  door/viper/explosion saves, full-BSP resolver-backed classifier fixtures for
  all 20 audited hashes, same-name/wrong-hash, explicit metadata, save
  stability, and stock/base/Xatrix/Rogue/ambiguous-community false positives.
  The current generated entity-string manifest and fail-closed JSON-save
  metadata tests are only an interim guard. A stock DM map must run
  injected Zaero items while retaining native mover flags. No supplied-BSP
  migration is required; community/remastered maps use the documented opt-in or
  a reviewed hash enrollment.

## D-019 — Autocannon style-4 idle overread

- **Status/date/owner:** ACTIVE; 2026-07-13; Autocannon slice/repository
  maintainers.
- **Context:** The source declares four `qboolean` entries in `turretIdle` but
  indexes it with styles 1 through 4. Seven shipped cannons use style 4, so a
  literal port would retain undefined memory access on an ordinary map path.
- **Decision:** Use a bounded five-entry table. Set the explicit style-4 value
  to `false`, which is the value read by the supplied retail ELF: `nm` places
  `turretIdle` at `0x7b4bc` and the zero-valued `turretIdleStart` symbol at
  `0x7b4cc`, the address reached by index four.
- **Alternatives:** Use `true` by analogy with style 3, rejected because it
  changes observed shipped-binary presentation; preserve the out-of-bounds
  read, rejected as undefined and compiler/layout dependent; disable style 4,
  rejected because five ceiling and two floor placements use it.
- **Behavioral impact:** Style-4 turret pieces begin on the active frame as in
  the supplied Linux binary, with no unsafe adjacent-global dependency. Other
  styles and all activation/deactivation state remain unchanged.
- **Evidence:** Hash-pinned `gamei386.so`
  (`db0fab26d46a74314142b6a1c268fd4986450932588352bd89c772b3964a3d12`),
  symbol addresses above, supplied `z_acannon.c`, and BSP style counts.
- **Tests/migration:**
  `tests/compatibility/test_zaero_autocannon.py` locks the binary hash, shipped
  count and explicit table. Add a repeatable live style-4 fresh-spawn/save
  capture on both variants before verification; no save migration is needed.

## D-020 — Selective EMP matrix and BFG state

- **Status/date/owner:** ACTIVE; 2026-07-13; EMP slice/repository maintainers.
- **Context:** Zaero does not disable every weapon inside an EMP field. The
  supplied source has 28 explicit queries: 26 play the historically misspelled
  `emp_missfire.wav`, while power armor and IRED are silent. Checks occur at
  attack-specific positions and ordering points; paired Boss2/Jorg attacks and
  Makron/Sentien paths include deliberate multiple or redundant checks. The
  BFG latches a frame-9 misfire in legacy flag `0x4000`, which collides with
  Rerelease `FL_SAM_RAIMI`. Rerelease `Weapon_Generic` also plays powerup audio
  before callbacks, unlike the supplied Zaero path.
- **Decision:** Use one explicit global EMP query that preserves the no-LOS
  radius rule and exact owner exemption, strengthened with entity-generation
  validation. Wire only the source's affected attack types/call sites; do not
  infer a blanket energy-weapon or all-weapon rule. Store the BFG animation
  latch as a saved per-client boolean, clear/check it at the original frames,
  and suppress both windup/discharge as the source does. Allow Zaero-gated stock
  wrappers to defer generic powerup audio so successful/misfired ordering,
  recoil, RNG, ammo, and sound count remain source-compatible. Generic
  Rerelease expansion monsters that use the same affected projectile wrappers
  on a Zaero-classified map inherit the attack-type rule; this is a deliberate
  native integration adaptation, not a new classname-wide EMP rule. Sentien,
  Plasma Shield placement, and ZBoss deployment now use the shared query at
  their supplied sites.
- **Alternatives:** A blanket EMP check in `Weapon_Generic`, rejected because it
  disables unaffected hitscan/shotgun/grenade attacks and loses exact ordering;
  reuse `0x4000`, rejected because it corrupts an unrelated Rerelease flag;
  duplicate independent EMP scans in every new module, rejected because owner/
  overlap semantics would drift; ignore expansion wrappers, rejected because
  the shared native attack helper cannot safely have two hidden meanings on the
  same Zaero map without duplicating the target baseline.
- **Behavioral impact:** EMP remains selective, owner-aware, overlapping-field
  safe, and source-ordered. Blocked BFG animations persist across saves without
  flag collision. Native stock/expansion behavior outside Zaero-classified maps
  remains unchanged.
- **Evidence:** The 28 supplied `EMPNukeCheck` sites in `g_combat.c`,
  `g_monster.c`, `g_target.c`, `g_turret.c`, stock monster files,
  `p_weapon.c`, `z_acannon.c`, `z_item.c`, `z_weapon.c`, and `z_sentien.c`;
  Rerelease flag and weapon-helper definitions; Q-043; and the dedicated
  implementation in `src/zaero/g_zaero_emp.cpp`.
- **Tests/migration:** `tests/compatibility/test_zaero_emp.py` locks field
  lifetime, radius/owner/generation behavior, all currently available explicit
  hooks, silent versus sounded responses, BFG frame/audio/recoil/ammo ordering,
  overlap, callback wiring, and saved latch registration. Before verification,
  run the named affected/unaffected live matrix under owner/foreign/overlapping
  fields, including Shield placement, Sentien burst/laser behavior, and ZBoss
  deployment. Existing development saves
  without the boolean load its false default; stable-schema policy applies once
  public save compatibility begins.

## D-021 — Visor copy collision and trace behavior

- **Status/date/owner:** ACTIVE/FIX; resolved 2026-07-14; Visor slice/repository
  maintainers.
- **Context:** `zCam_TrackEntity` hides the real player's model but leaves that
  player solid, then creates a solid, non-damageable `VisorCopy` at the same
  position. Legacy solid links append and are traversed oldest-first, while an
  equal-fraction hit does not replace its first winner. The original player is
  therefore hit immediately after copy creation, but a mover can relink the
  otherwise frozen player behind the copy and make the non-damageable copy win
  the same trace. Damage ownership is link/mover-order dependent rather than a
  stable combat rule.
- **Decision:** Apply a scoped FIX. Keep the real player solid, damageable, and
  hidden while remote viewing. Create a generation-owned visual `VisorCopy`
  with `SOLID_NOT` and no damage handling. Copy the ordinary player
  presentation every frame, and free only the matching owned generation.
- **Alternatives:** Copy the source literally without evidence, rejected because
  the supplied algorithm itself changes results after mover relinking; make both
  player and copy non-solid, rejected because remote-view vulnerability is
  gameplay; remove the copy, rejected because third-person presentation is
  visible.
- **Behavioral impact:** Entering Visor cannot intermittently absorb attacks,
  and the real player's collision and vulnerability remain.
- **Evidence:** Supplied `z_camera.c::zCam_TrackEntity`, `zCam_Stop`,
  `g_phys.c::SV_Push`, legacy `server/sv_world.c`, Q-044, PLY-008, the
  identity-locked retail `gamex86.dll`, and the generated
  [trace-order audit](../audits/visor-trace-order.md).
- **Tests/migration:** The deterministic audit and static copy/generation
  contracts pass. Live owner/team/enemy/monster hitscan and projectile cases,
  moving platforms, damage/death cancellation, drop/putaway/disconnect,
  split-screen isolation, entity free/reuse, and active JSON saves remain.
  This FIX must be disclosed in release notes before a supported release.

## D-022 — Hound schooling transient state

- **Status/date/owner:** ACTIVE; 2026-07-14; Hound and Boss slices/repository
  maintainers.
- **Context:** Legacy schooling builds linked radius and school lists by writing
  temporary pointers and distances into every nearby edict. ZBoss uses the same
  `zDistance` member as a persistent 30–35-second EMP cooldown, so a schooling
  Hound within the 2,000-unit scan radius can overwrite boss state. The scratch
  lists are also unsafe when entity slots are freed or reused and have no useful
  save meaning.
- **Decision:** Evaluate each school update with local direct radius scans and
  local distance/nearest accumulators. Do not add the legacy scratch pointers or
  shared distance member to Rerelease entities or saves. Preserve the visible
  schooling rules: a 2,000-unit candidate scan, 500-unit visible/in-front peer
  set, inclusion of non-schooling Hounds, arithmetic yaw averaging, leader
  decay/randomization, and the minimum-distance heading-copy quirk. Store boss
  cooldown independently when ZBoss lands.
- **Alternatives:** Copy the edict scratch fields literally, rejected because it
  retains demonstrated cross-system corruption and unsafe lifetime coupling;
  use saved safe entity handles to recreate the chains, rejected because the
  lists are one-update transient state and would create unnecessary save-order
  semantics; replace schooling with modern flock steering, rejected because its
  movement is visibly different.
- **Behavioral impact:** Ordinary Hound formation motion remains source-shaped,
  while schooling cannot mutate unrelated entities or corrupt the future boss
  cooldown. No mapper key, classname, spawnflag, or intended save state changes.
- **Evidence:** Supplied `z_ai.c::zCreateRaduisList`, `zSchoolAllVisiable`, and
  `zSchoolMonsters`; `z_hound.c`; ZBoss `zDistance` cooldown use; Q-014/Q-015;
  and the implementation in `src/zaero/g_zaero_hound.cpp`.
- **Tests/migration:** `tests/compatibility/test_zaero_hound.py` locks direct
  scanning, absence of legacy scratch state, scan/sight ranges, arithmetic yaw,
  non-schooling-peer inclusion, and heading-copy behavior. Add deterministic
  live obstacle/yaw/peer-loss sequences, mid-update Hound save/load, and a
  schooling Hound beside a cooldown-active ZBoss before verification. Existing
  development saves need no migration because the discarded scratch fields were
  never part of ZaeREo's schema.

## D-023 — Handler split identity and monster accounting

- **Status/date/owner:** ACTIVE; 2026-07-14; Handler/Hound slice/repository
  maintainers.
- **Context:** The supplied Handler reserves a future Hound in the map total,
  clamps lethal damage only after generic kill handling, creates a child with no
  classname or max health, and converts the original entity into Infantry
  behavior without restarting it. Literal porting can count one pre-split body
  as killed repeatedly, leave a `noclass` child outside stable save/debug
  identity, or double-increment totals if the Rerelease monster lifecycle is
  applied normally. The remaining health is intentionally duplicated into both
  post-split creatures.
- **Decision:** Keep the original entity and `monster_handler` classname through
  conversion. Use native `FL_IMMORTAL` before separation so damage still lands
  but health clamps to one before generic death/count handling, then clear it at
  conversion. Reserve the future Hound in `level.total_monsters` at initial
  Handler spawn unless Zaero no-count bit 16 applies. Create a stable
  `monster_hound`, run the complete native monster lifecycle under a transient
  no-count flag to avoid a second registration, then restore ordinary death
  counting for a reserved child. Replace the reserved debug-kill entry with the
  child. Duplicate the Handler's current health into the child, normalize its
  max/base health to the parent, and convert the original body through one
  reusable native Infantry-configuration hook without calling `monster_start`
  again or changing health, gib threshold, mass, targets, enemy, or identity.
- **Alternatives:** Reproduce the late die-callback clamp and anonymous child,
  rejected because it retains demonstrated count/save identity hazards; start a
  normal Hound and let totals increase at release, rejected because the map HUD
  and completion total change mid-encounter; replace the original entity with
  two new monsters, rejected because target/entity identity and save references
  would change; copy the current Infantry implementation into Zaero code,
  rejected because it would drift from the native substrate.
- **Behavioral impact:** Initial and post-split map totals remain stable, no-count
  applies to both bodies, counted bodies each contribute one kill, the Handler
  cannot die before release, and post-split total durability retains the source's
  health duplication. Entity names, references, callbacks, and max health become
  deterministic and save-safe.
- **Evidence:** Supplied `z_handler.c`, `z_hound.c::hound_createHound`,
  `m_infantry.c::handler_ConvertToInfantry`, legacy `Killed`, Rerelease
  `monster_start`/`G_MonsterKilled`, Q-016/Q-035, and the target implementation
  in `src/zaero/g_zaero_handler.cpp`, `src/zaero/g_zaero_hound.cpp`, and the
  focused hook in `src/m_infantry.cpp`.
- **Tests/migration:** `tests/compatibility/test_zaero_handler.py` locks source
  frames, pre-death clamping, health duplication, stable child identity,
  pre-reserved/no-count accounting, native conversion, timer loops, callback
  registration, and project/registry integration. Add live normal/no-count
  before/during/after split totals, damage-to-clear, death order, trigger-spawn,
  co-op scaling, failed target/owner, debug-kill, and JSON round trips before
  verification. No public stable save schema exists; development saves made
  before this implementation are unsupported.

## D-024 — Sentien locomotion, mitigation, and laser lifecycle

- **Status/date/owner:** ACTIVE; 2026-07-14; Sentien slice/repository
  maintainers.
- **Context:** The supplied Sentien model appears to hover and earlier planning
  text described it as flying, but `SP_monster_sentien` explicitly sets
  `MOVETYPE_STEP`, calls `walkmonster_start`, and never sets `FL_FLY`. Its fend
  holds frame 173 for one second while a generic Zaero damage hook scales damage
  to 85 percent. Its persistent `laser_yaya` child is saved only through a raw
  parent pointer and is switched off—but never freed—on death or gib. The same
  source damage hook later gives ZBoss a distinct monster-inflictor-only scale.
- **Decision:** Preserve grounded STEP/walkmonster locomotion and all 271 source
  frames; do not infer flight from presentation. Give Sentien a dedicated
  Zaero-owned module with exact burst, laser, skill, EMP, fend, pain, and death
  behavior. Represent the two damage-hook activation modes with non-colliding
  saved AI flags and one saved per-monster scale, gated to Zaero levels. Reuse
  the monster-inflictor flag for ZBoss rather than adding another global combat
  branch. Store the laser in the existing saved `beam` reference, record the
  parent's generation in the child, validate both directions before every use,
  and free the child once on death/gib or invalid ownership while preserving the
  visible off event and first-frame aim-lock ordering.
- **Alternatives:** Use native alternate-flight mechanics, rejected because it
  changes ledges, water, collision, paths, and attack positioning from the
  supplied code; copy the unsaved legacy reduced-damage member/flags verbatim,
  rejected because their numeric values collide with Rerelease AI flags; leave
  `laser_yaya` allocated after death, rejected because Q-017 demonstrates an
  entity leak and stale-owner risk; replace the persistent child with one
  instantaneous trace per animation frame, rejected because beam visibility,
  collision, 10 Hz damage debounce, save phase, and locked direction are
  observable.
- **Behavioral impact:** Sentien retains source-shaped grounded movement,
  two-damage burst quirk, skill-scaled locked laser, and one-second 85-percent
  fend. Native maps/monsters never see the mitigation flags. Death and gib no
  longer leave a live beam entity, and stale/reused entity slots cannot redirect
  it. The future boss can use the same isolated scale without sharing Hound or
  Sentien state.
- **Evidence:** Supplied `z_sentien.c/.h`, `g_combat.c` reduced-damage hook,
  legacy and Rerelease monster lifecycle/save code, Q-011/Q-017/Q-036/Q-050,
  and `src/zaero/g_zaero_sentien.cpp`, `src/g_combat.cpp`, `src/g_local.h`, and
  `src/g_save.cpp`.
- **Tests/migration:** `tests/compatibility/test_zaero_sentien.py` locks the
  exact classname, frames, stats, grounded lifecycle, hard-coded bullet damage,
  EMP sites, skill scaling, aim lock, typed fend state, shared hook gating,
  callbacks, generation checks, and cleanup. A historical legacy-v1 one-stage
  `zdef1` smoke recorded five placements but must be rerun under D-046 before
  it closes any current registry/resource claim. Add deterministic live
  attack/fend/death/free-reuse sequences and parent/child JSON round trips before
  verification. No public stable save schema exists; development saves made
  before the scale field and callback set are unsupported.

## D-025 — ZBoss child and projectile lifecycle

- **Status/date/owner:** ACTIVE; 2026-07-14; ZBoss slice/repository maintainers.
- **Context:** The supplied boss stores its live grapple in the generic `laser`
  pointer. A scripted one-shot target or the 42nd-pain retaliation can replace
  the attack while that child is active, after which a second hook overwrites
  the only parent link. Projectile owner pointers have no generation check, and
  the plasma explosion changes model/movement for two animation frames without
  clearing its solid box or touch callback. Those paths can leak a hook, leave a
  dragged client moving, attribute a later projectile to a reused edict slot,
  or run explosion contact more than once.
- **Decision:** Preserve the 281 source frames, attack selection, launch
  offsets, skill values, double-hit plasma damage, grapple/drag behavior, EMP
  pressure, and death barrage. Store the active hook in the existing saved
  `beam` link and record the boss generation in every hook. Validate both sides
  before every live callback; release a live victim and free the hook when an
  attack interrupts it, the boss dies/gibs, ownership becomes invalid, or the
  child expires. Record owner generations on boss plasma and shared flare
  projectiles. Once plasma damage is delivered, clear touch/solidity while its
  two-frame visual finishes. Validate `target_zboss_target` recipients as live
  `monster_zboss` entities before queuing the saved one-shot position.
- **Alternatives:** Retain raw pointers and the solid post-explosion projectile,
  rejected as lifetime/slot-reuse defects; suppress scripted attacks while a
  hook exists, rejected because it changes the mapper event contract; replace
  the grapple with an instantaneous pull or native player grapple, rejected
  because cable flight, impact, drag, reeling, melee handoff, and save phase are
  observable.
- **Behavioral impact:** Ordinary hit/miss/drag, rocket/flare/cannon, pain/EMP,
  and death sequences keep their source timing and values. Malformed targets no
  longer invoke unrelated monster callbacks. Interruptions no longer leak a
  hook or leave victim velocity behind, reused slots cannot inherit flare/plasma
  attribution, and the already-detonated plasma visual cannot damage again.
- **Evidence:** Supplied `z_boss.c/.h`, `z_weapon.c`, shipped `zboss` entity
  lump, Q-014/Q-018/Q-038/Q-051, and
  `src/zaero/g_zaero_zboss.cpp`, `src/zaero/g_zaero_entities.cpp`,
  `src/zaero/g_zaero_weapons.cpp`, `src/g_local.h`, and `src/g_save.cpp`.
- **Tests/migration:** `tests/compatibility/test_zaero_zboss.py` locks the exact
  classname, all source ranges/moves, stats, attacks, thresholds, typed/saved
  state, callback registration, ownership checks, and terminal explosion. The
  private bounded `zboss` observation is legacy v1 only and must be rerun under
  D-046 before it can close registry/resource loading. Add deterministic live
  hook interruption/victim-loss/disconnect/free-reuse,
  plasma direct/radius/owner-loss, all attack and death phases, and JSON
  round trips before verification. No public stable save schema exists;
  development saves made before these fields/callbacks are unsupported.

## D-026 — ZBoss inbound player persistence

- **Status/date/owner:** ACTIVE; 2026-07-14; finale slice/repository
  maintainers.
- **Context:** On `zboss`, the supplied `PutClientInServer` reinitializes every
  positive-health client persistence block, restores only current health, and
  thereby forces Push, Blaster, Flare Gun and three flares. In legacy co-op the
  same function also runs after death. Rerelease separately represents a fresh
  level-entry body, a serialized load-game body, and a death respawn, and can
  host several local/network clients with independent persistence. Its normal
  initializer may also inherit another co-op player's loadout or apply start
  items, Compass, and Grapple, none of which belongs to the finale reset.
- **Decision:** Apply the positive-health reset only when the current level is
  Zaero `zboss` and `ClientBegin` has marked this client's newly created body
  with `spawn_from_begin`. Call `InitClientPersistant` in an explicit boss-entry
  mode which bypasses co-op inheritance and native configurable extras, retain
  current health, and copy the result into that same client's co-op respawn
  snapshot. Do not add a global or serialized one-shot latch: a loaded game
  reuses its saved in-use body and a death respawn does not set the fresh-body
  marker.
- **Alternatives:** Copy the legacy map-name branch onto every Rerelease
  `PutClientInServer`, rejected because it would re-run the inbound operation
  during an ordinary death respawn; use one level-global boolean, rejected
  because later co-op/network clients and split-screen players enter
  independently; persist a per-client applied flag, rejected because the
  native body lifecycle already distinguishes load from entry and the extra
  state would need reset semantics for every travel/reconnect path; call the
  normal initializer unchanged, rejected because co-op inheritance and native
  start extras violate the exact inventory contract.
- **Behavioral impact:** Each positive-health player entering the finale loses
  carried inventory independently, retains current health, and starts with
  exactly Push, Blaster, Flare Gun and three flares. Loading a mid-boss save
  leaves serialized persistence untouched; death uses native respawn behavior
  from the per-client finale snapshot; non-Zaero and non-`zboss` maps are
  unaffected.
- **Evidence:** Supplied `p_client.c`, Rerelease `ClientBegin`,
  `PutClientInServer`, save/load and co-op persistence paths, Q-052, and
  `src/p_client.cpp`/`src/g_local.h`.
- **Tests/migration:** `tests/compatibility/test_zaero_zboss.py` locks the
  positive-health ordering, fresh-body/Zaero/exact-map gates, boss-entry mode,
  exact item surface and per-client co-op snapshot. Debug compiles with zero
  warnings. Live first entry, manual and autosave reload, death/respawn,
  outbound/re-entry travel, late join/reconnect, two-to-four-player co-op and
  two-to-four-way split-screen fixtures remain before verification. The change
  adds no serialized field and needs no save migration.

## D-027 — Finale white fade and handoff

- **Status/date/owner:** ACTIVE; 2026-07-14; finale slice/repository
  maintainers.
- **Context:** The supplied `BeginIntermission` assigns 50 legacy frames on
  non-deathmatch `zboss`; `G_RunFrame` holds an already-requested level exit
  while those frames count down, ordinary world work continues, and each
  intermission client receives a progressively opaque white blend. The authored
  `z_end` changelevel then passes the exact `outro.cin+victory.pcx` chain to
  `gamemap`. Rerelease's existing intermission fade is instead an optional
  1.3-second black phase begun by `ExitLevel`, and that branch returns before
  ordinary frame work.
- **Decision:** Implement the Zaero path in a dedicated module. At intermission
  start on an exact Zaero `zboss` non-deathmatch level, override the native
  fade flag with an active typed five-second deadline. At 40 Hz, write the same
  white alpha to every active client's native `screen_blend`, continue the
  ordinary game frame, and suppress `exitintermission` until the deadline.
  Then clear the reused native fade state and call the unchanged `ExitLevel`,
  which forwards the authored `outro.cin+victory.pcx` string through native
  `gamemap`. Add no protocol opcode or map mutation.
- **Alternatives:** Reuse the native black fade unchanged, rejected because
  color, duration, start point, and world cadence differ; add a custom network
  effect or cgame opcode, rejected because the supported player-state blend is
  sufficient; patch the BSP with a Rerelease screen-fader entity, rejected
  because mapper data should remain untouched and the exit deferral is a game
  rule; convert 50 literally to target ticks, rejected because it would finish
  four times too quickly at 40 Hz.
- **Behavioral impact:** The finale now fades each local/network view toward
  white for five seconds before beginning the exact supplied outro/victory
  sequence. Native maps, deathmatch, and authored Rerelease black fades retain
  their existing behavior. Ordinary entities continue running during the
  Zaero fade as in the supplied code.
- **Evidence:** Supplied `p_hud.c`, `p_view.c`, `g_main.c`, shipped `zboss`
  entity 88/`z_end`, Rerelease intermission/fade/player-state code, Q-053,
  `src/zaero/g_zaero_finale.cpp`, `src/g_main.cpp`, and `src/p_hud.cpp`.
- **Tests/migration:** `tests/compatibility/test_zaero_zboss.py` locks the exact
  map/mode gates, typed duration, per-client white blend, exit suppression,
  project wiring, and authored handoff string. Debug compiles with zero
  warnings. Live alpha samples at 40 Hz, a thinking-entity sentinel, multiple
  clients, boss death target, outro completion/skip, victory art, credits,
  return/menu state, and repeat-run cleanup remain before verification.
  Intermission saves are already prohibited by `G_CanSave`; existing native
  level fade fields are reused, so no save schema or migration changes.

## D-028 — A2K deadline and radius boundaries

- **Status/date/owner:** ACTIVE; 2026-07-14; A2K slice/repository maintainers.
- **Context:** The supplied A2K stores `level.framenum + 50` in one client,
  consumes the item at gunframe 14, holds frame 19 until exact equality, and
  grants absolute immunity while the stored frame is greater than the current
  frame. At equality it samples Quad, runs ordinary radial damage followed by
  a visibility-gated outer pass, and only then creates the six-frame visual.
  Qualifying entities may take two hits and the attacker receives the
  half-damage rule in each pass. Rerelease runs at 40 Hz, advances generic
  weapon frames in a different callback order, and its native
  `T_RadiusDamage` uses a linked inflictor's bbox center plus special BSP
  closest-point behavior rather than the source's `s.origin`/bbox-center
  equation.
- **Decision:** Store one absolute `gtime_t zaero_a2k_detonate_time` in each
  client and register it with the JSON save schema. Keep the view animation at
  its native-encoded 10 Hz cadence, but intercept held gunframe 19 on every
  host tick so the typed five-second/200-tick boundary is exact; let native
  `Weapon_Generic` release the firing state after detonation. Do not create a
  countdown entity. Apply immunity from the client deadline before ordinary
  invulnerability without a `DAMAGE_NO_PROTECTION` gate, and clear the deadline
  before blast damage. Use a Zaero-owned source-shaped damage walker for both
  ordered passes so origin, bbox-center distance, integer conversion,
  unnormalized direction, `CanDamage`, the exact `MASK_OPAQUE` eye-to-eye LOS
  trace, self halving, and multiplicity stay exact. Sample only the client's
  live Quad time at blast,
  scale damage and the inner radius by four, derive the outer radius from it,
  then create the registered `A2K Explosion` animation.
- **Alternatives:** Store 200 target ticks, rejected because a duration is the
  compatibility contract and literal ticks couple saves to host cadence; add a
  countdown edict, rejected because none exists in the source and it creates
  ownership/free-reuse state; call native `T_RadiusDamage` for the first pass,
  rejected because its linked/BSP geometry changes source boundaries; run the
  countdown from a global frame hook, rejected because weapon state, saves,
  split-screen clients, death, and reconnect are independently owned.
- **Behavioral impact:** Activation consumes one A2K even with infinite ammo,
  the firing client alone is immune for exactly five seconds and cannot switch
  away through the ordinary firing state, death cancels the event, and the HUD
  has source-priority truncated seconds. At blast, protection has ended, Quad
  is sampled then, visible inner targets may be hit twice, self damage is
  halved per pass, and no explosion helper exists beforehand. Non-Zaero levels
  and other clients are unaffected.
- **Evidence:** Supplied `z_weapon.c`, `g_combat.c`, `p_hud.c`, `p_client.c`,
  Rerelease `p_weapon.cpp`/`g_combat.cpp`, Q-003/Q-004, and
  `src/zaero/g_zaero_a2k.cpp`, `src/g_combat.cpp`, `src/p_hud.cpp`,
  `src/p_client.cpp`, `src/p_weapon.cpp`, `src/g_local.h`, and `src/g_save.cpp`.
- **Tests/migration:** `tests/compatibility/test_zaero_a2k.py` locks source
  hashes, typed timing, callback order, absolute protection, damage geometry,
  golden falloff/self/Quad arithmetic, helper creation/animation, item/project
  wiring, HUD priority, obituaries, cleanup and save registration. Debug builds
  with zero warnings. Live exact-boundary and skipped-frame capture,
  `DAMAGE_NO_PROTECTION`, death immediately before blast, inner/outer
  visibility and double-hit fixtures, Quad activation-versus-detonation,
  split-screen/co-op isolation, disconnect/changelevel, and
  pre/detonation/post-helper JSON round trips remain before verification. No
  public stable save schema exists; development saves made before the new
  client field/callback are unsupported.

## D-029 — Plasma Shield collision, durability, and placer identity

- **Status/date/owner:** ACTIVE; 2026-07-14; Plasma Shield slice/repository
  maintainers.
- **Context:** The supplied use callback creates a `MOVETYPE_PUSH`/
  `SOLID_BBOX` sprite 50 units ahead from only two view-rotated diagonal
  points, assigns 4,000 health and a ten-second think, and leaves its `owner`
  assignment explicitly commented out. As a result, the placing player's
  movement and projectiles collide like everyone else's; Sniper alone loops
  past exact-classname Shield traces. Its special `CheckPowerArmor` branch
  treats health as a read-only power limit, absorbs integer two-thirds damage
  up to `health * 2`, then lets ordinary damage subtract only the remainder.
  Native Rerelease power armor differs in CTF, energy-damage, low-damage,
  effect, and cell-spend behavior, and generic projectile code gives `owner`
  collision meaning.
- **Decision:** Preserve the exact oriented origin, angles, two-point bbox,
  pusher solidity, `EF_POWERSCREEN`, 4,000 health, ten-second typed lifetime,
  all-mode active loop, and deathmatch-only deploy/destruction sounds. Leave
  gameplay `owner` unset. Record the placer only in the already JSON-registered
  non-collision `activator` reference with `count` as its edict generation;
  clear stale metadata without expiring an otherwise independent Shield.
  Query EMP before sound, consumption, or spawn, and retain native infinite-
  ammo integration after a successful query. At the native power-armor seam,
  recognize the exact classname after the shared silent EMP and armor-bypass
  gates, then run the source integer formula and `TE_SHIELD_SPARKS`/
  200-millisecond feedback without spending health separately. Do not import
  the uncalled legacy `DAMAGE_ARMORMOSTLY`; Rerelease-only damage flags keep
  their native outer `T_Damage` semantics.
- **Alternatives:** Set `owner` to the player for convenient attribution,
  rejected because generic projectile/collision logic could grant an owner
  exemption the source does not have; omit placer state entirely, rejected
  because native diagnostics and future lifecycle fixtures need a stable
  association; route through native client/monster power armor, rejected
  because all of its changed equations and effects are observable; replace the
  pusher with a static non-pusher bbox or symmetric bounds, rejected because
  placement and collision boundaries would change.
- **Behavioral impact:** A successful use spends one Shield unless native
  infinite ammo is active; an EMP-blocked use only plays the shipped missfire.
  The barrier blocks the placer and ordinary placer shots, Sniper penetrates,
  and ordinary hits remove roughly one-third damage from health with exact
  integer boundaries until destruction or independent expiry. Disconnect or
  slot reuse cannot transfer placer identity and does not prematurely erase
  the legacy barrier. Stock/non-Zaero combat remains unchanged.
- **Evidence:** Supplied `z_item.c::Use_PlasmaShield`,
  `PlasmaShield_die`/`PlasmaShield_killed`, `g_combat.c::CheckPowerArmor`,
  `z_weapon.c::fire_sniper_bullet`, Rerelease `g_combat.cpp`, projectile and
  pusher physics, Q-008/Q-009/Q-019/Q-043, and
  `src/zaero/g_zaero_plasma_shield.cpp`.
- **Tests/migration:**
  `tests/compatibility/test_zaero_plasma_shield.py` locks source identities,
  EMP/inventory/sound/spawn order, exact geometry, mode sounds, typed lifetime,
  callbacks, ownerless generation metadata, golden mitigation boundaries,
  Sniper penetration, item wiring and project/save registration; Debug builds
  with zero warnings. Live owner/other/player/projectile collision, pitch/yaw
  bbox, one/low/large damage, `DAMAGE_NO_ARMOR`/native expansion flags, EMP
  owner/foreign/overlap, SP/co-op/DM audio, expiry/destruction, disconnect/
  free-reuse/changelevel, and post-deploy/pre-expiry/post-load JSON fixtures
  remain before verification. Existing edict fields and registered callbacks
  require no new schema field; pre-implementation development saves remain
  unsupported.

## D-030 — Visor duration representation and incremental gate

- **Status/date/owner:** ACTIVE; extended 2026-07-14; Visor slice/repository
  maintainers.
- **Context:** The supplied Visor stores `visorFrames` in both persistent client
  inventory state and dropped edicts. A fresh item supplies 300 legacy frames,
  exact-full owners reject it, a dropped pickup adds its saved value and may
  exceed 300, while a fresh pickup from any other state resets to 300. Literal
  frame storage would make 40 Hz exhaust four times too quickly. Active viewing
  also creates the overlapping `VisorCopy` covered by D-021.
- **Decision:** Represent carrier and dropped-item values as
  `gtime_t zaero_visor_remaining`, with independent JSON registration in
  `client_persistant_t` and `edict_t`. Preserve exact equality, addition,
  fresh-reset and 30-second DM respawn rules. Transfer the typed value on drop,
  clear it when ownership is lost, copy it with native co-op loadout cloning,
  and initialize it through start-item and cheat-grant paths that otherwise
  bypass an ordinary map pickup. Mark player drops with the native dropped-
  player/non-instanced state so one legacy item remains one transferable item
  under Rerelease co-op. The active lifecycle now decrements that same value by
  elapsed `gtime_t`, uses generation-checked camera/copy references, bounded
  traversal, client-local view/HUD/static state, and exact saved prior
  pmove/FOV/gun/visibility restoration. D-021 supplies the non-solid visual-copy
  FIX; D-008 supplies the active command policy.
- **Alternatives:** Store 300 or 1,200 target ticks, rejected because duration
  is the observable/save contract; leave generic
  `Pickup_General`/`Drop_General`, rejected because it loses partial/stacked
  time and dropped transfer; omit native grant/co-op hooks, rejected because an
  owned zero-time Visor is a broken Rerelease integration state.
- **Behavioral impact:** Fresh Visors carry exactly 30 seconds; dropped partial
  values add without a maximum, values above 30 may be reset by a fresh item,
  and drop/save/transition/co-op ownership retain the same duration. Active use
  consumes elapsed time at 40 Hz, redirects only that client's view/HUD,
  preserves the real player's collision, and cancels on health damage, death,
  drop, putaway, respawn, disconnect, intermission, invalid camera, or expiry.
- **Evidence:** Supplied `g_items.c::Pickup_Visor`/`Drop_Visor`,
  `z_item.c::Use_Visor`, `g_cmds.c` grant path, `g_save.c`, legacy
  `client_persistant_t`/`edict_t`, Rerelease item/drop/co-op/save paths, Q-045,
  D-021, and `src/zaero/g_zaero_visor.cpp`.
- **Tests/migration:** `tests/compatibility/test_zaero_visor.py` locks source
  hashes, typed 30-second/300-legacy-frame/1,200-target-tick equivalence, exact
  pickup arithmetic, bounded traversal goldens, drop/cancellation ordering,
  command, HUD/view/static, generation, lifecycle, trace-order FIX, and all
  carrier/drop/active save fields; Debug builds with zero warnings. Live
  fresh/exact/partial/stacked/reset pickups, active duration, camera cycling,
  cancellation, collision, split-screen, transition, and JSON round trips
  remain. No public stable save schema exists yet.

## D-031 — Weapon-number multiselect and native wheel coexistence

- **Status/date/owner:** ACTIVE; 2026-07-14; Player command/wheel integration
  maintainers.
- **Context:** Zaero 1.1 executable source and shipped configuration define
  `use weapon 1` through `use weapon 10`, with Flare Gun alternating behind
  Blaster on slot 1, Sniper Rifle behind Railgun on slot 9, and Sonic Cannon
  behind BFG10K on slot 10. The 1.1 readme instead says 0–9 even though its key
  0 configuration invokes slot 10. Rerelease also provides a native 32-entry
  weapon wheel and mission-pack weapon chains; neither existed in the legacy
  command path.
- **Decision:** Treat source/config and the observed key-0 bind as authoritative:
  preserve the exact ten-slot table and cycle an alternate only from the
  currently held weapon. Try each slot member once in source order and stop
  when an owned item is passed to its use callback, including the legacy case
  where ammo rules then reject the switch. Isolate this lookup from native
  mission-pack chains so they cannot insert a third weapon. Keep `zwepas_on`
  and `zwepas_off` opt-in and never rewrite user bindings by default. In
  parallel, expose eligible Zaero weapons through native wheel metadata;
  preserve Push and Sniper's source selection exclusions for ordinary cycling,
  while the explicit slot-9 command can still select Sniper.
- **Alternatives:** Implement readme-literal 0–9, rejected because it conflicts
  with executable source and the shipped key-0 bind; replace number commands
  with the wheel, rejected because keyboard command behavior is observable and
  mapper/player configuration may depend on it; reuse native weapon chains,
  rejected because expansion members and their order are not Zaero's table;
  auto-execute the binding aliases, rejected because the port must not trample
  existing Rerelease controls.
- **Behavioral impact:** `use weapon 1`, 9, and 10 toggle their exact two-member
  Zaero pairs based on the held weapon; slots 2–8 select one stock weapon. A
  missing first alternate falls through to the second, but an owned first
  alternate with insufficient ammo retains the source stop behavior. Native
  wheel selection remains available and uses the same item/use machinery.
- **Evidence:** Supplied `g_cmds.c::alternates`, `tryUse`, `findNext`,
  `altSelect`, and `Cmd_Use_f`; supplied `zaero.cfg`/1.1 documentation; tracked
  `pack/zaero.cfg`; Rerelease `Cmd_Use_f`, `Use_Weapon`, item wheel configstrings,
  PLY-012, and Q-027.
- **Tests/migration:**
  `tests/compatibility/test_zaero_items_weapons.py` locks all ten pairs,
  held-weapon offset, owned-item test, native-chain isolation, dispatch and
  wheel capacity/exclusion metadata; `tests/content/test_pack_scaffolding.py`
  locks all number binds and the no-auto-execution rule. Debug builds with zero
  warnings. Live all-number missing/owned/no-ammo/current/pending-switch tests,
  wheel selection, two-local-player isolation, and a clean-profile bind diff
  remain before verification. This adds no saved state or save migration.

## D-032 — Player HUD, lifecycle, and obituary presentation

- **Status/date/owner:** ACTIVE; 2026-07-14; Player presentation and lifecycle
  maintainers.
- **Context:** The supplied game exposes a per-client `showorigin` diagnostic
  through legacy statusbar slots 16–19, but those numbers collide with the
  Rerelease HUD contract. The native wheel configstrings already described
  Zaero weapons while the owned-weapon bitset stopped at the last stock
  weapon. Zaero also carries 25 exact monster obituary fallbacks, seven custom
  means-of-death messages, skin-first `f`/`F` gender selection, and an immediate
  post-suicide respawn after its five-second guard. Rerelease has safer format
  handling, localization keys, spectator-aware death flow, and per-client HUD
  state that must remain isolated for split screen.
- **Decision:** Store the `showorigin` toggle per client, register it with JSON
  saves, publish its integer-truncated coordinates through reserved private
  stats, and preserve the source-shaped left-edge layout without consuming
  native stat numbers. Build the owned-weapon bitset from every registered item
  that is both a weapon and assigned a valid wheel index. Retain the native
  spectator guard, typed five-second delay, `player_die` lifecycle, and deferred
  respawn; do not import the immediate legacy `respawn()` call. Emit the 25
  exact monster messages through native brace-safe formatting, limiting stock
  monster fallbacks to Zaero maps while allowing Zaero-owned actors wherever
  they validly spawn. On Zaero maps only, preserve first-character `skin`
  `f`/`F` gender selection for the source self-kill strings; keep native
  localized behavior on stock maps. Preserve all seven existing custom MOD
  messages. Add proper localization keys later rather than inventing an
  unvalidated runtime asset contract in this slice.
- **Alternatives:** Reuse stats 16–19, rejected because they overlap native HUD
  state; make `showorigin` global, rejected because it leaks between local
  clients; retain the bounded stock-item weapon loop, rejected because it
  silently hides custom wheel weapons; call immediate `respawn()`, rejected
  because it bypasses native death/spectator/timing flow; apply the English
  monster table globally, rejected because it changes stock-map presentation;
  pass the legacy strings through printf formatting, rejected because several
  contain unsafe percent text; add speculative localization resources now,
  rejected until their target asset format and loading path are validated.
- **Behavioral impact:** Each client can independently toggle the four-line
  origin display and retain it across a development save. Flare Gun, IRED and
  Sonic Cannon ownership can reach the native wheel while intentionally
  unindexed weapons remain excluded. Suicide remains unavailable before five
  seconds and uses Rerelease death/respawn scheduling. Zaero gameplay receives
  source-exact monster and custom-weapon death prose and skin-first pronouns
  without overwriting stock-map localization behavior.
- **Evidence:** Supplied `g_cmds.c::Cmd_ShowOrigin_f`, `p_hud.c::G_SetStats`,
  `g_spawn.c` statusbar, `g_cmds.c::Cmd_Kill_f`, and
  `p_client.c::ClientObituary`/`IsFemale`; Rerelease item registry, HUD stats,
  save registration, death lifecycle and localized obituary paths; PLY-012,
  PLY-016, PLY-018, PLY-019, Q-054, and the corresponding `src` integration
  points.
- **Tests/migration:**
  `tests/compatibility/test_zaero_player_presentation.py` locks source
  identities, per-client command/save/HUD/layout behavior, all-item wheel
  ownership, the native five-second/spectator/deferred-respawn path, all 25
  exact monster fallbacks, activation boundaries, seven custom MODs, safe
  formatting, and skin-first gender behavior. Live split-screen toggling,
  wheel selection, save/load round trips, suicide timing, every obituary
  attacker/self/world boundary, and localization-resource verification remain.
  No public stable save schema exists; pre-field development saves are not a
  supported migration target.

## D-033 — Projectile-dodge timing and Rerelease coexistence

- **Status/date/owner:** ACTIVE; 2026-07-14; Projectile-dodge slice/repository
  maintainers.
- **Context:** Zaero replaces legacy `check_dodge` with a client-firing-time
  8,192-unit trace, a 25-percent easy-skill random gate, and a saved two-stage
  `AI_DODGETIMEOUT`/`dodgetimeout` throttle. Rocket, BFG and Flare call it just
  before linking their projectile; Blaster's call is deliberately commented
  out. Rerelease instead marks many projectile types `FL_DODGE` and lets each
  monster perform a recurring 512-unit proximity scan governed by native
  `dodge_time`. Running both systems would double-trigger eligible projectiles,
  restore Blaster and grenade dodges, and alter the source's random/call timing;
  replacing the native path globally would regress stock and expansion maps.
- **Decision:** On classified Zaero maps, use a dedicated
  `Zaero_CheckProjectileDodge` call at the exact client Rocket, BFG and Flare
  spawn sites, before entity linking. Preserve the source `MASK_SHOT` trace,
  facing/health/callback checks, easy gate, strict time comparisons, skill cap
  at three, flag-clear/rearm order, initial `(4 - skill) * 1.1` seconds and
  armed `skill * 4` seconds. Store the deadline as `gtime_t` in
  `monsterinfo_t`, append a non-colliding Zaero AI flag, and register both
  through the native JSON save path. Pass the native trace and non-gravity
  marker to the Rerelease dodge callback without changing its ABI. Suppress the
  native proximity scan only on classified Zaero maps; retain it byte-for-byte
  for stock, mission-pack and other maps. Client ownership inside the helper
  preserves the source exclusion of monster-fired projectiles.
- **Alternatives:** Keep only native `FL_DODGE`, rejected because its projectile
  set, proximity timing and throttle are observably different; run both,
  rejected because it duplicates callbacks and defeats Blaster exclusion;
  remove `FL_DODGE` from stock projectile constructors, rejected because that
  changes non-Zaero modes and expansions; reuse native `dodge_time`, rejected
  because callbacks independently mutate it and it cannot represent Zaero's
  initial-unflagged versus armed state; add an engine/protocol change, rejected
  because the game DLL can express the complete contract.
- **Behavioral impact:** Player Rocket, BFG and Flare shots on Zaero maps can
  invoke the first eligible living, facing monster's dodge callback at firing
  time. Easy consumes the source-shaped 25-percent decision. Repeated eligible
  shots use the exact initial and armed windows, including skill zero's
  zero-duration armed phase and strict boundary. Blaster, grenades and
  monster-fired projectiles do not enter this Zaero path. Native projectile
  dodging remains unchanged outside classified Zaero maps.
- **Evidence:** Supplied `g_weapon.c::check_dodge`, `fire_rocket`, `fire_bfg`
  and commented `fire_blaster` call; supplied
  `z_weapon.c::fire_flare`; supplied `g_local.h` AI flag/field; Rerelease
  `g_monster.cpp::M_CheckDodge`, projectile flags, typed time and JSON save
  registration; AI-016 and Q-049.
- **Tests/migration:**
  `tests/compatibility/test_zaero_projectile_dodge.py` identity-locks both
  source oracles and verifies the typed field/flag/save schema, easy gate,
  exact trace/eligibility/ETA callback, both formulas and update order,
  Rocket/BFG/Flare-before-link hooks, Blaster exclusion, and Zaero-only native
  scanner suppression. Debug builds with zero warnings. Seeded live skills
  0–3 and capped higher-skill repeated shots, exact 40 Hz boundary samples,
  stock/custom callback behavior, blocked traces/facing/death, and JSON saves
  during initial, armed and expired windows remain. No public stable save
  schema exists; pre-field development saves are unsupported.

## D-034 — trigger_laser contract and target-callback lifetime

- **Status/date/owner:** ACTIVE; 2026-07-14; World-entity slice/repository
  maintainers.
- **Context:** `trigger_laser` is present in the supplied source and mapper
  comments but absent from all supplied BSPs. It requires a target, starts
  automatically after one legacy frame, traces 2,048 units every legacy frame,
  fires only for a player/monster hit, and either rearms after `wait` under bit
  1 or frees itself. It never assigns a use callback. Earlier editor metadata
  advertised `targetname` as an optional toggle even though the runtime had no
  such surface. The source also continues through `self` after `G_UseTargets`;
  a target can free the laser and a synchronous allocation can reuse that slot,
  so checking only `inuse` is insufficient in the safe-handle target.
- **Decision:** Preserve the source no-use point-entity ABI: required `target`,
  default `wait` 4, movedir from `angle`, exact beam presentation, hidden
  100-ms auto-start, 100-ms think cadence, 2,048-unit source mask with the
  Rerelease player contents bit added, one spark emission at obstruction, and
  bit-1 hidden rearm versus one-shot free. Keep `message` and `delay` through
  native `G_UseTargets`. Do not assign a use callback or expose `targetname` in
  generated editor definitions. Capture the laser's generation immediately
  before target dispatch and return unless both `inuse` and the generation
  still match; retain every ordinary post-dispatch ordering step otherwise.
- **Alternatives:** Add a `targetname` toggle because many trigger entities have
  one, rejected because the executable source never does; model this as a brush
  trigger, rejected because the source is a directional point beam; preserve
  the post-free write, rejected as an unobservable lifetime defect; check only
  `inuse`, rejected because synchronous slot reuse can make it true for a
  different entity; silently free the unsupported classname, rejected because
  source-only mapper contracts must remain functional.
- **Behavioral impact:** Community maps receive the source-authored automatic
  beam and rearm/free behavior with no invented toggle contract. Normal target
  callbacks behave identically. A callback that removes or replaces the laser
  terminates that think safely instead of hiding, scheduling, freeing, or
  writing beam state into the replacement entity. Supplied retail maps are
  unaffected because none places the classname.
- **Evidence:** Supplied `z_trigger.c::SP_trigger_laser`,
  `trigger_laser_on` and `trigger_laser_think`; BSP classname audit showing
  zero placements; Rerelease `G_UseTargets`, edict generation model, typed time,
  render/trace APIs and saveable callbacks; MAP-002, AI-010, E-030 and Q-055.
- **Tests/migration:**
  `tests/compatibility/test_zaero_world_entities.py` identity-locks
  `z_trigger.c` and verifies target/default/timing/render/range/mask/sparks,
  qualifying-hit target dispatch, generation guard, bit-1 rearm, one-shot free,
  callback registration, no use assignment, and canonical editor properties;
  `tests/editor/test_generate_editor_defs.py` proves all three generated FGD
  files are current and identical. Synthetic live no-target, obstruction,
  player/monster/dead-body, ordinary target, target-free/reuse, one-shot,
  repeated rearm and mid-wait JSON fixtures remain. No new saved field or save
  migration is introduced.

## D-035 — Step-physics trigger-free lifetime safety

- **Status/date/owner:** ACTIVE; 2026-07-14; Physics core/repository
  maintainers.
- **Context:** Supplied Zaero `SV_Physics_Step` removes the upstream legacy
  post-`G_TouchTriggers` `inuse` guard, allowing categorization, world effects,
  physics-change callbacks and ordinary think work to continue after a trigger
  frees the stepped entity. Rerelease retains both an immediate moved-path
  guard and a later defensive guard. The port's custom `MOVETYPE_FALLFLOAT`
  likewise calls projectile and trigger callbacks before water-transition and
  think work, so it needs the same lifetime boundary. The omission is not a
  useful mapper contract and continuing through freed storage is unsafe.
- **Decision:** Do not import Zaero's removed guard. Preserve the native
  Rerelease `SV_Physics_Step` ordering and immediate `inuse` return after
  `G_TouchTriggers`, before footstep, categorization, world effects,
  physics-change and think processing. In `SV_Physics_FallFloat`, return after
  `G_TouchProjectiles` or `G_TouchTriggers` frees the entity, before linking,
  water-transition, event or think work as applicable. Do not otherwise reorder
  valid touches, movement, ground checks, linking or ordinary thinking.
- **Alternatives:** Reproduce the omission literally, rejected as a use-after-
  free risk with no valid observable behavior to preserve; skip trigger touches
  for Zaero movers, rejected because triggers are gameplay-visible; defer only
  `SV_RunThink`, rejected because intermediate world/event work also dereferences
  the freed edict; replace the physics core wholesale with legacy code, rejected
  because it would import unrelated vintage drift.
- **Behavioral impact:** Ordinary step, Ride and FallFloat entities keep native
  movement/touch ordering. If a projectile or trigger callback removes one,
  physics stops for that entity in the same frame. No post-free sound/event,
  water, world-effect, animation or think callback is emitted. Supplied valid
  map behavior is unchanged except that pathological post-free effects cannot
  occur.
- **Evidence:** Supplied and upstream legacy `g_phys.c::SV_Physics_Step`, pinned
  Rerelease `g_phys.cpp::SV_Physics_Step`, port
  `SV_Physics_FallFloat`, Q-047 and MAP-010.
- **Tests/migration:**
  `tests/compatibility/test_zaero_physics_contract.py` identity-locks supplied
  `g_phys.c` and proves the step trigger guard precedes categorization and
  think, while both FallFloat callback guards precede linking/transition/think
  work. Debug/Release binaries already compile the retained paths with zero
  warnings. Live ordinary trigger, one-shot free, projectile-free, synchronous
  free/reuse, Ride, FallFloat, event/audio and save fixtures remain. No saved
  field or migration is added.

## D-036 — func_plat bit-2 low-trigger collision

- **Status/date/owner:** ACTIVE; 2026-07-14; Map behaviors/repository
  maintainers.
- **Context:** Supplied Zaero `g_func.c::Touch_Plat_Center` assigns platform
  spawnflag bit 2 to `PLAT_LOW_TRIGGER_2`. While a platform is lowered, a live
  player activates it only when the player's feet are no more than eight units
  above `moveinfo.end_origin[2] + maxs[2]`; equality activates because the
  source rejects only a strict greater-than result. Eleven authored platforms
  across eight supplied maps use the bit. Rerelease independently assigns the
  same bit to `SPAWNFLAG_PLAT_NO_MONSTER`, so applying either interpretation
  globally would break the other map family.
- **Decision:** Keep both symbolic meanings at bit 2. In
  `Touch_Plat_Center`, apply the source feet-height rejection only when
  `level.zaero_mapper_contract` selects the mapper semantics, only at
  `STATE_BOTTOM`, and only after the existing live-client checks. Preserve the
  independent bit-1 low trigger-volume shaping. In `Use_Plat`, treat bit 2 as
  native no-monster only outside that scope, so Zaero's low-trigger bit does
  not accidentally acquire Rogue's unrelated monster restriction. D-018 owns
  the classifier evidence, not the boundary behavior.
- **Alternatives:** Interpret bit 2 as low-trigger globally, rejected because
  it removes native no-monster behavior; retain native meaning globally,
  rejected because all 11 authored Zaero platforms lose their mapper contract;
  infer intent from height, targetname, or nearby geometry, rejected as an
  ambiguous per-entity heuristic; patch supplied BSPs, rejected because drop-in
  compatibility is required.
- **Behavioral impact:** A qualifying live player at or below the exact
  eight-unit boundary raises a lowered flagged Zaero platform; a player above
  it does not. Dead players and non-clients remain ineligible. Non-Zaero maps
  retain ordinary player touch behavior and native bit-2 monster suppression;
  bit 1 continues to alter only the trigger volume.
- **Evidence:** Identity-locked supplied `g_func.c` SHA-256
  `aa7d05629c1213145e8fb74d14252d0b982b35cbc2dd4c75f1c27882f72adea6`;
  pinned Rerelease `g_func.cpp`; normalized BSP audit plus direct entity-lump
  inventory of zbase2 (1), zdef1 (1), zdef2 (2), zdef4 (1), zdm1 (1), zdm3
  (1), zdm4 (2), and ztomb3 (2); D-018, MAP-019 and E-046.
- **Tests/migration:**
  `tests/compatibility/test_stock_map_behaviors.py` locks source identity, all
  11 placements, below/equal/above boundary behavior, dead/non-player
  rejection, explicit bit collision, bit-1 independence, and native fallback.
  Live trigger contact from below/at/above the boundary, movement, monster use,
  all-placement smoke, mid-move JSON round trip, non-Zaero stock/Rogue maps,
  and D-018 classifier false-positive/false-negative fixtures remain. No new
  saved field, callback, or save migration is introduced.

## D-037 — misc_explobox FALLFLOAT and push contract

- **Status/date/owner:** ACTIVE; 2026-07-14; Stock world
  extensions/repository maintainers.
- **Context:** Zaero changes stock `misc_explobox` in two source-delta functions.
  Spawn uses `MOVETYPE_FALLFLOAT`, default mass 400, `AI_NOSTEP`, and a
  two-legacy-frame drop-to-floor deadline. Its touch callback accepts only
  clients, rejects a client standing on the barrel, deliberately does not
  require the pusher to be grounded, and moves the barrel away through
  `SV_movestep` by `20 * other_mass / barrel_mass` units per second. Rerelease
  instead uses STEP, default mass 50, `FL_TRAP`, repeated barrel world-effect
  thinking, and a grounded-contact `M_walkmove` path. Thirty-one supplied
  entities across five maps exercise the Zaero spawn contract.
- **Decision:** On the D-018 mapper-contract scope, select FALLFLOAT and default
  mass 400, assign `AI_NOSTEP`, run the existing saveable `barrel_start` after
  200 ms, and stop its native repeated-think handoff after `M_droptofloor`.
  In `barrel_touch`, dispatch the source client/standing checks and call the
  existing Rerelease `SV_movestep` with relinking. Scale distance by
  `gi.frame_time_s`, preserving the legacy speed at 40 Hz rather than moving
  four times too fast. Retain STEP, mass 50, `FL_TRAP`, native contact
  eligibility, `M_walkmove`, world-effect thinking, damage, and explosion on
  non-Zaero maps. Retain the native Rerelease damage/explosion implementation
  in both scopes because Zaero did not alter those functions relative to the
  legacy comparison baseline; do not import unrelated vintage drift.
- **Alternatives:** Apply FALLFLOAT globally, rejected because it changes stock
  and mission-pack barrels; keep the native barrel globally, rejected because
  it removes Zaero buoyancy and authored mass/push behavior; use `M_walkmove`
  with a relaxed ground check, rejected because the source explicitly calls
  `SV_movestep`; multiply each legacy touch by 0.1 seconds at 40 Hz, rejected
  because it quadruples speed; replace the full Rerelease barrel with vintage
  code, rejected as unrelated baseline drift.
- **Behavioral impact:** Zaero barrels use the existing typed FALLFLOAT
  slope/freefall/buoyancy path and move away from any touching live client,
  including an airborne one, in proportion to client/barrel mass. A client
  standing on the barrel and every non-client cannot push it. Explicit mapper
  mass remains authoritative. Stock and expansion maps retain their native
  barrels and modern explosion presentation.
- **Evidence:** Identity-locked supplied `g_misc.c` SHA-256
  `60378a0a35864453e5d6a2e1a18a43cc73c327e28dc3a45a1bec087425515fe1`;
  `SP_misc_explobox` and `barrel_touch` source delta; pinned Rerelease
  `g_misc.cpp::SP_misc_explobox`, `barrel_touch` and `m_move.cpp::SV_movestep`;
  normalized BSP counts zbase1 (4), zdef1 (2), ztomb2 (6), zwaste2 (7), and
  zwaste3 (12); D-018, MAP-010, MAP-020, and E-047.
- **Tests/migration:**
  `tests/compatibility/test_stock_world_extensions.py` locks the source
  identity, all 31 placements, gated movement/mass/flag/start state, exact
  10-to-40 Hz mass-ratio conversion, client-only and airborne eligibility,
  `SV_movestep` relinking, existing saveable callbacks/explosion path, and
  native fallback. Live dry/water/freefall/sink/float, grounded and airborne
  client contact, standing-on-barrel, non-client, slope/step/block,
  weapon-Push, damage/explosion, explicit-mass, mid-motion JSON round trip,
  stock/Rogue map, and D-018 classifier fixtures remain. No saved field or save
  migration is added; existing movetype/callback registrations carry state.

## D-038 — func_door_rotating zero-damage default

- **Status/date/owner:** ACTIVE; 2026-07-14; Stock world
  extensions/repository maintainers.
- **Context:** Supplied Zaero `SP_func_door_rotating` deliberately comments out
  the legacy `dmg 2` default while leaving the sliding-door default intact.
  Its shared `door_blocked` callback applies crush damage only when `dmg > 0`
  and still reverses an ordinary non-crusher door after a zero-damage block.
  Six supplied rotating doors omit `dmg` and six explicitly author zero across
  zdef1, zdef3, zdm5, ztomb2, zwaste1, and zwaste3. Rerelease restores default
  damage 2 for a zero value, so an unscoped port would damage players on those
  authored routes.
- **Decision:** In `SP_func_door_rotating`, assign the Rerelease default 2 only
  when damage is zero and the level is not Zaero-classified. Leave missing and
  explicit zero as zero on Zaero maps and preserve every positive mapper value
  exactly. Do not alter `door_blocked`: its existing zero check suppresses
  damage while retaining crusher/wait/reversal behavior and its Rerelease
  debounce for positive damage. Do not change `SP_func_door`, whose source
  retains default 2. The gate is the D-018 mapper-contract scope.
- **Alternatives:** Remove the default globally, rejected because it regresses
  stock and mission-pack doors; keep default 2 globally, rejected because it
  changes 12 supplied Zaero doors; treat explicit zero differently from a
  missing key, rejected because the supplied spawn function observes both as
  zero; suppress the entire blocked callback at zero, rejected because reversal
  remains part of valid movement; copy the full vintage door implementation,
  rejected as unrelated baseline drift.
- **Behavioral impact:** Missing/zero rotating doors on Zaero maps can block a
  player or monster without dealing crush damage, then continue the normal
  reversal/state path. Authored values 1, 2, 6, and any other positive value
  remain damaging. Sliding doors and all non-Zaero rotating doors retain native
  Rerelease defaults and behavior.
- **Evidence:** Identity-locked supplied `g_func.c` SHA-256
  `aa7d05629c1213145e8fb74d14252d0b982b35cbc2dd4c75f1c27882f72adea6`;
  supplied `SP_func_door_rotating` and `door_blocked`; pinned Rerelease
  equivalents; direct entity-lump inventory of six missing and six explicit
  zero values among 32 rotating doors; D-018, MAP-009, and E-048.
- **Tests/migration:**
  `tests/compatibility/test_stock_world_extensions.py` locks all 12 affected
  map/entity-index/value records, the six/six split, missing/zero/positive
  evaluation, the scoped spawn default, shared damage-before-reversal order,
  sliding-door isolation, and native fallback. Live missing, explicit-zero,
  values 1/2/6, player/monster/non-client block, crusher, wait -1, reversal,
  team movement, mid-move JSON round trip, stock/Rogue maps, and D-018
  classifier fixtures remain. No saved field, callback, or migration is added.

## D-039 — Train and path-corner colliding mapper semantics

- **Status/date/owner:** ACTIVE; 2026-07-14; Train/path-corner slice and
  repository maintainers.
- **Context:** Supplied Zaero `train_next` reads a destination corner's
  speed/accel/decel, gives ordinary `misc_viper` segments the corner's raw
  origin, and passes corner bits 2/4 to a source-specific smooth transition.
  `path_corner_touch` turns a waiting monster toward its next goal and both
  monster/train teleport paths omit `EV_OTHER_TELEPORT`. `func_train` also
  exposes aspeed rotation through bits 8/16/32/64 as reverse/X/Y/Z. Rerelease
  already has per-corner speed but resets different state, emits teleport
  events, and uses bits 8/16/32 as Rogue MOVE_TEAMCHAIN/FIX_OFFSET/USE_ORIGIN.
  An unscoped copy would therefore corrupt stock/Rogue routes. The supplied
  maps contain 375 corners, 28 trains, seven Vipers, five nonzero zdef4 node
  speeds, 96 waits and four teleports; no shipped corner uses smooth bits and
  no shipped train uses a rotation bit, while four authored aspeed values are
  explicitly zero.
- **Decision:** On a Zaero-classified map, retain the supplied per-corner
  speed/accel/decel state without the Rogue self-speed/current-speed reset;
  carry regular-segment current speed into later smooth nodes; use a raw
  corner origin only for an ordinary `train_next` Viper segment; keep
  origin-minus-mins for initial placement, teleport and resume; omit both
  teleport events; and turn a waiting monster before its stand callback.
  Implement bits 2/4 through the exact source transition state and 10 Hz
  decision/final cadence, allowing Rerelease physics to integrate each
  velocity over four 40 Hz ticks. Interpret train bits 8/16/32/64 as
  reverse/X/Y/Z only in that scope, including disabling Rogue team-front and
  child-move behavior there. Retain every native/Rogue meaning elsewhere; the
  gate is the D-018 mapper-contract classifier.
- **Alternatives:** Use Rerelease per-corner movement unchanged, rejected
  because it misses Viper, wait, event, smooth and angular contracts; enable
  native USE_ORIGIN on all Zaero Vipers, rejected because the supplied code
  uses raw origin only in ordinary `train_next`; interpolate smooth decisions
  every 40 Hz tick, rejected because it changes the source's 10 Hz state
  cadence; enable Zaero bits globally, rejected because it breaks Rogue train
  ABI; omit unshipped flags, rejected because source-exposed community mapper
  behavior remains part of compatibility.
- **Behavioral impact:** The zdef4 Bulldog can follow all five authored speed
  changes using its raw route points; waiting monsters face their departure
  goal before pausing; the four teleport corners move without a visible
  teleport event; and community maps can use exact smooth or rotating train
  behavior. Stock, Xatrix, Rogue and community maps not classified as Zaero
  retain their native destination, team-chain, offset, event and flag rules.
- **Evidence:** Identity-locked supplied `g_func.c` SHA-256
  `aa7d05629c1213145e8fb74d14252d0b982b35cbc2dd4c75f1c27882f72adea6`
  and `g_misc.c` SHA-256
  `60378a0a35864453e5d6a2e1a18a43cc73c327e28dc3a45a1bec087425515fe1`;
  their `Move_Calc`, `Think_SmoothAccelMove`, `train_next`,
  `SP_func_train`, and `path_corner_touch`; pinned legacy/Rerelease
  equivalents; exact supplied entity-lump inventory; D-018, MAP-017,
  E-039, E-044 and E-045.
- **Tests/migration:**
  `tests/compatibility/test_stock_world_extensions.py` locks the source
  identities, complete map/count/index/value inventory, per-node fallback,
  destination scope, pre-wait order, event suppression, auto/custom smooth
  arithmetic, 10-to-40 Hz integration, final segment, colliding flag dispatch,
  native team/destination isolation, callback registration and existing JSON
  state fields. Live all shipped Viper/train/wait/teleport routes, rider/team
  contact, blocked motion, synthetic bit-2/4 transitions, nonzero aspeed on
  every axis/reverse combination, mid-segment JSON round trips, stock/Rogue
  fixtures and D-018 classifier cases remain. No new serialized field or save
  migration is required; the new think callback and existing mover fields are
  registered through the native save system.

## D-040 — Health pickup sound concurrency

- **Status/date/owner:** ACTIVE; 2026-07-14; Item foundation/repository
  maintainers.
- **Context:** Supplied Zaero moves health sound selection from the legacy
  touch path into `Pickup_Health`, assigning `ent->item->pickup_sound` from the
  effective count: 2 selects small, 10 normal, 25 large, and every other value
  mega. `gitem_t` records are shared global metadata, so one pickup temporarily
  changes the sound observed by every entity using that item record; concurrent
  or re-entrant pickups can hear the wrong sound. Rerelease already splits the
  four standard health classnames into immutable item records with the same
  sounds, but a Zaero community entity with an explicit custom `count` heals by
  that amount while native code still plays the classname sound. The 20
  supplied BSPs contain 447 health entities—111 small, 198 normal, 129 large,
  and nine mega—with no count override, so their ordinary presentation already
  matches.
- **Decision:** On the D-018 mapper-contract scope, after honoring an explicit
  Rerelease `noise_index`, derive the pickup sound locally from the effective
  count (`ent->count`, otherwise the immutable item quantity) using the exact
  2/10/25/default table. Pass that local path directly to `gi.soundindex` and
  never write `gitem_t::pickup_sound`. Keep the ordinary immutable item sound
  path unchanged on non-Zaero maps. This is a scoped FIX for shared-state
  safety that preserves all shipped sounds and the source-exposed custom-count
  mapper result; the classification gate is D-018's mapper scope.
- **Alternatives:** Retain the Zaero shared assignment, rejected because global
  metadata mutation is a concurrency/re-entrancy defect; rely exclusively on
  Rerelease's fixed per-classname sounds, rejected because it loses Zaero's
  explicit-count mapper behavior; apply count-derived sounds globally,
  rejected because native/custom Rerelease maps may intentionally combine a
  count override with their classname sound; override `noise_index`, rejected
  because that is a target-native explicit per-entity presentation choice;
  add a saved sound field, rejected because selection is synchronous and fully
  derived.
- **Behavioral impact:** All 447 supplied pickups sound exactly as authored.
  Synthetic/community Zaero health with count 2/10/25/default uses the same
  source table, simultaneous local/network pickups cannot contaminate each
  other, and explicit entity noise plus every stock/expansion map retains
  native behavior.
- **Evidence:** Identity-locked supplied `g_items.c` SHA-256
  `a02f4cfda2944ad36cf51eb928c82f13f4317d4198389ef63fac361795b0bf46`;
  supplied `Pickup_Health`/`Touch_Item`; pinned legacy and Rerelease
  equivalents; direct entity-lump health inventory/count-override audit;
  PLY-020, E-049, Q-025, and D-018.
- **Tests/migration:**
  `tests/compatibility/test_zaero_health_pickup.py` locks source identity, all
  447 placements and zero shipped overrides, exact 2/10/25/default mapping,
  effective-count fallback, immutable metadata, interleaved selection,
  explicit-noise precedence, Zaero gating, and native fallback. Live standard
  and synthetic custom-count pickups, two clients/split-screen picking
  different sizes in the same frame, re-entrant target callbacks, explicit
  noise, stock/Rogue maps, and D-018 classifier fixtures remain. No callback,
  field, save migration, asset, or package change is introduced.

## D-041 — Zaero monster damage reaction and self-target safety

- **Status/date/owner:** ACTIVE; 2026-07-14; AI reaction slice/repository
  maintainers.
- **Context:** Zaero's `M_ReactToDamage` admits the exact non-`SVF_MONSTER`
  `monster_autocannon` classname, retains `AI_SOUND_TARGET` when a player
  becomes the enemy, prevents direct anger between matching non-empty `mteam`
  values, and excludes Tank, Supertank, Makron and Jorg from the ordinary
  same-movement-class reaction. Its final buddy branch can assign
  `attacker->enemy == targ` and make the reacting monster target itself.
  Rerelease already rejects that self-selection and adds Tesla, target-anger,
  medic cleanup, reaction cooldown and `AI_IGNORE_SHOTS` behavior that must not
  be discarded.
- **Decision:** Extend the native Rerelease function at its existing decision
  points. Admit the exact Autocannon; positively scope Zaero semantics through
  a shipped Zaero map, that exact classname, or either mapper-authored `mteam`;
  retain `AI_SOUND_TARGET` only in that scope; and apply matching-team plus
  four-class spray exclusions before direct retaliation. Preserve native
  Tesla, target-anger, medic, cooldown, ignore-shot, ducked, good-guy and
  enemy-history behavior. Keep the native `attacker->enemy != targ` guard as a
  scoped FIX for Q-046.
- **Alternatives:** Replace the whole native function with the 1998 source,
  rejected because it removes Rerelease/expansion lifecycle behavior; apply
  every Zaero rule globally, rejected because it changes native maps; reproduce
  self-targeting, rejected because it is pathological AI state with no valid
  combat intent; ignore Autocannon and `mteam`, rejected because both are
  gameplay-observable Zaero contracts.
- **Behavioral impact:** Zaero monsters can retaliate against incidental
  Autocannon fire, paired/team creatures do not directly turn on each other,
  the four spray-heavy bosses retain legacy exclusions, and a player reaction
  does not clear the legacy sound-target state. Buddy indirection can select a
  valid third party but never the reacting monster. Ordinary Rerelease maps
  retain native reactions.
- **Evidence:** Identity-locked supplied `g_combat.c` SHA-256
  `b600b4371abe59a0e7d3ac2fbb6e3c19cd17ae24100b3e3d9f34882d1d3180cb`;
  its `M_ReactToDamage`; pinned legacy and Rerelease equivalents; Q-046,
  AI-014, E-014, E-017 and E-018.
- **Tests/migration:**
  `tests/compatibility/test_zaero_ai_reaction.py` locks source identity, exact
  scope/admission/class tables, sound retention, matching-team/buddy behavior,
  self-target rejection, native Tesla/medic/target-anger/cooldown/ignore-shot
  preservation, existing `mteam` and reaction-time saves, and executable
  branch goldens. Debug builds with zero warnings. Live player, monster,
  Autocannon, same/different/missing `mteam`, sound target, good-guy, medic,
  Tesla, ducked, death, free/reuse and JSON-save cases remain. No new serialized
  field or save migration is introduced.

## D-042 — Hover fly-strafe and expired-state reset

- **Status/date/owner:** ACTIVE; 2026-07-14; Hover strafe slice/repository
  maintainers.
- **Context:** The supplied Hover adds a projectile-dodge callback that rejects
  75 percent of calls during its straight attack, chooses a roll from
  `crandom() * 180`, searches one initial direction plus 36 ten-degree retries
  for 96 units of clearance, and arms a one-second state. `ai_run` then faces
  the enemy, applies a 1.5-times 3D impulse through `SV_FlyMove`, and exits on
  a clip. Its timeout branch writes
  `attack_state == AS_STRAIGHT` instead of assigning, leaving a stale state.
  Rerelease already uses `AS_SLIDING` for Hover/Daedalus circle attacks and an
  alternate-flight model, while D-033 routes Zaero client projectiles through
  the source firing-time dodge callback.
- **Decision:** Assign the callback only to the exact `monster_hover` classname
  on a classified Zaero map. Use a dedicated attack-state value appended after
  all native values plus named, typed, JSON-saved roll/deadline fields; do not
  alias native `AS_SLIDING`, `AI_DODGING`, or Daedalus behavior. Preserve the
  37-trace search, strict `< level.time` one-second boundary, 1.5-times source
  scaling, `MASK_MONSTERSOLID` selection, and `MASK_SHOT` direct slide through
  the supported Rerelease `SV_FlyMove`. Relink after the direct think-time move
  so authoritative Rerelease collision queries see it. Treat a velocity change
  as the native equivalent of legacy clip flags. On expiry, invalid lifecycle,
  or collision, explicitly assign `AS_STRAIGHT` and clear both fields: the
  scoped Q-013 FIX.
- **Alternatives:** Reuse `AS_SLIDING`, rejected because it aliases native
  horizontal circle attacks and `AI_DODGING`; replace Rerelease Hover movement
  or copy legacy server physics, rejected because it discards expansion and
  2023 substrate behavior; reproduce the comparison typo, rejected because it
  has no intended movement and leaves invalid AI state; enable the callback on
  every Hover/Daedalus, rejected because Zaero changed only its exact stock
  Hover surface.
- **Behavioral impact:** All 22 supplied Hovers in `zdef1`, `ztomb1`, `ztomb3`,
  and `zwaste1` can respond to Zaero's Rocket/BFG/Flare firing trace with the
  authored radial dodge and deterministic timeout recovery. Ordinary
  Rerelease Hovers and Daedalus retain native circle attacks, proximity dodge
  policy, and alternate flight. The immediate relink is a target-native safety
  adaptation rather than the stale-link side effect of calling legacy physics
  from an AI think.
- **Evidence:** Identity-locked supplied `g_ai.c` SHA-256
  `9900846fdd8349b0fd75535705de98d2c1c270a0cbc4bc7a357d175dcbdd62ef`
  and `m_hover.c` SHA-256
  `d2b8dc0ad586c69d886b38ca404c65b2e211302ce6cc3b5cabf8d9c4e18d965a`;
  their `ai_fly_strafe`, `ai_run`, `hover_dodge`, and `SP_monster_hover`;
  pinned legacy/Rerelease equivalents; generated 22-placement BSP audit;
  AI-012, E-050, Q-013, D-018 and D-033.
- **Tests/migration:**
  `tests/compatibility/test_zaero_hover_strafe.py` locks both source identities,
  exact scope and callback probability, all 37 trace directions, typed strict
  boundary at target tick 40/41, movement scaling/masks, collision and expiry
  resets, AI-hook order, native hooks, and JSON registration. Debug builds
  with zero warnings. Older saves default the appended enum/fields to their
  zero state; native enum values are unchanged. Live seeded clear/blocked
  direction selection, repeated projectile cadence, exact 40 Hz boundary,
  wall/actor clips, death/free/reuse, mid-dodge save/load, all four affected
  maps, and stock Hover/Daedalus fixtures remain. No asset or package migration
  is introduced.

## D-043 — Stock-monster precache extraction and sound-index strategy

- **Status/date/owner:** ACTIVE; 2026-07-14; Handler/resource slice/repository
  maintainers.
- **Context:** The supplied Zaero tree extracts 22 `SP_*_precache` helpers from
  19 legacy stock-monster files. The generated call graph proves that 21 are
  consumed only inside their owning file; only
  `SP_monster_infantry_precache` has a cross-file consumer, in Handler beside
  the custom Hound precache. The pinned Rerelease baseline already exposes
  `InfantryPrecache` to both stock Infantry and `SP_turret_driver`, so no new
  generic stock API is needed. Legacy Zaero also carries an optional
  `CACHE_SOUND` interceptor around the 256-entry sound limit, but neither
  supplied Release nor Debug project configuration defines it. The dormant
  path globally replaces `gi.soundindex`, lowercases the caller's buffer in
  place, allocates a level list and copied names, and rejects later entries
  with index zero. Rerelease provides 2,048 sound indexes and keeps 256 only as
  an old-protocol compatibility value.
- **Decision:** Reuse the existing native `InfantryPrecache` from Handler's
  precache and conversion paths, and retain the Zaero-owned Hound precache.
  Keep every other ordinary stock monster on its current Rerelease spawn-local
  resource path; do not copy 18 files or add 21 unused public helpers merely
  to mirror source organization. Use Rerelease `cached_soundindex` assignments
  for Infantry, Handler, and Hound. Do not port `CACHE_SOUND`, global import
  interception, caller-buffer mutation, the 256-entry rejection behavior, or
  eager all-item precaching. This decision classifies only the helper surfaces
  and index strategy: EMP, flash, Chick audio, Hover, cadence, and any other
  observable deltas in the same stock files remain independently routed.
- **Alternatives:** Recreate all 22 legacy helpers, rejected because 21 have no
  cross-file consumer and would increase native drift without a behavior;
  clone legacy Infantry or invoke its full spawn during conversion, rejected
  because Rerelease already provides the helper and Handler must preserve its
  entity/count/health identity; enable the legacy sound interceptor, rejected
  because it was absent from supplied builds, deliberately loses resources at
  256, and violates const-safe/native API ownership; precache every item and
  stock monster eagerly, rejected because it changes resource pressure and
  expansion behavior without a mapper dependency.
- **Behavioral impact:** Handler precaches both halves before its combined
  spawn and again uses the native Infantry resource set when conversion occurs.
  Direct Infantry, native turret drivers, and all other stock monsters retain
  current Rerelease resource/expansion behavior. Maps no longer inherit the
  dormant legacy policy of silently returning sound index zero after 255
  recorded names. This is static resource-path closure only; it does not prove
  that every authored sound is referenced or audible on every map.
- **Evidence:** The normalized
  [stock-monster precache audit](../audits/stock-precaches.md) locks all 22
  helper definitions, 19 owner-file identities, the sole
  `z_handler.c:SP_monster_handler_precache` external call, native and port call
  graphs, project defines, unsafe interceptor operations, and 256/2,048
  constants. It cross-checks the pinned legacy, Zaero, Rerelease, and current
  port bytes. AI-003, AI-015, E-016, Q-030 and Q-040 route through this record.
- **Tests/migration:**
  `tests/audit/test_stock_precache_audit.py` exercises deterministic discovery
  and fail-closed call-graph drift. `tests/compatibility/test_zaero_stock_precaches.py`
  locks source/baseline/current identities, helper counts, the sole external
  dependency, native/port consumers, cached-index strategy, disabled project
  macro, and limit facts. The existing Handler contracts and private legacy v1
  `zbase1` sample remain historical supporting evidence only; rerun it under
  D-046 before treating it as current. Add per-map
  referenced-resource enumeration, sound-index counts, audible combat/pain/
  ambient playback, Handler pre/during/post-conversion, expansion isolation,
  and save/reload tests before closure. No serialized field, save migration,
  asset copy, or package-format change is introduced.

## D-044 — Global SV_FlyMove duplicate-plane delta

- **Status/date/owner:** ACTIVE; 2026-07-15; Physics core/repository
  maintainers.
- **Context:** Legacy Quake II appends collision planes in `SV_FlyMove` but
  omits an exact duplicate from the candidate-validity comparisons. Zaero
  removes only that `!VectorCompare(planes[i], planes[j])` clause, globally.
  It therefore affects ordinary Step physics, custom FallFloat, and direct
  Hover strafe calls rather than a dedicated Zaero entity. The pinned
  Rerelease no longer uses that legacy resolver: `SV_FlyMove` delegates to
  `PM_StepSlideMove_Generic`, which rejects new near-duplicate planes above a
  0.99 normal dot product, nudges repeated contacts, and overclips at 1.01.
  The same helper also owns ordinary player step-slide and special/water-jump
  movement, while the server wrapper is used by native Step, Rogue NewToss,
  Zaero FallFloat, and Zaero Hover callers.
- **Decision:** Treat the one-line Zaero removal as global source-age drift,
  not a required mapper or monster contract. Keep the current Rerelease
  `SV_FlyMove` function exact and its shared helper byte-identical to the
  pinned baseline. FallFloat and Hover use that existing server surface; do
  not fork player movement, add a Zaero map branch, or reproduce an exact-
  duplicate float-residual dead-stop.
- **Alternatives:** Import the condition globally, rejected because the target
  algorithm no longer contains that condition and a shared-helper rewrite
  would alter native players, water jumps, and expansion entities; add a
  Zaero-only copy of legacy server physics, rejected because it would discard
  Rerelease collision fixes and create divergent touch/ground semantics; treat
  every numeric overclip difference as a parity failure, rejected because the
  Rerelease 1.01 solver is target substrate behavior and the Zaero change
  itself differs from legacy only under the exact-repeat float residual.
- **Behavioral impact:** Ordinary Zaero maps, custom FallFloat objects, and
  Hover dodges receive the same Rerelease collision stability as stock and
  expansion entities. In the deterministic exact-repeat case, the target
  continues with its native overclipped slide instead of reproducing Zaero's
  dead-stop. No classname, map key, protocol, timing, save, or asset surface
  changes.
- **Evidence:** The normalized identity-locked
  [SV_FlyMove audit](../audits/flymove.md) proves the exact one-condition
  legacy/Zaero delta, current/baseline function and helper identity, all legacy,
  Zaero, baseline, and target call graphs, and seven float32 control/wall/
  corner/stair/wedge/projectile/monster plane-resolution goldens. Only the
  exact repeated non-axial case distinguishes legacy from Zaero: legacy skips
  one duplicate comparison, Zaero rejects both candidates on a negative
  `-0.00005340576171875` residual and stops, and Rerelease skips the repeated
  plane through its native threshold.
- **Tests/migration:**
  `tests/audit/test_flymove_audit.py` fails on any additional source delta or
  call-graph/helper drift. `tests/compatibility/test_zaero_flymove.py`
  reproduces every float32 golden, locks source/current identities and the
  exact residual outcome, and proves the helper remains shared and unbranched.
  Live always-windowed synthetic corner/wedge/stair, repeated-plane projectile,
  Step/FallFloat/Hover, ordinary player, water-jump, and Rogue NewToss fixtures
  remain before Q-048 verification. No save or package migration is required.

## D-045 — zdmflags and deathmatch item injection

- **Status/date/owner:** ACTIVE; 2026-07-15; Multiplayer/item/repository
  maintainers.
- **Context:** Zaero registers `zdmflags` as a server-info cvar with default 0.
  Bit 1 disables the Flare Gun's compensation damage to a deathmatch client
  with `gl_polyblend 0`. Bit 2 also disables behavior despite its supplied
  positive-sounding `ZDM_ZAERO_ITEMS` name: when clear, deathmatch maps with
  none of eight exact Zaero item classnames enter the injection pass. The pass
  scans live post-inhibition entities, then tries the exact Sonic, Sniper,
  Flare, IRED, A2K, Flares, EMP Nuke, and Plasma Shield order. Each item gets
  four successive deathmatch-start ordinals; the old finder wraps at the end
  of the entity list. Each attempt starts 16 units above that start, chooses a
  random initial yaw, sweeps 360 degrees in 15-degree increments, and accepts
  the first unobstructed 128-unit `MASK_SHOT` bounding-box trace. The new item
  begins in `MOVETYPE_BOUNCE`, then follows ordinary item drop/pickup/respawn
  lifecycle. “All-or-none” describes only the initial existing-classname
  precondition: a later geometry failure does not roll back earlier successes,
  so the console count may be 0–8. All 20 supplied BSPs contain at least one
  member and therefore suppress injection; six omit one or more members but
  are still ineligible. Stock/community fixtures are required to exercise the
  positive path.
- **Decision:** Keep the public cvar name, default, server-info flag, and numeric
  values exactly compatible. Internally name the bits
  `ZAERO_DMFLAG_DISABLE_FLARE_POLYBLEND_DAMAGE` and
  `ZAERO_DMFLAG_DISABLE_ITEM_INJECTION`; do not retain the inverted legacy
  symbol in executable code. Implement injection in a Zaero-owned module with
  one hook after `G_FindTeams` and before CTF setup. Reproduce the eight-item
  order, live-member precondition, ordinal wrap, four attempts, 16/128-unit
  geometry, 15-degree sweep, interim Bounce state, partial-success behavior,
  and console count. Use the native Rerelease RNG and route the entity through
  `ED_CallSpawn`/`SpawnItem`, retaining `droptofloor`, `Touch_Item`, item
  respawn/save callbacks, IR presentation, random-item behavior, and pickup
  rejection by native modes. Check `inuse` immediately after that native path
  so instagib or another rejecting mode cannot leave a use-after-free. This is
  Zaero content activation on every eligible map and must not read or set
  D-018's mapper-contract classification.
- **Alternatives:** Gate injection on `level.is_zaero`, rejected because the
  feature exists specifically to add Zaero content to non-Zaero maps; rename or
  invert the external cvar bit, rejected because server configs rely on values
  0–3; require the complete set before suppressing injection, rejected because
  one existing member historically aborts the pass; make eight placements
  transactional or deterministic/fair, rejected because it changes visible
  failure/count and spawn-distribution quirks; bypass `ED_CallSpawn`, rejected
  because it would evade native Rerelease item modes, precaching, callbacks,
  and save lifecycle.
- **Behavioral impact:** With bit 2 clear, an eligible deathmatch map can gain
  up to one live entity for each member in the historical order; with bit 2
  set, in non-deathmatch, with no deathmatch starts, or when any member already
  exists, it gains none. Bit 1 remains independent. Stock/community maps may
  use Zaero items while their movers and stock classnames retain native
  Rerelease semantics. Native instagib/random-item/expansion settings continue
  through their existing item-spawn paths rather than being silently bypassed.
- **Evidence:** The normalized
  [deathmatch-injection audit](../audits/dm-injection.md) identity-records
  supplied `z_spawn.c`, `g_local.h`, and `g_save.c`; locks the exact bits,
  cvar, item order, geometry, attempts, hook order, native lifecycle, and port
  source; and joins them to the 20-map/230-start BSP inventory. It proves all
  supplied maps contain at least one member, while `zbase2`, `zboss`, `zdm5`,
  `ztomb3`, `ztomb4`, and `zwaste1` omit at least one and still suppress the
  pass. SYS-012, Q-005, Q-028, E-001–E-008, and all deathmatch map rows route
  through this record. Five ignored/private reports validate against the
  runtime-smoke schema and use Debug DLL SHA-256
  `2a92ffde550bb088ea984f3a1751db84f2b1b9bd02191849706624529cef102f`:
  `q2dm1` values 0/1 report eight additions (report SHA-256
  `832f29d57edb88aeb0f8859d948b8320b761cb133a1628167a8fe81a2137d91a` /
  `1c9243e2d9b71dbbffb6500fb00a034ad3bc9969fd9994e62042dd2b9267adc8`),
  values 2/3 take the no-count disable return
  (`c9093dfa7b68a623a518667db62d71a8d3a599f36a443dbf670dc70c83b74e48` /
  `28e3004c79c5551c5739df98c16527659f9be14cdd5010a3d2e9164c7dc9de86`),
  and authored `zdm1` suppresses the pass
  (`9b0def756ff83d221bf9e0613e48d008d1ede2c896a015dcbcfa6f494c9f2be7`).
  All five observed an 868×517 captioned/non-popup native window, no
  non-windowed visible window, successful spawn/client/shutdown markers, no
  stderr/fatal/dump evidence, and no residual game process.
  Three newer structured-probe reports use Debug DLL SHA-256
  `8e9d7d5ce3dd389e2a38651335e5c428b857e956fe715f4e3de4b54392eceee2`.
  Eligible `q2dm1` value 0 records all eight exact classnames in historical
  set order, successive start ordinals 1–8, first attempts, 128-unit XY and
  16-unit Z initial offsets, generation-checked live entities, final origins,
  and native Toss/trigger/`Touch_Item`/IR state (report SHA-256
  `8fd9ea132fa21a5ee77d451f97f83145a03ced0c45e20fb129c2c7b5b684828a`).
  The same probe records exactly zero for stock `q2dm1` with bit 2 set
  (`6b592653c2abebaf500e1ba69d8ae17950858b2f7f4392f1d74bc08fa970246b`)
  and authored `zdm1` with value 0
  (`04d8a8461550cf3dca14e2fd59423cb49a94da7e56a75d5913fd48d1890f5a10`).
  The probe is a private `_DEBUG`-only read surface covered by D-015; its two
  signatures are absent from the produced Release DLL.
  The private deterministic [fixture generator](../../tools/make_dm_runtime_fixture.py)
  selectively reads a legitimate local `baseq2/pak0.pak`, preserves every
  `q2dm1` geometry byte, and replaces only the ignored derived BSP's entity
  lump with one open and four starts inside a real solid collision brush. The
  source member is 2,874,472 bytes at SHA-256
  `fdec16c999e6275ffc461e85f273db259804383fd54ffdf3e2d5ec9a89e9818e`;
  the generated fixture is the same size at SHA-256
  `33d2a82057c252c12fdc82f7868d36cff9e77f2ce7c73e8f06f986caab59bc6d`.
  A historical schema-v1 single-stage value-0 run records exactly four live native
  items at set indices 0/2/4/6, wrapped start ordinals 1/6/11/16, and attempt 1
  for each (report SHA-256
  `391a27d07c98308e838d3d5a309730827f504610bc79cad4048a5764f97b0f0d`).
  It observed an 868×517 captioned/non-popup native window from startup, no
  non-windowed visible window, complete spawn/client/shutdown markers, and no
  residual process. The path-scoped installer overlay refuses collisions and
  reparse points; the immediate normal reinstall removed every fixture member
  and reproduced the ordinary 947-entry PAK at SHA-256
  `b44e124c8d744c4db1cd1f335c7493231b8db78601014bfdfd40446efff76847`.
  The BSP, fixture manifest, PAK, and report remain ignored/private-local-only.
  With `--include-existing-member-controls`, the same generator emits eight
  additional derived maps containing one valid start and exactly one member in
  historical set order. The suite manifest has SHA-256
  `b579511be54a94b4eaf94b0ed96e6f6adf235a5efb0695bb6c87db9aba76aa88`;
  its temporary nine-map managed PAK had 956 entries and SHA-256
  `9b2c303f6e61685d9ab8f8a10901f609445d3187eac1b49db4cad79e013b30d8`.
  Each value-0 Debug run records no addition line and exactly zero structured
  records/live items: Sonic `ac2056c03f566ef472041ed4cb1396fbe1f4638b2b240b27dcae2d746b4915e1`,
  Sniper `70a2167533a108f2427166628a4a58e14ed35af511d5bb91dadf6da779ffb131`,
  Flare Gun `4853f0f8bc8d9e78a1ab24d253383d020df1491b4e74a6b13b1c7c78b2c45f3d`,
  IRED `223923f1b6070a5ade465d90478785bca36e37bd6cd172c1e952f99d7c727501`,
  A2K `d3324b0e9c7074c94d7e49929d7db6373979b825c540a199a0822dfccbb264df`,
  Flares `843320a1b657ada6a4b7483b4d1177bb3e1b64a1f65fe4a1632e6bfa2f062240`,
  EMP Nuke `097e8e40cd9545784543455d4c796d1c107a56dce206173ee662ff85e48f247a`,
  and Plasma Shield `6417664d063289c2d5b1f02718241f9151df5fb696a14a471d39d50a2b37085e`.
  Every listed report uses the legacy schema-v1 one-stage protocol. Their
  captioned/non-popup windows, lifecycle markers, and no-residual-process facts
  remain item-injection evidence, but they are not current launch-safety proof
  and must be rerun as v2 before advancing a runtime claim. The immediate
  normal reinstall again reproduced the ordinary 947-entry PAK hash above with
  no fixture member.
- **Tests/migration:** `tests/audit/test_dm_injection_audit.py` fails closed on
  item-order, bit, hook, lifecycle, or supplied-inventory drift.
  `tests/compatibility/test_zaero_dm_injection.py` covers values 0–3,
  independent flare/injection bits, every single-member precondition, no-DM/
  no-start cases, successive/wrapping start order, seven-item partial success,
  native callback/save surfaces, and D-018 isolation. Debug compilation passes
  with zero warnings. Historical legacy-v1 reports record the open-stock exact
  identity/position/native-drop state, values 0–3, bit-2 zero result, one
  full-set ineligibility control, deterministic real-brush partial success, and
  all eight one-member ineligibility cases. `tools/runtime-scenarios-dm.json`
  schedules the five ordinary reruns and
  `tools/runtime-scenarios-dm-fixtures.json` schedules all nine overlay reruns.
  Rerun all of them through D-046 before they count as current runtime evidence.
  Before verification, add pickup/30-second respawn/drop,
  pre/post-droptofloor and JSON save round trips, 2/4/8 clients, dedicated
  server, server-info/config persistence, reconnect/map rotation, and
  instagib/random-items/CTF/native-mover isolation. No save-schema, cvar, asset,
  map, or package migration is introduced.

## D-046 — two-stage visible window-before-mod/map runtime launch

- **Status/date/owner:** ACTIVE; 2026-07-15; Runtime tooling maintainers.
- **Context:** Development, debugging, and all manual or automated client
  validation must never start fullscreen. The original smoke wrapper did pass
  `-window` and `v_windowmode 0`, but also supplied `+set game zaereo` and
  `+map` before it could inspect the created native window. Checking only the
  process main window also could not prove that a secondary popup was absent.
- **Decision:** Start a visible bootstrap with the authoritative pre-video
  `-window`, `v_windowmode 0`, and explicit dimensions, but no mod/map selector.
  After three seconds of process quiescence, enumerate every visible top-level
  window belonging to every exact newly observed Rerelease executable PID. Any
  popup/non-windowed window, missing verified window, or failed delivery
  immediately terminates the exact PID and creates a failed private report.
  Only after all observed windows are captioned/non-popup may the wrapper send
  its mode, `zdmflags`, `game zaereo`, and map command. Delivery first obtains
  foreground only for that verified native handle, attaching both the helper's
  calling thread and target queue to the foreground input queue (or, where the
  host exposes no foreground queue, to each other) and retrying through the
  native task-switch activation path before using genuine system keyboard input;
  it
  never posts characters to an arbitrary process. On every
  timeout or safety abort, it re-enumerates exact selected-executable PIDs
  newer than the post-quiescence boundary, terminates them, and records any
  unkillable residual IDs in the report. The private focus diagnostic records
  the last guarded activation stage, foreground PID when available, and whether
  it was the exact target. `command_delivery` distinguishes an
  unattempted command, unavailable target/foreground, individual input-send
  failures, accepted `input-submitted` input, and `engine-confirmed` delivery
  from the session marker rather than inferring delivery from the eventual map
  markers. `-ManualCommandDelivery` is the interactive fallback when a KEX
  client rejects injected input: after the exact window is verified, it prints
  the nonce-bearing command for the developer to enter in that window and does
  not mark delivery until the engine emits the matching marker. A passing
  `zaereo.runtime-smoke/v2` report must identify this protocol and record that
  the command was injected after window verification with zero residual IDs.
  Shared VS Code entries invoke this wrapper; no direct-game launch entry is
  allowed.
- **Alternatives:** A direct full command line, an after-the-fact cvar switch,
  or a single `MainWindowHandle` check is rejected because each can select
  content or miss a visible fullscreen/popup state before the required safety
  result. A hidden/headless client run is rejected because it cannot prove a
  native client window. Dedicated/headless server tests remain a separate lane
  and are never evidence for client-window or presentation gates.
- **Behavioral impact:** The visible bootstrap may briefly present the base
  client before the verified console command selects the managed mod/map. This
  is a validation-only launch protocol and does not alter game-DLL behavior,
  mapper semantics, save data, cvars, or package contents. Console injection
  must receive a private live test on each supported KEX distribution before it
  can advance a gameplay row.
- **Evidence:** [The wrapper](../../tools/run_game.ps1), [v2 schema](../provenance/schemas/runtime-smoke.schema.json), [private matrix](../../tools/run_runtime_matrix.ps1), [shared VS Code entry](../../.vscode/launch.json), and [runtime contracts](../../tests/runtime/) lock window ordering, exact caller/target-queue-attached/task-switch-retried foreground-gated `SendInput` delivery status, residual-PID capture, and fail-closed JSON/JUnit aggregation. The matrix independently binds a claimed pass to its scenario's map/mode/flags and verifies the complete v2 launch/marker/window/exit/output/residual evidence; its serial manual fallback records use but requires the same engine-confirmed marker. All retained v1 reports remain historical registry/resource or item-injection observations; they must be rerun in v2 before satisfying D-015, SYS-021, a release gate, or any statement of current launch safety.
- **Tests/migration:** Parser, schema, synthetic `-WhatIf`, and editor-wrapper
  contracts must pass. Private live reruns must cover Debug and Release,
  `zbase1`, `zdef1`, `zboss`, `zdm6`, D-045 values 0–3 and its fixtures; each
  result must contain the v2 protocol/injection marker, no popup/non-windowed
  observation, no safety abort, no timeout, no fatal output, and no residual
  process. Preserve v1 reports only as dated pre-decision evidence; do not
  relabel or regenerate them as v2.

## D-047 — legacy PAK layer to runtime ownership semantics

- **Status/date/owner:** INTERIM; 2026-07-15; Content/provenance/release
  maintainers.
- **Context:** The legitimate legacy installation has ordered source layers
  `pak0 < pak1 < pak2`, with `pak1/default.cfg` and `pak2/maps.lst` as the two
  effective-path overrides, plus nine required loose files. The planned
  Rerelease layout instead has a project-owned `pak0.pak` and a local,
  importer-owned `pak1.pak`. Treating either output-layer count or a generic
  PAK build as proof of source precedence would lose provenance or silently
  choose the wrong byte at a project/import collision.
- **Decision:** Preserve the complete source-layer directory/hash inventory and
  resolve the source PAKs in original order before producing any local runtime
  view. It is permissible to collapse that resolved legacy view into an
  importer-owned effective `pak1.pak`—rather than redistributing three source
  PAKs—provided the import manifest retains every winning source container/path
  and all overridden candidates. Project-owned `pak0` must never silently
  shadow or be shadowed by imported content: reject every collision unless a
  reviewed, path-specific rule records the expected winner and reason. Retain
  the nine verified loose files at their runtime paths until target precedence
  tests authorize an alternative. Package, install, repair, update, rollback,
  and uninstall ownership manifests must distinguish project, imported, and
  generated bytes.
- **Alternatives:** Copy the three source PAKs unchanged, rejected while media
  rights are open and because it obscures generated/runtime ownership; flatten
  files without origin, rejected because it cannot prove the two overrides or
  support rights review; let project data overwrite arbitrary import paths,
  rejected because mapper/media behavior could drift silently; pack loose media
  now, rejected before Rerelease lookup behavior is tested.
- **Behavioral impact:** Rerelease sees the same effective legacy runtime paths
  and bytes after importer completion, subject only to approved safe
  configuration adaptation. The physical output has two owned layers for
  install/update purposes, not a claim that legacy source-layer history ceased
  to matter. No player-facing asset is redistributed by this decision.
- **Evidence:** `docs/audits/assets.json` identifies the three source layers,
  their hashes, override paths, and loose files. The importer manifest retains
  source-container/origin and effective-byte records. `install_dev.ps1` now
  writes project/import/generated ownership groups in its managed-file record;
  `package_windows.ps1` emits `RUNTIME-OWNERSHIP.json` with layer and loose-file
  hashes, and both run `validate_runtime.py --stage` to reject package/member/
  loose and file/directory-prefix collisions while comparing every imported
  staged byte to the import manifest. The future path-level asset policy and
  full ownership lifecycle manifests are still required before a release claim.
- **Tests/migration:** Contract tests lock the separated project `pak0`, import
  `pak1`, private-fixture `pak2`, collision check, package ownership record, and
  synthetic layered-stage byte/exact/path-prefix collision cases. The checked-in
  asset audit test locks both legacy `default.cfg` and `maps.lst` source winners and hashes before
  their distinct Rerelease handling. Exercise the engine's loose-over-PAK lookup,
  reject cross-layer reference ambiguity, and prove package/install/repair/
  update/rollback removes only its owned bytes. Until those pass, SYS-016 remains
  IN PROGRESS and no archive or local stage may claim precedence closure.

## D-048 — fail-closed release-readiness evidence

- **Status/date/owner:** ACTIVE; 2026-07-15; Release/provenance maintainers.
- **Context:** The distribution policy already makes every public mode
  ineligible, while the former release surface had no machine-readable record
  tying that decision to the current source, ledgers, and requested mode. A
  package or a prose acknowledgement cannot safely stand in for that record.
- **Decision:** [release_readiness.py](../../tools/release_readiness.py) is the
  only current readiness generator. It validates the policy, selected mode,
  channel, and non-promotable profile; fingerprints `VERSION`, provenance,
  audits, compatibility ledgers, and runtime scenario source; records Git
  source state; and writes an atomic schema-valid record only beneath ignored
  `dist/`. It has no publication, tag, upload, dirty-tree bypass, or readiness
  override. It records the policy's non-waivable rules and refuses a
  hand-promoted ready record. While the active policy blocks public channels and
  exact-candidate evidence is missing, all output remains `ready: false`.
  `publish_github_release.ps1` and remote workflows remain deliberately
  disabled; later integration must consume a validated record, never relax it.
- **Alternatives:** A `-Force`/`-AllowDirty` flag, an editable JSON checklist,
  or allowing a blocked result to return publication eligibility is rejected:
  each would permit a local assertion to defeat rights, provenance, or
  compatibility gates.
- **Behavioral impact:** None on the game, maps, assets, saves, or developer
  installation. This is private generated engineering evidence only and does
  not authorize a package, public tag, release asset, CI upload, or remote read.
- **Evidence:** [Schema](../provenance/schemas/release-readiness.schema.json),
  [generator](../../tools/release_readiness.py), [distribution policy](../provenance/distribution-policy.json),
  and [release contract tests](../../tests/release/test_release_readiness.py).
- **Tests/migration:** Validate an ordinary blocked `local-full-private`
  record, reject output outside `dist/`, reject a mode/profile mismatch, retain
  a false record under `--require-ready` while returning failure, and reject a
  manually changed ready record. Add exact release-manifest, package/SBOM,
  build/test, save/editor, map/live, and rights/channel collectors before any
  future record can be eligible.

## Adding or superseding a decision

A new record must state status, date, owner, context, decision, alternatives,
behavioral impact, evidence, tests, and migration/release consequences. Do not
erase old reasoning. Mark it SUPERSEDED, link the replacement, and update every
affected feature/entity/map/quirk row.

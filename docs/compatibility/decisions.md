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
| D-002 | Rerelease baseline | OPEN | Pin official upstream identity; archive hashes if no commit exists | Before Phase 1 closes |
| D-003 | Source/media distribution | INTERIM | Gate code/media and distribution channel independently; no public gameplay-repo push/tag while code is open; tools-only needs a history-clean distribution root; local-full is always private | When rights evidence is obtained |
| D-004 | Git binary strategy | INTERIM | No legacy assets; LFS only for cleared canonical source binaries; never generated packages | Before first binary source commit |
| D-005 | Compatibility bug policy | ACTIVE | Parity first; tested FIX for safety/undefined behavior | Per quirk |
| D-006 | Rerelease co-op defaults | OPEN | Decide from all-map tests | Before Phase 5 |
| D-007 | Flare blend compensation | INTERIM | Preserve historical behavior and zdmflags opt-out | Phase 4 and before 1.0 |
| D-008 | Visor command/chat restrictions | INTERIM | Preserve gameplay control lock; chat suppression unresolved | Phase 4 |
| D-009 | Loose sprites/videos | INTERIM | Keep nine files loose until target behavior is verified | Phase 2 packaging proof |
| D-010 | Music values 1–11 | OPEN | Use legally available Rerelease mapping with logged silent fallback | Phase 2/7 |
| D-011 | ztomb1 absent tomb1 target | OPEN | Preserve data and test reachability before any patch | Phase 6 |
| D-012 | New protocol/engine fork | ACTIVE | Avoid for 1.0 unless required parity is impossible through supported APIs | Any engine-fork proposal |
| D-013 | Bot/navigation scope | INTERIM | Safe metadata/fallback for 1.0; advanced tactics post-parity | Phase 8 |
| D-014 | Legacy demos/saves | ACTIVE | Evidence only; no playback/load promise | Only with a separate compatibility project |
| D-015 | Source debug/test tools | ACTIVE | Developer-only, disabled and excluded from releases | Post-parity |
| D-016 | Stable publication | ACTIVE | CI-equivalent package, clean tree, checksums, human-approved draft/manual release | Each stable release |
| D-017 | Remastered content | ACTIVE | Optional overlay after 1.0; never replaces original parity baseline | Post-1.0 enhancement |
| D-018 | Zaero semantics on stock classnames | ACTIVE | Separate content/gameplay activation from hash/metadata/signature-proved mapper semantics; retain native meanings elsewhere | Classifier plus live stock/Zaero map fixture evidence |
| D-019 | Autocannon style-4 idle overread | ACTIVE | Preserve the shipped ELF's false result in a bounded fifth table entry | Only if repeatable retail Windows behavior contradicts the shipped ELF |
| D-020 | Selective EMP matrix and BFG state | ACTIVE | Explicit attack-type hooks, generation-safe owner exemption, saved non-colliding BFG latch, and Zaero-gated audio ordering; never blanket-disable weapons | Live full matrix and future Shield/Sentien/ZBoss integration |
| D-021 | Visor copy collision | OPEN | Capture whether the overlapping solid VisorCopy absorbs gameplay traces before choosing PARITY or a safe transparent-copy FIX | Before Visor implementation closes |

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

- **Status/date/owner:** OPEN; opened 2026-07-13; Unassigned.
- **Context:** The supplied Rerelease tree is not known from current evidence to
  be a Git checkout with a trustworthy commit identity.
- **Required decision:** Obtain the official upstream repository and pin the
  exact commit, or record source/archive origin, retrieval date, per-file SHA-256
  values, and an aggregate tree hash. Preserve a pristine comparison snapshot.
- **Alternatives:** Unpinned moving copy, rejected because API/layout drift would
  be unreviewable; vendored archive with hashes, acceptable only when commit
  provenance cannot be recovered.
- **Behavioral impact:** Determines API 2023 substrate, reproducible builds,
  upstream diffs, and future merge policy.
- **Evidence:** Supplied local Rerelease source, upstream license files, roadmap
  evidence boundary. Current src presence alone does not close identity.
- **Tests/migration:** Baseline manifest verifier; pristine-reference diff;
  Debug/Release API load smoke. Changing baseline runs the complete suite.

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

- **Status/date/owner:** INTERIM; 2026-07-13; Unassigned implementation owner.
- **Context:** Legacy Visor freezes gameplay controls and permits only a narrow
  command allowlist, suppressing chat too.
- **Decision:** Preserve control lock and explicit cancellation. Do not decide
  chat suppression until native command routing and multiplayer impact are
  tested.
- **Alternatives:** Literal allowlist including chat suppression; permit chat
  while retaining gameplay lock; remove lock, rejected as gameplay-changing.
- **Behavioral impact:** Remote-view vulnerability and multiplayer communication.
- **Evidence:** Supplied command/camera source.
- **Tests/migration:** Command allowlist, chat, death, damage, disconnect, save,
  zero/all-inactive cameras, and two-local-client isolation.

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

- **Status/date/owner:** OPEN; opened 2026-07-13; Unassigned.
- **Context:** Map worldspawn sounds selects legacy CD tracks; redistributable
  audio availability and Rerelease mapping are not yet established.
- **Required decision:** Map values to legally available Rerelease tracks and use
  a logged silent fallback when unavailable.
- **Alternatives:** Ship original music without permission, rejected; hard fail,
  rejected because maps must remain playable; arbitrary remapping, rejected
  without a documented episode presentation choice.
- **Behavioral impact:** Map ambience and transitions, not progression.
- **Evidence:** MAP worldspawn values, target Rerelease music facilities.
- **Tests/migration:** Values 1–11, missing tracks, transitions, volume, server
  and cinematic interaction. Document mapping in release notes.

## D-011 — ztomb1 target for absent tomb1 BSP

- **Status/date/owner:** OPEN; opened 2026-07-13; Unassigned.
- **Context:** A ztomb1 changelevel names tomb1, which is absent from all supplied
  packages.
- **Required decision:** Preserve exact data and test whether the path is
  reachable and what the retail result is. Patch only if it blocks intended
  progression, as a versioned FIX.
- **Alternatives:** Silent spelling correction, rejected; literal broken path,
  acceptable only if unreachable/intentional; opt-in compatibility data patch.
- **Behavioral impact:** Potential Tomb progression failure.
- **Evidence:** MAP/PKG entity and content inventory.
- **Tests/migration:** Route reachability from valid inbound states, save before
  trigger, original retail comparison if available, package data-patch manifest.

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

- **Status/date/owner:** INTERIM; 2026-07-13; Unassigned.
- **Context:** Rerelease bots need correct item/weapon/trap/projectile metadata,
  while advanced tactics and navigation authoring are larger parity-neutral
  work.
- **Decision:** 1.0 provides safe metadata and graceful behavior with or without
  navigation. Advanced custom-weapon tactics and generated navigation are
  post-parity enhancements.
- **Alternatives:** No bot integration, rejected because native paths must not
  crash; full tactical/nav scope before parity, rejected as critical-path drift.
- **Behavioral impact:** Bots can coexist safely but may not use every system
  optimally at 1.0.
- **Evidence:** Rerelease ownership audit and Phase 8 scope.
- **Tests/migration:** 2/4/8-client bot smokes on zdm1–6 and no-navigation
  fallback; publish known limitations.

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

- **Status/date/owner:** ACTIVE; 2026-07-13; repository maintainers.
- **Context:** Legacy source has _DEBUG/_Z_TESTMODE entities/commands plus
  disabled experiments that were not in the shipped Release DLL.
- **Decision:** They are not 1.0 gameplay requirements. Useful capability may
  return developer-only after parity and must be absent from Release.
- **Alternatives:** Port now, rejected as risk/scope; delete historical evidence,
  rejected; expose publicly, rejected because it changes the mapper/game ABI.
- **Behavioral impact:** Release players cannot spawn experimental tools.
- **Evidence:** SRC build/project guards and compiled-out blocks.
- **Tests/migration:** Release classname/command/archive denylist; explicit
  developer build flag if reintroduced.

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
  semantics; keep native Rerelease behavior on all other maps. The mapper scope
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
  door/viper/explosion saves, plus classifier fixtures for all 20 audited hashes,
  same-name/wrong-hash, explicit metadata, save stability, and stock/base/
  Xatrix/Rogue/ambiguous-community false positives. A stock DM map must run
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
  native integration adaptation, not a new classname-wide EMP rule. Add
  explicit Plasma Shield, Sentien, and ZBoss sites when those systems land.
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
  fields and complete Shield/Sentien/ZBoss sites. Existing development saves
  without the boolean load its false default; stable-schema policy applies once
  public save compatibility begins.

## D-021 — Visor copy collision and trace behavior

- **Status/date/owner:** OPEN; opened 2026-07-13; Visor implementation owner.
- **Context:** `zCam_TrackEntity` hides the real player's model but leaves that
  player solid, then creates a solid, non-damageable `VisorCopy` at the same
  position. The copy can intercept traces without taking damage, which may
  change who can hit the remotely viewing player.
- **Required decision:** Capture the supplied retail behavior for owner,
  teammate, enemy, monster, hitscan, and projectile traces. Preserve exact copy
  collision as PARITY if it is a stable gameplay trait; otherwise make the
  visual copy non-blocking as a scoped FIX while keeping the real player's
  collision, vulnerability, and remote-view presentation unchanged.
- **Alternatives:** Copy the source literally without evidence, rejected because
  overlapping solids and trace ordering differ across engines; make both
  player and copy non-solid, rejected because remote-view vulnerability is
  gameplay; remove the copy, rejected because third-person presentation is
  visible.
- **Behavioral impact:** Determines whether entering Visor can absorb attacks or
  alter line-of-fire interactions in single player, co-op, and deathmatch.
- **Evidence:** Supplied `z_camera.c::zCam_TrackEntity`, `zCam_Stop`, Q-044,
  PLY-008, and Rerelease trace/entity-link semantics.
- **Tests/migration:** Repeatable retail capture and Rerelease fixtures for all
  attacker/weapon classes, overlapping entity order, damage/death cancellation,
  drop/putaway/disconnect, split-screen isolation, entity free/reuse, and saves.
  The final choice requires a quirk status update and player-facing release note
  if it differs from retail.

## Adding or superseding a decision

A new record must state status, date, owner, context, decision, alternatives,
behavioral impact, evidence, tests, and migration/release consequences. Do not
erase old reasoning. Mark it SUPERSEDED, link the replacement, and update every
affected feature/entity/map/quirk row.

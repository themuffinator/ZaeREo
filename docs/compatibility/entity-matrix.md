# Entity compatibility matrix

- Evidence: all 20 supplied BSP entity lumps plus the supplied Zaero spawn/item
  tables
- Audit date: 2026-07-13
- Runtime implementation: **in progress; see per-row evidence**

The BSPs contain 14,933 entity records and 132 distinct exact classnames. The
Rerelease baseline recognizes 105 of those names; the first table locks the 27
map-facing names that require Zaero implementations. Counts below are literal
entity-lump occurrences after pak0 < pak1 < pak2 resolution. They do not prove
that an entity currently spawns in ZaeREo.

The partial port currently resolves 127/132 exact shipped names. The remaining
five are `monster_handler`, `monster_hound`, `monster_sentien`,
`monster_zboss`, and `target_zboss_target`. This progress count does not weaken
the invariant below: a production package must resolve all 132 without a
placeholder or silent free unless the exact entity's compatibility contract is
an approved no-op.

The checked-in `docs/audits/bsp-entities.*` intentionally records the pristine
upstream 105/132 baseline. Reproduce the worktree-only 127/132 progress snapshot
without overwriting that evidence:

~~~powershell
python tools/audit_bsp_entities.py --assets-root "E:\_SOURCE\_ASSETS\Zaero" --rerelease-root src --pak pak0.pak --pak pak1.pak --pak pak2.pak --json-output build/audits/current-registry.json --markdown-output build/audits/current-registry.md
~~~

The generated local report must show exactly the five names above. A committed
current-registry report is added only when the project defines its regeneration
and baseline-update policy; until then this count is reproducible progress
evidence, not a VERIFIED release proof.

Every implementation must retain its exact classname, accepted keys and flags,
stable save identity, callbacks, resources, and cleanup. The historical
monster_sentien spelling is part of the mapper ABI.

## Missing map-facing classnames

| ID | Exact classname | Shipped placements | Contract to preserve | Phase | Implementation / owner | Required save or lifecycle proof | Status |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| E-001 | weapon_flaregun | 23: zbase1, zboss, zdef1–4, zdm1–6, ztomb1–3, zwaste1–3 | Custom item/weapon, ammo relationship, wheel/aliases, pickup flags | 4 | [item registry](../../src/g_items.cpp) and [Flare Gun](../../src/zaero/g_zaero_weapons.cpp) / Item/weapon slice | [Registry, projectile, flash, and save contracts](../../tests/compatibility/test_zaero_items_weapons.py) pass; live held/firing/death/transition round trips remain | IN PROGRESS |
| E-002 | weapon_sniperrifle | 17: zbase1, zdef1–4, zdm1–6, ztomb1–2, zwaste1–3 | Custom weapon, zoom by mode, three-slug use, cycle exclusions | 4 | [implemented registry](../../src/g_items.cpp) and [dedicated Sniper Rifle](../../src/zaero/g_zaero_sniper.cpp) / Sniper slice | [Metadata, firing, trace, charge, zoom/HUD, cleanup, and save-wiring contracts](../../tests/compatibility/test_zaero_sniper.py) pass; live SP/DM/split-screen/Shield/save behavior remains | IN PROGRESS |
| E-003 | weapon_soniccannon | 21: zbase1–2, zdef1–4, zdm1–6, ztomb1–4, zwaste1–3 | Custom cell weapon and charge state | 4 | [implemented item callback](../../src/g_items.cpp) and [Sonic Cannon](../../src/zaero/g_zaero_sonic.cpp) / Sonic weapon slice | [Charge/cell/damage/effect/Quad/audio/save-wiring contracts](../../tests/compatibility/test_zaero_sonic.py) pass; live charge/release, real EMP, split-screen and save round trips remain | IN PROGRESS |
| E-004 | ammo_flares | 40: zbase1, zboss, zdef1–4, zdm1–6, ztomb1–4, zwaste1–3 | Ammo quantity/max, custom cap/respawn spawnflags | 4 | [item registry, caps, Pack omission, and pickup flags](../../src/g_items.cpp) / Item/weapon slice | [Metadata, cap, Pack, and spawnflag contracts](../../tests/compatibility/test_zaero_items_weapons.py) pass; live pickup/respawn/save remains | IN PROGRESS |
| E-005 | ammo_ired | 76: all 20 maps | Usable ammo/deployable, quantity/max, custom pickup flags | 4 | [implemented registry](../../src/g_items.cpp) and [dedicated player/map IRED](../../src/zaero/g_zaero_ired.cpp) / IRED slice | [Metadata, cap, pickup, placement, beam, expiry, blast/shrapnel, callback, and save-wiring contracts](../../tests/compatibility/test_zaero_ired.py) pass; live lifecycle/cleanup/save remains | IN PROGRESS |
| E-006 | ammo_a2k | 28: all except zbase2 and zdm5 | Use-as-weapon item, maximum one; activation consumption, gunframe-19 client countdown/immunity, HUD, death cancellation, detonation helper and dual blast | 4 | [exact registry with explicit safe placeholder](../../src/g_items.cpp) / Item/weapon slice | Metadata/cap contracts pass; exact five seconds (`50` legacy frames = `200` target ticks, represented as duration), no-protection immunity, death/save phases, damage boundaries/multiplicity, and Quad-at-blast remain | IN PROGRESS |
| E-007 | ammo_empnuke | 46: all 20 maps | Use-as-weapon item and EMP-center owner/state | 4 | [implemented registry](../../src/g_items.cpp) and [dedicated EMP field/query](../../src/zaero/g_zaero_emp.cpp) / EMP slice | [Metadata, lifecycle, radius, owner/generation exemption, selective hooks, BFG latch/audio/order, callback, and save-wiring contracts](../../tests/compatibility/test_zaero_emp.py) pass; live overlap/cleanup/save and missing monster/Shield integrations remain | IN PROGRESS |
| E-008 | ammo_plasmashield | 28: zbase1, zdef1–4, zdm1–6, ztomb1–4, zwaste2–3 | Use-as-weapon ammo and oriented shield entity | 4 | [exact registry with explicit safe placeholder](../../src/g_items.cpp) / Item/weapon slice | [Metadata, cap, and no-stock-alias contracts](../../tests/compatibility/test_zaero_items_weapons.py) pass; shield deployment/lifecycle is not implemented | IN PROGRESS |
| E-009 | item_visor | 30: zbase1–2, zdef1–4, zdm1–6, ztomb1–3, zwaste1–3 | 30-second timed item (`300` legacy frames = `1,200` target ticks as duration), additive dropped time that may exceed 30 seconds, camera enumeration, solid copy, view/HUD lifecycle | 4 | [exact registry with explicit safe placeholder](../../src/g_items.cpp) / Item/weapon slice | Metadata contracts pass; fresh/partial/dropped/stacked duration, camera cycling, trace absorption, 0.2-second static, yaw sway, cancellation, split-screen, and saves are not implemented | IN PROGRESS |
| E-010 | key_energy | 2: ztomb1, ztomb3 | Custom key with native key/coop rules | 4–8 | [native key-backed registry](../../src/g_items.cpp) / Item/weapon slice | [Exact metadata/callback contract](../../tests/compatibility/test_zaero_items_weapons.py) passes; live Tomb/co-op/save proof remains | IN PROGRESS |
| E-011 | key_landing_area | 1: zdef4 | Airfield Pass key with native key/coop rules | 4–8 | [native key-backed registry](../../src/g_items.cpp) / Item/weapon slice | [Exact metadata/callback contract](../../tests/compatibility/test_zaero_items_weapons.py) passes; live zdef4/co-op/save proof remains | IN PROGRESS |
| E-012 | key_lava | 2: ztomb1, ztomb4 | Custom key with native key/coop rules | 4–8 | [native key-backed registry](../../src/g_items.cpp) / Item/weapon slice | [Exact metadata/callback contract](../../tests/compatibility/test_zaero_items_weapons.py) passes; live Tomb/co-op/save proof remains | IN PROGRESS |
| E-013 | key_slime | 2: ztomb1, ztomb2 | Custom key with native key/coop rules | 4–8 | [native key-backed registry](../../src/g_items.cpp) / Item/weapon slice | [Exact metadata/callback contract](../../tests/compatibility/test_zaero_items_weapons.py) passes; live Tomb/co-op/save proof remains | IN PROGRESS |
| E-014 | monster_autocannon | 13: zdef2–4, ztomb2, zwaste1–2 | Ceiling cannon; style/arcs, active/use, health/death; intentionally not SVF_MONSTER | 6 | [ceiling multipart implementation and exact registry](../../src/zaero/g_zaero_autocannon.cpp) / Autocannon slice | [Retail/source/map-backed style, cadence, arc, EMP, state, death and save-registration contracts](../../tests/compatibility/test_zaero_autocannon.py) pass; live combat and all-state save fixtures remain | IN PROGRESS |
| E-015 | monster_autocannon_floor | 2: ztomb3 | Floor cannon; rejects style 1 and rides movers | 6 | [floor assembly using generation-safe RIDE children](../../src/zaero/g_zaero_autocannon.cpp) / Autocannon slice | [Style rejection, bounds/models and two-child rider contracts](../../tests/compatibility/test_zaero_autocannon.py) pass; live ztomb3 platform movement and all-state saves remain | IN PROGRESS |
| E-016 | monster_handler | 7: zbase1–2, zwaste2–3 | Composite spawn, lethal clamp, Hound release, Infantry conversion, no-count flag | 5 | — / Unassigned | Before/during/after split, totals, identity and death | NOT STARTED |
| E-017 | monster_hound | 20: zdef1, ztomb1, ztomb3, zwaste1 | Bite/leap, spawnflag-8 schooling, mteam and custom AI fields | 5–6 | — / Unassigned | Attack/school/pain/death and peer loss across save | NOT STARTED |
| E-018 | monster_sentien | 31: zdef1–2, zdef4, ztomb1, ztomb4, zwaste1–3 | Flying attacks, persistent laser, fend/shield, EMP, exact spelling | 6 | — / Unassigned | Every attack/fend/pain/death and helper cleanup | NOT STARTED |
| E-019 | monster_zboss | 1: zboss | Skill health, attack/state set, grapple, EMP, 42nd-pain retaliation, below-25% branch/30–35-second cooldown, marker and death barrage | 7 | — / Unassigned | Every phase/attack, pain boundary, cooldown/save, Hound-schooling isolation, grapple target loss, death/finale | NOT STARTED |
| E-020 | func_barrier | 1: ztomb4 | Invisible immortal solid, reveal on touch/damage, trace state | 3–4 | [world entities](../../src/zaero/g_zaero_entities.cpp) / World entities | [Static lifecycle and defined-trace contracts](../../tests/compatibility/test_zaero_world_entities.py) pass; live weapon/save proof remains | IN PROGRESS |
| E-021 | misc_commdish | 1: zbase2 | One-shot use-triggered animation; supplied callback does not fire ordinary targets | 3 | [world entities](../../src/zaero/g_zaero_entities.cpp) / World entities | [Model/callback/timing contract](../../tests/compatibility/test_zaero_world_entities.py) passes; live zbase2/save proof remains | IN PROGRESS |
| E-022 | misc_crate | 2: zbase1, zwaste2 | 64-unit pushable FALLFLOAT object, mass/damage/collision | 3 | [world entities](../../src/zaero/g_zaero_entities.cpp) and [FALLFLOAT](../../src/g_phys.cpp) / World entities | [Bounds/model/mass contract](../../tests/compatibility/test_zaero_world_entities.py) passes; live ground/water/Push/save proof remains | IN PROGRESS |
| E-023 | misc_crate_medium | 2: zdef2, zdef4 | 48-unit pushable FALLFLOAT object | 3 | [world entities](../../src/zaero/g_zaero_entities.cpp) and [FALLFLOAT](../../src/g_phys.cpp) / World entities | [Bounds/model/mass contract](../../tests/compatibility/test_zaero_world_entities.py) passes; live ground/water/Push/save proof remains | IN PROGRESS |
| E-024 | misc_ired | 2: ztomb3 | Mapper-authored IRED, use toggle, back-wall check and targets | 3–4 | [shared map/player IRED implementation and exact spawn registry](../../src/zaero/g_zaero_ired.cpp) / IRED slice | [Map toggle, back-wall, target, beam and registry contracts](../../tests/compatibility/test_zaero_ired.py) pass; live ztomb3 off/armed/triggered/expired/save states remain | IN PROGRESS |
| E-025 | misc_seat | 1: zbase1 | Pushable FALLFLOAT seat with mass-sensitive interaction | 3 | [world entities](../../src/zaero/g_zaero_entities.cpp) and [FALLFLOAT](../../src/g_phys.cpp) / World entities | [Bounds/model/mass contract](../../tests/compatibility/test_zaero_world_entities.py) passes; live ground/water/Push/save proof remains | IN PROGRESS |
| E-026 | misc_securitycamera | 113: every map except zboss and ztomb4 | Message required; initial active solely from targetname; `{-16,-16,-32}`–`{16,16,0}` solid bounds; forward-8/down-32 view offset; health-1 native immortality; use/mangle; frames 0–59 at 10 Hz/six seconds; 0.2-second pain shell; Visor visibility and ±15-degree 6.4-second sway | 3–4 | [camera entity lifecycle](../../src/zaero/g_zaero_entities.cpp) / World entities | [Required-message, mangle, damage, immortality and callback contract](../../tests/compatibility/test_zaero_world_entities.py) passes; targetname/no-targetname spawn, bounds/offset, exact durations/cadence, use/save, Visor enumeration, and live maps remain | IN PROGRESS |
| E-027 | target_zboss_target | 5: zboss | One-shot boss target marker with validated target/owner | 3/7 | — / Unassigned | Unused/used, missing enemy/target, save and free/reuse | NOT STARTED |

## Source-exposed classnames not placed by the supplied maps

These remain compatibility surfaces for source behavior, editor definitions,
and community maps. A no-op must be explicit and must still parse and save
safely where state exists.

| ID | Exact classname | Source contract | Disposition | Phase | Implementation / owner | Required proof | Status |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| E-028 | sound_echo | Deliberately frees itself; compatibility no-op | PARITY | 2 | [explicit no-op](../../src/zaero/g_zaero_entities.cpp) / World entities | [No-op registry/source contract](../../tests/compatibility/test_zaero_world_entities.py) passes; live spawn-log proof remains | IN PROGRESS |
| E-029 | load_mirrorlevel | Deliberately frees itself; compatibility no-op | PARITY | 2 | [explicit no-op](../../src/zaero/g_zaero_entities.cpp) / World entities | [No-op registry/source contract](../../tests/compatibility/test_zaero_world_entities.py) passes; live key/spawn proof remains | IN PROGRESS |
| E-030 | trigger_laser | No use callback; target required; auto-start after 0.1 seconds; wait defaults 4; 2,048-unit player/monster-only trace; bit 1 rearms, otherwise frees after first hit | PARITY | 3 | [Current bounded trace scaffold](../../src/zaero/g_zaero_entities.cpp) exposes a non-legacy use toggle / World entities | Synthetic target/no-target, timing/range/mask, hit filtering, rearm/free, callback/save, and editor proof remain; no shipped BSP placement exists | IN PROGRESS |
| E-031 | misc_crate_small | 32-unit pushable FALLFLOAT crate | PARITY | 3 | [world entities](../../src/zaero/g_zaero_entities.cpp) and [FALLFLOAT](../../src/g_phys.cpp) / World entities | [Bounds/model/mass contract](../../tests/compatibility/test_zaero_world_entities.py) passes; live ground/water/Push/save proof remains | IN PROGRESS |
| E-032 | weapon_push | Hidden always-owned player weapon; never ordinary map loot | PARITY | 4 | [hidden Push implementation](../../src/zaero/g_zaero_weapons.cpp) and [registry](../../src/g_items.cpp) / Item/weapon slice | [Ownership, hiding, range, damage, mass, and save registration contracts](../../tests/compatibility/test_zaero_items_weapons.py) pass; live non-placement/save round trip remains | IN PROGRESS |
| E-033 | key_lab | Source-exposed Laboratory key with stock key semantics | ADAPT | 4 | [native key-backed registry](../../src/g_items.cpp) / Item/weapon slice | [Exact metadata/callback contract](../../tests/compatibility/test_zaero_items_weapons.py) passes; live community-map/co-op/save fixture remains | IN PROGRESS |
| E-034 | key_clearancepass | Source-exposed Clearance Pass key with stock key semantics | ADAPT | 4 | [native key-backed registry](../../src/g_items.cpp) / Item/weapon slice | [Exact metadata/callback contract](../../tests/compatibility/test_zaero_items_weapons.py) passes; live community-map/co-op/save fixture remains | IN PROGRESS |

## Stock classnames with Zaero semantics

Native Rerelease behavior remains the base. Only the listed observable Zaero
extension is added; ordinary uses must continue to pass stock smoke tests.

| ID | Exact classname | Shipped evidence | Zaero extension | Phase | Implementation / owner | Required proof | Status |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| E-035 | func_timer | 45 in 11 maps; three semicolon target lists in ztomb2, ztomb4, zdm6 | Randomly fire one listed target with bounded parsing | 3 | [g_func.cpp](../../src/g_func.cpp), [save fields](../../src/g_save.cpp) / Map behaviors | [Target/parser contracts](../../tests/compatibility/test_stock_map_behaviors.py) pass; live distribution, delayed use, and save remain | IN PROGRESS |
| E-036 | trigger_push | 5: zdef3 and zdm6 | Spawnflag bit 2 start-off, bit 4 no-sound, use toggle | 3 | [g_trigger.cpp](../../src/g_trigger.cpp) / Map behaviors | [Flag separation and toggle contracts](../../tests/compatibility/test_stock_map_behaviors.py) pass; off/on client/non-client/sound/save fixture remains | IN PROGRESS |
| E-037 | func_rotating | 14: zbase1, zdef1–2, zdm4, zdm6, ztomb2, zwaste1 | Acceleration/deceleration and stateful toggle | 3 | [g_func.cpp](../../src/g_func.cpp), [saved state](../../src/g_local.h) / Map behaviors | [40 Hz curve and toggle contracts](../../tests/compatibility/test_stock_map_behaviors.py) pass; rider/contact/live save remain | IN PROGRESS |
| E-038 | func_door | 318 in 19 maps | active bit 1 changes use/touch eligibility; bit 2 is current auto-trigger state; repeated uses preserve message; blocked path skips damage when `dmg <= 0` | 3 | [Zaero-gated active/team/touch/spawn integration](../../src/g_func.cpp) / Stock world extensions | Existing active/team contracts pass; repeated-message, blocked zero/positive damage, movement/save, and native fallback remain | IN PROGRESS |
| E-039 | misc_viper | 7: zbase1, zdef4, zboss | Smoke, explicit solid/bounds, model2–4, ordinary train route | 3 | [Zaero-gated multipart viper integration](../../src/g_misc.cpp) / Stock world extensions | [Smoke consumption, zdef4 bulldog, model2–4 and native fallback contracts](../../tests/compatibility/test_stock_world_extensions.py) pass; linked live motion/save remains | IN PROGRESS |
| E-040 | target_explosion | 35 in six maps | Flag 1 selects A2K-style cosmetic effect/sound only | 3 | [cosmetic-only animated explosion](../../src/g_target.cpp) / Stock world extensions | [All-map counts, three flagged zbase2 patterns, damage/target ordering, callbacks and generation guard](../../tests/compatibility/test_stock_world_extensions.py) pass; live damage/target/save remains | IN PROGRESS |
| E-041 | target_help | 39 in ten campaign maps | Cross-level objective state and Zaero HUD intent | 3–8 | [native two-message target/help state](../../src/g_target.cpp), [F1/HUD presentation](../../src/p_hud.cpp), and [JSON fields](../../src/g_save.cpp) / Mission-help integration | Ten-map semantic audit plus live update/transition/save/notification and per-client display remain | IN PROGRESS |
| E-042 | worldspawn | 20: one per map | Music values 1–11 and Zaero resource/start integration | 2–7 | — / Unassigned | Every value plus missing-track and map load checks | NOT STARTED |
| E-043 | target_changelevel | 30 in 14 campaign maps | Exact unit, spawnpoint, cinematic/image target strings | 2–7 | [native target handling](../../src/g_target.cpp), [generated BSP evidence](../audits/bsp-entities.md), and tracked start/mapdb data / Campaign integration | Deterministic flow report plus all inbound/outbound unit, spawnpoint, cinematic/image, suspicious `tomb1`, save, and co-op live routes remain | IN PROGRESS |
| E-044 | path_corner | 375 in 12 campaign maps; 96 waits, four teleports, five nonzero node speeds in zdef4; no shipped smooth bits 2/4 | Turn toward next goal before waiting; suppress teleport event; source-exposed smooth flags remain community-map ABI | 3 | [D-018 map gate](decisions.md#d-018--zaero-semantics-on-stock-classnames) / Unassigned | Shipped wait/teleport/speed routes, save/orientation, and synthetic smooth-bit fixtures | NOT STARTED |
| E-045 | func_train | 28: zdef2–3, ztomb2, zwaste3; no shipped rotation bits 8/16/32/64; all four aspeed values zero | Per-corner speed/accel/decel, raw-origin misc_viper destination, attached/rotating source contract and rider integration | 3/6 | [D-018 map gate](decisions.md#d-018--zaero-semantics-on-stock-classnames) / Unassigned | Shipped paths/Viper/riders/save plus synthetic colliding flag and nonzero-aspeed fixtures with native fallback | NOT STARTED |
| E-046 | func_plat | 11 bit-2 platforms: zbase2, zdef1–2, zdef4, zdm1, zdm3–4, ztomb3 | Zaero bit 2 accepts a player touch only within eight units of the lowered platform top | 3 | [D-018 map gate](decisions.md#d-018--zaero-semantics-on-stock-classnames) / Unassigned | Exact above/below boundary, non-player touch, move/save, all 11 placements, and native Rerelease bit-2 no-monster fallback | NOT STARTED |
| E-047 | misc_explobox | 31: zbase1 (4), zdef1 (2), ztomb2 (6), zwaste2 (7), zwaste3 (12) | FALLFLOAT, mass 400, client-only airborne-capable `SV_movestep` pushing | 3 | [D-018 map gate](decisions.md#d-018--zaero-semantics-on-stock-classnames) / Unassigned | Water/sink, grounded/airborne push, slope/block, Push interaction, explosion, JSON save, and native mass-50/fallback | NOT STARTED |
| E-048 | func_door_rotating | 32 in ten maps; six omit dmg and six set dmg 0 | No legacy default damage 2; zero/missing damage blocks without damage, explicit positive damage remains | 3 | [D-018 map gate](decisions.md#d-018--zaero-semantics-on-stock-classnames) / Unassigned | All 12 zero/missing placements, explicit positive damage, block/use/team/save, and native Rerelease default fallback | NOT STARTED |

## Required registry invariant

Production validation must reject a release when:

- any of the 132 shipped exact classnames is unknown;
- an incomplete entity silently substitutes a placeholder;
- a recognized classname ignores a Zaero-required key/flag without a recorded
  no-op decision;
- callback, move, resource, or state registration is absent from JSON saves; or
- the normalized audit no longer matches these counts without an intentional
  baseline decision.

The committed generated BSP audit supersedes hand-maintained counts. Any
generated change must be reviewed before this matrix is updated.

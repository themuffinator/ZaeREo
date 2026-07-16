# Map compatibility matrix

- Scope: 14 campaign BSPs and six dedicated deathmatch BSPs
- Evidence: parsed effective pak0/pak2 entity lumps
- Audit date: 2026-07-13
- Runtime status: **`zbase1`, `zdef1`, and `zboss` have bounded load/spawn
  smokes only; no map has passed completion or gameplay-compatibility
  verification**

All 20 maps contain authored deathmatch starts. All 14 campaign maps also
contain co-op starts. Co-op and deathmatch are therefore required compatibility
surfaces, not optional stretch goals.

Counts are planning-audit evidence only. Entity count means records with a
classname. Monster count means classnames beginning with monster_ and is not a
verified in-game total after spawn filtering, composite spawns, or no-count
flags.

Phase-3 source contracts now cover the seven shipped `misc_viper` placements,
all 318 sliding doors including the 81/37/16 `active` value patterns, and all 35
`target_explosion` placements including zbase2's three cosmetic flag-1 events.
They also translate Zaero's low monster spawnflag 16 into native no-count
accounting and route monster spawn killboxes through a player-safe compatibility
path. The two shipped low-bit placements are the tank in `zbase1` (flags 20) and
the Sentien in `zdef4` (flags 18).
The normalized/static proof is in
[`test_stock_world_extensions.py`](../../tests/compatibility/test_stock_world_extensions.py)
and [`test_zaero_monster_spawn.py`](../../tests/compatibility/test_zaero_monster_spawn.py);
no map status below changes until those paths have live runtime/save evidence.

The worktree registry currently resolves all 132/132 shipped classnames; the
exact reproduction command and zero-missing result are recorded in the
[entity matrix](entity-matrix.md). Static contracts now also cover the
[Sniper Rifle](../../tests/compatibility/test_zaero_sniper.py),
[player/map IRED including ztomb3's two `misc_ired` entities](../../tests/compatibility/test_zaero_ired.py),
the [EMP field/selective hook matrix](../../tests/compatibility/test_zaero_emp.py),
and the [28 authored Plasma Shield pickups and deployable lifecycle](../../tests/compatibility/test_zaero_plasma_shield.py)
across 17 maps. The [Visor's typed inventory and active camera lifecycle](../../tests/compatibility/test_zaero_visor.py)
covers its 30 authored pickups across 18 maps and bounded enumeration of all
113 cameras across 18 maps, including the D-021 non-solid-copy FIX. This is
static/source proof only: no affected map gains live view, collision, save, or
split-screen status. Static contracts also cover
[A2K's typed countdown and dual blast](../../tests/compatibility/test_zaero_a2k.py)
for its 28 authored placements in every map except `zbase2` and `zdm5`, plus
the exact opt-in `use weapon 1`–`10` alternate table and native wheel metadata
used across campaign and deathmatch maps. The player-presentation contracts now
also cover the private `showorigin` HUD, full custom owned-wheel bitset, typed
five-second kill guard, all 25 Zaero monster obituary fallbacks and seven custom
MOD paths. The shared projectile-dodge slice also now gives classified Zaero
maps the exact client Rocket/BFG/Flare firing-time trace, skill throttle and
saved typed deadline while excluding Blaster and retaining native behavior on
non-Zaero maps. None of these static contracts change any live map status.
The [D-041 damage-reaction integration](../../tests/compatibility/test_zaero_ai_reaction.py)
also statically covers player/monster/non-monster Autocannon admission,
`mteam`/buddy selection, retained `AI_SOUND_TARGET`, the four tank exclusions,
and Q-046 self-target rejection while preserving native expansion lifecycle.
This changes no map row: all reaction, combat and save behavior remains live
unverified.
[D-042's Hover strafe integration](../../tests/compatibility/test_zaero_hover_strafe.py)
statically covers all 22 `monster_hover` placements: zdef1 (11), ztomb1 (5),
ztomb3 (3), and zwaste1 (3). It preserves the bounded radial dodge and strict
typed one-second boundary while fixing Q-013's stale state and isolating native
Hover/Daedalus behavior. No affected map row advances: projectile, direction,
collision, expiry, save, and completion behavior remain live-unverified.
[D-043's stock-precache audit](../audits/stock-precaches.md) proves that the
supplied source's 22 helpers in 19 stock files have only one cross-file stock
dependency: Handler reuses Infantry resources. The port routes that dependency
through Rerelease's existing `InfantryPrecache` and its custom Hound precache,
without cloning the other stock files or the disabled 256-sound interceptor.
This statically covers the resource route used by all seven Handlers in
`zbase1`, `zbase2`, `zwaste2`, and `zwaste3`; only `zbase1` has the separate
sampled load/spawn smoke. No map row advances until referenced-index, audible,
conversion, save, gameplay, and completion evidence exists.
[D-044's SV_FlyMove audit](../audits/flymove.md) isolates Zaero's one-condition
global exact-duplicate-plane removal and executes seven float32 wall/corner/
stair/wedge/projectile/monster goldens. It retains the shared native Rerelease
near-duplicate solver for Step physics, all custom FALLFLOAT entities, and all
22 Hovers rather than adding a Zaero-map branch. No map row advances: live
always-windowed geometry, caller isolation, save/lifecycle, and completion
evidence remains.
[D-045's deathmatch-injection audit](../audits/dm-injection.md) joins the exact
eight-classname source precondition to all 20 BSP inventories and 230 authored
deathmatch starts. Every supplied map has at least one member, so all suppress
automatic injection; `zbase2`, `zboss`, `zdm5`, `ztomb3`, `ztomb4`, and
`zwaste1` omit one or more members but remain ineligible under the historical
any-member rule. Static values 0–3, item order, wrapping start walk,
partial-success, native lifecycle, and mapper-isolation contracts now pass.
A private legacy-v1 one-stage `q2dm1` matrix records aggregate counts
8/8/disabled/disabled for values 0–3, and a `zdm1` control records
existing-member suppression. A structured `q2dm1` probe records exact identities/order,
successive first-attempt start ordinals, 128/16-unit offsets, final origins,
and native live item state; disabled/authored controls record zero. A private
real-brush fixture records alternating failures at indices 0/2/4/6 and wrapped
ordinals 1/6/11/16. Eight private one-member maps each record zero injection.
All such reports predate D-046 and must be rerun before they count as current
runtime evidence. No item row advances: pickup/respawn/drop/save, dedicated
and 2/4/8-client sessions, and native-mode isolation remain live-unverified.
The source-only `trigger_laser` has no supplied BSP placement, but its community-
map ABI is now statically closed for required target, 0.1-second auto-start,
default wait, trace/render/spark behavior, bit-1 rearm versus one-shot free,
saved callbacks, no-use surface, generation-safe target dispatch, and generated
editor metadata. A synthetic live fixture is still required before verification.
These reduce implementation risk but are not map completion evidence. The
historical one-stage load/spawn results recorded below originally observed that
the installed DLL reached local client entry and orderly shutdown; every
completion and save cell remains NOT TESTED. They are no longer current runtime
evidence: each injected `game`/`map` before the wrapper could verify a native
window. Rerun them with the v2 two-stage wrapper before using them for a
launch-safety, load/spawn, resource, or registry claim.

The completed source/BSP audit also identifies 11 bit-2 low-trigger `func_plat`
entities: one each in `zbase2`, `zdef1`, `zdef4`, `zdm1`, and `zdm3`, plus two
each in `zdef2`, `zdm4`, and `ztomb3`. [D-036](decisions.md#d-036--func_plat-bit-2-low-trigger-collision)
now applies the exact source feet-height boundary only on Zaero-classified maps
and preserves native bit-2 no-monster behavior elsewhere. Identity-locked
static tests cover that dispatch and inventory, but no platform has yet passed
live touch, movement, monster-use, or save/load verification.

[D-037](decisions.md#d-037--misc_explobox-fallfloat-and-push-contract) now
gates the 31 authored `misc_explobox` entities to FALLFLOAT, default mass 400,
legacy drop startup, and client-only airborne-capable `SV_movestep` pushing;
non-Zaero maps retain native STEP/mass-50/contact behavior. Static tests lock
the zbase1 (4), zdef1 (2), ztomb2 (6), zwaste2 (7), and zwaste3 (12) inventory
and 40 Hz rate conversion. No barrel has passed live water, slope/blocking,
push-contact, explosion, or save/load verification.

[D-038](decisions.md#d-038--func_door_rotating-zero-damage-default) now keeps
all 12 missing/explicit-zero rotating doors non-damaging on Zaero-classified
maps while retaining authored positive values and the native default elsewhere.
Static tests lock six missing and six zero entities in `zdef1`, `zdef3`,
`zdm5`, `ztomb2`, `zwaste1`, and `zwaste3`, plus shared blocked/reversal order;
none has passed live block, movement, team, or save/load verification.

[D-039](decisions.md#d-039--train-and-path-corner-colliding-mapper-semantics)
now gates the train/path delta: Zaero nodes can replace speed/accel/decel,
ordinary `train_next` segments use raw origins for `misc_viper`, waiting
monsters turn before standing, and Zaero teleports omit their presentation
event. Static tests lock all 375 corners by map, all 28 trains and seven Vipers,
the five nonzero zdef4 node speeds, 96 waits, and four exact teleport indices.
They also cover unshipped smooth bits 2/4 and rotating-train bits 8/16/32/64 at
the supplied 10 Hz decision cadence over 40 Hz physics while retaining native
Rogue meanings elsewhere. No train, Viper route, wait, teleport, smooth move,
rotation, rider, or mid-segment save has passed live verification, so every map
status remains NOT TESTED.

[D-010](decisions.md#d-010--music-values-111) now maps each supplied
worldspawn's numeric music request through Rerelease's own base-soundtrack
contract without packaging any soundtrack media. The exact values are zbase1
9, zbase2 6, zboss 11, zdef1 4, zdef2 9, zdef3 6, zdef4 3, zdm1 8, zdm2 4,
zdm3 3, zdm4 5, zdm5 6, zdm6 1, ztomb1 5, ztomb2 6, ztomb3 3, ztomb4 11,
zwaste1 6, zwaste2 9, and zwaste3 11. Values 2–11 retain native numeric
selection; zdm6's unavailable data-track value 1 becomes logged silence.
Static tests cover provenance, explicit `music` precedence, native-map
isolation, transition replacement, and no volume/loop mutation. A historical
legacy-v1 one-stage zdm6 report recorded the exact value-1 fallback line but
must be rerun under D-046 and did not capture audio. No track has yet passed
live audibility, transition, client-volume, or dedicated-server proof, so no
music or load/spawn cell advances on that observation.

[D-011](decisions.md#d-011--ztomb1-target-for-absent-tomb1-bsp) resolves the
ztomb1 `tomb1` anomaly without changing map data. The generated closure report
now records every one of the 30 changelevels: 29 have exactly one activation
reference and a present BSP destination (or zboss's presentation chain), while
ztomb1 entity 522 is both the sole missing BSP and the sole entity with zero
activation or other references. Native/supplied `target_changelevel` is
invisible and use-only, and no production source names its `mainexit`
targetname, so fresh/carried/co-op inbound state cannot make it reachable. It
remains an inert mapper artifact; no alias, replacement BSP, or import patch is
authorized. Valid Tomb routes still require live completion evidence.

[D-040](decisions.md#d-040--health-pickup-sound-concurrency) replaces Zaero's
shared item-table sound mutation with a scoped per-pickup 2/10/25/default
selection after any explicit native noise. The supplied maps contain 447
health entities—111 small, 198 normal, 129 large, and nine mega—and no custom
count, so their sound choice is unchanged; the local resolver preserves the
source-exposed custom-count result without cross-client contamination. Static
concurrency/native-isolation contracts pass, but no health set has passed live
same-frame multiplayer/split-screen, custom-count, or re-entrant pickup proof;
no map status changes.

## Entity-lump inventory

| Map | Unit/mode | Entities | Unique classnames | Co-op starts | DM starts | Secrets | Monster records |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| zbase1 | Base campaign | 508 | 76 | 12 | 7 | 1 | 28 |
| zbase2 | Base campaign | 501 | 60 | 4 | 8 | 1 | 31 |
| zdef1 | Defence campaign | 1,143 | 75 | 16 | 12 | 2 | 122 |
| zdef2 | Defence campaign | 770 | 81 | 4 | 13 | 3 | 109 |
| zdef3 | Defence campaign | 1,989 | 84 | 4 | 19 | 2 | 114 |
| zdef4 | Defence campaign | 1,084 | 76 | 12 | 14 | 2 | 98 |
| zwaste1 | Wasteland campaign | 656 | 65 | 21 | 8 | 3 | 63 |
| zwaste2 | Wasteland campaign | 467 | 63 | 4 | 9 | 2 | 35 |
| zwaste3 | Wasteland campaign | 443 | 68 | 8 | 8 | 3 | 53 |
| ztomb1 | Tomb campaign | 1,009 | 80 | 20 | 15 | 2 | 74 |
| ztomb2 | Tomb campaign | 1,334 | 84 | 4 | 11 | 5 | 74 |
| ztomb3 | Tomb campaign | 777 | 77 | 4 | 17 | 3 | 95 |
| ztomb4 | Tomb campaign | 471 | 55 | 4 | 9 | 1 | 17 |
| zboss | Finale campaign | 270 | 46 | 4 | 8 | 0 | 1 |
| zdm1 | Deathmatch arena | 727 | 44 | 0 | 13 | 0 | 0 |
| zdm2 | Deathmatch arena | 464 | 48 | 0 | 10 | 0 | 0 |
| zdm3 | Deathmatch arena | 674 | 53 | 0 | 12 | 0 | 0 |
| zdm4 | Deathmatch arena | 403 | 42 | 0 | 10 | 0 | 0 |
| zdm5 | Deathmatch arena | 533 | 48 | 0 | 11 | 0 | 0 |
| zdm6 | Deathmatch arena | 710 | 48 | 0 | 16 | 0 | 0 |
| **Total** |  | **14,933** | **132 distinct globally** | **121** | **230** | **30** | **914 records** |

## Progress and dependencies

NOT TESTED means no compatible runtime evidence exists for that cell. It must
not be interpreted as failing or passing. HISTORICAL V1 ONLY records an
otherwise useful pre-v2 observation, not a current harness result and not
playability: it does not prove window-safe launch, entity closure, objectives,
combat, saves, transitions, or completion. Completion requires both supported
fresh starts and intended inbound campaign state.

**Window-protocol boundary:** every retained runtime report named below was
produced by the legacy v1 single-stage launcher, which supplied `game`/`map`
before observing its window. It remains evidence only for the explicitly
described registry/resource result and does not satisfy the current v2
window-before-mod/map safety gate. Rerun each cited smoke before using it as
post-rule launch, presentation, or release evidence.

| Map | Planned phase | Notable Zaero dependencies | Historical v1 sample only | SP completion | Co-op completion | DM smoke | Save/transition evidence |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| zbase1 | 5 | Handler; crate/seat; four cameras; rotating objects; all major player systems; start cinematics/help | HISTORICAL V1 ONLY¹ | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zbase2 | 5 | Two Handlers; comm dish; four cameras; Visor flow/help | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zdef1 | 6 | Four Hounds; five Sentiens; six cameras; accelerating laser rotation; mteam/mirror metadata/help | HISTORICAL V1 ONLY³ | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zdef2 | 6 | Four Autocannons; three Sentiens; rotating objects; medium crate; six cameras | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zdef3 | 6 | Two Autocannons; six cameras; active machinery; toggle push | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zdef4 | 6 | Three Autocannons; six Sentiens; Landing key; medium crate; five cameras | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zwaste1 | 6 | Two Autocannons; seven Hounds; three Sentiens; rotating object; schooling/team; nine cameras | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zwaste2 | 6 | Autocannon; two Handlers; four Sentiens; crate; nine cameras | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zwaste3 | 6 | Two Handlers; four Sentiens; schooling/team; nine cameras | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| ztomb1 | 6 | Seven Hounds; five Sentiens; Energy/Lava/Slime keys; five cameras; D-011 preserved inert tomb1 artifact | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| ztomb2 | 6 | Autocannon; Slime key; random timer; rotating object; seven cameras | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| ztomb3 | 6 | Two floor Autocannons; two Hounds; two map IREDs; Energy key; six cameras | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| ztomb4 | 6 | Sentien; Barrier; Lava key; random timer | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zboss | 7 | Static positive-health inbound reset; ZBoss five targets, grapple, pain/EMP cooldown branches and death barrage; static five-second white fade and exact outro/victory handoff | HISTORICAL V1 ONLY² | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zdm1 | 8 | Full custom item set; seven cameras/Visor | HISTORICAL V1 ONLY⁵ | N/A | N/A | HISTORICAL V1 ONLY⁵ | NOT TESTED |
| zdm2 | 8 | Full custom item set; seven cameras/Visor | NOT TESTED | N/A | N/A | NOT TESTED | NOT TESTED |
| zdm3 | 8 | Full custom item set; nine cameras/Visor | NOT TESTED | N/A | N/A | NOT TESTED | NOT TESTED |
| zdm4 | 8 | Full custom item set; three cameras/Visor; rotating objects | NOT TESTED | N/A | N/A | NOT TESTED | NOT TESTED |
| zdm5 | 8 | Custom set without placed A2K; five cameras/Visor | NOT TESTED | N/A | N/A | NOT TESTED | NOT TESTED |
| zdm6 | 8 | Full custom item set; six cameras/Visor; random timer; four accelerating fans and toggle pushes | HISTORICAL V1 ONLY⁴ | N/A | N/A | NOT TESTED | NOT TESTED |

¹ The 2026-07-14 private-local **legacy v1** report
`.install/runtime-reports/zbase1-load-spawn.json` (SHA-256
`b9425f38ecd2f394a1470afa16e4c4acda507e1cb693ff3d75a8effa7bc0e129`)
validates against the [runtime-smoke schema](../provenance/schemas/runtime-smoke.schema.json).
The [harness](../../tools/run_game.ps1) observed a captioned, non-popup native
868×517 window, never observed a non-windowed visible window, loaded Debug DLL
SHA-256 `46949bcb3d9a282823b3af90f268a5786be47bc33a0ad161aaa838cc5d5e9fb7`,
spawned `zbase1`, entered a local client, shut down, and left no game process.
The session contains no missing-spawn log, closing the direct Handler registry/
resource load for this map only. It does not exercise separation, combat,
counts, saves, objectives, progression, or playability. The report is kept out
of Git because it records developer-machine paths and local runtime evidence.
The companion 2026-07-15 D-015 Release **legacy v1** report
`.install/runtime-reports/zbase1-release-surface-smoke.json` (SHA-256
`b0ca47bc40779ef6e4ee83cf3e656c20f51f97ab9dec8988abb514a9ab8c7bd4`)
loads audited Release DLL SHA-256
`273ac734dc2ee0199e1aa88bd745d657b53c2e181419e13fd0cbaf7af2cf2fc0`,
spawns the same map, reaches native client begin, and shuts down under the
hardened captioned/non-popup window guard. It closes Release-surface runtime
containment only and does not advance any gameplay column.

² The latest 2026-07-14 private-local **legacy v1** report
`.install/runtime-reports/zboss-load-spawn.json` (SHA-256
`8d54af97247ea4103b9a9779c4321f26cac14c91c63062be38ae2f3824d311e2`)
validates against the same schema. The harness observed a captioned, non-popup
868×517 native window, never observed a non-windowed visible window, loaded
Debug DLL SHA-256
`76fef999de68bbcc0b3a5221ec0a013ca222fe24face169624d642431a517488`,
resolved the single `monster_zboss` and all five `target_zboss_target`
placements with zero fatal matches, entered a local client, shut down, and left
no process. This closes sampled registry/resource loading only: no attack,
marker use, damage, grapple, EMP, save, death target, finale, or completion
status is advanced.

³ The 2026-07-14 private-local **legacy v1** report
`.install/runtime-reports/zdef1-load-spawn.json` (SHA-256
`175ffae612738cb3983defe29e019002179b041d1267880160f65d9f7f336dfc`)
validates against the same schema. The harness observed a captioned, non-popup
868×517 native window, never observed a non-windowed visible window, loaded the
Debug DLL with SHA-256
`ef9b397b0fef3cfb97b96ef6bd705b9fdc8a11953f443e8447f6c935564e1f5a`,
spawned `zdef1`, entered a local client, shut down, and left no game process.
The session contains no missing-spawn log for any of the four Hounds or five
Sentiens. It proves direct Hound/Sentien registry and resource-load closure on
this map only, not combat, schooling, attacks, fend, `mteam`, save behavior,
progression, or playability.

⁴ The 2026-07-14 private-local **legacy v1** report `.install/runtime-reports/zdm6.json`
(SHA-256
`68ab47b74486949b81290252ee907e9e85e50526aca82cfdf985744aa0438d59`)
validates against the same schema. The harness observed a captioned, non-popup
868×517 native window, never observed a non-windowed visible window, loaded
Debug DLL SHA-256
`f4b7c260700ca92f46601fd01e1e800590b32573fb7a11dc47dab72f70d66732`,
spawned zdm6, emitted `Zaero map zdm6 requests unavailable CD track 1; using
silence.`, entered a local client, shut down, and left no process. This proves
the value-1 resolver/log and a bounded non-deathmatch load only. It does not
acoustically prove silence or test audible music, deathmatch, cameras, timers,
fans/pushes, combat, saves, transitions, or playability. The report is kept out
of Git because it records developer-machine paths and local runtime evidence.

⁵ The 2026-07-15 private-local **legacy v1** report
`.install/runtime-reports/zdm1-zdmflags0-placement.json` (SHA-256
`04d8a8461550cf3dca14e2fd59423cb49a94da7e56a75d5913fd48d1890f5a10`)
validates against the same schema. The harness started with `-window`, observed
an 868×517 captioned/non-popup native window and no non-windowed window,
loaded Debug DLL SHA-256
`8e9d7d5ce3dd389e2a38651335e5c428b857e956fe715f4e3de4b54392eceee2`,
spawned `zdm1` in deathmatch with `zdmflags 0`, entered one local client, and
shut down cleanly with no residual process. No “Zaero entities added” line was
emitted and the structured Debug probe recorded exactly zero automatic
placements, proving the full authored item set suppresses the pass. This is
only a one-client load/spawn and suppression result; it does not
prove item pickup/respawn, cameras, combat, spawn fairness, saves, timed play,
multiple clients, or map playability. The report remains ignored/private.

The private `zaereo_fixture_dm_partial` geometry fixture is deliberately not a
shipped-map row. `tools/make_dm_runtime_fixture.py` preserves the locally owned
`q2dm1` BSP geometry and substitutes only an ignored entity lump containing one
open and four real-solid-brush deathmatch starts. Its 2026-07-15 historical
legacy-v1 one-stage windowed report
(`.install/runtime-reports/zaereo-fixture-dm-partial.json`, SHA-256
`391a27d07c98308e838d3d5a309730827f504610bc79cad4048a5764f97b0f0d`)
records exactly four D-045 placements at set indices 0/2/4/6 and wrapped start
ordinals 1/6/11/16. It must be rerun under D-046 before it counts as current
runtime evidence. The fixture is historical injection-failure evidence, not
evidence that `q2dm1` or any Zaero map is playable. The generated BSP,
manifest, PAK, and report are ignored/private-local-only, and a normal managed
reinstall proved the fixture absent afterward.

The same private suite contains `zaereo_fixture_dm_m0` through `m7`, each with
one valid deathmatch start and exactly one Sonic/Sniper/Flare/IRED/A2K/Flares/
EMP/Shield member respectively. All eight 2026-07-15 schema-valid historical
legacy-v1 one-stage windowed reports record zero automatic placements and no
addition line. They must be rerun under D-046 before closing a runtime
precondition; they remain test fixtures, not shipped-map or
item-pickup/playability evidence. Their exact report hashes are recorded in
[D-045](decisions.md#d-045--zdmflags-and-deathmatch-item-injection).

## Campaign flow contract

The episode must start with this exact chain:

~~~text
*elogo.cin+intro.cin+zlogo.cin+zbase1
~~~

| Boundary | Required behavior | Current evidence |
| --- | --- | --- |
| Intro to Base | Logos and introduction enter zbase1; supported skipping cannot corrupt state | Map/config audit only |
| Base internal | zbase1 and zbase2 preserve named spawnpoints and carried state | Entity-flow audit only |
| Base to Defence | Unit boundary targets *zdef1 | Entity-flow audit only |
| Defence internal | zdef1–zdef4 hub routes and named spawnpoints remain exact | Entity-flow audit only |
| Defence to Wasteland | Unit boundary targets *zwaste1 | Entity-flow audit only |
| Wasteland internal | zwaste1–zwaste3 routes and named spawnpoints remain exact | Entity-flow audit only |
| Wasteland to Tomb | Unit boundary targets *ztomb1 | Entity-flow audit only |
| Tomb internal | ztomb1–ztomb4 routes and named spawnpoints remain exact | Entity-flow audit only |
| Preserved orphan | ztomb1 entity 522 names absent tomb1 but has no activation/other reference and no alternate callback | Deterministic 30-changelevel closure; preserved inert under D-011 |
| Tomb to Finale | Unit boundary targets *zboss | Entity-flow audit only |
| Finale | zboss hands off to outro.cin+victory.pcx and returns cleanly | Static typed white-fade/exact-chain implementation; live cinematic/victory/return untested |

Never silently repair a map target. D-011 proves the supplied tomb1 anomaly is
unreachable and preserves it exactly. Any supported map revision that adds a
`mainexit` reference or `tomb1` BSP must fail the current audit and reopen the
decision before a versioned FIX or new compatibility disposition is considered.

## Required validation per campaign map

For each campaign row, record evidence for:

1. fresh map start and every intended inbound transition/spawnpoint;
2. completion on skills 0, 1, 2, and 3 with carried episode state;
3. objectives/help, keys, secrets, monster/item counts, scripted targets,
   movers, sounds, and outbound transitions;
4. representative saves at entry, a stateful custom entity, a critical puzzle,
   and before/after exit;
5. two-player co-op, then the wider 3/4-player and split-screen matrix required
   by Phase 8;
6. every authored deathmatch start and a timed smoke session; and
7. zero unknown entities/fields, placeholders, mandatory missing assets, or
   four-times-fast decisions.

For each ZDM row, record 2/4/8-client or bot sessions, spawn safety, item
pickup/respawn/drop, Visor/cameras, MOD/kill messages, spectators, intermission,
rotation, save prohibition/behavior as applicable, and relevant zdmflags.

## Completion rule

A map moves from NOT TESTED only when the linked normalized runtime report
proves that exact column. A successful console map command is not completion.
The map is VERIFIED only when all requirements in the roadmap's map definition
of done pass and the report is reproducible from a clean staged package.

# Map compatibility matrix

- Scope: 14 campaign BSPs and six dedicated deathmatch BSPs
- Evidence: parsed effective pak0/pak2 entity lumps
- Audit date: 2026-07-13
- Runtime status: **no map has been verified in ZaeREo**

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

The worktree registry currently resolves 127/132 shipped classnames; the exact
reproduction command and five remaining names are recorded in the
[entity matrix](entity-matrix.md). Static contracts now also cover the
[Sniper Rifle](../../tests/compatibility/test_zaero_sniper.py),
[player/map IRED including ztomb3's two `misc_ired` entities](../../tests/compatibility/test_zaero_ired.py),
and the [EMP field/selective hook matrix](../../tests/compatibility/test_zaero_emp.py).
These reduce implementation risk but are not map evidence, so every row remains
NOT TESTED until a retained live load/completion/save result exists.

The completed source/BSP audit also adds map-backed Phase-3 backlog that is not
yet implemented: 11 bit-2 low-trigger `func_plat` entities across `zbase2`,
`zdef1`, `zdef2`, `zdef4`, `zdm1`, `zdm3`, `zdm4`, and `ztomb3`; 31
FALLFLOAT/mass-400 `misc_explobox` entities across `zbase1`, `zdef1`, `ztomb2`,
`zwaste2`, and `zwaste3`; and 12 of 32 rotating doors with missing or explicit
zero damage. Train/path evidence includes five nonzero per-corner speeds in
`zdef4`, 96 waiting path corners, and four teleport corners; no shipped corner
uses smooth bits 2/4 and no shipped train uses Zaero rotation bits 8/16/32/64.
These counts constrain MAP-009/MAP-017/MAP-019/MAP-020 and E-044–E-048 but do
not change any NOT TESTED map status.

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

NOT TESTED means no compatible runtime evidence exists. It must not be
interpreted as failing or passing. Completion requires both supported fresh
starts and intended inbound campaign state.

| Map | Planned phase | Notable Zaero dependencies | SP completion | Co-op completion | DM smoke | Save/transition evidence |
| --- | ---: | --- | --- | --- | --- | --- |
| zbase1 | 5 | Handler; crate/seat; four cameras; rotating objects; all major player systems; start cinematics/help | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zbase2 | 5 | Two Handlers; comm dish; four cameras; Visor flow/help | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zdef1 | 6 | Four Hounds; five Sentiens; six cameras; accelerating laser rotation; mteam/mirror metadata/help | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zdef2 | 6 | Four Autocannons; three Sentiens; rotating objects; medium crate; six cameras | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zdef3 | 6 | Two Autocannons; six cameras; active machinery; toggle push | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zdef4 | 6 | Three Autocannons; six Sentiens; Landing key; medium crate; five cameras | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zwaste1 | 6 | Two Autocannons; seven Hounds; three Sentiens; rotating object; schooling/team; nine cameras | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zwaste2 | 6 | Autocannon; two Handlers; four Sentiens; crate; nine cameras | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zwaste3 | 6 | Two Handlers; four Sentiens; schooling/team; nine cameras | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| ztomb1 | 6 | Seven Hounds; five Sentiens; Energy/Lava/Slime keys; five cameras; suspicious tomb1 target | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| ztomb2 | 6 | Autocannon; Slime key; random timer; rotating object; seven cameras | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| ztomb3 | 6 | Two floor Autocannons; two Hounds; two map IREDs; Energy key; six cameras | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| ztomb4 | 6 | Sentien; Barrier; Lava key; random timer | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zboss | 7 | Positive-health inbound inventory reset; ZBoss five targets, grapple, pain/EMP cooldown branches, death barrage, white fade, outro/victory | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED |
| zdm1 | 8 | Full custom item set; seven cameras/Visor | N/A | N/A | NOT TESTED | NOT TESTED |
| zdm2 | 8 | Full custom item set; seven cameras/Visor | N/A | N/A | NOT TESTED | NOT TESTED |
| zdm3 | 8 | Full custom item set; nine cameras/Visor | N/A | N/A | NOT TESTED | NOT TESTED |
| zdm4 | 8 | Full custom item set; three cameras/Visor; rotating objects | N/A | N/A | NOT TESTED | NOT TESTED |
| zdm5 | 8 | Custom set without placed A2K; five cameras/Visor | N/A | N/A | NOT TESTED | NOT TESTED |
| zdm6 | 8 | Full custom item set; six cameras/Visor; random timer; four accelerating fans and toggle pushes | N/A | N/A | NOT TESTED | NOT TESTED |

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
| Suspicious route | One ztomb1 changelevel names absent tomb1; test reachability before any data patch | Catalogued, unresolved |
| Tomb to Finale | Unit boundary targets *zboss | Entity-flow audit only |
| Finale | zboss hands off to outro.cin+victory.pcx and returns cleanly | Asset/entity audit only |

Never silently repair a map target. If the tomb1 anomaly is reachable and
blocks intended progress, document original behavior and ship any correction as
a versioned FIX with an explicit decision and regression test.

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

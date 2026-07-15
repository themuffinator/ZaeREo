# Zaero deathmatch item-injection audit

This audit identity-records the supplied source, verifies the port contract,
and joins it to the normalized retail BSP inventory.

## Result

- `zdmflags` remains a server-info cvar with default 0.
- Bit 1 disables Flare Gun compensation damage; bit 2 disables item injection.
  The port names both bits by their set-bit behavior and keeps values 1 and 2.
- The source order contains **8** items and each gets up to **4** starts, a **15°** sweep, and a **128-unit** `MASK_SHOT` trace.
- One existing member suppresses the whole automatic pass. Geometry failures
  after that gate do not roll back items already placed.
- The port hook is content activation on every map; it does not enable Zaero
  mapper semantics on stock/community maps.

## Supplied-map inventory

- **20** maps contain **230** deathmatch starts.
- All supplied maps already contain at least one member, so **0** are eligible for automatic injection.
- **6** maps omit at least one member but still suppress injection under the historical precondition.

| Map | Kind | DM starts | Present classnames | Item entities | Missing members |
| --- | --- | ---: | ---: | ---: | --- |
| `zbase1` | campaign | 7 | 8 | 9 | — |
| `zbase2` | campaign | 8 | 3 | 4 | `weapon_sniperrifle`, `weapon_flaregun`, `ammo_a2k`, `ammo_flares`, `ammo_plasmashield` |
| `zboss` | campaign | 8 | 5 | 5 | `weapon_soniccannon`, `weapon_sniperrifle`, `ammo_plasmashield` |
| `zdef1` | campaign | 12 | 8 | 16 | — |
| `zdef2` | campaign | 13 | 8 | 15 | — |
| `zdef3` | campaign | 19 | 8 | 17 | — |
| `zdef4` | campaign | 14 | 8 | 19 | — |
| `zdm1` | deathmatch | 13 | 8 | 15 | — |
| `zdm2` | deathmatch | 10 | 8 | 12 | — |
| `zdm3` | deathmatch | 12 | 8 | 13 | — |
| `zdm4` | deathmatch | 10 | 8 | 13 | — |
| `zdm5` | deathmatch | 11 | 7 | 12 | `ammo_a2k` |
| `zdm6` | deathmatch | 16 | 8 | 20 | — |
| `ztomb1` | campaign | 15 | 8 | 16 | — |
| `ztomb2` | campaign | 11 | 8 | 21 | — |
| `ztomb3` | campaign | 17 | 7 | 14 | `weapon_sniperrifle` |
| `ztomb4` | campaign | 9 | 6 | 9 | `weapon_sniperrifle`, `weapon_flaregun` |
| `zwaste1` | campaign | 8 | 7 | 11 | `ammo_plasmashield` |
| `zwaste2` | campaign | 9 | 8 | 16 | — |
| `zwaste3` | campaign | 8 | 8 | 22 | — |

Static/source and BSP-inventory evidence proves the compatibility surface and implementation shape. Private runtime evidence is maintained separately and now closes open stock placement, disabled/authored controls, and one deterministic real-brush partial-placement path. Eight private live controls also close every possible one-member suppression case. Item pickup/respawn, save/load, and multiplayer fixtures remain.

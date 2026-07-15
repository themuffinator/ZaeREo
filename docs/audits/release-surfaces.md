# D-015 Release-surface audit

This normalized source audit distinguishes legacy developer experiments from
shipped gameplay. It remains static evidence and does not embed a runtime report;
D-015 separately records the retained live Release smoke that closes Q-039/SYS-018.

## Result

- **15** supplied source/project files are identity-locked.
- The legacy project includes **7** debug/test modules and exposes **3** guarded commands only in its Debug configuration.
- `_SHANETEST` guards the animated-rocket path at **2** sites but is absent from both supplied build configurations.
- The ZBoss grapple renderer has **2** literal `#if 0` blocks; the selected source path uses `TE_MEDIC_CABLE_ATTACK`.
- The current port source and project contain zero forbidden legacy surfaces.
- Release DLL and ZIP validation is intentionally local so generated artifact
  hashes do not enter the checked-in normalized report.

## Supplied project definitions

| Configuration | Definitions |
| --- | --- |
| Debug | `WIN32`, `_DEBUG`, `_WINDOWS`, `_Z_TESTMODE` |
| Release | `WIN32`, `NDEBUG`, `_WINDOWS` |

## Current project definitions

| Configuration | Definitions | Forbidden present |
| --- | --- | --- |
| Debug|x64 | `KEX_Q2_GAME`, `KEX_Q2GAME_EXPORTS`, `NO_FMT_SOURCE`, `KEX_Q2GAME_DYNAMIC`, `_CRT_SECURE_NO_WARNINGS`, `_DEBUG`, `_CONSOLE` | none |
| Release|x64 | `KEX_Q2_GAME`, `KEX_Q2GAME_EXPORTS`, `NO_FMT_SOURCE`, `KEX_Q2GAME_DYNAMIC`, `_CRT_SECURE_NO_WARNINGS`, `NDEBUG`, `_CONSOLE` | none |

## Production deny contracts

- Source tokens: **11** binary-safe signatures plus the broader source-only symbol list in the policy.
- Archive member basenames: **14**.
- Binary member suffixes scanned inside archives: `.dll`.
- Runtime PAK member suffixes scanned inside archives: `.pak`.
- `TE_GRAPPLE_CABLE` is denied only in the Zaero ZBoss implementation; native
  Rerelease protocol declarations and CTF use remain allowed.

## Runtime evidence boundary

Produced Release DLL/package validation remains local generated evidence.
D-015 separately links the retained windowed Release DLL-load/map-spawn/
client-entry/shutdown report. This static gate does not embed that live proof.

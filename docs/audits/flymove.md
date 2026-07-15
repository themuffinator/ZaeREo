# Q-048 SV_FlyMove plane-resolution audit

This identity-locked audit isolates Zaero's one-line global plane-comparison
change and compares it with the Rerelease shared step-slide solver.

## Source result

- Legacy Quake II suppresses exact duplicate-plane comparisons while testing
  a clipped candidate; Zaero removes only that suppression condition.
- The change is inside global `SV_FlyMove`, so it affects Step, FallFloat, and
  direct fly-strafe callers rather than a Zaero-only entity type.
- Rerelease instead rejects accumulated planes whose normal dot product is above **0.99**, nudges on repeat contact, and clips with **1.01** overbounce.
- The current port keeps the Rerelease `SV_FlyMove` function exact and
  `PM_StepSlideMove_Generic` byte-for-byte unchanged.
- That helper is shared by server entities, ordinary player step-slide, and
  special/water-jump movement; a global Zaero transplant would alter native
  players and expansion entities.

## Executable float32 goldens

| Case | Role | Legacy final | Zaero final | Rerelease final | Native duplicate skips |
| --- | --- | --- | --- | --- | ---: |
| `open-control` | unobstructed control | `[100.0, 20.0, 0.0]` | `[100.0, 20.0, 0.0]` | `[100.0, 20.0, 0.0]` | 0 |
| `wall-slide` | single axial wall | `[0.0, 20.0, 0.0]` | `[0.0, 20.0, 0.0]` | `[-1.0, 20.0, 0.0]` | 0 |
| `corner-crease` | perpendicular corner | `[0.0, 0.0, 20.0]` | `[0.0, 0.0, 20.0]` | `[0.0, -1.0, 20.0]` | 0 |
| `stair-riser-floor` | vertical riser plus floor | `[0.0, 25.0, 0.0]` | `[0.0, 25.0, 0.0]` | `[0.0, 25.0, 0.5]` | 0 |
| `three-plane-wedge` | three unique blocking planes | `[0.0, 0.0, 0.0]` | `[0.0, 0.0, 0.0]` | `[0.0, 0.0, 0.0]` | 0 |
| `projectile-duplicate-plane` | fraction-zero repeat on an exact non-axial plane | `[305.685394, -6.345245, -216.150848]` | `[0.0, 0.0, 0.0]` | `[305.079346, -9.296173, -216.921295]` | 1 |
| `monster-near-duplicate-plane` | two nearly parallel curved-surface contacts | `[0.0, 45.0, 10.0]` | `[0.0, 45.0, 10.0]` | `[-1.199997, 45.0, 10.0]` | 1 |

Only **1** of the **7** cases distinguishes the two legacy algorithms: an exact repeated non-axial plane produces a small negative float32 residual. Legacy skips that duplicate comparison and continues sliding; Zaero tests it and dead-stops. Rerelease recognizes the repeated plane through its native near-duplicate gate.

## D-044 disposition

Retain the unmodified Rerelease shared step-slide helper for stock, expansion, FallFloat, and Hover callers; do not import the one-line global Zaero plane-comparison removal.

These are deterministic float32 plane-resolution goldens, not live BSP trace captures. Windowed corner/wedge/stair/projectile/monster fixtures remain before Q-048 is verified.

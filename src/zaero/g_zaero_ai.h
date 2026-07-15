#pragma once

struct edict_t;

// Zaero's Hover projectile dodge uses a dedicated three-dimensional strafe
// state. The begin helper selects the legacy roll direction; the run helper
// owns its typed deadline and returns true when it consumed this AI frame.
void Zaero_BeginHoverFlyStrafe(edict_t *self);
bool Zaero_RunFlyStrafe(edict_t *self, float distance);

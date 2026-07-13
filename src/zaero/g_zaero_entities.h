// SPDX-License-Identifier: GPL-2.0-only
#pragma once

struct edict_t;

// Intentional legacy compatibility no-ops.
void SP_sound_echo(edict_t *self);
void SP_load_mirrorlevel(edict_t *self);

// Mapper-facing Zaero entities.
void SP_trigger_laser(edict_t *self);
void SP_misc_commdish(edict_t *self);
void SP_misc_securitycamera(edict_t *self);
void SP_misc_crate(edict_t *self);
void SP_misc_crate_medium(edict_t *self);
void SP_misc_crate_small(edict_t *self);
void SP_func_barrier(edict_t *self);
void SP_misc_seat(edict_t *self);

// Used by Zaero weapon traces to distinguish a barrier obstruction from an
// ordinary line-of-sight obstruction.
bool Zaero_TraceThroughBarrier(edict_t *target, edict_t *inflictor);

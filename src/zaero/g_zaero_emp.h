// SPDX-License-Identifier: GPL-2.0-only
#pragma once

struct edict_t;
struct vec3_t;

// Deploy the supplied Zaero EMP field.  The boss uses the same entry point as
// the player item, but may supply a different center or radius.
edict_t *Zaero_FireEMPNuke(edict_t *owner, const vec3_t &center, int radius);

// Pure legacy-shaped field query.  This signature is intentionally compatible
// with zaero_sonic_emp_check_t / Zaero_SetSonicEMPCheck.
bool Zaero_EMPNukeCheck(edict_t *subject, const vec3_t &position);

// Shared response for the explicit legacy call-site matrix.  EMP does not
// globally disable every attack; callers must query only the systems that the
// supplied source queried.
void Zaero_PlayEMPMisfire(edict_t *subject);

// ammo_empnuke's use-as-weapon callback.
void Weapon_ZaeroEMPNuke(edict_t *ent);

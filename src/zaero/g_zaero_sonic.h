// SPDX-License-Identifier: GPL-2.0-only
#pragma once

struct edict_t;
struct vec3_t;

// EMP support is owned by the EMP Nuke implementation. Register its query
// once during game initialization; a null query means no active EMP system.
// The query receives the legacy arguments (subject and sample position).
using zaero_sonic_emp_check_t = bool (*)(edict_t *subject, const vec3_t &origin);
void Zaero_SetSonicEMPCheck(zaero_sonic_emp_check_t check);

void Weapon_ZaeroSonicCannon(edict_t *ent);

// SPDX-License-Identifier: GPL-2.0-only
#pragma once

#include <cstdint>

struct edict_t;
struct gtime_t;
struct vec3_t;

// EMP support is owned by the EMP Nuke implementation. The supplied Zaero
// code asks EMPNukeCheck before each laser trace, so the integration layer
// installs the eventual EMP query here without coupling the two weapons.
using zaero_ired_emp_check_t = bool (*)(edict_t *subject, const vec3_t &origin);
void Zaero_SetIREDEMPCheck(zaero_ired_emp_check_t check);

// Player weapon and mapper-facing spawn entry points.
void Weapon_ZaeroIRED(edict_t *ent);
void SP_misc_ired(edict_t *self);

// Shared deployment entry point. Returns false unless the trace reaches the
// world within the legacy 64-unit placement distance.
bool Zaero_FireIRED(edict_t *owner, const vec3_t &start, const vec3_t &direction,
	                   gtime_t arm_delay, int32_t damage, float damage_radius);

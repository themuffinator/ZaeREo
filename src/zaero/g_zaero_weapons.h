// SPDX-License-Identifier: GPL-2.0-only
#pragma once

struct edict_t;
struct gitem_t;
struct vec3_t;

// Fully ported Zaero weapons.
void Weapon_ZaeroPush(edict_t *ent);
void Weapon_ZaeroFlareGun(edict_t *ent);

// Shared legacy flare projectile. ZBoss uses different launch speed/damage
// metadata from the player weapon while retaining the same flash lifecycle.
edict_t *Zaero_FireFlare(edict_t *self, const vec3_t &start, const vec3_t &dir,
	int damage, int speed, float damage_radius, int radius_damage);

// Zaero's client-fired projectile dodge trace and its independent two-stage
// skill throttle. Call only from source-authoritative projectile call sites;
// the helper also gates itself to Zaero maps and client owners.
void Zaero_CheckProjectileDodge(edict_t *self, const vec3_t &start,
	const vec3_t &dir, int speed);

// Shared flare presentation/AI state updates. Values stored on clients and
// monsters are expressed in legacy 10 Hz ticks and are time-scaled here.
void Zaero_AddFlareBlend(edict_t *ent);
void Zaero_UpdateMonsterFlareFlash(edict_t *ent);
bool Zaero_MonsterMoveAwayFromFlare(edict_t *ent, float distance);

// Explicit development placeholders. These keep the exact mapper/item ABI
// live without silently substituting an unrelated stock weapon or consuming
// inventory before each dedicated implementation lands.

// SPDX-License-Identifier: GPL-2.0-only
#pragma once

struct edict_t;
struct gitem_t;

// Fully ported Zaero weapons.
void Weapon_ZaeroPush(edict_t *ent);
void Weapon_ZaeroFlareGun(edict_t *ent);

// Shared flare presentation/AI state updates. Values stored on clients and
// monsters are expressed in legacy 10 Hz ticks and are time-scaled here.
void Zaero_AddFlareBlend(edict_t *ent);
void Zaero_UpdateMonsterFlareFlash(edict_t *ent);
bool Zaero_MonsterMoveAwayFromFlare(edict_t *ent, float distance);

// Explicit development placeholders. These keep the exact mapper/item ABI
// live without silently substituting an unrelated stock weapon or consuming
// inventory before each dedicated implementation lands.
void Weapon_ZaeroA2KPending(edict_t *ent);
void Use_ZaeroVisorPending(edict_t *ent, gitem_t *item);
void Use_ZaeroPlasmaShieldPending(edict_t *ent, gitem_t *item);

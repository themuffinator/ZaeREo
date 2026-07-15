// SPDX-License-Identifier: GPL-2.0-only
#pragma once

struct edict_t;
struct gitem_t;

// ammo_plasmashield's use callback. The deployed entity deliberately has no
// gameplay owner: owner projectiles must still collide with it.
void Use_ZaeroPlasmaShield(edict_t *ent, gitem_t *item);

// Recognize and apply the supplied PlasmaShield-only power-armor formula.
// A true return means the entity was a Zaero PlasmaShield, even when rounding
// produced zero absorption; save receives the amount removed from this hit.
bool Zaero_PlasmaShieldCheckPowerArmor(edict_t *ent, int damage, int &save);

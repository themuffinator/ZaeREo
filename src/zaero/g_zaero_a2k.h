// SPDX-License-Identifier: GPL-2.0-only
#pragma once

struct edict_t;

// Armageddon 2000 weapon and native integration hooks. The countdown is an
// absolute typed time stored per client; no helper entity exists before the
// exact detonation boundary.
void Weapon_ZaeroA2K(edict_t *ent);
bool Zaero_A2KProtects(const edict_t *ent);
bool Zaero_A2KSetTimerStats(edict_t *ent);
void Zaero_A2KClearClientState(edict_t *ent);

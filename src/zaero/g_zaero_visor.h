// SPDX-License-Identifier: GPL-2.0-only
#pragma once

struct edict_t;
struct gitem_t;

// Inventory and active camera lifecycle.
bool Pickup_ZaeroVisor(edict_t *ent, edict_t *other);
void Drop_ZaeroVisor(edict_t *ent, gitem_t *item);
void Use_ZaeroVisor(edict_t *ent, gitem_t *item);

// Native grant/reset and inventory-clear integration points.
void Zaero_VisorSetDefaultDuration(edict_t *ent);
void Zaero_VisorClearDurationIfUnowned(edict_t *ent);

// Per-client Rerelease integration. The active view leaves the real player's
// collision and movetype untouched while freezing only that client's pmove.
bool Zaero_VisorIsActive(const edict_t *ent);
bool Zaero_VisorClientThink(edict_t *ent);
void Zaero_VisorRunFrame(edict_t *ent);
void Zaero_VisorApplyView(edict_t *ent);
void Zaero_VisorApplyStatic(edict_t *ent);
void Zaero_VisorUpdateCopy(edict_t *ent);
void Zaero_VisorSetStats(edict_t *ent);
void Zaero_VisorStop(edict_t *ent, bool play_sound);

// Assign a bounded general configstring for the mapper-authored camera label.
void Zaero_VisorRegisterCameraMessage(edict_t *camera);

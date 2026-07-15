// SPDX-License-Identifier: GPL-2.0-only
#pragma once

struct edict_t;

void ZaeroHoundPrecache();
edict_t *ZaeroCreateHandlerHound(edict_t *handler);
void SP_monster_hound(edict_t *self);

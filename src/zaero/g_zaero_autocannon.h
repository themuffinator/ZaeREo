// SPDX-License-Identifier: GPL-2.0-only
#pragma once

struct edict_t;

// Multipart Zaero ceiling/floor defence entities. The floor entry point
// validates its narrower style range before sharing the common assembly.
void SP_monster_autocannon(edict_t *self);
void SP_monster_autocannon_floor(edict_t *self);


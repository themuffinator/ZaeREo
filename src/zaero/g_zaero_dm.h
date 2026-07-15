// SPDX-License-Identifier: GPL-2.0-only
#pragma once

#include <cstdint>

// Keep the public cvar and its numeric values compatible while naming both
// bits for what a set bit actually does. The supplied positive-sounding bit-2
// name was inverted: it suppresses, rather than enables, automatic injection.
enum zaero_dmflag_t : int32_t
{
	ZAERO_DMFLAG_DISABLE_FLARE_POLYBLEND_DAMAGE = 1 << 0,
	ZAERO_DMFLAG_DISABLE_ITEM_INJECTION = 1 << 1
};

// Add Zaero's eight-item deathmatch set to an otherwise Zaero-item-free map.
// This is content activation, not mapper-contract classification: stock and
// community maps are intentionally eligible while retaining native flags.
void Zaero_SpawnDeathmatchItems();

#if defined(_DEBUG)
// Emit the current map's recorded automatic placements and their post-drop
// native item state. This is a read-only private-runtime evidence surface and
// is deliberately absent from Release builds.
void Zaero_DebugDumpDeathmatchItems();
#endif

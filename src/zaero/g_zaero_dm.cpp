// SPDX-License-Identifier: GPL-2.0-only

#include "../g_local.h"
#include "g_zaero_dm.h"

namespace
{
constexpr const char *ZAERO_DEATHMATCH_ITEMS[] = {
	"weapon_soniccannon",
	"weapon_sniperrifle",
	"weapon_flaregun",
	"ammo_ired",
	"ammo_a2k",
	"ammo_flares",
	"ammo_empnuke",
	"ammo_plasmashield"
};
constexpr int32_t ZAERO_DEATHMATCH_ITEM_COUNT =
	static_cast<int32_t>(std::size(ZAERO_DEATHMATCH_ITEMS));

constexpr int32_t ZAERO_ITEM_PLACEMENT_ATTEMPTS = 4;
constexpr int32_t ZAERO_ITEM_ANGLE_STEP = 15;
constexpr float ZAERO_ITEM_PLACEMENT_RADIUS = 128.0f;
constexpr float ZAERO_ITEM_PLACEMENT_HEIGHT = 16.0f;

#if defined(_DEBUG)
struct zaero_dm_probe_placement_t
{
	int32_t item_index;
	int32_t spawn_ordinal;
	int32_t attempt;
	int32_t entity_number;
	int32_t entity_spawn_count;
	vec3_t start_origin;
	vec3_t placed_origin;
};

zaero_dm_probe_placement_t zaero_dm_probe_placements[ZAERO_DEATHMATCH_ITEM_COUNT];
int32_t zaero_dm_probe_placement_count;

void Zaero_ResetDeathmatchProbe()
{
	zaero_dm_probe_placement_count = 0;
}

void Zaero_RecordDeathmatchPlacement(int32_t item_index, int32_t spawn_ordinal,
	int32_t attempt, edict_t *ent, const vec3_t &start_origin,
	const vec3_t &placed_origin)
{
	if (zaero_dm_probe_placement_count >= ZAERO_DEATHMATCH_ITEM_COUNT)
		return;

	zaero_dm_probe_placement_t &placement =
		zaero_dm_probe_placements[zaero_dm_probe_placement_count++];
	placement.item_index = item_index;
	placement.spawn_ordinal = spawn_ordinal;
	placement.attempt = attempt;
	placement.entity_number = ent->s.number;
	placement.entity_spawn_count = ent->spawn_count;
	placement.start_origin = start_origin;
	placement.placed_origin = placed_origin;
}
#endif

// Preserve FindZSpawn's ordinal walk, including its wrap to the first start
// after reaching the end of the entity list. Placement attempts therefore
// continue through successive starts even when a map has fewer than 32.
edict_t *Zaero_FindDeathmatchSpawn(int32_t ordinal)
{
	edict_t *previous = nullptr;
	edict_t *spot = nullptr;

	while (ordinal)
	{
		spot = G_FindByString<&edict_t::classname>(previous, "info_player_deathmatch");
		if (spot)
			ordinal--;
		else if (!previous)
			return nullptr;

		previous = spot;
	}

	if (!spot)
		spot = G_FindByString<&edict_t::classname>(nullptr, "info_player_deathmatch");
	return spot;
}

bool Zaero_SpawnDeathmatchItem(gitem_t *item, edict_t *spot,
	int32_t item_index, int32_t spawn_ordinal, int32_t attempt)
{
	edict_t *ent = G_Spawn();
	ent->classname = item->classname;
	ent->mins = { -15, -15, -15 };
	ent->maxs = { 15, 15, 15 };
	ent->solid = SOLID_TRIGGER;
	ent->movetype = MOVETYPE_BOUNCE;
	ED_CallSpawn(ent);

	// Native modes such as instagib may reject pickups in SpawnItem. Preserve
	// that Rerelease rule without touching a freed/recycled entity.
	if (!ent->inuse)
		return false;

	const int32_t start_angle = irandom(360);
	vec3_t start = spot->s.origin;
	start[2] += ZAERO_ITEM_PLACEMENT_HEIGHT;

	for (int32_t angle = start_angle; angle < start_angle + 360;
		 angle += ZAERO_ITEM_ANGLE_STEP)
	{
		vec3_t angles = { 0, static_cast<float>(angle), 0 };
		vec3_t forward;
		AngleVectors(angles, forward, nullptr, nullptr);
		const vec3_t end = start + forward * ZAERO_ITEM_PLACEMENT_RADIUS;
		const trace_t trace = gi.trace(start, ent->mins, ent->maxs, end,
			nullptr, MASK_SHOT);
		if (trace.fraction < 1.0f)
			continue;

		ent->s.origin = end;
		// Map-parsed and dropped Rerelease items are IR-visible. Retain that native
		// presentation property for dynamically injected pickups as well.
		ent->s.renderfx |= RF_IR_VISIBLE;
		gi.linkentity(ent);
#if defined(_DEBUG)
		Zaero_RecordDeathmatchPlacement(item_index, spawn_ordinal, attempt, ent,
			spot->s.origin, end);
#endif
		return true;
	}

	G_FreeEdict(ent);
	return false;
}
} // namespace

void Zaero_SpawnDeathmatchItems()
{
#if defined(_DEBUG)
	Zaero_ResetDeathmatchProbe();
#endif
	if (!deathmatch->integer)
		return;
	if (zdmflags->integer & ZAERO_DMFLAG_DISABLE_ITEM_INJECTION)
		return;

	// The precondition is all-or-none: one live member of the set suppresses
	// every automatic addition. Individual geometry failures after this gate do
	// not roll back successful placements in the supplied implementation.
	for (const char *classname : ZAERO_DEATHMATCH_ITEMS)
		if (G_FindByString<&edict_t::classname>(nullptr, classname))
			return;

	int32_t added = 0;
	int32_t spawn_ordinal = 1;
	for (int32_t item_index = 0;
		 item_index < ZAERO_DEATHMATCH_ITEM_COUNT; item_index++)
	{
		const char *classname = ZAERO_DEATHMATCH_ITEMS[item_index];
		gitem_t *item = FindItemByClassname(classname);
		if (!item)
			continue;

		for (int32_t attempt = 0; attempt < ZAERO_ITEM_PLACEMENT_ATTEMPTS; attempt++)
		{
			const int32_t current_spawn_ordinal = spawn_ordinal++;
			edict_t *spot = Zaero_FindDeathmatchSpawn(current_spawn_ordinal);
			if (!spot)
				break;
			if (Zaero_SpawnDeathmatchItem(item, spot, item_index,
				current_spawn_ordinal, attempt + 1))
			{
				added++;
				break;
			}
		}
	}

	gi.Com_PrintFmt("{} Zaero entities added\n", added);
}

#if defined(_DEBUG)
void Zaero_DebugDumpDeathmatchItems()
{
	gi.Com_PrintFmt("ZAEREO_DM_PROBE_BEGIN recorded={}\n",
		zaero_dm_probe_placement_count);

	int32_t live_count = 0;
	for (int32_t i = 0; i < zaero_dm_probe_placement_count; i++)
	{
		const zaero_dm_probe_placement_t &placement = zaero_dm_probe_placements[i];
		edict_t *ent = nullptr;
		if (placement.entity_number > 0 &&
			static_cast<uint32_t>(placement.entity_number) < globals.num_edicts)
		{
			edict_t *candidate = &g_edicts[placement.entity_number];
			if (candidate->inuse &&
				candidate->spawn_count == placement.entity_spawn_count &&
				candidate->classname &&
				strcmp(candidate->classname,
					ZAERO_DEATHMATCH_ITEMS[placement.item_index]) == 0)
			{
				ent = candidate;
				live_count++;
			}
		}

		const vec3_t live_origin = ent ? ent->s.origin : vec3_origin;
		gi.Com_PrintFmt(
			"ZAEREO_DM_PROBE_ITEM index={} classname={} spawn={} attempt={} "
			"entity={} start={:.3f},{:.3f},{:.3f} placed={:.3f},{:.3f},{:.3f} "
			"live={} origin={:.3f},{:.3f},{:.3f} toss={} trigger={} touch={} "
			"ir={} grounded={}\n",
			placement.item_index,
			ZAERO_DEATHMATCH_ITEMS[placement.item_index],
			placement.spawn_ordinal,
			placement.attempt,
			placement.entity_number,
			placement.start_origin[0], placement.start_origin[1],
			placement.start_origin[2],
			placement.placed_origin[0], placement.placed_origin[1],
			placement.placed_origin[2],
			ent ? 1 : 0,
			live_origin[0], live_origin[1], live_origin[2],
			ent && ent->movetype == MOVETYPE_TOSS ? 1 : 0,
			ent && ent->solid == SOLID_TRIGGER ? 1 : 0,
			ent && ent->touch == Touch_Item ? 1 : 0,
			ent && (ent->s.renderfx & RF_IR_VISIBLE) ? 1 : 0,
			ent && ent->groundentity ? 1 : 0);
	}

	gi.Com_PrintFmt("ZAEREO_DM_PROBE_END recorded={} live={}\n",
		zaero_dm_probe_placement_count, live_count);
}
#endif

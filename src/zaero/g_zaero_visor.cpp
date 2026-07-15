// SPDX-License-Identifier: GPL-2.0-only

#include "../g_local.h"
#include "g_zaero_visor.h"

namespace
{
constexpr gtime_t ZAERO_VISOR_DEFAULT_DURATION = 30_sec;
constexpr gtime_t ZAERO_VISOR_STATIC_DURATION = 200_ms;
constexpr float ZAERO_VISOR_SWAY_PERIOD_SECONDS = 6.4f;
constexpr float ZAERO_VISOR_SWAY_DEGREES = 15.0f;
constexpr const char *ZAERO_VISOR_COPY_CLASSNAME = "VisorCopy";
constexpr const char *ZAERO_SECURITY_CAMERA_CLASSNAME = "misc_securitycamera";
constexpr const char *ZAERO_VISOR_ACTIVATE_SOUND = "items/visor/act.wav";
constexpr const char *ZAERO_VISOR_DEACTIVATE_SOUND = "items/visor/deact.wav";

bool Zaero_VisorEntityMatches(const edict_t *ent, int32_t spawn_count,
	const char *classname)
{
	return ent && ent->inuse && ent->spawn_count == spawn_count &&
		ent->classname && !Q_strcasecmp(ent->classname, classname);
}

edict_t *Zaero_VisorCamera(edict_t *ent)
{
	if (!ent || !ent->client ||
		!Zaero_VisorEntityMatches(ent->client->zaero_visor_camera,
			ent->client->zaero_visor_camera_spawn_count,
			ZAERO_SECURITY_CAMERA_CLASSNAME))
		return nullptr;

	return ent->client->zaero_visor_camera;
}

edict_t *Zaero_VisorCopy(edict_t *ent)
{
	if (!ent || !ent->client ||
		!Zaero_VisorEntityMatches(ent->client->zaero_visor_copy,
			ent->client->zaero_visor_copy_spawn_count,
			ZAERO_VISOR_COPY_CLASSNAME))
		return nullptr;

	edict_t *copy = ent->client->zaero_visor_copy;
	if (copy->owner != ent || copy->count != ent->spawn_count)
		return nullptr;

	return copy;
}

edict_t *Zaero_FindFirstActiveCamera()
{
	edict_t *camera = nullptr;
	while ((camera = G_FindByString<&edict_t::classname>(camera,
		ZAERO_SECURITY_CAMERA_CLASSNAME)) != nullptr)
		if (camera->active)
			return camera;

	return nullptr;
}

edict_t *Zaero_FindNextActiveCamera(edict_t *current)
{
	// The supplied source wraps an unbounded G_Find loop and hangs when every
	// camera is inactive. Two finite passes preserve wraparound while visiting
	// every other camera at most once.
	for (int32_t pass = 0; pass < 2; ++pass)
	{
		edict_t *camera = pass == 0 ? current : nullptr;
		while ((camera = G_FindByString<&edict_t::classname>(camera,
			ZAERO_SECURITY_CAMERA_CLASSNAME)) != nullptr)
		{
			if (camera == current)
				return nullptr;
			if (camera->active)
				return camera;
		}
	}

	return nullptr;
}

void Zaero_CopyPlayerPresentation(edict_t *player, edict_t *copy)
{
	copy->s.origin = player->s.origin;
	copy->s.old_origin = player->s.old_origin;
	copy->s.angles = player->s.angles;
	copy->s.modelindex = player->s.modelindex;
	copy->s.modelindex2 = player->s.modelindex2;
	copy->s.modelindex3 = player->s.modelindex3;
	copy->s.modelindex4 = player->s.modelindex4;
	copy->s.frame = player->s.frame;
	copy->s.skinnum = player->s.skinnum;
	copy->s.effects = player->s.effects;
	copy->s.renderfx = player->s.renderfx;
	copy->s.alpha = player->s.alpha;
	copy->s.scale = player->s.scale;
	copy->mins = player->mins;
	copy->maxs = player->maxs;
	gi.linkentity(copy);
}

edict_t *Zaero_CreateVisorCopy(edict_t *player)
{
	edict_t *copy = G_Spawn();
	copy->classname = ZAERO_VISOR_COPY_CLASSNAME;
	copy->owner = player;
	copy->count = player->spawn_count;
	copy->movetype = MOVETYPE_NONE;

	// D-021/Q-044: the real player remains solid and damageable. The visual
	// duplicate is deliberately non-blocking so identical overlapping hulls
	// cannot alternate trace ownership as their area-link order changes.
	copy->solid = SOLID_NOT;
	copy->takedamage = false;

	player->client->zaero_visor_copy = copy;
	player->client->zaero_visor_copy_spawn_count = copy->spawn_count;
	Zaero_CopyPlayerPresentation(player, copy);
	return copy;
}

void Zaero_VisorStartStatic(edict_t *ent)
{
	ent->client->zaero_visor_static_until = level.time + ZAERO_VISOR_STATIC_DURATION;
}

void Zaero_VisorSelectCamera(edict_t *ent, edict_t *camera, bool initial)
{
	if (initial)
	{
		ent->client->zaero_visor_saved_pm_type = ent->client->ps.pmove.pm_type;
		ent->client->zaero_visor_saved_fov = ent->client->ps.fov;
		ent->client->zaero_visor_saved_gunindex = ent->client->ps.gunindex;
		ent->client->zaero_visor_saved_gunskin = ent->client->ps.gunskin;
		ent->client->zaero_visor_saved_noclient =
			(ent->svflags & SVF_NOCLIENT) != 0;
		ent->client->zaero_visor_last_update = level.time;
		Zaero_CreateVisorCopy(ent);
		ent->svflags |= SVF_NOCLIENT;
	}

	ent->client->zaero_visor_camera = camera;
	ent->client->zaero_visor_camera_spawn_count = camera->spawn_count;
	Zaero_VisorStartStatic(ent);
	gi.sound(ent, CHAN_AUTO, gi.soundindex(ZAERO_VISOR_ACTIVATE_SOUND),
		1.0f, ATTN_NORM, 0.0f);
}
}

bool Pickup_ZaeroVisor(edict_t *ent, edict_t *other)
{
	if (!level.zaero_content_active || !ent || !ent->item || !other || !other->client)
		return false;

	auto &inventory = other->client->pers.inventory[ent->item->id];
	auto &remaining = other->client->pers.zaero_visor_remaining;

	// This exact equality is source-observable. A stacked duration above the
	// nominal maximum may pick up a fresh map item and be reset to 30 seconds.
	if (inventory == 1 && remaining == ZAERO_VISOR_DEFAULT_DURATION)
		return false;

	inventory = 1;
	if (ent->spawnflags.has(SPAWNFLAG_ITEM_DROPPED))
		remaining += ent->zaero_visor_remaining;
	else
		remaining = ZAERO_VISOR_DEFAULT_DURATION;

	if (deathmatch->integer && !ent->spawnflags.has(SPAWNFLAG_ITEM_DROPPED))
		SetRespawn(ent, ZAERO_VISOR_DEFAULT_DURATION);

	return true;
}

void Drop_ZaeroVisor(edict_t *ent, gitem_t *item)
{
	if (!level.zaero_content_active || !ent || !ent->client || !item)
		return;

	Zaero_VisorStop(ent, true);
	edict_t *dropped = Drop_Item(ent, item);
	// Preserve one transferable legacy item while using the Rerelease marker
	// required for correct cleanup with instanced co-op items.
	dropped->spawnflags |= SPAWNFLAG_ITEM_DROPPED_PLAYER;
	dropped->svflags &= ~SVF_INSTANCED;
	dropped->zaero_visor_remaining = ent->client->pers.zaero_visor_remaining;

	ent->client->pers.inventory[item->id] = 0;
	ent->client->pers.zaero_visor_remaining = 0_ms;
	ValidateSelectedItem(ent);
}

void Zaero_VisorSetDefaultDuration(edict_t *ent)
{
	if (!level.zaero_content_active || !ent || !ent->client)
		return;

	ent->client->pers.zaero_visor_remaining = ZAERO_VISOR_DEFAULT_DURATION;
}

void Zaero_VisorClearDurationIfUnowned(edict_t *ent)
{
	if (!level.zaero_content_active || !ent || !ent->client)
		return;

	if (ent->client->pers.inventory[IT_ITEM_VISOR] <= 0)
	{
		Zaero_VisorStop(ent, false);
		ent->client->pers.zaero_visor_remaining = 0_ms;
	}
}

void Use_ZaeroVisor(edict_t *ent, gitem_t *)
{
	if (!level.zaero_content_active || !ent || !ent->client)
		return;

	if (ent->client->zaero_visor_camera && !Zaero_VisorCamera(ent))
		Zaero_VisorStop(ent, false);

	if (edict_t *current = Zaero_VisorCamera(ent))
	{
		if (edict_t *next = Zaero_FindNextActiveCamera(current))
			Zaero_VisorSelectCamera(ent, next, false);
		return;
	}

	if (ent->client->pers.zaero_visor_remaining <= 0_ms)
	{
		gi.Client_Print(ent, PRINT_HIGH, "No time left for visor\n");
		return;
	}

	edict_t *camera = Zaero_FindFirstActiveCamera();
	if (!camera)
	{
		gi.Client_Print(ent, PRINT_HIGH, "No cameras are available\n");
		return;
	}

	Zaero_VisorSelectCamera(ent, camera, true);
}

bool Zaero_VisorIsActive(const edict_t *ent)
{
	return level.zaero_content_active && ent && ent->client &&
		ent->client->zaero_visor_camera != nullptr;
}

bool Zaero_VisorClientThink(edict_t *ent)
{
	if (!Zaero_VisorIsActive(ent))
		return false;

	if (!Zaero_VisorCamera(ent))
	{
		Zaero_VisorStop(ent, false);
		return false;
	}

	// Preserve ent->movetype verbatim. PM_FREEZE provides the intended input
	// lock without Q-007's unconditional MOVETYPE_WALK restoration defect.
	ent->client->ps.pmove.pm_type = PM_FREEZE;
	return true;
}

void Zaero_VisorRunFrame(edict_t *ent)
{
	if (!Zaero_VisorIsActive(ent))
		return;

	if (!Zaero_VisorCamera(ent))
	{
		Zaero_VisorStop(ent, false);
		return;
	}

	auto &last_update = ent->client->zaero_visor_last_update;
	if (last_update > level.time)
		last_update = level.time;
	if (last_update < level.time)
	{
		ent->client->pers.zaero_visor_remaining = max(0_ms,
			ent->client->pers.zaero_visor_remaining - (level.time - last_update));
		last_update = level.time;
	}

	if (ent->client->pers.zaero_visor_remaining > 0_ms)
		return;

	Zaero_VisorStop(ent, true);
	ent->client->pers.inventory[IT_ITEM_VISOR] = 0;
	ent->client->pers.zaero_visor_remaining = 0_ms;
	ValidateSelectedItem(ent);
}

void Zaero_VisorApplyView(edict_t *ent)
{
	edict_t *camera = Zaero_VisorCamera(ent);
	if (!camera)
		return;

	ent->client->ps.pmove.origin = camera->move_origin;
	ent->client->ps.viewoffset = {};
	ent->client->ps.viewangles = camera->move_angles;

	const float phase = fmodf(level.time.seconds(),
		ZAERO_VISOR_SWAY_PERIOD_SECONDS) /
		ZAERO_VISOR_SWAY_PERIOD_SECONDS;
	ent->client->ps.viewangles[YAW] +=
		sinf(phase * 2.0f * PIf) * ZAERO_VISOR_SWAY_DEGREES;
	ent->client->ps.gunindex = 0;
	ent->client->ps.gunskin = 0;
	ent->client->ps.fov = 90.0f;
}

void Zaero_VisorApplyStatic(edict_t *ent)
{
	if (Zaero_VisorIsActive(ent) &&
		ent->client->zaero_visor_static_until > level.time)
		G_AddBlend(1.0f, 1.0f, 1.0f, 1.0f,
			ent->client->ps.screen_blend);
}

void Zaero_VisorUpdateCopy(edict_t *ent)
{
	if (!Zaero_VisorCamera(ent))
		return;

	edict_t *copy = Zaero_VisorCopy(ent);
	if (!copy)
		copy = Zaero_CreateVisorCopy(ent);

	Zaero_CopyPlayerPresentation(ent, copy);
}

void Zaero_VisorSetStats(edict_t *ent)
{
	edict_t *camera = Zaero_VisorCamera(ent);
	if (!camera)
	{
		ent->client->ps.stats[STAT_ZAERO_CAMERA_ICON] = 0;
		ent->client->ps.stats[STAT_ZAERO_CAMERA_TIMER] = 0;
		ent->client->ps.stats[STAT_ZAERO_CAMERA_LABEL] = 0;
		return;
	}

	ent->client->ps.stats[STAT_ZAERO_CAMERA_ICON] = gi.imageindex("i_visor");
	ent->client->ps.stats[STAT_ZAERO_CAMERA_TIMER] =
		static_cast<int16_t>(max<int64_t>(0,
			ent->client->pers.zaero_visor_remaining.milliseconds() / 1000));
	ent->client->ps.stats[STAT_ZAERO_CAMERA_LABEL] = camera->sounds;
}

void Zaero_VisorStop(edict_t *ent, bool play_sound)
{
	if (!ent || !ent->client ||
		(!ent->client->zaero_visor_camera && !ent->client->zaero_visor_copy))
		return;

	if (edict_t *copy = Zaero_VisorCopy(ent))
		G_FreeEdict(copy);

	ent->client->zaero_visor_camera = nullptr;
	ent->client->zaero_visor_camera_spawn_count = 0;
	ent->client->zaero_visor_copy = nullptr;
	ent->client->zaero_visor_copy_spawn_count = 0;
	ent->client->zaero_visor_last_update = 0_ms;
	ent->client->zaero_visor_static_until = 0_ms;
	ent->client->ps.pmove.pm_type = ent->client->zaero_visor_saved_pm_type;
	ent->client->ps.fov = ent->client->zaero_visor_saved_fov;
	ent->client->ps.gunindex = ent->client->zaero_visor_saved_gunindex;
	ent->client->ps.gunskin = ent->client->zaero_visor_saved_gunskin;

	if (ent->client->zaero_visor_saved_noclient)
		ent->svflags |= SVF_NOCLIENT;
	else
		ent->svflags &= ~SVF_NOCLIENT;

	if (play_sound)
		gi.sound(ent, CHAN_AUTO, gi.soundindex(ZAERO_VISOR_DEACTIVATE_SOUND),
			1.0f, ATTN_NORM, 0.0f);
}

void Zaero_VisorRegisterCameraMessage(edict_t *camera)
{
	if (!camera || !camera->message)
		return;

	for (int32_t i = 0; i < MAX_ZAERO_CAMERA_MESSAGES; ++i)
	{
		const int32_t index = CONFIG_ZAERO_CAMERA_MESSAGE + i;
		const char *existing = gi.get_configstring(index);
		if (existing[0] && strcmp(existing, camera->message) != 0)
			continue;

		if (!existing[0])
			gi.configstring(index, camera->message);
		camera->sounds = index;
		return;
	}

	camera->sounds = 0;
	gi.Com_PrintFmt("misc_securitycamera message table exhausted on {}; label omitted.\n",
		level.mapname);
}

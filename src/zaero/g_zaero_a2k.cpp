// SPDX-License-Identifier: GPL-2.0-only

#include "../g_local.h"
#include "g_zaero_a2k.h"

namespace
{
constexpr gtime_t ZAERO_A2K_COUNTDOWN = 5_sec;
constexpr gtime_t ZAERO_A2K_EXPLOSION_TICK = 100_ms;
constexpr float ZAERO_A2K_DAMAGE = 2500.0f;
constexpr float ZAERO_A2K_INNER_RADIUS = 512.0f;
constexpr float ZAERO_A2K_OUTER_RADIUS_SCALE = 2.0f;
constexpr float ZAERO_A2K_QUAD_SCALE = 4.0f;
constexpr int32_t ZAERO_A2K_LAST_VISIBLE_FRAME = 5;

constexpr int32_t ZAERO_A2K_ACTIVATE_LAST = 9;
constexpr int32_t ZAERO_A2K_START_FRAME = 14;
constexpr int32_t ZAERO_A2K_HOLD_FRAME = 19;
constexpr int32_t ZAERO_A2K_FIRE_LAST = 19;
constexpr int32_t ZAERO_A2K_IDLE_LAST = 49;
constexpr int32_t ZAERO_A2K_DEACTIVATE_LAST = 55;

constexpr const char *ZAERO_A2K_EXPLOSION_CLASSNAME = "A2K Explosion";
constexpr const char *ZAERO_A2K_EXPLOSION_MODEL = "models/objects/b_explode/tris.md2";
constexpr const char *ZAERO_A2K_COUNTDOWN_SOUND = "weapons/a2k/countdn.wav";
constexpr const char *ZAERO_A2K_EXPLOSION_SOUND = "weapons/a2k/ak_exp01.wav";
constexpr const char *ZAERO_A2K_QUAD_SOUND = "items/damage3.wav";
constexpr const char *ZAERO_A2K_ICON = "w_a2k";

void Zaero_A2KPlayQuadSound(edict_t *ent)
{
	if (ent->client->quad_time > level.time)
		gi.sound(ent, CHAN_ITEM, gi.soundindex(ZAERO_A2K_QUAD_SOUND), 1.0f, ATTN_NORM, 0);
}

bool Zaero_A2KHasLineOfSight(edict_t *inflictor, edict_t *target)
{
	vec3_t start = inflictor->s.origin;
	start[2] += inflictor->viewheight;
	vec3_t end = target->s.origin;
	end[2] += target->viewheight;
	const trace_t trace = gi.traceline(start, end, inflictor, MASK_OPAQUE);
	return trace.fraction == 1.0f;
}

// Retain the legacy origin, bbox-center falloff, integer conversion,
// unnormalized direction, and damage point for both passes. Native
// T_RadiusDamage moves linked/BSP boundaries and is not equivalent here.
void Zaero_A2KRadiusDamage(edict_t *inflictor, edict_t *attacker, float damage,
	float radius, bool require_visible)
{
	edict_t *target = nullptr;
	while ((target = findradius(target, inflictor->s.origin, radius)) != nullptr)
	{
		if (!target->takedamage)
			continue;
		if (require_visible && !Zaero_A2KHasLineOfSight(inflictor, target))
			continue;

		const vec3_t target_center = target->s.origin + ((target->mins + target->maxs) * 0.5f);
		const float distance = (inflictor->s.origin - target_center).length();
		float points = damage - (0.5f * distance);
		if (target == attacker)
			points *= 0.5f;

		if (points > 0.0f && CanDamage(target, inflictor))
		{
			const vec3_t direction = target->s.origin - inflictor->s.origin;
			T_Damage(target, inflictor, attacker, direction, inflictor->s.origin,
				vec3_origin, static_cast<int32_t>(points), static_cast<int32_t>(points),
				DAMAGE_RADIUS, MOD_ZAERO_A2K);
		}
	}
}

THINK(Zaero_A2KExplosionThink) (edict_t *self) -> void
{
	self->s.frame++;
	self->s.skinnum++;

	if (self->s.frame > ZAERO_A2K_LAST_VISIBLE_FRAME)
	{
		G_FreeEdict(self);
		return;
	}

	self->nextthink = level.time + ZAERO_A2K_EXPLOSION_TICK;
}

void Zaero_A2KSpawnExplosion(edict_t *ent)
{
	edict_t *explosion = G_Spawn();
	explosion->classname = ZAERO_A2K_EXPLOSION_CLASSNAME;
	explosion->solid = SOLID_NOT;
	explosion->movetype = MOVETYPE_NONE;
	explosion->mins = vec3_origin;
	explosion->maxs = vec3_origin;
	explosion->s.origin = ent->s.origin;
	explosion->s.modelindex = gi.modelindex(ZAERO_A2K_EXPLOSION_MODEL);
	explosion->s.frame = 0;
	explosion->s.skinnum = 6;
	explosion->think = Zaero_A2KExplosionThink;
	explosion->nextthink = level.time + ZAERO_A2K_EXPLOSION_TICK;
	gi.linkentity(explosion);
	gi.positioned_sound(explosion->s.origin, explosion, CHAN_AUTO,
		gi.soundindex(ZAERO_A2K_EXPLOSION_SOUND), 1.0f, ATTN_NORM, 0);
}

void Zaero_A2KDetonate(edict_t *ent)
{
	// Clear first so self damage at the exact boundary is not absorbed by the
	// countdown protection.
	ent->client->zaero_a2k_detonate_time = 0_ms;
	ent->client->weapon_sound = 0;

	float damage = ZAERO_A2K_DAMAGE;
	float radius = ZAERO_A2K_INNER_RADIUS;
	Zaero_A2KPlayQuadSound(ent);
	if (ent->client->quad_time > level.time)
	{
		damage *= ZAERO_A2K_QUAD_SCALE;
		radius *= ZAERO_A2K_QUAD_SCALE;
	}

	// A qualifying target intentionally receives both independent hits.
	Zaero_A2KRadiusDamage(ent, ent, damage, radius, false);
	Zaero_A2KRadiusDamage(ent, ent, damage,
		radius * ZAERO_A2K_OUTER_RADIUS_SCALE, true);
	Zaero_A2KSpawnExplosion(ent);
}

void Zaero_A2KFireFrame(edict_t *ent)
{
	if (ent->client->ps.gunframe != ZAERO_A2K_START_FRAME)
		return;

	ent->client->zaero_a2k_detonate_time = level.time + ZAERO_A2K_COUNTDOWN;
	// Consumption is absolute in the supplied source, including infinite-ammo
	// modes. Weapon_Generic has already proved that one item is present.
	ent->client->pers.inventory[ent->client->pers.weapon->ammo]--;
	ent->client->ps.gunframe++;
	gi.sound(ent, CHAN_WEAPON, gi.soundindex(ZAERO_A2K_COUNTDOWN_SOUND),
		1.0f, ATTN_NORM, 0);
	Zaero_A2KPlayQuadSound(ent);
}
} // namespace

bool Zaero_A2KProtects(const edict_t *ent)
{
	return level.is_zaero && ent && ent->client &&
		ent->client->zaero_a2k_detonate_time > level.time;
}

bool Zaero_A2KSetTimerStats(edict_t *ent)
{
	if (!Zaero_A2KProtects(ent))
		return false;

	ent->client->ps.stats[STAT_TIMER_ICON] = gi.imageindex(ZAERO_A2K_ICON);
	// Legacy `(deadline - frame) / 10` truncates, so 4.9 seconds displays 4.
	ent->client->ps.stats[STAT_TIMER] = static_cast<int16_t>(
		(ent->client->zaero_a2k_detonate_time - level.time).milliseconds() / 1000);
	return true;
}

void Zaero_A2KClearClientState(edict_t *ent)
{
	if (!ent || !ent->client)
		return;

	ent->client->zaero_a2k_detonate_time = 0_ms;
	ent->client->weapon_sound = 0;
}

void Weapon_ZaeroA2K(edict_t *ent)
{
	static const int32_t pause_frames[] = {20, 30, 40, 0};
	static const int32_t fire_frames[] = {ZAERO_A2K_START_FRAME, ZAERO_A2K_HOLD_FRAME, 0};

	if (!level.is_zaero || !ent->client || ent->deadflag ||
		ent->s.modelindex != MODELINDEX_PLAYER)
	{
		return;
	}

	// The protocol's zero gunrate represents the legacy 10 Hz animation.
	ent->client->ps.gunrate = 0;

	if (ent->client->weaponstate == WEAPON_FIRING &&
		ent->client->ps.gunframe == ZAERO_A2K_HOLD_FRAME &&
		ent->client->zaero_a2k_detonate_time)
	{
		if (level.time < ent->client->zaero_a2k_detonate_time)
			return;

		Zaero_A2KDetonate(ent);
		// Leave frame 19 for native Weapon_Generic to advance to idle frame 20
		// and release WEAPON_FIRING without altering the exact boundary.
	}

	Weapon_Generic(ent, ZAERO_A2K_ACTIVATE_LAST, ZAERO_A2K_FIRE_LAST,
		ZAERO_A2K_IDLE_LAST, ZAERO_A2K_DEACTIVATE_LAST, pause_frames,
		fire_frames, Zaero_A2KFireFrame, false);
}

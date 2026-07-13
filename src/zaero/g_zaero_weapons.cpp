// SPDX-License-Identifier: GPL-2.0-only

#include "../g_local.h"
#include "g_zaero_weapons.h"

namespace
{
constexpr float ZAERO_PUSH_RANGE = 64.0f;
constexpr int32_t ZAERO_PUSH_DAMAGE = 2;
constexpr int32_t ZAERO_PUSH_KICK = 512;
constexpr int32_t ZAERO_PUSH_CONTACT_FRAME = 4;
constexpr int32_t ZAERO_PUSH_END_FRAME = 8;

constexpr int32_t ZAERO_FLARE_SPEED = 600;
// The supplied expression divides two integers. At the player speed of 600,
// the active lifetime is therefore 13 seconds, not 13 1/3 seconds.
constexpr int32_t ZAERO_FLARE_LIFETIME_DISTANCE = 8000;
constexpr float ZAERO_FLARE_FLASH_RANGE = 256.0f;
constexpr gtime_t ZAERO_FLARE_TICK = 100_ms;
constexpr gtime_t ZAERO_FLARE_IGNITION_DELAY = 1_sec;
constexpr gtime_t ZAERO_FLARE_BURNOUT_DELAY = 4_sec;
constexpr float ZAERO_REFERENCE_TICKS_PER_SECOND = 10.0f;
constexpr float ZAERO_PLAYER_FLASH_ADD = 25.0f;
constexpr float ZAERO_PLAYER_FLASH_MAX = 25.0f;
constexpr float ZAERO_PLAYER_FLASH_BASE = 30.0f;
constexpr float ZAERO_MONSTER_FLASH_ADD = 150.0f;
constexpr float ZAERO_MONSTER_FLASH_BASE = 50.0f;
constexpr int32_t ZAERO_FLARE_COMPENSATION_MAX_DAMAGE = 10;
constexpr int32_t ZDM_NO_GL_POLYBLEND_DAMAGE = 1 << 0;

constexpr const char *ZAERO_FLARE_MODEL = "models/objects/flare/tris.md2";
constexpr const char *ZAERO_FLARE_FIRE_SOUND = "weapons/flare/shoot.wav";
constexpr const char *ZAERO_FLARE_HISS_SOUND = "weapons/flare/flarehis.wav";
constexpr const char *ZAERO_PUSH_CONTACT_SOUND = "weapons/push/contact.wav";

bool Zaero_ClientUsesPolyblend(const edict_t *target)
{
	char value[16] = {};

	// Rerelease clients need not advertise the old renderer cvar. Legacy Zaero
	// defaulted it to one, so a missing/malformed value must not cause damage.
	if (!gi.Info_ValueForKey(target->client->pers.userinfo, "gl_polyblend", value, sizeof(value)) || !value[0])
		return true;

	return atoi(value) != 0;
}

void Zaero_ApplyFlareFlash(edict_t *flare)
{
	edict_t *target = nullptr;

	while ((target = findradius(target, flare->s.origin, ZAERO_FLARE_FLASH_RANGE)) != nullptr)
	{
		if (!target->client && !(target->svflags & SVF_MONSTER))
			continue;
		if (target->deadflag)
			continue;
		if (!visible(flare, target))
			continue;

		vec3_t delta = flare->s.origin - target->s.origin;
		const float distance = delta.normalize();
		float ratio = max(0.0f, 1.0f - (distance / ZAERO_FLARE_FLASH_RANGE));

		vec3_t target_forward;
		AngleVectors(target->s.angles, target_forward, nullptr, nullptr);
		ratio *= max(0.0f, delta.dot(target_forward));

		if (target->client)
		{
			const float added_ticks = static_cast<float>(static_cast<int32_t>(ratio * ZAERO_PLAYER_FLASH_ADD));
			target->client->zaero_flare_flash_ticks = min(
				ZAERO_PLAYER_FLASH_MAX,
				target->client->zaero_flare_flash_ticks + added_ticks);
			target->client->zaero_flare_flash_base = ZAERO_PLAYER_FLASH_BASE;

			if (deathmatch->integer &&
				!Zaero_ClientUsesPolyblend(target) &&
				!(zdmflags->integer & ZDM_NO_GL_POLYBLEND_DAMAGE))
			{
				const int32_t damage = static_cast<int32_t>(ZAERO_FLARE_COMPENSATION_MAX_DAMAGE * ratio);
				if (damage > 0)
				{
					edict_t *attacker = (flare->owner && flare->owner->inuse) ? flare->owner : flare;
					T_Damage(target, flare, attacker, vec3_origin, target->s.origin, vec3_origin,
						damage, 0, DAMAGE_NONE, MOD_ZAERO_GL_POLYBLEND);
				}
			}
		}
		else if (!target->classname || strcmp(target->classname, "monster_zboss"))
		{
			const float flash_ticks = static_cast<float>(static_cast<int32_t>(ratio * ZAERO_MONSTER_FLASH_ADD));
			target->monsterinfo.zaero_flare_flash_ticks = max(
				target->monsterinfo.zaero_flare_flash_ticks,
				flash_ticks);
			target->monsterinfo.zaero_flare_flash_base = ZAERO_MONSTER_FLASH_BASE;

			if (!target->enemy && flare->owner && flare->owner->inuse)
			{
				target->enemy = flare->owner;
				FoundTarget(target);
			}
		}
	}
}

THINK(Zaero_FlareThink) (edict_t *self) -> void
{
	if (level.time > self->timestamp)
	{
		self->s.effects &= ~EF_ROCKET;
		self->s.frame = 0;
		self->s.sound = 0;
		self->think = G_FreeEdict;
		self->nextthink = level.time + ZAERO_FLARE_BURNOUT_DELAY;
		return;
	}

	if (++self->s.frame > 14)
		self->s.frame = 5;

	self->s.sound = gi.soundindex(ZAERO_FLARE_HISS_SOUND);
	Zaero_ApplyFlareFlash(self);
	self->nextthink = level.time + ZAERO_FLARE_TICK;
}

edict_t *Zaero_FireFlare(edict_t *self, const vec3_t &start, const vec3_t &dir)
{
	vec3_t up;
	AngleVectors(vectoangles(dir), nullptr, nullptr, up);

	edict_t *flare = G_Spawn();
	flare->svflags |= SVF_PROJECTILE;
	flare->flags |= FL_DODGE;
	flare->s.origin = start;
	flare->s.old_origin = start;
	flare->movedir = dir;
	flare->s.angles = vectoangles(dir);
	flare->velocity = (dir * ZAERO_FLARE_SPEED) + (up * (200.0f + crandom_open() * 10.0f));
	flare->movetype = MOVETYPE_BOUNCE;
	flare->clipmask = MASK_PROJECTILE;
	if (self->client && !G_ShouldPlayersCollide(true))
		flare->clipmask &= ~CONTENTS_PLAYER;
	flare->solid = SOLID_BBOX;
	flare->mins = {-4, -4, -4};
	flare->maxs = {4, 4, 4};
	flare->s.effects = EF_ROCKET;
	flare->s.modelindex = gi.modelindex(ZAERO_FLARE_MODEL);
	flare->owner = self;
	flare->timestamp = level.time + gtime_t::from_sec(ZAERO_FLARE_LIFETIME_DISTANCE / ZAERO_FLARE_SPEED);
	flare->think = Zaero_FlareThink;
	flare->nextthink = level.time + ZAERO_FLARE_IGNITION_DELAY;
	flare->dmg = 1;
	flare->radius_dmg = 1;
	flare->dmg_radius = 1.0f;
	flare->classname = "flare";
	gi.linkentity(flare);
	return flare;
}

void Zaero_FlareGunFire(edict_t *ent)
{
	vec3_t start, forward;
	P_ProjectSource(ent, ent->client->v_angle, {8, 8, -8}, start, forward);
	Zaero_FireFlare(ent, start, forward);
	PlayerNoise(ent, start, PNOISE_WEAPON);

	G_RemoveAmmo(ent);

	const float volume = is_silenced ? 0.4f : 1.0f;
	gi.sound(ent, CHAN_VOICE, gi.soundindex(ZAERO_FLARE_FIRE_SOUND), volume, ATTN_NORM, 0);
}

bool Zaero_PushHit(edict_t *self, const vec3_t &start, const vec3_t &aim)
{
	const trace_t tr = gi.traceline(start, start + (aim * ZAERO_PUSH_RANGE), self, MASK_PROJECTILE);
	if (tr.fraction >= 1.0f || !tr.ent)
		return false;

	gi.sound(self, CHAN_WEAPON, gi.soundindex(ZAERO_PUSH_CONTACT_SOUND), 1, ATTN_NORM, 0);

	if ((tr.ent->svflags & SVF_MONSTER) || tr.ent->client)
	{
		vec3_t direction = (tr.ent->absmin + (tr.ent->size * 0.75f)) - start;
		direction.normalize();
		tr.ent->velocity += direction * ZAERO_PUSH_KICK;
		if (tr.ent->velocity.z > 0.0f)
			tr.ent->groundentity = nullptr;
	}
	else if (tr.ent->movetype == MOVETYPE_FALLFLOAT && tr.ent->touch)
	{
		const int32_t original_mass = tr.ent->mass;
		const int32_t original_spawn_count = tr.ent->spawn_count;
		tr.ent->mass = max(1, original_mass / 4);
		tr.ent->touch(tr.ent, self, tr, false);
		if (tr.ent->inuse && tr.ent->spawn_count == original_spawn_count)
			tr.ent->mass = original_mass;
	}

	if (!tr.ent->takedamage)
		return false;

	T_Damage(tr.ent, self, self, aim, tr.endpos, vec3_origin,
		ZAERO_PUSH_DAMAGE, ZAERO_PUSH_KICK / 2, DAMAGE_NO_KNOCKBACK, MOD_HIT);
	return true;
}

void Zaero_ReturnFromTransientWeapon(edict_t *ent)
{
	gitem_t *return_weapon = ent->client->pers.lastweapon;
	if (!return_weapon || return_weapon == ent->client->pers.weapon)
		return_weapon = GetItemByIndex(IT_WEAPON_BLASTER);

	gitem_t *previous_history = ent->client->zaero_transient_lastweapon;
	ent->client->newweapon = return_weapon;
	ChangeWeapon(ent);
	ent->client->pers.lastweapon = previous_history ? previous_history : return_weapon;
	ent->client->zaero_transient_lastweapon = nullptr;
}

void Zaero_PendingWeapon(edict_t *ent, const char *message)
{
	if (ent->client->ps.gunframe == 0)
		gi.Client_Print(ent, PRINT_HIGH, message);

	Zaero_ReturnFromTransientWeapon(ent);
}
} // namespace

void Weapon_ZaeroPush(edict_t *ent)
{
	if (ent->client->weapon_think_time > level.time)
		return;

	if (ent->client->ps.gunframe == ZAERO_PUSH_CONTACT_FRAME)
	{
		vec3_t forward;
		AngleVectors(ent->client->v_angle, forward, nullptr, nullptr);
		const vec3_t start = ent->s.origin + vec3_t{0, 0, ent->viewheight * 0.5f};
		Zaero_PushHit(ent, start, forward);
	}

	if (ent->client->ps.gunframe >= ZAERO_PUSH_END_FRAME)
	{
		Zaero_ReturnFromTransientWeapon(ent);
		return;
	}

	ent->client->ps.gunframe++;
	ent->client->weapon_think_time = level.time + ZAERO_FLARE_TICK;
}

void Weapon_ZaeroFlareGun(edict_t *ent)
{
	static const int pause_frames[] = {15, 25, 35, 0};
	static const int fire_frames[] = {8, 0};
	Weapon_Generic(ent, 5, 14, 44, 48, pause_frames, fire_frames, Zaero_FlareGunFire);
}

void Zaero_AddFlareBlend(edict_t *ent)
{
	if (ent->client->zaero_flare_flash_ticks <= 0.0f)
		return;

	const float base = max(1.0f, ent->client->zaero_flare_flash_base);
	G_AddBlend(1.0f, 1.0f, 1.0f,
		min(1.0f, ent->client->zaero_flare_flash_ticks / base),
		ent->client->ps.screen_blend);
	ent->client->zaero_flare_flash_ticks = max(0.0f,
		ent->client->zaero_flare_flash_ticks - (gi.frame_time_s * ZAERO_REFERENCE_TICKS_PER_SECOND));
}

void Zaero_UpdateMonsterFlareFlash(edict_t *ent)
{
	ent->monsterinfo.zaero_flare_flash_ticks = max(0.0f,
		ent->monsterinfo.zaero_flare_flash_ticks - (gi.frame_time_s * ZAERO_REFERENCE_TICKS_PER_SECOND));
}

bool Zaero_MonsterMoveAwayFromFlare(edict_t *ent, float distance)
{
	edict_t *flare = nullptr;
	while ((flare = findradius(flare, ent->s.origin, ZAERO_FLARE_FLASH_RANGE)) != nullptr)
		if (flare->classname && !Q_strcasecmp(flare->classname, "flare"))
			break;

	vec3_t goal;
	if (!flare)
	{
		vec3_t forward;
		AngleVectors(ent->s.angles, forward, nullptr, nullptr);
		goal = ent->s.origin + (forward * 128.0f);
	}
	else
	{
		vec3_t away = ent->s.origin - flare->s.origin;
		away.normalize();
		goal = ent->s.origin + (away * 128.0f);
	}

	// The supplied source's `rand() & 7 == 1` precedence means its ideal-yaw
	// assignment is never reached. Keep that observable quirk, but avoid the
	// throwaway temporary edict it used solely to hold this goal position.
	if (irandom(4) == 1 || !SV_StepDirection(ent, ent->ideal_yaw, distance, false))
		SV_NewChaseDir(ent, goal, distance);

	return true;
}

void Weapon_ZaeroA2KPending(edict_t *ent)
{
	Zaero_PendingWeapon(ent, "Zaero A2K behavior is not implemented yet.\n");
}

void Use_ZaeroVisorPending(edict_t *ent, gitem_t *)
{
	gi.Client_Print(ent, PRINT_HIGH, "Zaero Visor behavior is not implemented yet.\n");
}

void Use_ZaeroPlasmaShieldPending(edict_t *ent, gitem_t *)
{
	gi.Client_Print(ent, PRINT_HIGH, "Zaero Plasma Shield behavior is not implemented yet.\n");
}

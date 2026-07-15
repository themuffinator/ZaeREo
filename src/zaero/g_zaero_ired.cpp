// SPDX-License-Identifier: GPL-2.0-only

#include "../g_local.h"
#include "../m_player.h"
#include "g_zaero_ired.h"

namespace
{
constexpr gtime_t ZAERO_IRED_REFERENCE_TICK = 100_ms;
constexpr gtime_t ZAERO_IRED_ARM_DELAY = 1_sec;
constexpr gtime_t ZAERO_IRED_BEAM_TIMEOUT = 180_sec;
constexpr gtime_t ZAERO_IRED_GLOW_TIME = 200_ms;
constexpr float ZAERO_IRED_PLACEMENT_RANGE = 64.0f;
constexpr float ZAERO_IRED_WALL_OFFSET = 3.0f;
constexpr float ZAERO_IRED_BEAM_RANGE = 2048.0f;
constexpr float ZAERO_IRED_TRIGGER_EPSILON = 1.0f;
constexpr float ZAERO_IRED_PHASE_SKIP_CHANCE = 0.1f;
constexpr int32_t ZAERO_IRED_DAMAGE = 150;
constexpr float ZAERO_IRED_DAMAGE_RADIUS = 384.0f;
constexpr int32_t ZAERO_IRED_HEALTH = 1;
constexpr int32_t ZAERO_IRED_SHRAPNEL_COUNT = 5;
constexpr int32_t ZAERO_IRED_SHRAPNEL_DAMAGE = 15;
constexpr int32_t ZAERO_IRED_SHRAPNEL_KNOCKBACK = 8;
constexpr float ZAERO_IRED_SHRAPNEL_FORWARD_SPEED = 500.0f;
constexpr float ZAERO_IRED_SHRAPNEL_RANDOM_SPEED = 500.0f;
constexpr gtime_t ZAERO_IRED_SHRAPNEL_BASE_LIFETIME = 3_sec;
constexpr float ZAERO_IRED_SHRAPNEL_LIFETIME_VARIANCE_SECONDS = 1.5f;
constexpr int32_t ZAERO_IRED_MAX_DEPLOYED = 25;
constexpr int32_t ZAERO_IRED_INITIAL_SPARK_COUNT = 8;
constexpr int32_t ZAERO_IRED_BEAM_SKIN = static_cast<int32_t>(0xb0b1b2b3u);

constexpr int32_t ZAERO_IRED_ACTIVATE_LAST = 6;
constexpr int32_t ZAERO_IRED_FIRE_FIRST = 7;
constexpr int32_t ZAERO_IRED_PLACE_FRAME = 10;
constexpr int32_t ZAERO_IRED_RESTORE_MODEL_FRAME = 15;
constexpr int32_t ZAERO_IRED_IDLE_FIRST = 16;
constexpr int32_t ZAERO_IRED_READY_FRAME = 17;
constexpr int32_t ZAERO_IRED_IDLE_LAST = 43;
constexpr int32_t ZAERO_IRED_DEACTIVATE_FIRST = 44;
constexpr int32_t ZAERO_IRED_DEACTIVATE_LAST = 48;

constexpr spawnflags_t SPAWNFLAG_IRED_CHECK_BACK_WALL = 1_spawnflag;
constexpr spawnflags_t SPAWNFLAG_IRED_LASER_ON = 1_spawnflag;
constexpr spawnflags_t SPAWNFLAG_IRED_INITIAL_SPARKS = 0x80000000_spawnflag;

constexpr const char *ZAERO_IRED_DYNAMIC_CLASSNAME = "ired";
constexpr const char *ZAERO_IRED_MAP_CLASSNAME = "misc_ired";
constexpr const char *ZAERO_IRED_BEAM_CLASSNAME = "laser trip bomb laser";
constexpr const char *ZAERO_IRED_SHRAPNEL_CLASSNAME = "shrapnel";
constexpr const char *ZAERO_IRED_MODEL = "models/objects/ired/tris.md2";
constexpr const char *ZAERO_IRED_SHRAPNEL_MODEL = "models/objects/shrapnel/tris.md2";
constexpr const char *ZAERO_IRED_VIEW_MODEL = "models/weapons/v_ired/tris.md2";
constexpr const char *ZAERO_IRED_HAND_MODEL = "models/weapons/v_ired/hand.md2";
constexpr const char *ZAERO_IRED_SET_SOUND = "weapons/ired/las_set.wav";
constexpr const char *ZAERO_IRED_ARM_SOUND = "weapons/ired/las_arm.wav";
constexpr const char *ZAERO_QUAD_SOUND = "items/damage3.wav";

zaero_ired_emp_check_t zaero_ired_emp_check = nullptr;

bool Zaero_IREDHasClassname(const edict_t *entity, const char *classname)
{
	return entity && entity->classname && !Q_strcasecmp(entity->classname, classname);
}

bool Zaero_IREDIsBomb(const edict_t *entity)
{
	return Zaero_IREDHasClassname(entity, ZAERO_IRED_DYNAMIC_CLASSNAME) ||
		Zaero_IREDHasClassname(entity, ZAERO_IRED_MAP_CLASSNAME);
}

edict_t *Zaero_IREDValidatedOwner(edict_t *entity)
{
	if (entity->owner && entity->owner->inuse && entity->owner->spawn_count == entity->style)
		return entity->owner;
	return nullptr;
}

edict_t *Zaero_IREDValidatedBeam(edict_t *bomb)
{
	edict_t *beam = bomb->chain;
	if (beam && beam->inuse && beam->spawn_count == bomb->count &&
		Zaero_IREDHasClassname(beam, ZAERO_IRED_BEAM_CLASSNAME))
		return beam;

	// A save-restored pointer is resolved normally, while a freed/reused slot is
	// rejected by its saved generation. Never free an unrelated replacement.
	bomb->chain = nullptr;
	bomb->count = 0;
	return nullptr;
}

edict_t *Zaero_IREDValidatedBomb(edict_t *beam)
{
	edict_t *bomb = beam->chain;
	if (bomb && bomb->inuse && bomb->spawn_count == beam->count && Zaero_IREDIsBomb(bomb))
		return bomb;

	beam->chain = nullptr;
	beam->count = 0;
	return nullptr;
}

void Zaero_IREDDetachBeam(edict_t *bomb)
{
	edict_t *beam = Zaero_IREDValidatedBeam(bomb);
	bomb->chain = nullptr;
	bomb->count = 0;
	if (!beam)
		return;

	beam->chain = nullptr;
	beam->count = 0;
	beam->owner = nullptr;
	G_FreeEdict(beam);
}

TOUCH(Zaero_IREDShrapnelTouch) (edict_t *self, edict_t *other, const trace_t &tr,
	bool other_touching_self) -> void
{
	if (!other->takedamage || self->velocity == vec3_origin)
		return;

	edict_t *attacker = Zaero_IREDValidatedOwner(self);
	if (!attacker)
		attacker = self;
	T_Damage(other, self, attacker, self->velocity, self->s.origin, tr.plane.normal,
		ZAERO_IRED_SHRAPNEL_DAMAGE, ZAERO_IRED_SHRAPNEL_KNOCKBACK,
		DAMAGE_NONE, MOD_ZAERO_TRIPBOMB);
	G_FreeEdict(self);
}

THINK(Zaero_IREDExplode) (edict_t *self) -> void
{
	Zaero_IREDDetachBeam(self);

	edict_t *attacker = Zaero_IREDValidatedOwner(self);
	if (!attacker)
		attacker = self;
	T_RadiusDamage(self, attacker, static_cast<float>(self->dmg), self->enemy,
		self->dmg_radius, DAMAGE_NONE, MOD_ZAERO_TRIPBOMB);

	const vec3_t origin = self->s.origin + (self->velocity * -0.02f);
	gi.WriteByte(svc_temp_entity);
	if (self->waterlevel)
		gi.WriteByte(self->groundentity ? TE_GRENADE_EXPLOSION_WATER : TE_ROCKET_EXPLOSION_WATER);
	else
		gi.WriteByte(self->groundentity ? TE_GRENADE_EXPLOSION : TE_ROCKET_EXPLOSION);
	gi.WritePosition(origin);
	gi.multicast(self->s.origin, MULTICAST_PHS, false);

	for (int32_t i = 0; i < ZAERO_IRED_SHRAPNEL_COUNT; ++i)
	{
		angle_vectors_t axes = AngleVectors(self->s.angles);
		edict_t *shrapnel = G_Spawn();
		shrapnel->classname = ZAERO_IRED_SHRAPNEL_CLASSNAME;
		shrapnel->movetype = MOVETYPE_BOUNCE;
		shrapnel->solid = SOLID_BBOX;
		// The bot bridge consumes FL_TRAP for transient danger metadata.  Keep
		// the legacy unlinked/spawn-on-first-physics-step behavior below intact.
		shrapnel->flags |= FL_TRAP;
		shrapnel->s.effects |= EF_GRENADE;
		shrapnel->s.modelindex = gi.modelindex(ZAERO_IRED_SHRAPNEL_MODEL);
		shrapnel->owner = Zaero_IREDValidatedOwner(self);
		if (!shrapnel->owner)
			shrapnel->owner = shrapnel;
		shrapnel->style = shrapnel->owner->spawn_count;
		shrapnel->avelocity = {300.0f, 300.0f, 300.0f};
		shrapnel->s.origin = self->s.origin;
		shrapnel->velocity = (axes.forward * ZAERO_IRED_SHRAPNEL_FORWARD_SPEED) +
			(axes.right * (crandom() * ZAERO_IRED_SHRAPNEL_RANDOM_SPEED)) +
			(axes.up * (crandom() * ZAERO_IRED_SHRAPNEL_RANDOM_SPEED));
		shrapnel->touch = Zaero_IREDShrapnelTouch;
		shrapnel->think = G_FreeEdict;
		shrapnel->nextthink = level.time + ZAERO_IRED_SHRAPNEL_BASE_LIFETIME +
			gtime_t::from_sec(crandom() * ZAERO_IRED_SHRAPNEL_LIFETIME_VARIANCE_SECONDS);
		// The supplied code deliberately leaves each point-sized shard unlinked;
		// bounce physics links it on its first 10 Hz reference step.
	}

	G_FreeEdict(self);
}

void Zaero_IREDTriggerFromBeam(edict_t *beam)
{
	edict_t *bomb = Zaero_IREDValidatedBomb(beam);
	if (bomb)
	{
		bomb->chain = nullptr;
		bomb->count = 0;
		bomb->think = Zaero_IREDExplode;
		bomb->nextthink = level.time + ZAERO_IRED_REFERENCE_TICK;
	}

	beam->chain = nullptr;
	beam->count = 0;
	beam->owner = nullptr;
	G_FreeEdict(beam);
}

THINK(Zaero_IREDLaserThink) (edict_t *self) -> void
{
	self->nextthink = level.time + ZAERO_IRED_REFERENCE_TICK;

	if (level.time > self->timestamp)
	{
		Zaero_IREDTriggerFromBeam(self);
		return;
	}

	if ((zaero_ired_emp_check && zaero_ired_emp_check(self, self->s.origin)) ||
		frandom() < ZAERO_IRED_PHASE_SKIP_CHANCE)
	{
		// Preserve the supplied `svflags != SVF_NOCLIENT` no-op: an EMP or the
		// ten-percent random phase skips detection but does not hide the beam.
		return;
	}

	self->svflags &= ~SVF_NOCLIENT;
	const vec3_t start = self->s.origin;
	const trace_t tr = gi.traceline(start, start + (self->movedir * ZAERO_IRED_BEAM_RANGE),
		self, MASK_SHOT);
	if (!tr.ent)
		return;

	const vec3_t delta = tr.endpos - self->move_origin;
	if (self->s.origin == self->move_origin)
	{
		self->move_origin = tr.endpos;
		if (self->spawnflags.has(SPAWNFLAG_IRED_INITIAL_SPARKS))
		{
			self->spawnflags &= ~SPAWNFLAG_IRED_INITIAL_SPARKS;
			gi.WriteByte(svc_temp_entity);
			gi.WriteByte(TE_LASER_SPARKS);
			gi.WriteByte(ZAERO_IRED_INITIAL_SPARK_COUNT);
			gi.WritePosition(tr.endpos);
			gi.WriteDir(tr.plane.normal);
			gi.WriteByte(static_cast<uint8_t>(self->s.skinnum));
			gi.multicast(tr.endpos, MULTICAST_PVS, false);
		}
	}
	else if (delta.length() > ZAERO_IRED_TRIGGER_EPSILON)
	{
		Zaero_IREDTriggerFromBeam(self);
		return;
	}

	self->s.old_origin = self->move_origin;
}

THINK(Zaero_IREDLaserOn) (edict_t *self) -> void
{
	self->svflags &= ~SVF_NOCLIENT;
	self->think = Zaero_IREDLaserThink;
	gi.sound(self, CHAN_VOICE, gi.soundindex(ZAERO_IRED_ARM_SOUND), 1.0f, ATTN_NORM, 0.0f);
	Zaero_IREDLaserThink(self);
}

THINK(Zaero_CreateIREDLaser) (edict_t *bomb) -> void
{
	if (Zaero_IREDValidatedBeam(bomb))
		return;

	edict_t *laser = G_Spawn();
	bomb->chain = laser;
	bomb->count = laser->spawn_count;
	laser->classname = ZAERO_IRED_BEAM_CLASSNAME;
	laser->s.origin = bomb->s.origin;
	laser->move_origin = bomb->s.origin;
	laser->s.angles = bomb->s.angles;
	G_SetMovedir(laser->s.angles, laser->movedir);
	laser->owner = bomb;
	laser->s.skinnum = ZAERO_IRED_BEAM_SKIN;
	laser->s.frame = 2;
	laser->movetype = MOVETYPE_NONE;
	laser->solid = SOLID_NOT;
	// Use the Rerelease laser-field form so bots receive the real start/end
	// points and active state after the beam becomes visible.
	laser->flags |= FL_TRAP_LASER_FIELD;
	laser->s.renderfx |= RF_BEAM | RF_TRANSLUCENT;
	laser->s.modelindex = 1;
	laser->chain = bomb;
	laser->count = bomb->spawn_count;
	laser->spawnflags |= SPAWNFLAG_IRED_INITIAL_SPARKS | SPAWNFLAG_IRED_LASER_ON;
	laser->think = Zaero_IREDLaserOn;
	laser->nextthink = level.time + ZAERO_IRED_REFERENCE_TICK;
	laser->svflags |= SVF_NOCLIENT;
	laser->timestamp = level.time + ZAERO_IRED_BEAM_TIMEOUT;
	gi.linkentity(laser);
}

USE(Zaero_IREDUse) (edict_t *self, edict_t *other, edict_t *activator) -> void
{
	if (Zaero_IREDValidatedBeam(self))
		Zaero_IREDDetachBeam(self);
	else
		Zaero_CreateIREDLaser(self);
}

THINK(Zaero_IREDTurnOffGlow) (edict_t *self) -> void
{
	self->s.effects &= ~EF_COLOR_SHELL;
	self->s.renderfx &= ~RF_SHELL_GREEN;
	self->think = nullptr;
	self->nextthink = 0_ms;
}

PAIN(Zaero_IREDPain) (edict_t *self, edict_t *other, float kick, int damage,
	const mod_t &mod) -> void
{
	self->damage_debounce_time = level.time + ZAERO_IRED_GLOW_TIME;
	if (!self->think)
	{
		self->s.effects |= EF_COLOR_SHELL;
		self->s.renderfx |= RF_SHELL_GREEN;
		self->nextthink = self->damage_debounce_time;
		self->think = Zaero_IREDTurnOffGlow;
	}
}

THINK(Zaero_IREDThink) (edict_t *self) -> void
{
	if (!Zaero_IREDValidatedBeam(self) && self->teleport_time < level.time)
		Zaero_CreateIREDLaser(self);

	if (self->damage_debounce_time > level.time)
	{
		self->s.effects |= EF_COLOR_SHELL;
		self->s.renderfx |= RF_SHELL_GREEN;
	}
	else
	{
		self->s.effects &= ~EF_COLOR_SHELL;
		self->s.renderfx &= ~RF_SHELL_GREEN;
	}

	self->nextthink = level.time + ZAERO_IRED_REFERENCE_TICK;
}

void Zaero_SetupIREDBomb(edict_t *bomb, const char *classname, int32_t damage,
	float damage_radius)
{
	bomb->classname = classname;
	bomb->mins = {-8.0f, -8.0f, -8.0f};
	bomb->maxs = {8.0f, 8.0f, 8.0f};
	bomb->solid = SOLID_BBOX;
	bomb->movetype = MOVETYPE_NONE;
	bomb->s.modelindex = gi.modelindex(ZAERO_IRED_MODEL);
	bomb->radius_dmg = damage;
	bomb->dmg = damage;
	bomb->dmg_radius = damage_radius;
	bomb->health = ZAERO_IRED_HEALTH;
	bomb->takedamage = true;
	// FL_IMMORTAL is the Rerelease equivalent of Zaero's DAMAGE_IMMORTAL:
	// damage effects and pain run, but health never falls below one.
	// FL_TRAP is metadata for the native bot bridge only; the flag is otherwise
	// unused by the Zaero mine's collision, damage, or mapper behavior.
	bomb->flags |= FL_IMMORTAL | FL_TRAP;
	bomb->pain = Zaero_IREDPain;
}

void Zaero_RemoveOldestIRED()
{
	edict_t *oldest = nullptr;
	edict_t *candidate = nullptr;
	int32_t count = 0;
	while ((candidate = G_FindByString<&edict_t::classname>(candidate,
		ZAERO_IRED_DYNAMIC_CLASSNAME)) != nullptr)
	{
		++count;
		if (!oldest || candidate->timestamp < oldest->timestamp)
			oldest = candidate;
	}

	// The newly placed 26th mine exists for one reference tick while the oldest
	// is scheduled to explode, exactly matching the supplied `count > 25` test.
	if (count > ZAERO_IRED_MAX_DEPLOYED && oldest)
	{
		oldest->think = Zaero_IREDExplode;
		oldest->nextthink = level.time + ZAERO_IRED_REFERENCE_TICK;
		Zaero_IREDDetachBeam(oldest);
	}
}

void Zaero_IREDStartPlayerAttack(edict_t *ent)
{
	ent->client->anim_priority = ANIM_ATTACK;
	if (ent->client->ps.pmove.pm_flags & PMF_DUCKED)
	{
		ent->s.frame = FRAME_crattak1 - 1;
		ent->client->anim_end = FRAME_crattak9;
	}
	else
	{
		ent->s.frame = FRAME_attack1 - 1;
		ent->client->anim_end = FRAME_attack8;
	}
	ent->client->anim_time = 0_ms;
}

void Zaero_IREDWeaponFireFrame(edict_t *ent)
{
	if (ent->client->ps.gunframe == ZAERO_IRED_PLACE_FRAME)
	{
		vec3_t forward;
		AngleVectors(ent->client->v_angle, forward, nullptr, nullptr);
		const vec3_t start = ent->s.origin + vec3_t{0.0f, 0.0f, ent->viewheight * 0.75f};
		const int32_t damage = (ent->client->quad_time > level.time)
			? ZAERO_IRED_DAMAGE * 4
			: ZAERO_IRED_DAMAGE;

		if (Zaero_FireIRED(ent, start, forward, ZAERO_IRED_ARM_DELAY, damage,
			ZAERO_IRED_DAMAGE_RADIUS))
		{
			G_RemoveAmmo(ent, 1);
			ent->client->ps.gunindex = gi.modelindex(ZAERO_IRED_HAND_MODEL);
			if (ent->client->quad_time > level.time)
				gi.sound(ent, CHAN_ITEM, gi.soundindex(ZAERO_QUAD_SOUND), 1.0f, ATTN_NORM, 0.0f);
		}
	}
	else if (ent->client->ps.gunframe == ZAERO_IRED_RESTORE_MODEL_FRAME)
	{
		const int32_t model = gi.modelindex(ZAERO_IRED_VIEW_MODEL);
		if (ent->client->ps.gunindex != model)
		{
			ent->client->ps.gunindex = model;
			ent->client->ps.gunframe = 0;
			return;
		}
	}
	else if (ent->client->ps.gunframe == ZAERO_IRED_ACTIVATE_LAST)
	{
		ent->client->ps.gunframe = ZAERO_IRED_IDLE_FIRST;
		return;
	}

	ent->client->ps.gunframe++;
}
} // namespace

void Zaero_SetIREDEMPCheck(zaero_ired_emp_check_t check)
{
	zaero_ired_emp_check = check;
}

bool Zaero_FireIRED(edict_t *owner, const vec3_t &start, const vec3_t &direction,
	gtime_t arm_delay, int32_t damage, float damage_radius)
{
	if (!level.zaero_content_active || !owner)
		return false;

	const trace_t tr = gi.traceline(start, start + (direction * ZAERO_IRED_PLACEMENT_RANGE),
		owner, MASK_SHOT);
	if (tr.fraction == 1.0f || !Zaero_IREDHasClassname(tr.ent, "worldspawn"))
		return false;

	edict_t *bomb = G_Spawn();
	bomb->s.origin = tr.endpos + (tr.plane.normal * ZAERO_IRED_WALL_OFFSET);
	bomb->s.angles = vectoangles(tr.plane.normal);
	bomb->owner = owner;
	bomb->style = owner->spawn_count;
	Zaero_SetupIREDBomb(bomb, ZAERO_IRED_DYNAMIC_CLASSNAME, damage, damage_radius);
	gi.linkentity(bomb);

	bomb->timestamp = level.time;
	bomb->teleport_time = level.time + arm_delay;
	bomb->nextthink = level.time + ZAERO_IRED_REFERENCE_TICK;
	bomb->think = Zaero_IREDThink;
	Zaero_RemoveOldestIRED();

	gi.sound(owner, CHAN_VOICE, gi.soundindex(ZAERO_IRED_SET_SOUND), 1.0f, ATTN_NORM, 0.0f);
	return true;
}

void Weapon_ZaeroIRED(edict_t *ent)
{
	static const int32_t pause_frames[] = {24, 33, 43, 0};

	if (!level.zaero_content_active || !ent->client || ent->deadflag || ent->s.modelindex != MODELINDEX_PLAYER)
		return;

	// IRED frames retain the supplied 10 Hz cadence at a 40 Hz host rate. The
	// view protocol uses zero as its compact encoding for the normal 10 Hz rate.
	ent->client->ps.gunrate = 0;

	if (ent->client->weaponstate == WEAPON_DROPPING)
	{
		if (g_instant_weapon_switch->integer)
		{
			ChangeWeapon(ent);
			return;
		}
		if (ent->client->weapon_think_time > level.time)
			return;
		if (ent->client->ps.gunframe == ZAERO_IRED_DEACTIVATE_LAST)
		{
			ChangeWeapon(ent);
			return;
		}

		ent->client->ps.gunframe++;
		ent->client->weapon_think_time = level.time + ZAERO_IRED_REFERENCE_TICK;
		return;
	}

	if (ent->client->weaponstate == WEAPON_ACTIVATING)
	{
		if (ent->client->weapon_think_time > level.time && !g_instant_weapon_switch->integer)
			return;
		if (ent->client->ps.gunframe == ZAERO_IRED_ACTIVATE_LAST ||
			g_instant_weapon_switch->integer)
		{
			ent->client->weaponstate = WEAPON_READY;
			ent->client->ps.gunframe = ZAERO_IRED_IDLE_FIRST;
			ent->client->weapon_fire_buffered = false;
			ent->client->weapon_fire_finished = g_instant_weapon_switch->integer
				? 0_ms
				: level.time + ZAERO_IRED_REFERENCE_TICK;
			ent->client->weapon_think_time = level.time + ZAERO_IRED_REFERENCE_TICK;
			return;
		}

		ent->client->ps.gunframe++;
		ent->client->weapon_think_time = level.time + ZAERO_IRED_REFERENCE_TICK;
		return;
	}

	bool is_holstering = false;
	if (!g_instant_weapon_switch->integer)
		is_holstering = ((ent->client->latched_buttons | ent->client->buttons) & BUTTON_HOLSTER);
	if ((ent->client->newweapon || is_holstering) && ent->client->weaponstate != WEAPON_FIRING)
	{
		if (!g_instant_weapon_switch->integer && ent->client->weapon_think_time > level.time)
			return;
		if (!ent->client->newweapon)
			ent->client->newweapon = ent->client->pers.weapon;
		if (g_instant_weapon_switch->integer)
		{
			ChangeWeapon(ent);
			return;
		}
		ent->client->weaponstate = WEAPON_DROPPING;
		ent->client->ps.gunframe = ZAERO_IRED_DEACTIVATE_FIRST;
		ent->client->weapon_think_time = level.time + ZAERO_IRED_REFERENCE_TICK;
		return;
	}

	if (ent->client->weaponstate == WEAPON_READY)
	{
		const bool request_firing = ent->client->weapon_fire_buffered ||
			((ent->client->latched_buttons | ent->client->buttons) & BUTTON_ATTACK);
		if (request_firing && ent->client->weapon_fire_finished <= level.time)
		{
			ent->client->latched_buttons &= ~BUTTON_ATTACK;
			ent->client->weapon_fire_buffered = false;
			if (ent->client->pers.inventory[ent->client->pers.weapon->ammo] > 0)
			{
				ent->client->ps.gunframe = ZAERO_IRED_FIRE_FIRST;
				ent->client->weaponstate = WEAPON_FIRING;
				ent->client->last_firing_time = level.time + COOP_DAMAGE_FIRING_TIME;
				ent->client->weapon_think_time = level.time;
				Zaero_IREDStartPlayerAttack(ent);
			}
			else
			{
				NoAmmoWeaponChange(ent, true);
				return;
			}
		}
		else if (ent->client->weapon_think_time <= level.time)
		{
			ent->client->weapon_think_time = level.time + ZAERO_IRED_REFERENCE_TICK;
			if (ent->client->ps.gunframe == ZAERO_IRED_IDLE_LAST)
			{
				ent->client->ps.gunframe = ZAERO_IRED_IDLE_FIRST;
				return;
			}
			for (int32_t i = 0; pause_frames[i]; ++i)
				if (ent->client->ps.gunframe == pause_frames[i] && irandom(16))
					return;
			ent->client->ps.gunframe++;
			return;
		}
	}

	if (ent->client->weaponstate == WEAPON_FIRING &&
		ent->client->weapon_think_time <= level.time)
	{
		Zaero_IREDWeaponFireFrame(ent);
		if (ent->client->ps.gunframe == ZAERO_IRED_READY_FRAME)
		{
			ent->client->weaponstate = WEAPON_READY;
			ent->client->weapon_fire_buffered = false;
		}
		ent->client->last_firing_time = level.time + COOP_DAMAGE_FIRING_TIME;
		ent->client->weapon_think_time = level.time + ZAERO_IRED_REFERENCE_TICK;
		ent->client->weapon_fire_finished = level.time + ZAERO_IRED_REFERENCE_TICK;
	}
}

void SP_misc_ired(edict_t *self)
{
	if (!level.zaero_content_active)
	{
		G_FreeEdict(self);
		return;
	}

	gi.soundindex(ZAERO_IRED_SET_SOUND);
	gi.soundindex(ZAERO_IRED_ARM_SOUND);
	gi.modelindex(ZAERO_IRED_SHRAPNEL_MODEL);
	gi.modelindex(ZAERO_IRED_MODEL);

	if (self->spawnflags.has(SPAWNFLAG_IRED_CHECK_BACK_WALL))
	{
		vec3_t forward;
		AngleVectors(self->s.angles, forward, nullptr, nullptr);
		const trace_t tr = gi.traceline(self->s.origin,
			self->s.origin - (forward * ZAERO_IRED_PLACEMENT_RANGE), self, MASK_SOLID);
		self->s.origin = tr.endpos;
		self->s.angles = vectoangles(tr.plane.normal);
	}

	Zaero_SetupIREDBomb(self, ZAERO_IRED_MAP_CLASSNAME, ZAERO_IRED_DAMAGE,
		ZAERO_IRED_DAMAGE_RADIUS);
	if (self->targetname)
		self->use = Zaero_IREDUse;
	else
	{
		self->think = Zaero_CreateIREDLaser;
		self->nextthink = level.time + ZAERO_IRED_ARM_DELAY;
	}
	gi.linkentity(self);
}

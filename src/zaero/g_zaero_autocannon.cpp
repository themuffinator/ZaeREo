// SPDX-License-Identifier: GPL-2.0-only

#include "../g_local.h"
#include "g_zaero_autocannon.h"
#include "g_zaero_emp.h"

namespace
{
// Zaero advances this entity once per original 10 Hz game frame. Running the
// animation at the Rerelease host's 40 Hz cadence would quadruple every turn,
// activation, burst, and death transition.
constexpr gtime_t ZAERO_AUTOCANNON_TICK = 10_hz;

constexpr spawnflags_t SPAWNFLAG_AUTOCANNON_START_OFF = 1_spawnflag;
constexpr spawnflags_t SPAWNFLAG_AUTOCANNON_BERSERK = 2_spawnflag;
constexpr spawnflags_t SPAWNFLAG_AUTOCANNON_BERSERK_TOGGLE = 4_spawnflag;

constexpr float AUTOCANNON_RANGE = 2048.0f;
constexpr gtime_t AUTOCANNON_TIMEOUT = 2_sec;
constexpr int32_t AUTOCANNON_EXPLOSION_DAMAGE = 150;
constexpr float AUTOCANNON_EXPLOSION_RADIUS = 384.0f;
constexpr float AUTOCANNON_TURN_SPEED = 6.0f;
constexpr gtime_t AUTOCANNON_TURN_DELAY = 1_sec;

constexpr int32_t AUTOCANNON_BULLET_DAMAGE = 4;
constexpr int32_t AUTOCANNON_BULLET_KICK = 2;
constexpr int32_t AUTOCANNON_ROCKET_DAMAGE = 100;
constexpr int32_t AUTOCANNON_ROCKET_SPEED = 650;
constexpr int32_t AUTOCANNON_ROCKET_RADIUS_DAMAGE = 120;
constexpr float AUTOCANNON_ROCKET_DAMAGE_RADIUS = 120.0f;
constexpr int32_t AUTOCANNON_BLASTER_DAMAGE = 20;
constexpr int32_t AUTOCANNON_BLASTER_SPEED = 1000;

enum autocannon_state_t : int32_t
{
	AUTOCANNON_IDLE,
	AUTOCANNON_ACTIVATING,
	AUTOCANNON_ACTIVE,
	AUTOCANNON_DEACTIVATING
};

struct autocannon_anim_frame_t
{
	bool last;
	bool fire;
	int32_t frame;
};

struct autocannon_anim_t
{
	int32_t first_non_pause;
	autocannon_anim_frame_t frames[32];
};

// Indices and repeated frames are data, not approximations: a cannon that
// loses its enemy halfway through a burst deliberately finishes this table,
// including its remaining shots, before returning to sequence zero.
constexpr autocannon_anim_t AUTOCANNON_FIRING_FRAMES[5] = {
	{ 0, { { true, false, -1 } } },
	{ 6,
	  {
		  { false, false, 11 }, { false, false, 11 }, { false, false, 11 },
		  { false, false, 11 }, { false, false, 11 }, { false, false, 11 },
		  { false, true, 11 },  { false, false, 12 }, { false, true, 13 },
		  { false, false, 14 }, { false, true, 15 },  { false, false, 16 },
		  { false, true, 17 },  { false, false, 18 }, { false, true, 19 },
		  { false, false, 20 }, { false, true, 21 },  { true, false, 2 },
	  } },
	{ 6,
	  {
		  { false, false, 11 }, { false, false, 11 }, { false, false, 11 },
		  { false, false, 11 }, { false, false, 11 }, { false, false, 11 },
		  { false, true, 11 },  { false, false, 11 }, { false, false, 12 },
		  { false, false, 12 }, { false, false, 13 }, { false, false, 13 },
		  { false, false, 14 }, { false, false, 14 }, { false, false, 15 },
		  { false, false, 15 }, { false, false, 16 }, { true, false, 16 },
	  } },
	{ 6,
	  {
		  { false, false, 11 }, { false, false, 11 }, { false, false, 11 },
		  { false, false, 11 }, { false, false, 11 }, { false, false, 11 },
		  { false, true, 11 },  { false, false, 11 }, { false, false, 11 },
		  { false, false, 11 }, { false, false, 11 }, { true, false, 11 },
	  } },
	{ 6,
	  {
		  { false, false, 11 }, { false, false, 11 }, { false, false, 11 },
		  { false, false, 11 }, { false, false, 11 }, { false, false, 11 },
		  { false, true, 11 },  { false, false, 11 }, { false, false, 11 },
		  { false, false, 11 }, { false, false, 11 }, { false, false, 11 },
		  { false, false, 11 }, { false, false, 11 }, { false, false, 11 },
		  { false, false, 11 }, { false, false, 11 }, { true, false, 11 },
	  } },
};

constexpr vec3_t AUTOCANNON_FIRE_OFFSETS[5] = {
	{ 0.0f, 0.0f, 0.0f },
	{ 24.0f, -4.0f, 0.0f },
	{ 0.0f, -4.0f, 0.0f },
	{ 24.0f, -5.0f, 0.0f },
	{ 24.0f, -5.0f, 0.0f },
};

constexpr const char *AUTOCANNON_MODELS[5] = {
	nullptr,
	"models/objects/acannon/chain/tris.md2",
	"models/objects/acannon/rocket/tris.md2",
	"models/objects/acannon/laser/tris.md2",
	"models/objects/acannon/laser/tris.md2",
};

constexpr const char *AUTOCANNON_FLOOR_MODELS[5] = {
	nullptr,
	"",
	"models/objects/acannon/rocket2/tris.md2",
	"models/objects/acannon/laser2/tris.md2",
	"models/objects/acannon/laser2/tris.md2",
};

constexpr int32_t AUTOCANNON_IDLE_START[5] = { 0, 0, 0, 0, 0 };
constexpr int32_t AUTOCANNON_ACTIVATE_START[5] = { 0, 1, 1, 1, 1 };
constexpr int32_t AUTOCANNON_ACTIVATE_END[5] = { 0, 9, 9, 9, 9 };
constexpr int32_t AUTOCANNON_ACTIVE_START[5] = { 0, 10, 10, 10, 10 };
constexpr int32_t AUTOCANNON_ACTIVE_END[5] = { 0, 10, 10, 10, 10 };
constexpr int32_t AUTOCANNON_DEACTIVATE_START[5] = { 0, 23, 23, 23, 23 };
constexpr int32_t AUTOCANNON_DEACTIVATE_END[5] = { 0, 31, 31, 31, 31 };

constexpr int32_t TURRET_IDLE_START = 0;
constexpr int32_t TURRET_ACTIVATE_START = 1;
constexpr int32_t TURRET_ACTIVE_START = 10;
constexpr int32_t TURRET_DEACTIVATE_START = 23;

// The supplied source declared only four entries but indexed this table with
// styles 1..4. In the shipped ELF, turretIdle is immediately followed by the
// zero-valued turretIdleStart symbol, so style 4 observably read false. Spell
// that value out: this preserves the retail frame quirk without retaining UB.
constexpr bool TURRET_COLLAPSES_WHEN_IDLE[5] = { false, false, true, true, false };

constexpr const char *SOUND_AUTOCANNON_IDLE = "objects/acannon/ac_idle.wav";
constexpr const char *SOUND_AUTOCANNON_ACTIVATE = "objects/acannon/ac_act.wav";
constexpr const char *SOUND_EMP_MISFIRE = "items/empnuke/emp_missfire.wav";
bool Zaero_AutocannonIsFloor(const edict_t *self)
{
	return self->classname && !Q_strcasecmp(self->classname, "monster_autocannon_floor");
}

bool Zaero_AutocannonRiderIsValid(const edict_t *base, size_t slot, const edict_t *rider)
{
	return base && base->inuse && rider && rider->inuse &&
		slot < edict_t::ZAERO_MAX_RIDERS && base->ride_with[slot] == rider &&
		base->ride_with_spawn_count[slot] == rider->spawn_count;
}

edict_t *Zaero_AutocannonTurret(edict_t *self)
{
	edict_t *turret = self->chain;
	if (!turret || !turret->inuse || !turret->classname ||
		Q_strcasecmp(turret->classname, "autocannon turret"))
		return nullptr;

	edict_t *base = turret->chain;
	if (!base || !base->classname || Q_strcasecmp(base->classname, "autocannon base") ||
		!Zaero_AutocannonRiderIsValid(base, 0, turret) ||
		!Zaero_AutocannonRiderIsValid(base, 1, self))
		return nullptr;

	return turret;
}

// This intentionally mutates all three values. One legacy call passes the
// cannon yaw itself, making wrap normalization an observable part of turning.
bool Zaero_AngleBetween(float &angle, float &minimum, float &maximum)
{
	if (angle > minimum && angle < maximum)
		return true;

	while (minimum < 0.0f)
		minimum += 360.0f;
	while (angle < minimum)
		angle += 360.0f;
	while (maximum < minimum)
		maximum += 360.0f;

	return angle > minimum && angle < maximum;
}

float Zaero_Mod180(float value)
{
	while (value > 180.0f)
		value -= 360.0f;
	while (value < -180.0f)
		value += 360.0f;
	return value;
}

float Zaero_ApproachAngle(float current, float ideal, float speed)
{
	current = anglemod(current);
	float move = ideal - current;
	if (ideal > current)
	{
		if (move >= 180.0f)
			move -= 360.0f;
	}
	else if (move <= -180.0f)
	{
		move += 360.0f;
	}

	move = clamp(move, -speed, speed);
	return anglemod(current + move);
}

void Zaero_AngleToward(edict_t *self, const vec3_t &point, float speed)
{
	const vec3_t destination_angles = vectoangles(point - self->s.origin);
	self->s.angles[YAW] = Zaero_ApproachAngle(self->s.angles[YAW], destination_angles[YAW], speed);
	self->s.angles[PITCH] = Zaero_ApproachAngle(self->s.angles[PITCH], destination_angles[PITCH], speed);

	// The shared legacy helper also redirected velocity to the resulting
	// forward vector. It is normally zero for this stationary entity.
	const float velocity = self->velocity.length();
	self->velocity = AngleVectors(self->s.angles).forward * velocity;
}

bool Zaero_AutocannonCanShoot(edict_t *self, edict_t *candidate)
{
	vec3_t candidate_angles = vectoangles(candidate->s.origin - self->s.origin);
	candidate_angles[PITCH] = Zaero_Mod180(candidate_angles[PITCH]);
	const bool on_floor = Zaero_AutocannonIsFloor(self);
	if ((!on_floor && candidate_angles[PITCH] < 0.0f) ||
		(on_floor && candidate_angles[PITCH] > 0.0f))
		return false;

	if (self->monsterinfo.linkcount > 0)
	{
		const float ideal_yaw = self->move_angles[YAW];
		float maximum_yaw = anglemod(ideal_yaw + self->monsterinfo.linkcount);
		float minimum_yaw = anglemod(ideal_yaw - self->monsterinfo.linkcount);
		if (!Zaero_AngleBetween(candidate_angles[YAW], minimum_yaw, maximum_yaw))
			return false;
	}

	return true;
}

bool Zaero_AutocannonInFront(edict_t *self, edict_t *other)
{
	const vec3_t candidate_angles = vectoangles(other->s.origin - self->s.origin);
	float difference = candidate_angles[YAW] - self->s.angles[YAW];
	float minimum = -30.0f;
	float maximum = 30.0f;
	return Zaero_AngleBetween(difference, minimum, maximum);
}

void Zaero_AutocannonFindEnemy(edict_t *self)
{
	if (self->enemy && !self->enemy->inuse)
		self->enemy = nullptr;
	if (self->oldenemy && !self->oldenemy->inuse)
		self->oldenemy = nullptr;

	if (self->enemy)
	{
		if (!Zaero_AutocannonCanShoot(self, self->enemy))
		{
			self->oldenemy = nullptr;
			self->enemy = nullptr;
		}
		else if (!visible(self, self->enemy))
		{
			self->oldenemy = self->enemy;
			self->enemy = nullptr;
		}
		else if ((self->enemy->flags & FL_NOTARGET) || self->enemy->health <= 0)
		{
			self->oldenemy = nullptr;
			self->enemy = nullptr;
		}
	}

	edict_t *candidate = nullptr;
	while (!self->enemy)
	{
		candidate = findradius(candidate, self->s.origin, AUTOCANNON_RANGE);
		if (!candidate)
		{
			if (!self->oldenemy)
				return;
			if (level.time > self->timestamp)
			{
				self->oldenemy = nullptr;
				return;
			}
			self->enemy = self->oldenemy;
			break;
		}

		if (self->spawnflags.has(SPAWNFLAG_AUTOCANNON_BERSERK))
		{
			if (!candidate->client && !(candidate->svflags & SVF_MONSTER))
				continue;
		}
		else if (!candidate->client)
		{
			continue;
		}

		if (candidate->health <= 0 || (candidate->flags & FL_NOTARGET) || candidate == self)
			continue;
		if (candidate->classname && !Q_strcasecmp(candidate->classname, "monster_autocannon"))
			continue;
		if (!visible(self, candidate) || !Zaero_AutocannonInFront(self, candidate))
			continue;
		if (Zaero_AutocannonCanShoot(self, candidate))
			self->enemy = candidate;
	}
}

void Zaero_AutocannonTurn(edict_t *self)
{
	const vec3_t old_angles = self->s.angles;
	const bool on_floor = Zaero_AutocannonIsFloor(self);

	if (!self->enemy)
	{
		if (self->monsterinfo.linkcount > 0)
		{
			const int32_t ideal_yaw = static_cast<int32_t>(self->move_angles[YAW]);
			int32_t maximum_yaw = static_cast<int32_t>(anglemod(ideal_yaw + self->monsterinfo.linkcount));
			const int32_t minimum_yaw = static_cast<int32_t>(anglemod(ideal_yaw - self->monsterinfo.linkcount));
			while (maximum_yaw < minimum_yaw)
				maximum_yaw += 360;

			self->s.angles[YAW] += self->monsterinfo.lefty ? -AUTOCANNON_TURN_SPEED : AUTOCANNON_TURN_SPEED;
			if (self->s.angles[YAW] > maximum_yaw)
			{
				self->monsterinfo.lefty = true;
				self->s.angles[YAW] = static_cast<float>(maximum_yaw);
			}
			else if (self->s.angles[YAW] < minimum_yaw)
			{
				self->monsterinfo.lefty = false;
				self->s.angles[YAW] = static_cast<float>(minimum_yaw);
			}
		}
		else
		{
			self->s.angles[YAW] = anglemod(self->s.angles[YAW] + AUTOCANNON_TURN_SPEED);
		}

		if (!on_floor)
		{
			if (self->s.angles[PITCH] > 10.0f)
				self->s.angles[PITCH] -= 4.0f;
			else if (self->s.angles[PITCH] < 5.0f)
				self->s.angles[PITCH] += 4.0f;
		}
		else
		{
			if (self->s.angles[PITCH] < -10.0f)
				self->s.angles[PITCH] += 4.0f;
			else if (self->s.angles[PITCH] > -5.0f)
				self->s.angles[PITCH] -= 4.0f;
		}
	}
	else if (visible(self, self->enemy))
	{
		const vec3_t offset = (self->enemy->mins + self->enemy->maxs) * 0.65f;
		const vec3_t destination = self->enemy->s.origin + offset;
		Zaero_AngleToward(self, destination, AUTOCANNON_TURN_SPEED);
		self->monsterinfo.last_sighting = destination;
		self->timestamp = level.time + AUTOCANNON_TIMEOUT;

		if (self->monsterinfo.linkcount > 0)
		{
			float maximum_yaw = anglemod(self->move_angles[YAW] + self->monsterinfo.linkcount);
			float minimum_yaw = anglemod(self->move_angles[YAW] - self->monsterinfo.linkcount);
			self->s.angles[YAW] = anglemod(self->s.angles[YAW]);
			if (!Zaero_AngleBetween(self->s.angles[YAW], minimum_yaw, maximum_yaw))
			{
				if (self->s.angles[YAW] - maximum_yaw < minimum_yaw - self->s.angles[YAW])
					self->s.angles[YAW] = minimum_yaw;
				else
					self->s.angles[YAW] = maximum_yaw;
			}
		}
	}
	else
	{
		Zaero_AngleToward(self, self->monsterinfo.last_sighting, AUTOCANNON_TURN_SPEED);
	}

	self->s.angles[PITCH] = Zaero_Mod180(self->s.angles[PITCH]);
	const float minimum_pitch = on_floor ? -60.0f : 0.0f;
	const float maximum_pitch = on_floor ? 0.0f : 60.0f;
	self->s.angles[PITCH] = clamp(self->s.angles[PITCH], minimum_pitch, maximum_pitch);

	if (edict_t *turret = Zaero_AutocannonTurret(self))
	{
		turret->s.angles[YAW] = self->s.angles[YAW];
		turret->s.angles[PITCH] = 0.0f;
		turret->s.sound = self->s.angles == old_angles ? 0 : gi.soundindex(SOUND_AUTOCANNON_IDLE);
	}
}

void Zaero_AutocannonMuzzleflash(edict_t *self, player_muzzle_t flash)
{
	gi.WriteByte(svc_muzzleflash);
	gi.WriteEntity(self);
	gi.WriteByte(flash);
	gi.multicast(self->s.origin, MULTICAST_PVS, false);
}

void Zaero_AutocannonFire(edict_t *self)
{
	angle_vectors_t axes = AngleVectors(self->s.angles);
	if (Zaero_AutocannonIsFloor(self))
		axes.right = -axes.right;
	const vec3_t start = G_ProjectSource(self->s.origin, AUTOCANNON_FIRE_OFFSETS[self->style], axes.forward, axes.right);

	if (Zaero_EMPNukeCheck(self, start))
	{
		Zaero_PlayEMPMisfire(self);
		return;
	}

	switch (self->style)
	{
	case 1:
	default:
		fire_bullet(self, start, axes.forward, AUTOCANNON_BULLET_DAMAGE,
			AUTOCANNON_BULLET_KICK, DEFAULT_BULLET_HSPREAD,
			DEFAULT_BULLET_VSPREAD, MOD_ZAERO_AUTOCANNON);
		Zaero_AutocannonMuzzleflash(self, MZ_CHAINGUN2);
		break;
	case 2:
		fire_rocket(self, start, axes.forward, AUTOCANNON_ROCKET_DAMAGE,
			AUTOCANNON_ROCKET_SPEED, AUTOCANNON_ROCKET_DAMAGE_RADIUS,
			AUTOCANNON_ROCKET_RADIUS_DAMAGE);
		Zaero_AutocannonMuzzleflash(self, MZ_ROCKET);
		break;
	case 3:
	case 4:
		fire_blaster(self, start, axes.forward, AUTOCANNON_BLASTER_DAMAGE,
			AUTOCANNON_BLASTER_SPEED, EF_HYPERBLASTER, MOD_HYPERBLASTER);
		Zaero_AutocannonMuzzleflash(self, MZ_HYPERBLASTER);
		break;
	}
}

THINK(Zaero_AutocannonThink) (edict_t *self) -> void
{
	self->nextthink = level.time + ZAERO_AUTOCANNON_TICK;

	edict_t *old_enemy = self->enemy;
	Zaero_AutocannonFindEnemy(self);
	if (self->enemy && old_enemy != self->enemy)
		gi.sound(self, CHAN_VOICE, gi.soundindex(SOUND_AUTOCANNON_ACTIVATE), 1.0f, ATTN_NORM, 0.0f);

	const bool old_lefty = self->monsterinfo.lefty;
	if (level.time > self->teleport_time)
	{
		Zaero_AutocannonTurn(self);
		if (self->monsterinfo.lefty != old_lefty)
			self->teleport_time = level.time + AUTOCANNON_TURN_DELAY;
	}

	// count is the save-registered Rerelease slot used for legacy seq. Clamp a
	// malformed external save rather than indexing arbitrary animation memory.
	if (self->count < 0 || self->count >= 32)
		self->count = 0;
	const autocannon_anim_t &animation = AUTOCANNON_FIRING_FRAMES[self->style];
	const autocannon_anim_frame_t &frame = animation.frames[self->count];

	if (!self->enemy)
	{
		if (self->count == 0)
		{
			self->s.frame++;
			if (self->s.frame > AUTOCANNON_ACTIVE_END[self->style] ||
				self->s.frame < AUTOCANNON_ACTIVE_START[self->style])
				self->s.frame = AUTOCANNON_ACTIVE_START[self->style];
			return;
		}

		self->s.frame = frame.frame;
		if (frame.fire)
			Zaero_AutocannonFire(self);
		self->count = frame.last ? 0 : self->count + 1;
		return;
	}

	if (!Zaero_AutocannonInFront(self, self->enemy))
	{
		self->s.frame = frame.frame;
		if (self->count == animation.first_non_pause)
			return;
		self->count = frame.last ? animation.first_non_pause : self->count + 1;
		return;
	}

	self->s.frame = frame.frame;
	if (frame.fire)
		Zaero_AutocannonFire(self);
	self->count = frame.last ? animation.first_non_pause : self->count + 1;
}

THINK(Zaero_AutocannonExplode) (edict_t *self) -> void
{
	T_RadiusDamage(self, self, AUTOCANNON_EXPLOSION_DAMAGE, self->enemy,
		AUTOCANNON_EXPLOSION_RADIUS, DAMAGE_NONE, MOD_ZAERO_TRIPBOMB);

	const vec3_t origin = self->s.origin + (self->velocity * -0.02f);
	gi.WriteByte(svc_temp_entity);
	if (self->waterlevel)
		gi.WriteByte(self->groundentity ? TE_GRENADE_EXPLOSION_WATER : TE_ROCKET_EXPLOSION_WATER);
	else
		gi.WriteByte(self->groundentity ? TE_GRENADE_EXPLOSION : TE_ROCKET_EXPLOSION);
	gi.WritePosition(origin);
	gi.multicast(self->s.origin, MULTICAST_PHS, false);

	// Zaero frees the barrel and turret but deliberately leaves the base behind
	// with its damaged skin. Cross-check both rider generations before touching
	// any child so an independently freed/reused edict cannot be destroyed.
	if (edict_t *turret = Zaero_AutocannonTurret(self))
	{
		edict_t *base = turret->chain;
		base->s.skinnum = 1;
		G_ClearZaeroRiders(base);
		G_FreeEdict(turret);
	}
	G_FreeEdict(self);
}

DIE(Zaero_AutocannonDie) (edict_t *self, edict_t *inflictor, edict_t *attacker,
	int damage, const vec3_t &point, const mod_t &mod) -> void
{
	self->takedamage = false;
	self->think = Zaero_AutocannonExplode;
	self->nextthink = level.time + ZAERO_AUTOCANNON_TICK;
}

PAIN(Zaero_AutocannonPain) (edict_t *self, edict_t *other, float kick,
	int damage, const mod_t &mod) -> void
{
	if (other->client || (other->svflags & SVF_MONSTER))
		self->enemy = other;
}

THINK(Zaero_AutocannonActivate) (edict_t *self) -> void
{
	self->active = AUTOCANNON_ACTIVATING;
	self->nextthink = level.time + ZAERO_AUTOCANNON_TICK;
	edict_t *turret = Zaero_AutocannonTurret(self);

	if (self->s.frame >= AUTOCANNON_ACTIVATE_START[self->style] &&
		self->s.frame < AUTOCANNON_ACTIVATE_END[self->style])
	{
		self->s.frame++;
		if (turret)
			turret->s.frame++;
	}
	else if (self->s.frame == AUTOCANNON_ACTIVATE_END[self->style])
	{
		self->s.frame = AUTOCANNON_ACTIVE_START[self->style];
		if (turret)
			turret->s.frame = TURRET_ACTIVE_START;
		self->think = Zaero_AutocannonThink;
		self->active = AUTOCANNON_ACTIVE;
	}
	else
	{
		self->s.frame = AUTOCANNON_ACTIVATE_START[self->style];
		if (turret)
			turret->s.frame = TURRET_ACTIVATE_START;
	}
}

THINK(Zaero_AutocannonDeactivate) (edict_t *self) -> void
{
	self->active = AUTOCANNON_DEACTIVATING;
	self->nextthink = level.time + ZAERO_AUTOCANNON_TICK;
	edict_t *turret = Zaero_AutocannonTurret(self);

	if (self->s.angles[PITCH] != 0.0f)
	{
		if (self->s.angles[PITCH] > 0.0f)
			self->s.angles[PITCH] = max(0.0f, self->s.angles[PITCH] - 5.0f);
		else
			self->s.angles[PITCH] = min(0.0f, self->s.angles[PITCH] + 5.0f);
	}
	else if (self->s.frame >= AUTOCANNON_DEACTIVATE_START[self->style] &&
		self->s.frame < AUTOCANNON_DEACTIVATE_END[self->style])
	{
		if (turret)
		{
			turret->s.sound = 0;
			turret->s.frame++;
		}
		self->s.frame++;
	}
	else if (self->s.frame == AUTOCANNON_DEACTIVATE_END[self->style])
	{
		self->s.frame = AUTOCANNON_IDLE_START[self->style];
		if (turret)
		{
			turret->s.frame = TURRET_IDLE_START;
			turret->s.sound = 0;
		}
		self->think = nullptr;
		self->nextthink = 0_ms;
		self->active = AUTOCANNON_IDLE;
	}
	else
	{
		self->s.frame = AUTOCANNON_DEACTIVATE_START[self->style];
		if (turret)
			turret->s.frame = TURRET_DEACTIVATE_START;
	}
}

void Zaero_AutocannonAct(edict_t *self)
{
	if (self->active == AUTOCANNON_IDLE)
	{
		self->think = Zaero_AutocannonActivate;
		self->nextthink = level.time + ZAERO_AUTOCANNON_TICK;
	}
	else if (self->active == AUTOCANNON_ACTIVE)
	{
		self->nextthink = level.time + ZAERO_AUTOCANNON_TICK;
		self->think = Zaero_AutocannonDeactivate;
	}
	// Activating/deactivating uses are ignored by the supplied state machine.
}

USE(Zaero_AutocannonUse) (edict_t *self, edict_t *other, edict_t *activator) -> void
{
	if (self->spawnflags.has(SPAWNFLAG_AUTOCANNON_BERSERK_TOGGLE))
		self->spawnflags ^= SPAWNFLAG_AUTOCANNON_BERSERK;
	else
		Zaero_AutocannonAct(self);
}

THINK(Zaero_AutocannonUseStub) (edict_t *self) -> void
{
	Zaero_AutocannonAct(self);
}
} // namespace

void SP_monster_autocannon(edict_t *self)
{
	if (deathmatch->integer)
	{
		G_FreeEdict(self);
		return;
	}

	if (self->style < 1 || self->style > 4)
		self->style = 1;
	if (skill->value >= 2.0f && self->style == 4)
		self->style = 3;

	gi.soundindex(SOUND_AUTOCANNON_IDLE);
	gi.soundindex(SOUND_AUTOCANNON_ACTIVATE);
	gi.soundindex(SOUND_EMP_MISFIRE);
	gi.modelindex("models/objects/rocket/tris.md2");
	gi.modelindex("models/objects/laser/tris.md2");

	const bool on_floor = Zaero_AutocannonIsFloor(self);
	edict_t *base = G_Spawn();
	base->classname = "autocannon base";
	base->solid = SOLID_BBOX;
	base->s.origin = self->s.origin;
	base->movetype = on_floor ? MOVETYPE_RIDE : MOVETYPE_NONE;
	base->s.modelindex = gi.modelindex(on_floor
		? "models/objects/acannon/base2/tris.md2"
		: "models/objects/acannon/base/tris.md2");
	gi.linkentity(base);

	edict_t *turret = G_Spawn();
	turret->classname = "autocannon turret";
	turret->solid = SOLID_BBOX;
	turret->movetype = MOVETYPE_NONE;
	turret->chain = base;
	turret->s.origin = self->s.origin;
	turret->s.modelindex = gi.modelindex(on_floor
		? "models/objects/acannon/turret2/tris.md2"
		: "models/objects/acannon/turret/tris.md2");
	turret->s.frame = TURRET_COLLAPSES_WHEN_IDLE[self->style]
		? TURRET_IDLE_START : TURRET_ACTIVE_START;
	turret->s.angles[YAW] = self->s.angles[YAW];
	turret->s.angles[PITCH] = 0.0f;
	gi.linkentity(turret);

	self->solid = SOLID_BBOX;
	self->movetype = MOVETYPE_NONE;
	self->s.origin[2] += on_floor ? 20.0f : -20.0f;
	if (on_floor)
	{
		self->mins = { -12.0f, -12.0f, -16.0f };
		self->maxs = { 12.0f, 12.0f, 28.0f };
	}
	else
	{
		self->mins = { -12.0f, -12.0f, -28.0f };
		self->maxs = { 12.0f, 12.0f, 16.0f };
	}
	self->chain = turret;
	self->s.modelindex = gi.modelindex(on_floor
		? AUTOCANNON_FLOOR_MODELS[self->style]
		: AUTOCANNON_MODELS[self->style]);
	self->s.frame = AUTOCANNON_IDLE_START[self->style];
	self->active = AUTOCANNON_IDLE;
	self->monsterinfo.lefty = false;
	// Legacy attack_state was an int, so assignment truncated fractional yaw.
	self->move_angles[YAW] = static_cast<float>(static_cast<int32_t>(self->s.angles[YAW]));
	self->count = 0; // legacy seq
	self->monsterinfo.linkcount = st.lip > 0.0f ? static_cast<int32_t>(st.lip) : 0;

	if (!self->health)
		self->health = 100;
	if (self->targetname)
		self->use = Zaero_AutocannonUse;
	if (self->spawnflags.has(SPAWNFLAG_AUTOCANNON_BERSERK_TOGGLE) ||
		!self->spawnflags.has(SPAWNFLAG_AUTOCANNON_START_OFF))
	{
		self->think = Zaero_AutocannonUseStub;
		self->nextthink = level.time + ZAERO_AUTOCANNON_TICK;
	}

	self->takedamage = true;
	self->die = Zaero_AutocannonDie;
	self->pain = Zaero_AutocannonPain;

	G_SetZaeroRider(base, 0, turret);
	G_SetZaeroRider(base, 1, self);
	gi.linkentity(self);
}

void SP_monster_autocannon_floor(edict_t *self)
{
	if (self->style == 1)
	{
		gi.Com_Error("monster_autocannon_floor does not permit bullet style");
		G_FreeEdict(self);
		return;
	}

	if (self->style < 1 || self->style > 4)
		self->style = 2;
	SP_monster_autocannon(self);
}

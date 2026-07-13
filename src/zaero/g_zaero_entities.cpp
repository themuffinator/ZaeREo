// SPDX-License-Identifier: GPL-2.0-only

#include "../g_local.h"
#include "g_zaero_entities.h"

// Implemented by the native Rerelease barrel code. Reusing it retains the
// mass-sensitive push contract while the Zaero FALLFLOAT mover is pending.
void barrel_touch(edict_t *self, edict_t *other, const trace_t &tr, bool other_touching_self);

namespace
{
// Zaero's game DLL ran these callbacks once per 10 Hz server frame. Keep the
// elapsed time stable when the Rerelease calls the game DLL at 40 Hz.
constexpr gtime_t ZAERO_LEGACY_TICK = 100_ms;
constexpr spawnflags_t SPAWNFLAG_TRIGGER_LASER_MULTIPLE = 1_spawnflag;

constexpr const char *MODEL_COMMDISH = "models/objects/satdish/tris.md2";
constexpr const char *MODEL_SECURITY_CAMERA = "models/objects/camera/tris.md2";
constexpr const char *MODEL_CRATE_LARGE = "models/objects/crate/crate64.md2";
constexpr const char *MODEL_CRATE_MEDIUM = "models/objects/crate/crate48.md2";
constexpr const char *MODEL_CRATE_SMALL = "models/objects/crate/crate32.md2";
constexpr const char *MODEL_BARRIER = "models/objects/wall/tris.md2";
constexpr const char *MODEL_SEAT = "models/objects/seat/tris.md2";
constexpr const char *SOUND_COMMDISH = "misc/commdish.wav";
constexpr const char *SOUND_BARRIER_HIT = "weapons/lashit.wav";

THINK(zaero_drop_to_floor) (edict_t *self) -> void
{
	M_droptofloor(self);
}

void setup_crate(edict_t *self)
{
	self->solid = SOLID_BBOX;

	// Zaero crates and seats slide on steep slopes and float according to their
	// displaced volume; the dedicated Rerelease-native mover preserves that
	// behavior at 40 Hz.
	self->movetype = MOVETYPE_FALLFLOAT;

	if (!self->mass)
		self->mass = 400;

	self->touch = barrel_touch;
	self->think = zaero_drop_to_floor;
	self->nextthink = level.time + (ZAERO_LEGACY_TICK * 2);
	gi.linkentity(self);
}

void zaero_trigger_laser_on(edict_t *self);

THINK(zaero_trigger_laser_think) (edict_t *self) -> void
{
	self->nextthink = level.time + ZAERO_LEGACY_TICK;

	const vec3_t start = self->s.origin;
	const vec3_t end = start + (self->movedir * 2048.0f);

	// Players have a distinct contents bit in the Rerelease. Include it to
	// preserve the legacy CONTENTS_MONSTER trace's effective player coverage.
	constexpr contents_t mask = CONTENTS_SOLID | CONTENTS_MONSTER |
		CONTENTS_PLAYER | CONTENTS_DEADMONSTER;
	const trace_t tr = gi.traceline(start, end, self, mask);

	if (!tr.ent)
		return;

	if (!(tr.ent->svflags & SVF_MONSTER) && !tr.ent->client)
	{
		if (self->spawnflags.has(SPAWNFLAG_LASER_ZAP))
		{
			self->spawnflags &= ~SPAWNFLAG_LASER_ZAP;
			gi.WriteByte(svc_temp_entity);
			gi.WriteByte(TE_LASER_SPARKS);
			gi.WriteByte(8);
			gi.WritePosition(tr.endpos);
			gi.WriteDir(tr.plane.normal);
			gi.WriteByte(self->s.skinnum);
			gi.multicast(tr.endpos, MULTICAST_PVS, false);
		}
	}
	else
	{
		G_UseTargets(self, tr.ent);
		if (!self->inuse)
			return;

		if (self->spawnflags.has(SPAWNFLAG_TRIGGER_LASER_MULTIPLE))
		{
			self->svflags |= SVF_NOCLIENT;
			self->nextthink = level.time + gtime_t::from_sec(self->wait);
			self->think = zaero_trigger_laser_on;
		}
		else
		{
			// The legacy code wrote old_origin after freeing the edict. That write
			// is not observable and is unsafe with Rerelease entity reuse.
			G_FreeEdict(self);
			return;
		}
	}

	self->s.old_origin = tr.endpos;
}

THINK(zaero_trigger_laser_on) (edict_t *self) -> void
{
	self->svflags &= ~SVF_NOCLIENT;
	self->think = zaero_trigger_laser_think;
	zaero_trigger_laser_think(self);
}

THINK(zaero_commdish_animate) (edict_t *self) -> void
{
	self->s.frame++;

	if (self->s.frame >= 98)
	{
		self->s.frame = 98;
		return;
	}

	self->nextthink = level.time + ZAERO_LEGACY_TICK;
}

USE(zaero_commdish_use) (edict_t *self, edict_t *other, edict_t *activator) -> void
{
	self->nextthink = level.time + ZAERO_LEGACY_TICK;
	self->think = zaero_commdish_animate;
	self->use = nullptr;
	gi.sound(self, CHAN_AUTO, gi.soundindex(SOUND_COMMDISH), 1.0f, ATTN_NORM, 0.0f);
}

USE(zaero_securitycamera_use) (edict_t *self, edict_t *other, edict_t *activator) -> void
{
	self->active = !self->active;
}

THINK(zaero_securitycamera_think) (edict_t *self) -> void
{
	if (self->active)
	{
		self->s.frame++;
		if (self->s.frame > 59)
			self->s.frame = 0;
	}

	if (self->timestamp > level.time)
	{
		self->s.effects |= EF_COLOR_SHELL;
		self->s.renderfx |= RF_SHELL_GREEN;
	}
	else
	{
		self->s.effects &= ~EF_COLOR_SHELL;
		self->s.renderfx &= ~RF_SHELL_GREEN;
	}

	self->nextthink = level.time + ZAERO_LEGACY_TICK;
}

PAIN(zaero_securitycamera_pain) (edict_t *self, edict_t *other, float kick, int damage, const mod_t &mod) -> void
{
	self->timestamp = level.time + (ZAERO_LEGACY_TICK * 2);
}

THINK(zaero_barrier_think) (edict_t *self) -> void
{
	if (self->timestamp > level.time)
		self->svflags &= ~SVF_NOCLIENT;
	else
		self->svflags |= SVF_NOCLIENT;

	self->nextthink = level.time + ZAERO_LEGACY_TICK;
}

PAIN(zaero_barrier_pain) (edict_t *self, edict_t *other, float kick, int damage, const mod_t &mod) -> void
{
	self->timestamp = level.time + (ZAERO_LEGACY_TICK * 2);
	if (self->damage_debounce_time < level.time)
	{
		gi.sound(self, CHAN_AUTO, gi.soundindex(SOUND_BARRIER_HIT), 1.0f, ATTN_NORM, 0.0f);
		self->damage_debounce_time = level.time + (ZAERO_LEGACY_TICK * 2);
	}
}

TOUCH(zaero_barrier_touch) (edict_t *self, edict_t *other, const trace_t &tr, bool other_touching_self) -> void
{
	if (other == world)
		return;

	self->timestamp = level.time + (ZAERO_LEGACY_TICK * 2);
	if (self->touch_debounce_time < level.time)
	{
		gi.sound(self, CHAN_AUTO, gi.soundindex(SOUND_BARRIER_HIT), 1.0f, ATTN_NORM, 0.0f);
		self->touch_debounce_time = level.time + (ZAERO_LEGACY_TICK * 2);
	}
}
} // namespace

void SP_sound_echo(edict_t *self)
{
	// The shipped Zaero source deliberately implements this mapper surface as
	// a compatibility no-op.
	G_FreeEdict(self);
}

void SP_load_mirrorlevel(edict_t *self)
{
	// Mirror maps were never completed; the original entity frees itself.
	G_FreeEdict(self);
}

void SP_trigger_laser(edict_t *self)
{
	if (!self->target)
	{
		gi.Com_PrintFmt("{} without a target\n", *self);
		G_FreeEdict(self);
		return;
	}

	if (!self->wait)
		self->wait = 4.0f;

	G_SetMovedir(self->s.angles, self->movedir);
	self->s.skinnum = static_cast<int32_t>(0xf2f2f0f0u);
	self->s.frame = 2;
	self->movetype = MOVETYPE_NONE;
	self->solid = SOLID_NOT;
	self->s.renderfx |= RF_BEAM | RF_TRANSLUCENT;
	self->s.modelindex = MODELINDEX_WORLD;
	self->spawnflags |= SPAWNFLAG_LASER_ZAP;
	self->think = zaero_trigger_laser_on;
	self->nextthink = level.time + ZAERO_LEGACY_TICK;
	self->svflags |= SVF_NOCLIENT;
	gi.linkentity(self);
}

void SP_misc_commdish(edict_t *self)
{
	if (deathmatch->integer)
	{
		G_FreeEdict(self);
		return;
	}

	self->solid = SOLID_BBOX;
	self->movetype = MOVETYPE_STEP;
	self->model = MODEL_COMMDISH;
	self->s.modelindex = gi.modelindex(self->model);
	self->mins = { -100.0f, -100.0f, 0.0f };
	self->maxs = { 100.0f, 100.0f, 275.0f };
	self->monsterinfo.aiflags |= AI_NOSTEP;
	self->think = zaero_drop_to_floor;
	self->nextthink = level.time + (ZAERO_LEGACY_TICK * 2);
	self->use = zaero_commdish_use;
	gi.soundindex(SOUND_COMMDISH);
	gi.linkentity(self);
}

void SP_misc_securitycamera(edict_t *self)
{
	if (!self->message)
	{
		gi.Com_Error("misc_securitycamera w/o message");
		G_FreeEdict(self);
		return;
	}

	self->solid = SOLID_BBOX;
	self->movetype = MOVETYPE_NONE;
	self->s.modelindex = gi.modelindex(MODEL_SECURITY_CAMERA);
	self->mins = { -16.0f, -16.0f, -32.0f };
	self->maxs = { 16.0f, 16.0f, 0.0f };

	self->move_angles = self->mangle;
	self->s.angles = { 0.0f, self->mangle[YAW], 0.0f };
	const angle_vectors_t camera_axes = AngleVectors(self->s.angles);
	const vec3_t offset = (camera_axes.forward * 8.0f) - (camera_axes.up * 32.0f);
	self->move_origin = self->s.origin + offset;

	if (self->targetname)
	{
		self->use = zaero_securitycamera_use;
		self->active = false;
	}
	else
	{
		self->active = true;
	}

	self->think = zaero_securitycamera_think;
	self->nextthink = level.time + ZAERO_LEGACY_TICK;
	self->health = 1;
	self->takedamage = true;
	self->flags |= FL_IMMORTAL;
	self->pain = zaero_securitycamera_pain;
	gi.linkentity(self);
}

void SP_misc_crate(edict_t *self)
{
	self->s.modelindex = gi.modelindex(MODEL_CRATE_LARGE);
	self->mins = { -32.0f, -32.0f, 0.0f };
	self->maxs = { 32.0f, 32.0f, 64.0f };
	setup_crate(self);
}

void SP_misc_crate_medium(edict_t *self)
{
	self->s.modelindex = gi.modelindex(MODEL_CRATE_MEDIUM);
	self->mins = { -24.0f, -24.0f, 0.0f };
	self->maxs = { 24.0f, 24.0f, 48.0f };
	setup_crate(self);
}

void SP_misc_crate_small(edict_t *self)
{
	self->s.modelindex = gi.modelindex(MODEL_CRATE_SMALL);
	self->mins = { -16.0f, -16.0f, 0.0f };
	self->maxs = { 16.0f, 16.0f, 32.0f };
	setup_crate(self);
}

bool Zaero_TraceThroughBarrier(edict_t *target, edict_t *inflictor)
{
	if (!target || !inflictor)
		return false;

	edict_t *trace_from = inflictor;
	for (int32_t traversals = 0; trace_from && traversals < MAX_EDICTS; traversals++)
	{
		const trace_t tr = gi.traceline(trace_from->s.origin, target->s.origin, trace_from, MASK_SHOT);
		if (!tr.ent || tr.fraction >= 1.0f || tr.ent == target)
			return false;

		if (tr.ent->classname && !Q_strcasecmp(tr.ent->classname, "func_barrier"))
			return true;

		if (trace_from == tr.ent)
			break;

		trace_from = tr.ent;
	}

	// The legacy function fell off the end here. False is the only safe and
	// intent-consistent result when no barrier was found.
	return false;
}

void SP_func_barrier(edict_t *self)
{
	self->solid = SOLID_BBOX;
	self->movetype = MOVETYPE_NONE;
	self->s.modelindex = gi.modelindex(MODEL_BARRIER);
	self->svflags |= SVF_NOCLIENT;
	self->s.effects |= EF_BFG;
	self->think = zaero_barrier_think;
	self->nextthink = level.time + ZAERO_LEGACY_TICK;
	self->touch = zaero_barrier_touch;
	self->health = 1;
	self->takedamage = true;
	self->flags |= FL_IMMORTAL;
	self->pain = zaero_barrier_pain;
	gi.soundindex(SOUND_BARRIER_HIT);
	gi.linkentity(self);
}

void SP_misc_seat(edict_t *self)
{
	self->s.modelindex = gi.modelindex(MODEL_SEAT);
	self->mins = { -16.0f, -16.0f, 0.0f };
	self->maxs = { 16.0f, 16.0f, 40.0f };
	setup_crate(self);
}

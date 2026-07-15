// SPDX-License-Identifier: GPL-2.0-only

#include "../g_local.h"
#include "g_zaero_handler.h"
#include "g_zaero_hound.h"

void InfantryPrecache();
void InfantryConvertFromZaeroHandler(edict_t *self);

namespace
{
constexpr spawnflags_t SPAWNFLAG_HANDLER_RESTRAIN_LOOP = 8_spawnflag;

constexpr int32_t FRAME_STAND1_START = 0;
constexpr int32_t FRAME_STAND1_END = 30;
constexpr int32_t FRAME_STAND2_START = 31;
constexpr int32_t FRAME_STAND2_END = 59;
constexpr int32_t FRAME_STAND3_START = 60;
constexpr int32_t FRAME_STAND3_END = 89;
constexpr int32_t FRAME_STAND4_START = 90;
constexpr int32_t FRAME_STAND4_END = 100;
constexpr int32_t FRAME_STAND5_START = 101;
constexpr int32_t FRAME_STAND5_END = 110;
constexpr int32_t FRAME_RELEASE_START = 111;
constexpr int32_t FRAME_RELEASE_END = 128;

constexpr const char *HANDLER_MODEL = "models/monsters/guard/handler/tris.md2";
constexpr const char *HOUND_MODEL = "models/monsters/guard/hound/tris.md2";

static cached_soundindex sound_attack;
static cached_soundindex sound_hound_sight;
static cached_soundindex sound_infantry_sight;

void handler_stand(edict_t *self);
void handler_attack(edict_t *self);

void handler_precache()
{
	InfantryPrecache();
	ZaeroHoundPrecache();
	sound_attack.assign("monsters/guard/hhattack.wav");
	sound_hound_sight.assign("monsters/hound/hsight1.wav");
	sound_infantry_sight.assign("infantry/infsght1.wav");
}

void handler_stand_sitting_next(edict_t *self);
void handler_stand_next(edict_t *self);

mframe_t handler_frames_stand1[] = {
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }
};
MMOVE_T(handler_move_stand1) = {
	FRAME_STAND1_START, FRAME_STAND1_END, handler_frames_stand1,
	handler_stand_sitting_next
};

void handler_scratch(edict_t *self)
{
	// The supplied Release build keeps this authored callback silent.
}

mframe_t handler_frames_stand2[] = {
	{ ai_stand, 0, handler_scratch }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }
};
MMOVE_T(handler_move_stand2) = {
	FRAME_STAND2_START, FRAME_STAND2_END, handler_frames_stand2,
	handler_stand_sitting_next
};

mframe_t handler_frames_stand3[] = {
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }
};
MMOVE_T(handler_move_stand3) = {
	FRAME_STAND3_START, FRAME_STAND3_END, handler_frames_stand3,
	handler_stand_next
};

void handler_standup(edict_t *self)
{
	// Authored sound path is disabled in the supplied Release source.
}

mframe_t handler_frames_stand4[] = {
	{ ai_stand, 0, handler_standup }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }
};
MMOVE_T(handler_move_stand4) = {
	FRAME_STAND4_START, FRAME_STAND4_END, handler_frames_stand4,
	handler_stand_next
};

void handler_sitdown(edict_t *self)
{
	// Authored sound path is disabled in the supplied Release source.
}

mframe_t handler_frames_stand5[] = {
	{ ai_stand, 0, handler_sitdown }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }
};
MMOVE_T(handler_move_stand5) = {
	FRAME_STAND5_START, FRAME_STAND5_END, handler_frames_stand5,
	handler_stand_sitting_next
};

void handler_stand_next(edict_t *self)
{
	M_SetAnimation(self, frandom() < 0.90f ?
		&handler_move_stand3 : &handler_move_stand5);
}

void handler_stand_sitting_next(edict_t *self)
{
	const float choice = frandom();
	if (choice < 0.70f)
		M_SetAnimation(self, &handler_move_stand1);
	else if (choice < 0.85f)
		M_SetAnimation(self, &handler_move_stand2);
	else
		M_SetAnimation(self, &handler_move_stand4);
}

MONSTERINFO_STAND(handler_stand) (edict_t *self) -> void
{
	const save_mmove_t &move = self->monsterinfo.active_move;
	if (move != &handler_move_stand1 && move != &handler_move_stand2 &&
		move != &handler_move_stand3 && move != &handler_move_stand4 &&
		move != &handler_move_stand5)
	{
		M_SetAnimation(self, &handler_move_stand3);
	}
}

MONSTERINFO_WALK(handler_walk) (edict_t *self) -> void
{
	handler_stand(self);
}

void handler_start_release_timer(edict_t *self)
{
	self->powerarmor_time = level.time + 3_sec;
}

void handler_check_for_enemy(edict_t *self)
{
	if (self->enemy && (self->enemy->client || (self->enemy->svflags & SVF_MONSTER)))
	{
		self->powerarmor_time = 0_ms;
		return;
	}

	if (self->powerarmor_time < level.time)
	{
		self->enemy = nullptr;
		handler_stand(self);
		return;
	}

	// Preserve the source's same-frame retry: the next 10 Hz move increments
	// back to this callback without re-running the timer-start frame.
	self->s.frame--;
}

void handler_check_idle_loop(edict_t *self)
{
	if (!self->powerarmor_time && self->spawnflags.has(SPAWNFLAG_HANDLER_RESTRAIN_LOOP))
	{
		self->powerarmor_time = level.time +
			gtime_t::from_sec(frandom(0.0f, 0.3f));
	}
	if (self->powerarmor_time > level.time)
		self->s.frame -= 2;
}

void handler_create_hound(edict_t *self)
{
	if (!self->s.modelindex2)
		return;
	ZaeroCreateHandlerHound(self);
	self->s.modelindex2 = 0;
}

void handler_convert_to_infantry(edict_t *self)
{
	InfantryConvertFromZaeroHandler(self);
}

mframe_t handler_frames_release[] = {
	{ ai_run, 0, handler_start_release_timer },
	{ ai_run, 0, handler_check_for_enemy },
	{ ai_charge }, { ai_charge }, { ai_charge }, { ai_charge },
	{ ai_charge }, { ai_charge },
	{ ai_charge, 0, handler_check_idle_loop },
	{ ai_charge }, { ai_charge },
	{ ai_charge, 0, handler_create_hound },
	{ ai_charge }, { ai_charge }, { ai_charge }, { ai_charge },
	{ ai_charge }, { ai_charge }
};
MMOVE_T(handler_move_release) = {
	FRAME_RELEASE_START, FRAME_RELEASE_END, handler_frames_release,
	handler_convert_to_infantry
};

MONSTERINFO_ATTACK(handler_attack) (edict_t *self) -> void
{
	gi.sound(self, CHAN_VOICE, sound_attack, 1, ATTN_NORM, 0);
	M_SetAnimation(self, &handler_move_release);
	self->powerarmor_time = 0_ms;
}

MONSTERINFO_RUN(handler_run) (edict_t *self) -> void
{
	handler_attack(self);
}

MONSTERINFO_SIGHT(handler_sight) (edict_t *self, edict_t *other) -> void
{
	gi.sound(self, CHAN_WEAPON, sound_hound_sight, 1, ATTN_NORM, 0);
	gi.sound(self, CHAN_BODY, sound_infantry_sight, 1, ATTN_NORM, 0);
}

PAIN(handler_pain) (edict_t *self, edict_t *other, float kick, int damage,
	const mod_t &mod) -> void
{
	// Source behavior: combined Handler/Hound has no pain animation or sound.
}

DIE(handler_die) (edict_t *self, edict_t *inflictor, edict_t *attacker,
	int damage, const vec3_t &point, const mod_t &mod) -> void
{
	// FL_IMMORTAL performs this clamp before generic monster kill accounting.
	self->health = 1;
}

void handler_reserve_hound_count(edict_t *self)
{
	if (self->spawnflags.has(SPAWNFLAG_ZAERO_MONSTER_NO_COUNT))
		return;
	if (g_debug_monster_kills->integer)
		level.monsters_registered[level.total_monsters] = self;
	level.total_monsters++;
}
} // namespace

void SP_monster_handler(edict_t *self)
{
	if (!M_AllowSpawn(self))
	{
		G_FreeEdict(self);
		return;
	}

	handler_precache();
	self->s.modelindex = gi.modelindex(HANDLER_MODEL);
	self->s.modelindex2 = gi.modelindex(HOUND_MODEL);
	self->mins = { -32, -32, -24 };
	self->maxs = { 32, 32, 32 };
	self->movetype = MOVETYPE_STEP;
	self->solid = SOLID_BBOX;
	self->health = 175 * st.health_multiplier;
	self->gib_health = -50;
	self->mass = 250;
	self->flags |= FL_IMMORTAL;
	self->pain = handler_pain;
	self->die = handler_die;
	self->monsterinfo.stand = handler_stand;
	self->monsterinfo.walk = handler_walk;
	self->monsterinfo.run = handler_run;
	self->monsterinfo.attack = handler_attack;
	self->monsterinfo.melee = nullptr;
	self->monsterinfo.sight = handler_sight;
	self->monsterinfo.idle = nullptr;
	self->monsterinfo.scale = 1.0f;
	M_SetAnimation(self, &handler_move_stand1);
	gi.linkentity(self);

	// Preserve the legacy map-total contract from initial spawn while leaving
	// the future child's own native lifecycle free to suppress a second count.
	handler_reserve_hound_count(self);
	walkmonster_start(self);
}

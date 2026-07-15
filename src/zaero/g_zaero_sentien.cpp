// SPDX-License-Identifier: GPL-2.0-only
#include "../g_local.h"
#include "g_zaero_emp.h"
#include "g_zaero_sentien.h"

namespace
{
constexpr int32_t FRAME_STAND1_START = 0;
constexpr int32_t FRAME_STAND1_END = 28;
constexpr int32_t FRAME_STAND2_START = 29;
constexpr int32_t FRAME_STAND2_END = 48;
constexpr int32_t FRAME_STAND3_START = 49;
constexpr int32_t FRAME_STAND3_END = 79;
constexpr int32_t FRAME_WALK_START_START = 80;
constexpr int32_t FRAME_WALK_START_END = 87;
constexpr int32_t FRAME_WALK_LOOP_START = 88;
constexpr int32_t FRAME_WALK_LOOP_END = 103;
constexpr int32_t FRAME_WALK_END_START = 104;
constexpr int32_t FRAME_WALK_END_END = 111;
constexpr int32_t FRAME_BLAST_PRE_START = 112;
constexpr int32_t FRAME_BLAST_PRE_END = 115;
constexpr int32_t FRAME_BLAST_START = 116;
constexpr int32_t FRAME_BLAST_END = 121;
constexpr int32_t FRAME_BLAST_POST_START = 122;
constexpr int32_t FRAME_BLAST_POST_END = 125;
constexpr int32_t FRAME_LASER_PRE_START = 126;
constexpr int32_t FRAME_LASER_PRE_END = 130;
constexpr int32_t FRAME_LASER_START = 131;
constexpr int32_t FRAME_LASER_END = 141;
constexpr int32_t FRAME_LASER_POST_START = 142;
constexpr int32_t FRAME_LASER_POST_END = 145;
constexpr int32_t FRAME_FEND_START = 168;
constexpr int32_t FRAME_FEND_HOLD = 173;
constexpr int32_t FRAME_FEND_END = 182;
constexpr int32_t FRAME_PAIN1_START = 183;
constexpr int32_t FRAME_PAIN1_END = 186;
constexpr int32_t FRAME_PAIN2_START = 187;
constexpr int32_t FRAME_PAIN2_END = 192;
constexpr int32_t FRAME_PAIN3_START = 193;
constexpr int32_t FRAME_PAIN3_END = 213;
constexpr int32_t FRAME_DEATH1_START = 214;
constexpr int32_t FRAME_DEATH1_END = 241;
constexpr int32_t FRAME_DEATH2_START = 242;
constexpr int32_t FRAME_DEATH2_END = 270;

constexpr const char *SENTIEN_CLASSNAME = "monster_sentien";
constexpr const char *SENTIEN_LASER_CLASSNAME = "laser_yaya";
constexpr const char *SENTIEN_MODEL = "models/monsters/sentien/tris.md2";

static cached_soundindex sound_idle1;
static cached_soundindex sound_idle2;
static cached_soundindex sound_walk;
static cached_soundindex sound_fend;
static cached_soundindex sound_pain1;
static cached_soundindex sound_pain2;
static cached_soundindex sound_die1;
static cached_soundindex sound_die2;
static cached_soundindex sound_attack1;
static cached_soundindex sound_attack2;

constexpr vec3_t SENTIEN_FLASH_OFFSETS[] = {
	{ 23.7f, 25.4f, 29.6f },
	{ 23.7f, 25.3f, 26.7f },
	{ 23.7f, 27.7f, 28.1f },
	{ 23.7f, 27.4f, 31.2f },
	{ 23.7f, 24.9f, 32.3f },
	{ 23.7f, 22.5f, 30.6f },
	{ 23.7f, 22.7f, 27.8f }
};

constexpr vec3_t SENTIEN_LASER_OFFSETS[] = {
	{ 43.8f, -21.8f, 42.8f },
	{ 44.2f, -21.9f, 43.1f },
	{ 43.9f, -21.8f, 43.2f },
	{ 43.2f, -22.0f, 43.2f },
	{ 42.4f, -22.4f, 43.1f },
	{ 42.0f, -22.5f, 43.2f },
	{ 42.4f, -22.3f, 43.2f },
	{ 43.1f, -22.1f, 43.1f },
	{ 43.8f, -21.9f, 43.1f },
	{ 44.2f, -21.8f, 43.3f },
	{ 43.8f, -21.8f, 42.7f }
};

void sentien_stand(edict_t *self);
void sentien_walk(edict_t *self);
void sentien_run(edict_t *self);

void sentien_precache()
{
	sound_idle1.assign("monsters/sentien/sen_idle1.wav");
	sound_idle2.assign("monsters/sentien/sen_idle2.wav");
	sound_walk.assign("monsters/sentien/sen_walk.wav");
	sound_fend.assign("monsters/sentien/sen_fend.wav");
	sound_pain1.assign("monsters/sentien/sen_pain1.wav");
	sound_pain2.assign("monsters/sentien/sen_pain2.wav");
	sound_die1.assign("monsters/sentien/sen_die1.wav");
	sound_die2.assign("monsters/sentien/sen_die2.wav");
	sound_attack1.assign("monsters/sentien/sen_att1.wav");
	sound_attack2.assign("monsters/sentien/sen_att2.wav");
}

void sentien_sound_idle1(edict_t *self)
{
	gi.sound(self, CHAN_BODY, sound_idle1, 1, ATTN_NORM, 0);
}

void sentien_sound_idle2(edict_t *self)
{
	gi.sound(self, CHAN_BODY, sound_idle2, 1, ATTN_NORM, 0);
}

void sentien_sound_footstep(edict_t *self)
{
	gi.sound(self, CHAN_BODY, sound_walk, 1, ATTN_NORM, 0);
}

void sentien_sound_fend(edict_t *self)
{
	gi.sound(self, CHAN_BODY, sound_fend, 1, ATTN_NORM, 0);
}

void sentien_sound_die1(edict_t *self)
{
	gi.sound(self, CHAN_BODY, sound_die1, 1, ATTN_NORM, 0);
}

void sentien_sound_die2(edict_t *self)
{
	gi.sound(self, CHAN_BODY, sound_die2, 1, ATTN_NORM, 0);
}

bool sentien_laser_is_owned(edict_t *self)
{
	edict_t *laser = self ? self->beam : nullptr;
	return laser && laser->inuse && laser->classname &&
		!strcmp(laser->classname, SENTIEN_LASER_CLASSNAME) &&
		laser->owner == self && laser->count == self->spawn_count;
}

void sentien_laser_off(edict_t *self)
{
	if (sentien_laser_is_owned(self))
		target_laser_off(self->beam);
	else if (self)
		self->beam = nullptr;
}

void sentien_laser_free(edict_t *self)
{
	if (!self)
		return;
	if (sentien_laser_is_owned(self))
	{
		target_laser_off(self->beam);
		G_FreeEdict(self->beam);
	}
	self->beam = nullptr;
}

THINK(sentien_laser_think) (edict_t *self) -> void
{
	edict_t *sentien = self->owner;
	if (!sentien || !sentien->inuse || sentien->spawn_count != self->count ||
		sentien->beam != self || !sentien->classname ||
		strcmp(sentien->classname, SENTIEN_CLASSNAME))
	{
		G_FreeEdict(self);
		return;
	}
	target_laser_think(self);
}

void sentien_laser_on(edict_t *self)
{
	if (!sentien_laser_is_owned(self))
		return;
	edict_t *laser = self->beam;
	laser->activator = self;
	laser->spawnflags |= SPAWNFLAG_LASER_ZAP | SPAWNFLAG_LASER_ON;
	laser->svflags &= ~SVF_NOCLIENT;
	sentien_laser_think(laser);
}

void sentien_create_laser(edict_t *self)
{
	vec3_t forward, right;
	AngleVectors(self->s.angles, forward, right, nullptr);

	edict_t *laser = G_Spawn();
	self->beam = laser;
	laser->classname = SENTIEN_LASER_CLASSNAME;
	laser->owner = self;
	laser->activator = self;
	laser->count = self->spawn_count;
	laser->movetype = MOVETYPE_NONE;
	// Preserve the supplied point-sized BBOX trace obstruction contract.
	laser->solid = SOLID_BBOX;
	// The native bot bridge gives laser fields separate endpoint/active-state
	// metadata. It does not affect target_laser damage or legacy visibility.
	laser->flags |= FL_TRAP_LASER_FIELD;
	laser->s.renderfx = RF_BEAM | RF_TRANSLUCENT;
	laser->s.modelindex = MODELINDEX_WORLD;
	laser->s.frame = 2;
	laser->s.skinnum = 0xd0d1d2d3;
	laser->dmg = 8;
	laser->think = sentien_laser_think;
	laser->s.origin = G_ProjectSource(self->s.origin, SENTIEN_LASER_OFFSETS[0], forward, right);
	laser->s.angles = self->s.angles;
	G_SetMovedir(laser->s.angles, laser->movedir);
	gi.linkentity(laser);
	target_laser_off(laser);
}

mframe_t sentien_frames_stand1[] = {
	{ ai_stand, 0, sentien_sound_idle1 },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }
};

mframe_t sentien_frames_stand2[] = {
	{ ai_stand, 0, sentien_sound_idle2 },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }
};

mframe_t sentien_frames_stand3[] = {
	{ ai_stand, 0, sentien_sound_idle1 },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }
};

void sentien_stand_whatnow(edict_t *self);
void sentien_stand_earwax(edict_t *self);

MMOVE_T(sentien_move_stand1) = {
	FRAME_STAND1_START, FRAME_STAND1_END, sentien_frames_stand1, sentien_stand_whatnow
};
MMOVE_T(sentien_move_stand2) = {
	FRAME_STAND2_START, FRAME_STAND2_END, sentien_frames_stand2, sentien_stand_whatnow
};
MMOVE_T(sentien_move_stand3) = {
	FRAME_STAND3_START, FRAME_STAND3_END, sentien_frames_stand3, sentien_stand_earwax
};

MONSTERINFO_STAND(sentien_stand) (edict_t *self) -> void
{
	sentien_laser_off(self);
	M_SetAnimation(self, &sentien_move_stand1);
}

void sentien_stand_whatnow(edict_t *self)
{
	if (frandom() < self->random)
	{
		M_SetAnimation(self, &sentien_move_stand1);
		self->random -= 0.05f;
		return;
	}
	M_SetAnimation(self, brandom() ? &sentien_move_stand2 : &sentien_move_stand3);
	self->random = 1.0f;
}

void sentien_stand_earwax(edict_t *self)
{
	if (frandom() > 0.80f)
		M_SetAnimation(self, &sentien_move_stand3);
	else
		sentien_stand_whatnow(self);
}

mframe_t sentien_frames_walk_start[] = {
	{ ai_walk }, { ai_walk, 1.5f }, { ai_walk, 2.9f }, { ai_walk, 2.4f },
	{ ai_walk, 2.1f }, { ai_walk, 2.6f }, { ai_walk, 2.1f },
	{ ai_walk, 1.8f, sentien_sound_footstep }
};

mframe_t sentien_frames_walk[] = {
	{ ai_walk, 0.3f }, { ai_walk, 2.4f }, { ai_walk, 4.0f }, { ai_walk, 3.5f },
	{ ai_walk, 3.6f }, { ai_walk, 3.7f * 1.1f }, { ai_walk, 3.1f * 1.3f },
	{ ai_walk, 4.1f * 1.2f, sentien_sound_footstep },
	{ ai_walk, 2.0f }, { ai_walk, 2.6f }, { ai_walk, 3.8f }, { ai_walk, 3.6f },
	{ ai_walk, 3.6f }, { ai_walk, 4.3f }, { ai_walk, 4.2f * 1.2f },
	{ ai_walk, 5.2f, sentien_sound_footstep }
};

mframe_t sentien_frames_walk_end[] = {
	{ ai_walk, 0.8f }, { ai_walk, 1.0f }, { ai_walk, 1.6f }, { ai_walk, 1.4f },
	{ ai_walk, 1.5f }, { ai_walk, 1.4f }, { ai_walk, 1.5f },
	{ ai_walk, 1.8f, sentien_sound_footstep }
};

MMOVE_T(sentien_move_walk_start) = {
	FRAME_WALK_START_START, FRAME_WALK_START_END, sentien_frames_walk_start, sentien_walk
};
MMOVE_T(sentien_move_walk) = {
	FRAME_WALK_LOOP_START, FRAME_WALK_LOOP_END, sentien_frames_walk
};
MMOVE_T(sentien_move_walk_end) = {
	FRAME_WALK_END_START, FRAME_WALK_END_END, sentien_frames_walk_end, sentien_stand
};

MONSTERINFO_WALK(sentien_walk) (edict_t *self) -> void
{
	sentien_laser_off(self);
	if (self->monsterinfo.active_move == &sentien_move_walk)
		return;
	if (self->monsterinfo.active_move == &sentien_move_stand1 ||
		self->monsterinfo.active_move == &sentien_move_stand2 ||
		self->monsterinfo.active_move == &sentien_move_stand3)
		M_SetAnimation(self, &sentien_move_walk_start);
	else
		M_SetAnimation(self, &sentien_move_walk);
}

mframe_t sentien_frames_run_start[] = {
	{ ai_run }, { ai_run, 1.5f }, { ai_run, 2.9f }, { ai_run, 2.4f },
	{ ai_run, 2.1f }, { ai_run, 2.6f }, { ai_run, 2.1f },
	{ ai_run, 1.8f, sentien_sound_footstep }
};

mframe_t sentien_frames_run[] = {
	{ ai_run, 0.3f * 1.2f }, { ai_run, 2.4f }, { ai_run, 4.0f }, { ai_run, 3.5f },
	{ ai_run, 3.6f }, { ai_run, 3.7f * 1.1f }, { ai_run, 3.1f * 1.3f },
	{ ai_run, 4.1f * 1.2f, sentien_sound_footstep },
	{ ai_run, 2.0f }, { ai_run, 2.6f }, { ai_run, 3.8f }, { ai_run, 3.6f },
	{ ai_run, 3.6f }, { ai_run, 4.3f }, { ai_run, 4.2f * 1.2f },
	{ ai_run, 5.2f, sentien_sound_footstep }
};

mframe_t sentien_frames_run_end[] = {
	{ ai_run, 0.8f }, { ai_run, 1.0f }, { ai_run, 1.6f }, { ai_run, 1.4f },
	{ ai_run, 1.5f }, { ai_run, 1.4f }, { ai_run, 1.5f },
	{ ai_run, 1.8f, sentien_sound_footstep }
};

MMOVE_T(sentien_move_run_start) = {
	FRAME_WALK_START_START, FRAME_WALK_START_END, sentien_frames_run_start, sentien_run
};
MMOVE_T(sentien_move_run) = {
	FRAME_WALK_LOOP_START, FRAME_WALK_LOOP_END, sentien_frames_run
};
MMOVE_T(sentien_move_run_end) = {
	FRAME_WALK_END_START, FRAME_WALK_END_END, sentien_frames_run_end, sentien_stand
};

MONSTERINFO_RUN(sentien_run) (edict_t *self) -> void
{
	sentien_laser_off(self);
	if (self->monsterinfo.aiflags & AI_STAND_GROUND)
	{
		M_SetAnimation(self, &sentien_move_stand1);
		return;
	}
	if (self->monsterinfo.active_move == &sentien_move_run)
		return;
	if (self->monsterinfo.active_move == &sentien_move_walk ||
		self->monsterinfo.active_move == &sentien_move_run_start)
		M_SetAnimation(self, &sentien_move_run);
	else
		M_SetAnimation(self, &sentien_move_run_start);
}

void sentien_do_blast(edict_t *self);
void sentien_blast_attack(edict_t *self);
void sentien_post_blast_attack(edict_t *self);

mframe_t sentien_frames_pre_blast_attack[] = {
	{ ai_charge }, { ai_charge }, { ai_charge }, { ai_charge }
};
mframe_t sentien_frames_blast_attack[] = {
	{ ai_charge, 0, sentien_do_blast }, { ai_charge, 0, sentien_do_blast },
	{ ai_charge, 0, sentien_do_blast }, { ai_charge, 0, sentien_do_blast },
	{ ai_charge, 0, sentien_do_blast }, { ai_charge, 0, sentien_do_blast }
};
mframe_t sentien_frames_post_blast_attack[] = {
	{ ai_charge }, { ai_charge }, { ai_charge }, { ai_charge }
};

MMOVE_T(sentien_move_pre_blast_attack) = {
	FRAME_BLAST_PRE_START, FRAME_BLAST_PRE_END,
	sentien_frames_pre_blast_attack, sentien_blast_attack
};
MMOVE_T(sentien_move_blast_attack) = {
	FRAME_BLAST_START, FRAME_BLAST_END,
	sentien_frames_blast_attack, sentien_post_blast_attack
};
MMOVE_T(sentien_move_post_blast_attack) = {
	FRAME_BLAST_POST_START, FRAME_BLAST_POST_END,
	sentien_frames_post_blast_attack, sentien_run
};

void sentien_blast_attack(edict_t *self)
{
	sentien_laser_off(self);
	if (self->enemy && visible(self, self->enemy) && infront(self, self->enemy))
		M_SetAnimation(self, &sentien_move_blast_attack);
	else
		M_SetAnimation(self, &sentien_move_post_blast_attack);
}

void sentien_post_blast_attack(edict_t *self)
{
	float refire = 0.25f;
	if (!self->enemy || !visible(self, self->enemy) || !infront(self, self->enemy))
	{
		M_SetAnimation(self, &sentien_move_post_blast_attack);
		return;
	}
	if (skill->integer == 1)
		refire = 0.40f;
	else if (skill->integer == 2)
		refire = 0.60f;
	else if (skill->integer >= 3)
		refire = 0.75f;
	// If this branch does not change the move, the completed attack move loops,
	// matching the supplied refire behavior.
	if (frandom() > refire)
		M_SetAnimation(self, &sentien_move_post_blast_attack);
}

void sentien_fire_bullet(edict_t *self, const vec3_t &start, const vec3_t &dir, int damage)
{
	if (Zaero_EMPNukeCheck(self, self->s.origin))
	{
		Zaero_PlayEMPMisfire(self);
		return;
	}
	// `damage` is deliberately ignored: the shipped helper hard-codes two.
	(void) damage;
	fire_bullet(self, start, dir, 2, 4,
		DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, MOD_UNKNOWN);
	gi.sound(self, CHAN_BODY, sound_attack1, 1, ATTN_NORM, 0);
}

void sentien_do_blast(edict_t *self)
{
	if (!self->enemy || !self->enemy->inuse)
		return;
	const int32_t index = self->s.frame - FRAME_BLAST_START + 1;
	if (index < 1 || index >= static_cast<int32_t>(std::size(SENTIEN_FLASH_OFFSETS)))
		return;
	vec3_t forward, right;
	AngleVectors(self->s.angles, forward, right, nullptr);
	const vec3_t aim_start = G_ProjectSource(self->s.origin, SENTIEN_FLASH_OFFSETS[0], forward, right);
	vec3_t end = self->enemy->s.origin;
	end[2] += self->enemy->viewheight;
	const vec3_t aim = end - aim_start;
	const vec3_t start = G_ProjectSource(self->s.origin, SENTIEN_FLASH_OFFSETS[index], forward, right);
	if (Zaero_EMPNukeCheck(self, start))
	{
		Zaero_PlayEMPMisfire(self);
		return;
	}
	sentien_fire_bullet(self, start, aim, 5);
}

void sentien_do_laser(edict_t *self);
void sentien_laser_attack(edict_t *self);
void sentien_post_laser_attack(edict_t *self);

mframe_t sentien_frames_pre_laser_attack[] = {
	{ ai_charge }, { ai_charge }, { ai_charge }, { ai_charge }, { ai_charge }
};
mframe_t sentien_frames_laser_attack[] = {
	{ nullptr, 0, sentien_do_laser }, { nullptr, 0, sentien_do_laser },
	{ nullptr, 0, sentien_do_laser }, { nullptr, 0, sentien_do_laser },
	{ nullptr, 0, sentien_do_laser }, { nullptr, 0, sentien_do_laser },
	{ nullptr, 0, sentien_do_laser }, { nullptr, 0, sentien_do_laser },
	{ nullptr, 0, sentien_do_laser }, { nullptr, 0, sentien_do_laser },
	{ nullptr, 0, sentien_do_laser }
};
mframe_t sentien_frames_post_laser_attack[] = {
	{ ai_charge }, { ai_charge }, { ai_charge }, { ai_charge }
};

MMOVE_T(sentien_move_pre_laser_attack) = {
	FRAME_LASER_PRE_START, FRAME_LASER_PRE_END,
	sentien_frames_pre_laser_attack, sentien_laser_attack
};
MMOVE_T(sentien_move_laser_attack) = {
	FRAME_LASER_START, FRAME_LASER_END,
	sentien_frames_laser_attack, sentien_post_laser_attack
};
MMOVE_T(sentien_move_post_laser_attack) = {
	FRAME_LASER_POST_START, FRAME_LASER_POST_END,
	sentien_frames_post_laser_attack, sentien_run
};

void sentien_laser_attack(edict_t *self)
{
	if (self->enemy && visible(self, self->enemy) && infront(self, self->enemy))
		M_SetAnimation(self, &sentien_move_laser_attack);
	else
	{
		M_SetAnimation(self, &sentien_move_post_laser_attack);
		sentien_laser_off(self);
	}
}

void sentien_post_laser_attack(edict_t *self)
{
	M_SetAnimation(self, &sentien_move_post_laser_attack);
	sentien_laser_off(self);
}

void sentien_do_laser(edict_t *self)
{
	if (!self->enemy || !self->enemy->inuse || !sentien_laser_is_owned(self))
		return;
	if (Zaero_EMPNukeCheck(self, self->s.origin))
	{
		Zaero_PlayEMPMisfire(self);
		return;
	}
	const int32_t index = self->s.frame - FRAME_LASER_START;
	if (index < 0 || index >= static_cast<int32_t>(std::size(SENTIEN_LASER_OFFSETS)))
		return;

	// Preserve the original first-frame ordering: turn the persistent beam on
	// at its previous origin/direction, then move and lock its aim for the burst.
	if (self->s.frame == FRAME_LASER_START)
	{
		sentien_laser_off(self);
		self->beam->s.skinnum = 0xf2f2f0f0;
		sentien_laser_on(self);
	}

	vec3_t forward, right, up;
	AngleVectors(self->s.angles, forward, right, up);
	self->beam->s.origin = G_ProjectSource(
		self->s.origin, SENTIEN_LASER_OFFSETS[index], forward, right);

	if (self->s.frame == FRAME_LASER_START)
	{
		vec3_t end = self->enemy->s.origin;
		end[2] += self->enemy->viewheight * 66 / 100;
		end += right * (crandom() * 20.0f);
		const vec3_t aim = (end - self->beam->s.origin).normalized();
		self->beam->s.angles = vectoangles(aim);
		G_SetMovedir(self->beam->s.angles, self->beam->movedir);
		gi.sound(self, CHAN_BODY, sound_attack2, 1, ATTN_NORM, 0);
	}
	gi.linkentity(self->beam);
}

MONSTERINFO_ATTACK(sentien_attack) (edict_t *self) -> void
{
	sentien_laser_off(self);
	if (!self->enemy || !self->enemy->inuse)
	{
		sentien_run(self);
		return;
	}
	const float distance = (self->enemy->s.origin - self->s.origin).length();
	const float choice = frandom();
	if (distance <= 128.0f ||
		(distance <= 500.0f && choice < 0.50f) ||
		(distance > 500.0f && choice < 0.25f))
		M_SetAnimation(self, &sentien_move_pre_blast_attack);
	else
		M_SetAnimation(self, &sentien_move_pre_laser_attack);
}

void sentien_fend_ready(edict_t *self)
{
	if (self->monsterinfo.aiflags & AI_ZAERO_REDUCED_DAMAGE)
		return;
	self->monsterinfo.pausetime = level.time + 1_sec;
}

void sentien_fend_hold(edict_t *self)
{
	if (level.time >= self->monsterinfo.pausetime)
		self->monsterinfo.aiflags &= ~(AI_HOLD_FRAME | AI_ZAERO_REDUCED_DAMAGE);
	else
		self->monsterinfo.aiflags |= AI_HOLD_FRAME | AI_ZAERO_REDUCED_DAMAGE;
}

mframe_t sentien_frames_fend[] = {
	{ ai_move, 0, sentien_sound_fend }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move, 0, sentien_fend_ready }, { ai_move, 0, sentien_fend_hold },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }
};
MMOVE_T(sentien_move_fend) = {
	FRAME_FEND_START, FRAME_FEND_END, sentien_frames_fend, sentien_run
};

MONSTERINFO_DODGE(sentien_fend) (edict_t *self, edict_t *attacker,
	gtime_t eta, trace_t *tr, bool gravity) -> void
{
	(void) eta;
	(void) tr;
	(void) gravity;
	if (self->monsterinfo.active_move == &sentien_move_laser_attack ||
		self->monsterinfo.active_move == &sentien_move_blast_attack)
		return;
	const float chance = skill->integer == 0 ? 0.45f :
		(skill->integer == 1 ? 0.60f : 0.80f);
	if (frandom() > chance)
		return;
	if (!self->enemy)
		self->enemy = attacker;
	M_SetAnimation(self, &sentien_move_fend);
}

mframe_t sentien_frames_pain1[] = {
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }
};
mframe_t sentien_frames_pain2[] = {
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move }
};
mframe_t sentien_frames_pain3[] = {
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move }
};
MMOVE_T(sentien_move_pain1) = {
	FRAME_PAIN1_START, FRAME_PAIN1_END, sentien_frames_pain1, sentien_run
};
MMOVE_T(sentien_move_pain2) = {
	FRAME_PAIN2_START, FRAME_PAIN2_END, sentien_frames_pain2, sentien_run
};
MMOVE_T(sentien_move_pain3) = {
	FRAME_PAIN3_START, FRAME_PAIN3_END, sentien_frames_pain3, sentien_run
};

PAIN(sentien_pain) (edict_t *self, edict_t *other, float kick,
	int damage, const mod_t &mod) -> void
{
	(void) other;
	(void) kick;
	(void) mod;
	if (self->health < self->max_health / 2)
		self->s.skinnum |= 1;
	if (damage <= 10)
		return;
	const float sound_choice = frandom();
	if (sound_choice < 0.33f)
		gi.sound(self, CHAN_BODY, sound_pain1, 1, ATTN_NORM, 0);
	else if (sound_choice < 0.66f)
		gi.sound(self, CHAN_BODY, sound_pain2, 1, ATTN_NORM, 0);
	if (level.time < self->pain_debounce_time ||
		(self->monsterinfo.aiflags & AI_HOLD_FRAME))
		return;
	if (skill->integer >= 1 &&
		(self->monsterinfo.active_move == &sentien_move_laser_attack ||
		 self->monsterinfo.active_move == &sentien_move_blast_attack))
		return;
	if (skill->integer == 3)
		return;
	sentien_laser_off(self);
	const float animation_choice = frandom();
	if (damage > 60 && animation_choice < 0.3f)
		M_SetAnimation(self, &sentien_move_pain3);
	else if (damage > 30 && animation_choice < 0.5f)
		M_SetAnimation(self, &sentien_move_pain2);
	else if (animation_choice < 0.7f)
		M_SetAnimation(self, &sentien_move_pain1);
	self->pain_debounce_time = level.time + 3_sec;
}

MONSTERINFO_SETSKIN(sentien_setskin) (edict_t *self) -> void
{
	self->s.skinnum = self->health < self->max_health / 2 ? 1 : 0;
}

void sentien_dead(edict_t *self);

mframe_t sentien_frames_death1[] = {
	{ ai_move, 0, sentien_sound_die1 },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }
};
mframe_t sentien_frames_death2[] = {
	{ ai_move, 0, sentien_sound_die2 },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }
};
MMOVE_T(sentien_move_death1) = {
	FRAME_DEATH1_START, FRAME_DEATH1_END, sentien_frames_death1, sentien_dead
};
MMOVE_T(sentien_move_death2) = {
	FRAME_DEATH2_START, FRAME_DEATH2_END, sentien_frames_death2, sentien_dead
};

void sentien_dead(edict_t *self)
{
	vec3_t forward, right;
	AngleVectors(self->s.angles, forward, right, nullptr);
	const vec3_t start = G_ProjectSource(self->s.origin, { 6, -50, 0 }, forward, right) - self->s.origin;
	const vec3_t end = G_ProjectSource(self->s.origin, { 44, -12, 0 }, forward, right) - self->s.origin;
	self->mins = { std::min(start[0], end[0]), std::min(start[1], end[1]), -16 };
	self->maxs = { std::max(start[0], end[0]), std::max(start[1], end[1]), 0 };
	self->movetype = MOVETYPE_TOSS;
	self->svflags |= SVF_DEADMONSTER;
	self->nextthink = 0_ms;
	gi.linkentity(self);
}

DIE(sentien_die) (edict_t *self, edict_t *inflictor, edict_t *attacker,
	int damage, const vec3_t &point, const mod_t &mod) -> void
{
	(void) inflictor;
	(void) attacker;
	(void) point;
	sentien_laser_free(self);
	if (M_CheckGib(self, mod))
	{
		gi.sound(self, CHAN_VOICE, gi.soundindex("misc/udeath.wav"), 1, ATTN_NORM, 0);
		ThrowGibs(self, damage, {
			{ "models/objects/gibs/sm_meat/tris.md2" },
			{ 4, "models/objects/gibs/sm_metal/tris.md2", GIB_METALLIC },
			{ "models/objects/gibs/chest/tris.md2" },
			{ "models/objects/gibs/gear/tris.md2", GIB_HEAD | GIB_METALLIC }
		});
		self->deadflag = true;
		return;
	}
	if (self->deadflag)
		return;
	self->deadflag = true;
	self->takedamage = true;
	self->s.skinnum |= 1;
	M_SetAnimation(self, frandom() < 0.80f ? &sentien_move_death1 : &sentien_move_death2);
}

static_assert(std::size(sentien_frames_stand1) == FRAME_STAND1_END - FRAME_STAND1_START + 1);
static_assert(std::size(sentien_frames_stand2) == FRAME_STAND2_END - FRAME_STAND2_START + 1);
static_assert(std::size(sentien_frames_stand3) == FRAME_STAND3_END - FRAME_STAND3_START + 1);
static_assert(std::size(sentien_frames_walk_start) == FRAME_WALK_START_END - FRAME_WALK_START_START + 1);
static_assert(std::size(sentien_frames_walk) == FRAME_WALK_LOOP_END - FRAME_WALK_LOOP_START + 1);
static_assert(std::size(sentien_frames_walk_end) == FRAME_WALK_END_END - FRAME_WALK_END_START + 1);
static_assert(std::size(sentien_frames_run_start) == FRAME_WALK_START_END - FRAME_WALK_START_START + 1);
static_assert(std::size(sentien_frames_run) == FRAME_WALK_LOOP_END - FRAME_WALK_LOOP_START + 1);
static_assert(std::size(sentien_frames_run_end) == FRAME_WALK_END_END - FRAME_WALK_END_START + 1);
static_assert(std::size(sentien_frames_pre_blast_attack) == FRAME_BLAST_PRE_END - FRAME_BLAST_PRE_START + 1);
static_assert(std::size(sentien_frames_blast_attack) == FRAME_BLAST_END - FRAME_BLAST_START + 1);
static_assert(std::size(sentien_frames_post_blast_attack) == FRAME_BLAST_POST_END - FRAME_BLAST_POST_START + 1);
static_assert(std::size(sentien_frames_pre_laser_attack) == FRAME_LASER_PRE_END - FRAME_LASER_PRE_START + 1);
static_assert(std::size(sentien_frames_laser_attack) == FRAME_LASER_END - FRAME_LASER_START + 1);
static_assert(std::size(sentien_frames_post_laser_attack) == FRAME_LASER_POST_END - FRAME_LASER_POST_START + 1);
static_assert(std::size(sentien_frames_fend) == FRAME_FEND_END - FRAME_FEND_START + 1);
static_assert(std::size(sentien_frames_pain1) == FRAME_PAIN1_END - FRAME_PAIN1_START + 1);
static_assert(std::size(sentien_frames_pain2) == FRAME_PAIN2_END - FRAME_PAIN2_START + 1);
static_assert(std::size(sentien_frames_pain3) == FRAME_PAIN3_END - FRAME_PAIN3_START + 1);
static_assert(std::size(sentien_frames_death1) == FRAME_DEATH1_END - FRAME_DEATH1_START + 1);
static_assert(std::size(sentien_frames_death2) == FRAME_DEATH2_END - FRAME_DEATH2_START + 1);
} // namespace

void SP_monster_sentien(edict_t *self)
{
	if (!M_AllowSpawn(self))
	{
		G_FreeEdict(self);
		return;
	}

	sentien_precache();
	self->mass = 500;
	self->s.modelindex = gi.modelindex(SENTIEN_MODEL);
	self->mins = { -32, -32, -16 };
	self->maxs = { 32, 32, 72 };
	// Despite its hovering presentation, supplied Zaero uses the grounded STEP
	// and walkmonster lifecycle. This is a mapper-observable locomotion contract.
	self->movetype = MOVETYPE_STEP;
	self->solid = SOLID_BBOX;
	self->health = 900 * st.health_multiplier;
	self->gib_health = -425;
	self->yaw_speed = 10.0f;
	self->random = 1.0f;
	self->pain = sentien_pain;
	self->die = sentien_die;
	self->monsterinfo.stand = sentien_stand;
	self->monsterinfo.walk = sentien_walk;
	self->monsterinfo.run = sentien_run;
	self->monsterinfo.dodge = sentien_fend;
	self->monsterinfo.attack = sentien_attack;
	self->monsterinfo.setskin = sentien_setskin;
	self->monsterinfo.zaero_damage_scale = 0.85f;
	self->monsterinfo.combat_style = COMBAT_RANGED;
	self->monsterinfo.scale = 1.0f;
	M_SetAnimation(self, &sentien_move_stand1);
	gi.linkentity(self);
	sentien_create_laser(self);

	if (skill->integer == 2)
	{
		self->beam->dmg = static_cast<int32_t>(self->beam->dmg * 1.5f);
		self->yaw_speed *= 1.5f;
	}
	else if (skill->integer >= 3)
	{
		self->beam->dmg = static_cast<int32_t>(self->beam->dmg * 2.5f);
		self->yaw_speed *= 2.0f;
	}

	walkmonster_start(self);
}

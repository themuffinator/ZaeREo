// SPDX-License-Identifier: GPL-2.0-only
#include "../g_local.h"
#include "g_zaero_emp.h"
#include "g_zaero_weapons.h"
#include "g_zaero_zboss.h"

namespace
{
constexpr int32_t FRAME_STAND1_START = 1;
constexpr int32_t FRAME_STAND1_END = 31;
constexpr int32_t FRAME_STAND2_START = 32;
constexpr int32_t FRAME_STAND2_END = 56;
constexpr int32_t FRAME_PRE_HOOK_START = 57;
constexpr int32_t FRAME_PRE_HOOK_END = 66;
constexpr int32_t FRAME_PRE_CANNON_START = 67;
constexpr int32_t FRAME_PRE_CANNON_END = 70;
constexpr int32_t FRAME_ATTACK_ROCKET_START = 71;
constexpr int32_t FRAME_ATTACK_ROCKET_END = 91;
constexpr int32_t FRAME_RELOAD_START = 92;
constexpr int32_t FRAME_RELOAD_END = 98;
constexpr int32_t FRAME_HOOK_FIRE_START = 99;
constexpr int32_t FRAME_HOOK_FIRE_END = 106;
constexpr int32_t FRAME_HOOK_REEL_START = 107;
constexpr int32_t FRAME_HOOK_REEL_END = 109;
constexpr int32_t FRAME_HOOK_MELEE_START = 110;
constexpr int32_t FRAME_HOOK_MELEE_END = 118;
constexpr int32_t FRAME_ATTACK_CANNON_START = 119;
constexpr int32_t FRAME_ATTACK_CANNON_END = 132;
constexpr int32_t FRAME_POST_CANNON_START = 133;
constexpr int32_t FRAME_POST_CANNON_END = 135;
constexpr int32_t FRAME_POST_HOOK_START = 136;
constexpr int32_t FRAME_POST_HOOK_END = 141;
constexpr int32_t FRAME_HOOK_TO_CANNON_START = 142;
constexpr int32_t FRAME_HOOK_TO_CANNON_END = 147;
constexpr int32_t FRAME_CANNON_TO_HOOK_START = 148;
constexpr int32_t FRAME_CANNON_TO_HOOK_END = 153;
constexpr int32_t FRAME_PRE_WALK_START = 154;
constexpr int32_t FRAME_PRE_WALK_END = 160;
constexpr int32_t FRAME_WALK_START = 161;
constexpr int32_t FRAME_WALK_END = 176;
constexpr int32_t FRAME_POST_WALK_START = 177;
constexpr int32_t FRAME_POST_WALK_END = 184;
constexpr int32_t FRAME_PAIN1_START = 185;
constexpr int32_t FRAME_PAIN1_END = 187;
constexpr int32_t FRAME_PAIN2_START = 188;
constexpr int32_t FRAME_PAIN2_END = 192;
constexpr int32_t FRAME_PAIN3_START = 193;
constexpr int32_t FRAME_PAIN3_END = 217;
constexpr int32_t FRAME_DEATH1_START = 218;
constexpr int32_t FRAME_DEATH1_END = 236;
constexpr int32_t FRAME_DEATH2_START = 237;
constexpr int32_t FRAME_DEATH2_END = 281;

constexpr const char *ZBOSS_CLASSNAME = "monster_zboss";
constexpr const char *ZBOSS_HOOK_CLASSNAME = "bosshook";
constexpr const char *ZBOSS_PLASMA_CLASSNAME = "plasmaball";
constexpr const char *ZBOSS_MECH_MODEL = "models/monsters/bossz/mech/tris.md2";
constexpr const char *ZBOSS_PILOT_MODEL = "models/monsters/bossz/pilot/tris.md2";
constexpr const char *ZBOSS_GRAPPLE_MODEL = "models/monsters/bossz/grapple/tris.md2";
constexpr const char *ZBOSS_PLASMA_MODEL = "sprites/plasma1.sp2";
constexpr const char *ZBOSS_EXPLOSION_MODEL = "models/objects/b_explode/tris.md2";

constexpr int32_t ZBOSS_ROCKET_DAMAGE = 70;
constexpr int32_t ZBOSS_ROCKET_SPEED = 500;
constexpr int32_t ZBOSS_PLASMA_DAMAGE = 90;
constexpr float ZBOSS_PLASMA_RADIUS = 130.0f;
constexpr int32_t ZBOSS_HOOK_DAMAGE = 10;
constexpr int32_t ZBOSS_HOOK_SPEED = 1000;
constexpr gtime_t ZBOSS_HOOK_DRAG_LIFETIME = 15_sec;
constexpr gtime_t ZBOSS_PLASMA_LIFETIME = 2500_ms;
constexpr gtime_t ZBOSS_PAIN_DEBOUNCE = 5_sec;
constexpr gtime_t ZBOSS_FIRE_PRESSURE_WINDOW = 1_sec;
constexpr gtime_t ZBOSS_EMP_COOLDOWN = 30_sec;

static cached_soundindex sound_pain1;
static cached_soundindex sound_pain2;
static cached_soundindex sound_pain3;
static cached_soundindex sound_die1;
static cached_soundindex sound_die2;
static cached_soundindex sound_hook_impact;
static cached_soundindex sound_sight;
static cached_soundindex sound_hook_launch;
static cached_soundindex sound_hook_fly;
static cached_soundindex sound_swing;
static cached_soundindex sound_idle1;
static cached_soundindex sound_idle2;
static cached_soundindex sound_walk;
static cached_soundindex sound_raise_gun;
static cached_soundindex sound_lower_gun;
static cached_soundindex sound_switch_attacks;
static cached_soundindex sound_plasma_fly;
static cached_soundindex sound_plasma_explode;
static cached_soundindex sound_plasma_fire;
static cached_soundindex sound_taunt1;
static cached_soundindex sound_taunt2;
static cached_soundindex sound_taunt3;

void zboss_stand(edict_t *self);
void zboss_walk_loop(edict_t *self);
void zboss_run(edict_t *self);
void zboss_run_loop(edict_t *self);
void zboss_choose_next_attack(edict_t *self);
void zboss_reel_hook(edict_t *self);
void zboss_post_hook(edict_t *self);
void zboss_attack_start(edict_t *self);

void zboss_precache()
{
	sound_pain1.assign("monsters/bossz/bpain1.wav");
	sound_pain2.assign("monsters/bossz/bpain2.wav");
	sound_pain3.assign("monsters/bossz/bpain3.wav");
	sound_die1.assign("monsters/bossz/bdeth1.wav");
	sound_die2.assign("monsters/bossz/bdeth2.wav");
	sound_hook_launch.assign("monsters/bossz/bhlaunch.wav");
	sound_hook_impact.assign("monsters/bossz/bhimpact.wav");
	sound_hook_fly.assign("monsters/bossz/bhfly.wav");
	sound_sight.assign("monsters/bossz/bsight1.wav");
	sound_swing.assign("monsters/bossz/bswing.wav");
	sound_idle1.assign("monsters/bossz/bidle1.wav");
	sound_idle2.assign("monsters/bossz/bidle2.wav");
	sound_walk.assign("monsters/bossz/bwalk.wav");
	sound_raise_gun.assign("monsters/bossz/braisegun.wav");
	sound_lower_gun.assign("monsters/bossz/blowergun.wav");
	sound_switch_attacks.assign("monsters/bossz/bswitch.wav");
	sound_plasma_fly.assign("monsters/bossz/bpbfly.wav");
	sound_plasma_explode.assign("monsters/bossz/bpbexplode.wav");
	sound_plasma_fire.assign("monsters/bossz/bpbfire.wav");
	sound_taunt1.assign("monsters/bossz/btaunt1.wav");
	sound_taunt2.assign("monsters/bossz/btaunt2.wav");
	sound_taunt3.assign("monsters/bossz/btaunt3.wav");
}

void zboss_walk_sound(edict_t *self)
{
	gi.sound(self, CHAN_BODY, sound_walk, 1, ATTN_NORM, 0);
}

void zboss_possible_taunt(edict_t *self)
{
	const float choice = frandom();
	// The supplied source performs a second independent random draw for the
	// ten-percent gate; preserve that ordering and distribution.
	if (frandom() >= 0.10f)
		return;
	gi.sound(self, CHAN_VOICE,
		choice < 0.33f ? sound_taunt1 : (choice < 0.66f ? sound_taunt2 : sound_taunt3),
		1, ATTN_NORM, 0);
}

MONSTERINFO_SIGHT(zboss_sight) (edict_t *self, edict_t *other) -> void
{
	(void) other;
	gi.sound(self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0);
}

mframe_t zboss_frames_stand1[] = {
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }
};
mframe_t zboss_frames_stand2[] = {
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand },
	{ ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }, { ai_stand }
};
MMOVE_T(zboss_move_stand1) = {
	FRAME_STAND1_START, FRAME_STAND1_END, zboss_frames_stand1, zboss_stand
};
MMOVE_T(zboss_move_stand2) = {
	FRAME_STAND2_START, FRAME_STAND2_END, zboss_frames_stand2, zboss_stand
};

void zboss_stand_idle(edict_t *self)
{
	if (frandom() < 0.8f)
	{
		gi.sound(self, CHAN_VOICE, sound_idle1, 1, ATTN_NORM, 0);
		M_SetAnimation(self, &zboss_move_stand1);
	}
	else
	{
		gi.sound(self, CHAN_VOICE, sound_idle2, 1, ATTN_NORM, 0);
		M_SetAnimation(self, &zboss_move_stand2);
	}
}

mframe_t zboss_frames_postwalk[] = {
	{ ai_walk, 3 }, { ai_walk, 3 }, { ai_walk, 3 }, { ai_walk, 3 },
	{ ai_walk, 3 }, { ai_walk, 3 }, { ai_walk, 3 }, { ai_walk, 3 }
};
MMOVE_T(zboss_move_postwalk) = {
	FRAME_POST_WALK_START, FRAME_POST_WALK_END, zboss_frames_postwalk, zboss_stand_idle
};

mframe_t zboss_frames_prewalk[] = {
	{ ai_walk, 3 }, { ai_walk, 3 }, { ai_walk, 3 }, { ai_walk, 3 },
	{ ai_walk, 3 }, { ai_walk, 3 }, { ai_walk, 3 }
};
mframe_t zboss_frames_walk[] = {
	{ ai_walk, 2 }, { ai_walk, 3 }, { ai_walk, 3 }, { ai_walk, 4 },
	{ ai_walk, 4 }, { ai_walk, 4 }, { ai_walk, 4 }, { ai_walk, 3, zboss_walk_sound },
	{ ai_walk, 4 }, { ai_walk, 4 }, { ai_walk, 4 }, { ai_walk, 4 },
	{ ai_walk, 3 }, { ai_walk, 2 }, { ai_walk, 2 }, { ai_walk, 3, zboss_walk_sound }
};
MMOVE_T(zboss_move_prewalk) = {
	FRAME_PRE_WALK_START, FRAME_PRE_WALK_END, zboss_frames_prewalk, zboss_walk_loop
};
MMOVE_T(zboss_move_walk) = {
	FRAME_WALK_START, FRAME_WALK_END, zboss_frames_walk, zboss_walk_loop
};

MONSTERINFO_WALK(zboss_walk) (edict_t *self) -> void
{
	M_SetAnimation(self, &zboss_move_prewalk);
}

void zboss_walk_loop(edict_t *self)
{
	M_SetAnimation(self, &zboss_move_walk);
}

mframe_t zboss_frames_prerun[] = {
	{ ai_run, 3 }, { ai_run, 3 }, { ai_run, 3 }, { ai_run, 3 },
	{ ai_run, 3 }, { ai_run, 3 }, { ai_run, 3 }
};
mframe_t zboss_frames_run[] = {
	{ ai_run, 2 }, { ai_run, 3 }, { ai_run, 3 }, { ai_run, 4 },
	{ ai_run, 4 }, { ai_run, 4 }, { ai_run, 4 }, { ai_run, 3, zboss_walk_sound },
	{ ai_run, 4 }, { ai_run, 4 }, { ai_run, 4 }, { ai_run, 4 },
	{ ai_run, 3 }, { ai_run, 2 }, { ai_run, 2 }, { ai_run, 3, zboss_walk_sound }
};
MMOVE_T(zboss_move_prerun) = {
	FRAME_PRE_WALK_START, FRAME_PRE_WALK_END, zboss_frames_prerun, zboss_run_loop
};
MMOVE_T(zboss_move_run) = {
	FRAME_WALK_START, FRAME_WALK_END, zboss_frames_run
};

MONSTERINFO_RUN(zboss_run) (edict_t *self) -> void
{
	if (self->monsterinfo.aiflags & AI_STAND_GROUND)
		zboss_stand(self);
	else
		M_SetAnimation(self, &zboss_move_prerun);
}

void zboss_run_loop(edict_t *self)
{
	if (self->monsterinfo.aiflags & AI_STAND_GROUND)
		zboss_stand(self);
	else
		M_SetAnimation(self, &zboss_move_run);
}

MONSTERINFO_STAND(zboss_stand) (edict_t *self) -> void
{
	if (self->monsterinfo.active_move == &zboss_move_prewalk ||
		self->monsterinfo.active_move == &zboss_move_walk ||
		self->monsterinfo.active_move == &zboss_move_prerun ||
		self->monsterinfo.active_move == &zboss_move_run)
		M_SetAnimation(self, &zboss_move_postwalk);
	else
		zboss_stand_idle(self);
}

mframe_t zboss_frames_pain1[] = {
	{ ai_move }, { ai_move }, { ai_move }
};
mframe_t zboss_frames_pain2[] = {
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move }
};
mframe_t zboss_frames_pain3[] = {
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move }
};
MMOVE_T(zboss_move_pain1) = {
	FRAME_PAIN1_START, FRAME_PAIN1_END, zboss_frames_pain1, zboss_run
};
MMOVE_T(zboss_move_pain2) = {
	FRAME_PAIN2_START, FRAME_PAIN2_END, zboss_frames_pain2, zboss_run
};
MMOVE_T(zboss_move_pain3) = {
	FRAME_PAIN3_START, FRAME_PAIN3_END, zboss_frames_pain3, zboss_run
};

bool zboss_hook_owned(const edict_t *boss)
{
	const edict_t *hook = boss ? boss->beam : nullptr;
	return hook && hook->inuse && hook->owner == boss &&
		hook->count == boss->spawn_count && hook->classname &&
		!strcmp(hook->classname, ZBOSS_HOOK_CLASSNAME);
}

void zboss_free_hook(edict_t *boss, bool restore_model = true)
{
	if (!boss)
		return;
	if (zboss_hook_owned(boss))
	{
		if (boss->beam->enemy && boss->beam->enemy->inuse &&
			boss->beam->enemy->spawn_count == boss->beam->zaero_child_target_spawn_count)
			boss->beam->enemy->velocity = {};
		G_FreeEdict(boss->beam);
	}
	boss->beam = nullptr;
	if (restore_model)
		boss->s.modelindex3 = gi.modelindex(ZBOSS_GRAPPLE_MODEL);
}

void zboss_try_emp(edict_t *self)
{
	if (self->monsterinfo.zaero_boss_emp_cooldown >= level.time)
		return;
	Zaero_FireEMPNuke(self, self->s.origin, 1024);
	self->monsterinfo.zaero_boss_emp_cooldown = level.time + ZBOSS_EMP_COOLDOWN +
		gtime_t::from_sec(frandom() * 5.0f);
}

PAIN(zboss_pain) (edict_t *self, edict_t *other, float kick,
	int damage, const mod_t &mod) -> void
{
	(void) other;
	(void) kick;
	(void) mod;
	const float health_break = self->max_health / 3.0f;
	self->s.skinnum = self->health < health_break ? 2 :
		(self->health < health_break * 2.0f ? 1 : 0);

	const float sound_choice = frandom();
	if (sound_choice < 0.125f)
		gi.sound(self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0);
	else if (sound_choice < 0.25f)
		gi.sound(self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0);
	else if (sound_choice < 0.375f)
		gi.sound(self, CHAN_VOICE, sound_pain3, 1, ATTN_NORM, 0);
	else if (sound_choice < 0.5f)
		gi.sound(self, CHAN_VOICE, sound_taunt1, 1, ATTN_NORM, 0);
	else if (sound_choice < 0.625f)
		gi.sound(self, CHAN_VOICE, sound_taunt2, 1, ATTN_NORM, 0);
	else if (sound_choice < 0.75f)
		gi.sound(self, CHAN_VOICE, sound_taunt3, 1, ATTN_NORM, 0);

	if (self->monsterinfo.zaero_boss_fire_count &&
		self->monsterinfo.zaero_boss_fire_timeout < level.time)
		self->monsterinfo.zaero_boss_fire_count = 0;

	if (self->monsterinfo.zaero_boss_fire_count > 40 &&
		self->monsterinfo.zaero_boss_fire_timeout > level.time)
	{
		zboss_try_emp(self);
		zboss_attack_start(self);
		self->monsterinfo.zaero_boss_fire_count = 0;
		self->monsterinfo.zaero_boss_fire_timeout = 0_ms;
		return;
	}

	self->monsterinfo.zaero_boss_fire_count++;
	self->monsterinfo.zaero_boss_fire_timeout = level.time + ZBOSS_FIRE_PRESSURE_WINDOW;
	if (self->health < self->max_health / 4)
		zboss_try_emp(self);

	if (level.time < self->pain_debounce_time)
		return;
	self->pain_debounce_time = level.time + ZBOSS_PAIN_DEBOUNCE;
	if (skill->integer == 3 || zboss_hook_owned(self))
		return;

	const float animation_choice = frandom();
	if (damage > 150 && animation_choice < 0.33f)
		M_SetAnimation(self, &zboss_move_pain3);
	else if (damage > 80 && animation_choice < 0.66f)
		M_SetAnimation(self, &zboss_move_pain2);
	else if (animation_choice < 0.60f)
		M_SetAnimation(self, &zboss_move_pain1);
}

void zboss_swing(edict_t *self)
{
	fire_hit(self, { MELEE_DISTANCE, 0, -24 }, irandom(15, 20), 800);
}

mframe_t zboss_frames_hook_melee[] = {
	{ ai_charge }, { ai_charge, 0, zboss_swing }, { ai_charge }, { ai_charge },
	{ ai_charge, 0, zboss_possible_taunt }, { ai_charge }, { ai_charge },
	{ ai_charge, 0, zboss_swing }, { ai_charge }
};
MMOVE_T(zboss_move_hook_melee) = {
	FRAME_HOOK_MELEE_START, FRAME_HOOK_MELEE_END, zboss_frames_hook_melee, zboss_post_hook
};

void zboss_melee_finish(edict_t *self)
{
	M_SetAnimation(self, &zboss_move_hook_melee);
	gi.sound(self, CHAN_WEAPON, sound_swing, 1, ATTN_NORM, 0);
}

mframe_t zboss_frames_premelee[] = {
	{ ai_charge }, { ai_charge }, { ai_charge }, { ai_charge }, { ai_charge },
	{ ai_charge, 0, zboss_possible_taunt }, { ai_charge }, { ai_charge },
	{ ai_charge }, { ai_charge }
};
MMOVE_T(zboss_move_premelee) = {
	FRAME_PRE_HOOK_START, FRAME_PRE_HOOK_END, zboss_frames_premelee, zboss_melee_finish
};

MONSTERINFO_MELEE(zboss_melee) (edict_t *self) -> void
{
	gi.sound(self, CHAN_BODY, sound_raise_gun, 1, ATTN_NORM, 0);
	M_SetAnimation(self, &zboss_move_premelee);
}

constexpr vec3_t ROCKET_OFFSETS[] = {
	{ -5, -50, 33 }, { -5, -39, 27 }, { -5, -39, 39 }, { -5, -44, 27 },
	{ -5, -44, 39 }, { -5, -48, 29 }, { -5, -48, 29 }
};

bool zboss_attack_target(edict_t *self, vec3_t &target)
{
	if (self->monsterinfo.aiflags & AI_ZAERO_ONESHOT_TARGET)
	{
		target = self->monsterinfo.zaero_shot_target;
		return true;
	}
	if (!self->enemy || !self->enemy->inuse)
		return false;
	target = self->enemy->s.origin;
	target[2] += self->enemy->viewheight;
	return true;
}

void zboss_fire_flare(edict_t *self)
{
	const int32_t offset = (self->s.frame - FRAME_ATTACK_ROCKET_START) / 3;
	if (offset < 0 || offset >= static_cast<int32_t>(std::size(ROCKET_OFFSETS)))
		return;
	vec3_t target;
	if (!zboss_attack_target(self, target))
		return;
	vec3_t forward, right;
	AngleVectors(self->s.angles, forward, right, nullptr);
	const vec3_t start = G_ProjectSource(self->s.origin, ROCKET_OFFSETS[offset], forward, right);
	const vec3_t direction = (target - start).normalized();
	Zaero_FireFlare(self, start, direction, 10, 1000, 10.0f, 10);
	gi.sound(self, CHAN_WEAPON, gi.soundindex("weapons/flare/shoot.wav"), 1, ATTN_NORM, 0);
}

void zboss_fire_rocket(edict_t *self)
{
	const int32_t offset = (self->s.frame - FRAME_ATTACK_ROCKET_START) / 3;
	if (offset < 0 || offset >= static_cast<int32_t>(std::size(ROCKET_OFFSETS)))
		return;
	vec3_t target;
	if (!zboss_attack_target(self, target))
		return;
	vec3_t forward, right;
	AngleVectors(self->s.angles, forward, right, nullptr);
	const vec3_t start = G_ProjectSource(self->s.origin, ROCKET_OFFSETS[offset], forward, right);
	target += { 100.0f - 200.0f * frandom(), 100.0f - 200.0f * frandom(),
		40.0f - 80.0f * frandom() };
	const vec3_t direction = (target - start).normalized();
	fire_rocket(self, start, direction, ZBOSS_ROCKET_DAMAGE, ZBOSS_ROCKET_SPEED,
		90.0f, ZBOSS_ROCKET_DAMAGE);
	monster_muzzleflash(self, start, MZ2_BOSS2_ROCKET_1);
}

mframe_t zboss_frames_reload[] = {
	{ ai_charge }, { ai_charge }, { ai_charge }, { ai_charge },
	{ ai_charge }, { ai_charge }, { ai_charge }
};
MMOVE_T(zboss_move_reload) = {
	FRAME_RELOAD_START, FRAME_RELOAD_END, zboss_frames_reload, zboss_choose_next_attack
};

void zboss_reload_rockets(edict_t *self)
{
	self->monsterinfo.aiflags &= ~AI_ZAERO_ONESHOT_TARGET;
	M_SetAnimation(self, &zboss_move_reload);
}

mframe_t zboss_frames_rocket_attack[] = {
	{ ai_charge, 0, zboss_fire_flare }, { ai_charge }, { ai_charge },
	{ ai_charge, 0, zboss_fire_rocket }, { ai_charge }, { ai_charge },
	{ ai_charge, 0, zboss_fire_rocket }, { ai_charge }, { ai_charge },
	{ ai_charge, 0, zboss_fire_rocket }, { ai_charge, 0, zboss_possible_taunt }, { ai_charge },
	{ ai_charge, 0, zboss_fire_flare }, { ai_charge }, { ai_charge },
	{ ai_charge, 0, zboss_fire_rocket }, { ai_charge }, { ai_charge },
	{ ai_charge, 0, zboss_fire_rocket }, { ai_charge }, { ai_charge }
};
MMOVE_T(zboss_move_rocket_attack) = {
	FRAME_ATTACK_ROCKET_START, FRAME_ATTACK_ROCKET_END,
	zboss_frames_rocket_attack, zboss_reload_rockets
};

bool zboss_hook_owner_valid(edict_t *hook)
{
	edict_t *boss = hook ? hook->owner : nullptr;
	return boss && boss->inuse && boss->spawn_count == hook->count &&
		boss->classname && !strcmp(boss->classname, ZBOSS_CLASSNAME) && boss->beam == hook;
}

void zboss_write_hook_cable(edict_t *hook, const vec3_t &offset)
{
	edict_t *boss = hook->owner;
	vec3_t forward, right;
	AngleVectors(boss->s.angles, forward, right, nullptr);
	const vec3_t anchor = G_ProjectSource(boss->s.origin, offset, forward, right);
	gi.WriteByte(svc_temp_entity);
	gi.WriteByte(TE_MEDIC_CABLE_ATTACK);
	gi.WriteEntity(hook);
	gi.WritePosition(hook->s.origin);
	gi.WritePosition(anchor);
	gi.multicast(hook->s.origin, MULTICAST_PVS, false);
}

THINK(zboss_hook_drag_think) (edict_t *self) -> void
{
	if (!zboss_hook_owner_valid(self))
	{
		G_FreeEdict(self);
		return;
	}
	if (self->enemy && (!self->enemy->inuse || self->enemy->health <= 0 ||
		self->enemy->spawn_count != self->zaero_child_target_spawn_count))
		self->enemy = nullptr;
	if (self->enemy)
		self->s.origin = self->enemy->s.origin;

	edict_t *boss = self->owner;
	vec3_t forward, right;
	AngleVectors(boss->s.angles, forward, right, nullptr);
	const vec3_t anchor = G_ProjectSource(boss->s.origin, { -5, -24, 34 }, forward, right);
	self->velocity = (anchor - self->s.origin).normalized() * ZBOSS_HOOK_SPEED;
	if (self->enemy)
	{
		self->enemy->velocity = self->velocity;
		self->enemy->velocity[2] *= 1.3f;
	}
	gi.linkentity(self);
	zboss_write_hook_cable(self, { -5, -24, 34 });
	self->nextthink = level.time + FRAME_TIME_MS;
}

TOUCH(zboss_hook_touch) (edict_t *self, edict_t *other,
	const trace_t &tr, bool other_touching_self) -> void
{
	(void) other_touching_self;
	if (!zboss_hook_owner_valid(self) || other == self->owner)
		return;
	if (other->takedamage)
	{
		gi.sound(self, CHAN_WEAPON, sound_hook_impact, 1, ATTN_NORM, 0);
		T_Damage(other, self, self->owner, self->velocity, self->s.origin,
			tr.plane.normal, ZBOSS_HOOK_DAMAGE, 0, DAMAGE_NONE, MOD_ROCKET);
	}
	if (other->client && other->health > 0)
	{
		self->enemy = other;
		self->zaero_child_target_spawn_count = other->spawn_count;
	}
	self->timestamp = level.time + ZBOSS_HOOK_DRAG_LIFETIME;
	self->velocity = {};
	self->think = zboss_hook_drag_think;
	self->nextthink = level.time + FRAME_TIME_MS;
	self->s.frame = 283;
}

THINK(zboss_hook_fly_think) (edict_t *self) -> void
{
	if (!zboss_hook_owner_valid(self))
	{
		G_FreeEdict(self);
		return;
	}
	if (self->timestamp < level.time)
	{
		self->timestamp = level.time + ZBOSS_HOOK_DRAG_LIFETIME;
		self->velocity = {};
		self->enemy = nullptr;
		self->think = zboss_hook_drag_think;
		self->s.frame = 283;
	}
	zboss_write_hook_cable(self, { -3, -24, 34 });
	self->nextthink = level.time + FRAME_TIME_MS;
}

void zboss_fire_hook(edict_t *self)
{
	if (!self->enemy || !self->enemy->inuse)
		return;
	vec3_t forward, right;
	AngleVectors(self->s.angles, forward, right, nullptr);
	const vec3_t start = G_ProjectSource(self->s.origin, { -1, -24, 34 }, forward, right);
	vec3_t target = self->enemy->s.origin;
	target[2] += self->enemy->viewheight;
	const vec3_t direction = (target - start).normalized();
	self->s.modelindex3 = 0;
	gi.sound(self, CHAN_WEAPON, sound_hook_launch, 1, ATTN_NORM, 0);

	edict_t *hook = G_Spawn();
	self->beam = hook;
	hook->classname = ZBOSS_HOOK_CLASSNAME;
	hook->owner = self;
	hook->count = self->spawn_count;
	hook->s.origin = start;
	hook->s.old_origin = start;
	hook->movedir = direction;
	hook->s.angles = vectoangles(direction);
	hook->velocity = direction * ZBOSS_HOOK_SPEED;
	hook->movetype = MOVETYPE_FLYMISSILE;
	hook->svflags |= SVF_PROJECTILE;
	hook->clipmask = MASK_PROJECTILE;
	hook->solid = SOLID_BBOX;
	hook->s.modelindex = gi.modelindex(ZBOSS_GRAPPLE_MODEL);
	hook->s.frame = 282;
	hook->touch = zboss_hook_touch;
	hook->timestamp = level.time + 8_sec;
	hook->think = zboss_hook_fly_think;
	hook->nextthink = level.time + FRAME_TIME_MS;
	hook->s.sound = sound_hook_fly;
	gi.linkentity(hook);
}

void zboss_reel_hook_finish(edict_t *self)
{
	if (!zboss_hook_owned(self))
	{
		self->beam = nullptr;
		self->s.modelindex3 = gi.modelindex(ZBOSS_GRAPPLE_MODEL);
		zboss_choose_next_attack(self);
		return;
	}
	edict_t *hook = self->beam;
	vec3_t forward, right;
	AngleVectors(self->s.angles, forward, right, nullptr);
	const vec3_t anchor = G_ProjectSource(self->s.origin, { -5, -24, 34 }, forward, right);
	const float distance = (anchor - hook->s.origin).length();
	edict_t *victim = hook->enemy && hook->enemy->inuse && hook->enemy->health > 0 &&
		hook->enemy->spawn_count == hook->zaero_child_target_spawn_count
		? hook->enemy : nullptr;
	if (distance <= 80.0f ||
		(hook->think == zboss_hook_drag_think && hook->timestamp < level.time))
	{
		zboss_free_hook(self);
		if (victim)
		{
			victim->velocity = {};
			zboss_melee_finish(self);
		}
		else
			zboss_choose_next_attack(self);
	}
	else
		zboss_reel_hook(self);
}

mframe_t zboss_frames_hook_reel[] = {
	{ ai_charge }, { ai_charge }, { ai_charge }
};
MMOVE_T(zboss_move_hook_reel) = {
	FRAME_HOOK_REEL_START, FRAME_HOOK_REEL_END, zboss_frames_hook_reel, zboss_reel_hook_finish
};

void zboss_reel_hook(edict_t *self)
{
	M_SetAnimation(self, &zboss_move_hook_reel);
}

mframe_t zboss_frames_hook_fire[] = {
	{ ai_charge }, { ai_charge }, { ai_charge },
	{ ai_charge, 0, zboss_possible_taunt }, { ai_charge },
	{ ai_charge, 0, zboss_fire_hook }, { ai_charge }, { ai_charge }
};
MMOVE_T(zboss_move_hook_fire) = {
	FRAME_HOOK_FIRE_START, FRAME_HOOK_FIRE_END, zboss_frames_hook_fire, zboss_reel_hook
};

mframe_t zboss_frames_posthook[] = {
	{ ai_charge }, { ai_charge }, { ai_charge }, { ai_charge }, { ai_charge }, { ai_charge }
};
MMOVE_T(zboss_move_posthook) = {
	FRAME_POST_HOOK_START, FRAME_POST_HOOK_END, zboss_frames_posthook, zboss_run
};

void zboss_post_hook(edict_t *self)
{
	M_SetAnimation(self, &zboss_move_posthook);
}

void zboss_choose_hook_or_rocket(edict_t *self)
{
	if (frandom() < 0.2f && !(self->monsterinfo.aiflags & AI_ZAERO_ONESHOT_TARGET))
		M_SetAnimation(self, &zboss_move_hook_fire);
	else
		M_SetAnimation(self, &zboss_move_rocket_attack);
}

mframe_t zboss_frames_prehook[] = {
	{ ai_charge }, { ai_charge }, { ai_charge }, { ai_charge }, { ai_charge },
	{ ai_charge }, { ai_charge }, { ai_charge }, { ai_charge }, { ai_charge }
};
MMOVE_T(zboss_move_prehook) = {
	FRAME_PRE_HOOK_START, FRAME_PRE_HOOK_END, zboss_frames_prehook, zboss_choose_hook_or_rocket
};

THINK(zboss_plasma_blast_anim) (edict_t *self) -> void
{
	self->s.frame++;
	self->s.skinnum++;
	if (self->s.frame > 1)
		G_FreeEdict(self);
	else
		self->nextthink = level.time + 100_ms;
}

THINK(zboss_plasma_explode) (edict_t *self) -> void
{
	edict_t *attacker = self->owner && self->owner->inuse &&
		self->owner->spawn_count == self->count ? self->owner : self;
	if (self->enemy && self->enemy->inuse)
	{
		const vec3_t center = self->enemy->s.origin +
			((self->enemy->mins + self->enemy->maxs) * 0.5f);
		const int32_t points = static_cast<int32_t>(self->dmg -
			0.5f * (self->s.origin - center).length());
		if (points > 0)
		{
			const vec3_t direction = self->enemy->s.origin - self->s.origin;
			T_Damage(self->enemy, self, attacker, direction, self->s.origin,
				vec3_origin, points, points, DAMAGE_RADIUS, MOD_UNKNOWN);
		}
	}
	T_RadiusDamage(self, attacker, static_cast<float>(self->dmg), self->enemy,
		self->dmg_radius, DAMAGE_NONE, MOD_UNKNOWN);
	self->s.origin += self->velocity * -0.02f;
	self->velocity = {};
	self->movetype = MOVETYPE_NONE;
	self->solid = SOLID_NOT;
	self->touch = nullptr;
	self->s.modelindex = gi.modelindex(ZBOSS_EXPLOSION_MODEL);
	self->s.effects &= ~(EF_BFG | EF_ANIM_ALLFAST);
	self->s.frame = 0;
	self->s.skinnum = 6;
	gi.sound(self, CHAN_AUTO, sound_plasma_explode, 1, ATTN_NORM, 0);
	self->think = zboss_plasma_blast_anim;
	self->nextthink = level.time + 100_ms;
	gi.linkentity(self);
}

TOUCH(zboss_plasma_touch) (edict_t *self, edict_t *other,
	const trace_t &tr, bool other_touching_self) -> void
{
	(void) other_touching_self;
	if (other == self->owner && self->owner && self->owner->inuse &&
		self->owner->spawn_count == self->count)
		return;
	if (tr.surface && (tr.surface->flags & SURF_SKY))
	{
		G_FreeEdict(self);
		return;
	}
	self->enemy = other;
	zboss_plasma_explode(self);
}

void zboss_fire_plasma(edict_t *self, const vec3_t &start,
	const vec3_t &aim_direction, int speed, float distance)
{
	vec3_t forward, right, up;
	AngleVectors(vectoangles(aim_direction), forward, right, up);
	edict_t *plasma = G_Spawn();
	plasma->classname = ZBOSS_PLASMA_CLASSNAME;
	plasma->s.origin = start;
	plasma->s.old_origin = start;
	plasma->velocity = aim_direction * speed;
	plasma->velocity += up * ((distance - 500.0f) + crandom_open() * 10.0f);
	plasma->velocity += right * (crandom_open() * 10.0f);
	plasma->avelocity = { 300, 300, 300 };
	plasma->movetype = MOVETYPE_BOUNCE;
	plasma->svflags |= SVF_PROJECTILE;
	plasma->clipmask = MASK_PROJECTILE;
	plasma->solid = SOLID_BBOX;
	plasma->s.modelindex = gi.modelindex(ZBOSS_PLASMA_MODEL);
	plasma->s.effects = EF_BFG | EF_ANIM_ALLFAST;
	plasma->owner = self;
	plasma->count = self->spawn_count;
	plasma->touch = zboss_plasma_touch;
	plasma->nextthink = level.time + ZBOSS_PLASMA_LIFETIME;
	plasma->think = zboss_plasma_explode;
	plasma->dmg = ZBOSS_PLASMA_DAMAGE;
	plasma->dmg_radius = ZBOSS_PLASMA_RADIUS;
	plasma->s.sound = sound_plasma_fly;
	gi.sound(self, CHAN_AUTO, sound_plasma_fire, 1, ATTN_NORM, 0);
	gi.linkentity(plasma);
}

constexpr vec3_t CANNON_OFFSETS[] = {
	{ -19, -44, 30 }, { -14, -33, 32 }, { -4, -45, 32 }, { -2, -34, 32 },
	{ 7, -49, 32 }, { 6, -36, 34 }, { 6, -36, 34 }
};

void zboss_fire_cannon(edict_t *self)
{
	const int32_t offset = (self->s.frame - FRAME_ATTACK_CANNON_START) / 2;
	if (offset < 0 || offset >= static_cast<int32_t>(std::size(CANNON_OFFSETS)))
		return;
	vec3_t target;
	if (!zboss_attack_target(self, target) || !self->enemy || !self->enemy->inuse)
		return;
	vec3_t forward, right;
	AngleVectors(self->s.angles, forward, right, nullptr);
	const vec3_t start = G_ProjectSource(self->s.origin, CANNON_OFFSETS[offset], forward, right);
	if (self->monsterinfo.zaero_boss_cannon_spread != 0.0f)
		target += right * self->monsterinfo.zaero_boss_cannon_spread;
	self->monsterinfo.zaero_boss_cannon_spread -= 50.0f;
	const vec3_t direction = (target - start).normalized();
	const float distance = max(700.0f, (self->enemy->s.origin - self->s.origin).length());
	const int32_t speed = skill->integer < 2 ? 700 :
		static_cast<int32_t>(distance * (skill->integer < 3 ? 1.2f : 1.6f));
	zboss_fire_plasma(self, start, direction, speed, distance);
}

mframe_t zboss_frames_cannon_attack[] = {
	{ ai_charge, 0, zboss_fire_cannon }, { ai_charge },
	{ ai_charge, 0, zboss_fire_cannon }, { ai_charge },
	{ ai_charge, 0, zboss_fire_cannon }, { ai_charge },
	{ ai_charge, 0, zboss_fire_cannon }, { ai_charge, 0, zboss_possible_taunt },
	{ ai_charge, 0, zboss_fire_cannon }, { ai_charge },
	{ ai_charge, 0, zboss_fire_cannon }, { ai_charge },
	{ ai_charge, 0, zboss_fire_cannon }, { ai_charge }
};
MMOVE_T(zboss_move_cannon_attack) = {
	FRAME_ATTACK_CANNON_START, FRAME_ATTACK_CANNON_END,
	zboss_frames_cannon_attack, zboss_choose_next_attack
};

void zboss_fire_cannons(edict_t *self)
{
	M_SetAnimation(self, &zboss_move_cannon_attack);
	self->monsterinfo.zaero_boss_cannon_spread = 150.0f;
}

mframe_t zboss_frames_precannon[] = {
	{ ai_charge }, { ai_charge }, { ai_charge }, { ai_charge }
};
MMOVE_T(zboss_move_precannon) = {
	FRAME_PRE_CANNON_START, FRAME_PRE_CANNON_END, zboss_frames_precannon, zboss_fire_cannons
};

mframe_t zboss_frames_postcannon[] = {
	{ ai_charge }, { ai_charge }, { ai_charge }
};
MMOVE_T(zboss_move_postcannon) = {
	FRAME_POST_CANNON_START, FRAME_POST_CANNON_END, zboss_frames_postcannon, zboss_run
};

void zboss_post_cannon(edict_t *self)
{
	M_SetAnimation(self, &zboss_move_postcannon);
}

mframe_t zboss_frames_hook_to_cannon[] = {
	{ ai_charge }, { ai_charge }, { ai_charge }, { ai_charge }, { ai_charge }, { ai_charge }
};
MMOVE_T(zboss_move_hook_to_cannon) = {
	FRAME_HOOK_TO_CANNON_START, FRAME_HOOK_TO_CANNON_END,
	zboss_frames_hook_to_cannon, zboss_fire_cannons
};
mframe_t zboss_frames_cannon_to_hook[] = {
	{ ai_charge }, { ai_charge }, { ai_charge },
	{ ai_charge, 0, zboss_possible_taunt }, { ai_charge }, { ai_charge }
};
MMOVE_T(zboss_move_cannon_to_hook) = {
	FRAME_CANNON_TO_HOOK_START, FRAME_CANNON_TO_HOOK_END,
	zboss_frames_cannon_to_hook, zboss_choose_hook_or_rocket
};

void zboss_choose_next_attack(edict_t *self)
{
	if (!self->enemy || !self->enemy->inuse)
		return;
	self->monsterinfo.aiflags &= ~AI_ZAERO_ONESHOT_TARGET;
	if (frandom() < 0.5f)
	{
		if (frandom() < 0.4f)
		{
			if (self->monsterinfo.active_move == &zboss_move_cannon_attack)
			{
				gi.sound(self, CHAN_BODY, sound_switch_attacks, 1, ATTN_NORM, 0);
				M_SetAnimation(self, &zboss_move_cannon_to_hook);
			}
			else
				zboss_choose_hook_or_rocket(self);
		}
		else if (self->monsterinfo.active_move == &zboss_move_cannon_attack)
			zboss_fire_cannons(self);
		else
		{
			gi.sound(self, CHAN_BODY, sound_switch_attacks, 1, ATTN_NORM, 0);
			M_SetAnimation(self, &zboss_move_hook_to_cannon);
		}
	}
	else
	{
		gi.sound(self, CHAN_BODY, sound_lower_gun, 1, ATTN_NORM, 0);
		if (self->monsterinfo.active_move == &zboss_move_cannon_attack)
			zboss_post_cannon(self);
		else
			zboss_post_hook(self);
	}
}

MONSTERINFO_ATTACK(zboss_attack_start) (edict_t *self) -> void
{
	if (!self->enemy || !self->enemy->inuse)
		return;
	// Scripted targets and the 42nd-pain retaliation may interrupt a grapple.
	// Release the victim and retire the generation-owned child before changing
	// attack state instead of leaking the legacy `laser` allocation.
	if (zboss_hook_owned(self))
		zboss_free_hook(self);
	gi.sound(self, CHAN_BODY, sound_raise_gun, 1, ATTN_NORM, 0);
	M_SetAnimation(self, frandom() < 0.4f ? &zboss_move_prehook : &zboss_move_precannon);
}

void zboss_dead(edict_t *self)
{
	self->mins = { -32, -74, -30 };
	self->maxs = { 32, 40, 12 };
	self->movetype = MOVETYPE_TOSS;
	self->svflags |= SVF_DEADMONSTER;
	self->nextthink = 0_ms;
	gi.linkentity(self);
}

mframe_t zboss_frames_death1[] = {
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }
};
MMOVE_T(zboss_move_death1) = {
	FRAME_DEATH1_START, FRAME_DEATH1_END, zboss_frames_death1, zboss_dead
};

void zboss_dead_rocket(edict_t *self, const vec3_t &offset, vec3_t direction)
{
	vec3_t forward, right;
	AngleVectors(self->s.angles, forward, right, nullptr);
	const vec3_t start = G_ProjectSource(self->s.origin, offset, forward, right);
	fire_rocket(self, start, direction, ZBOSS_ROCKET_DAMAGE, ZBOSS_ROCKET_SPEED,
		90.0f, ZBOSS_ROCKET_DAMAGE);
	monster_muzzleflash(self, start, MZ2_BOSS2_ROCKET_1);
}

void zboss_dead_rocket1(edict_t *self)
{
	vec3_t forward;
	AngleVectors(self->s.angles, forward, nullptr, nullptr);
	zboss_dead_rocket(self, { -26, -26, 25 }, forward);
}
void zboss_dead_rocket2(edict_t *self)
{
	vec3_t forward;
	AngleVectors(self->s.angles, forward, nullptr, nullptr);
	forward[1] += 10.0f;
	zboss_dead_rocket(self, { -16, -21, 20 }, forward);
}
void zboss_dead_rocket3(edict_t *self)
{
	vec3_t up;
	AngleVectors(self->s.angles, nullptr, nullptr, up);
	zboss_dead_rocket(self, { -17, -20, 30 }, up);
}
void zboss_dead_rocket4(edict_t *self)
{
	vec3_t up;
	AngleVectors(self->s.angles, nullptr, nullptr, up);
	zboss_dead_rocket(self, { -8, -16, 17 }, up);
}
void zboss_dead_rocket5(edict_t *self)
{
	vec3_t forward;
	AngleVectors(self->s.angles, forward, nullptr, nullptr);
	zboss_dead_rocket(self, { -10, -16, 30 }, -forward);
}
void zboss_dead_rocket6(edict_t *self)
{
	vec3_t forward;
	AngleVectors(self->s.angles, forward, nullptr, nullptr);
	forward = -forward;
	forward[1] -= 10.0f;
	zboss_dead_rocket(self, { 0, -18, 25 }, forward);
}
void zboss_dead_rocket7(edict_t *self)
{
	vec3_t forward;
	AngleVectors(self->s.angles, forward, nullptr, nullptr);
	forward = -forward;
	forward[1] -= 10.0f;
	zboss_dead_rocket(self, { 17, -27, 30 }, forward);
}

void zboss_dead_cannon(edict_t *self, const vec3_t &offset)
{
	vec3_t forward, right;
	AngleVectors(self->s.angles, forward, right, nullptr);
	const vec3_t start = G_ProjectSource(self->s.origin, offset, forward, right);
	zboss_fire_plasma(self, start, forward, 700, 700.0f);
	monster_muzzleflash(self, start, MZ2_GUNNER_GRENADE_1);
}
void zboss_dead_cannon1(edict_t *self) { zboss_dead_cannon(self, { 9, -46, 33 }); }
void zboss_dead_cannon2(edict_t *self) { zboss_dead_cannon(self, { 3, -31, 37 }); }
void zboss_dead_cannon3(edict_t *self) { zboss_dead_cannon(self, { -21, -19, 24 }); }

THINK(zboss_dead_hook_expire) (edict_t *self) -> void
{
	if (self->owner && self->owner->inuse &&
		self->owner->spawn_count == self->count && self->owner->beam == self)
		self->owner->beam = nullptr;
	G_FreeEdict(self);
}

TOUCH(zboss_dead_hook_touch) (edict_t *self, edict_t *other,
	const trace_t &tr, bool other_touching_self) -> void
{
	(void) other_touching_self;
	if (other == self->owner)
		return;
	if (other->takedamage && self->owner && self->owner->inuse &&
		self->owner->spawn_count == self->count)
	{
		gi.sound(self, CHAN_WEAPON, sound_hook_impact, 1, ATTN_NORM, 0);
		T_Damage(other, self, self->owner, self->velocity, self->s.origin,
			tr.plane.normal, ZBOSS_HOOK_DAMAGE, 0, DAMAGE_NONE, MOD_ROCKET);
	}
	zboss_dead_hook_expire(self);
}

void zboss_fire_dead_hook(edict_t *self)
{
	if (!self->s.modelindex3 || zboss_hook_owned(self))
		return;
	vec3_t forward, right, up;
	AngleVectors(self->s.angles, forward, right, up);
	const vec3_t start = G_ProjectSource(self->s.origin, { -35, 8, 28 }, forward, right);
	self->s.modelindex3 = 0;
	gi.sound(self, CHAN_WEAPON, sound_hook_launch, 1, ATTN_NORM, 0);
	edict_t *hook = G_Spawn();
	self->beam = hook;
	hook->classname = ZBOSS_HOOK_CLASSNAME;
	hook->owner = self;
	hook->count = self->spawn_count;
	hook->s.origin = start;
	hook->s.old_origin = start;
	hook->movedir = up;
	hook->s.angles = vectoangles(up);
	hook->velocity = up * 500.0f;
	hook->movetype = MOVETYPE_FLYMISSILE;
	hook->svflags |= SVF_PROJECTILE;
	hook->clipmask = MASK_PROJECTILE;
	hook->solid = SOLID_BBOX;
	hook->s.modelindex = gi.modelindex(ZBOSS_GRAPPLE_MODEL);
	hook->s.frame = 282;
	hook->touch = zboss_dead_hook_touch;
	hook->nextthink = level.time + 16_sec;
	hook->think = zboss_dead_hook_expire;
	hook->s.sound = sound_hook_fly;
	gi.linkentity(hook);
}

mframe_t zboss_frames_death2[] = {
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move },
	{ ai_move, 0, zboss_dead_rocket1 }, { ai_move, 0, zboss_dead_rocket2 },
	{ ai_move, 0, zboss_dead_rocket3 }, { ai_move, 0, zboss_dead_rocket4 },
	{ ai_move, 0, zboss_dead_rocket5 }, { ai_move, 0, zboss_dead_rocket6 },
	{ ai_move, 0, zboss_dead_rocket7 }, { ai_move },
	{ ai_move, 0, zboss_dead_cannon1 }, { ai_move, 0, zboss_dead_cannon2 },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move, 0, zboss_dead_cannon3 }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move, 0, zboss_fire_dead_hook }
};
MMOVE_T(zboss_move_death2) = {
	FRAME_DEATH2_START, FRAME_DEATH2_END, zboss_frames_death2, zboss_dead
};

DIE(zboss_die) (edict_t *self, edict_t *inflictor, edict_t *attacker,
	int damage, const vec3_t &point, const mod_t &mod) -> void
{
	(void) inflictor;
	(void) attacker;
	(void) point;
	zboss_free_hook(self, false);
	if (M_CheckGib(self, mod))
	{
		self->s.modelindex2 = 0;
		self->s.modelindex3 = 0;
		gi.sound(self, CHAN_VOICE, gi.soundindex("misc/udeath.wav"), 1, ATTN_NORM, 0);
		ThrowGibs(self, damage, {
			{ 2, "models/objects/gibs/bone/tris.md2" },
			{ 4, "models/objects/gibs/sm_meat/tris.md2" },
			{ "models/objects/gibs/head2/tris.md2", GIB_HEAD }
		});
		self->deadflag = true;
		return;
	}
	if (self->deadflag)
		return;
	self->deadflag = true;
	self->takedamage = true;
	if (frandom() < 0.5f)
	{
		gi.sound(self, CHAN_VOICE, sound_die1, 1, ATTN_NORM, 0);
		M_SetAnimation(self, &zboss_move_death1);
	}
	else
	{
		gi.sound(self, CHAN_VOICE, sound_die2, 1, ATTN_NORM, 0);
		M_SetAnimation(self, &zboss_move_death2);
	}
}

static_assert(std::size(zboss_frames_stand1) == FRAME_STAND1_END - FRAME_STAND1_START + 1);
static_assert(std::size(zboss_frames_stand2) == FRAME_STAND2_END - FRAME_STAND2_START + 1);
static_assert(std::size(zboss_frames_postwalk) == FRAME_POST_WALK_END - FRAME_POST_WALK_START + 1);
static_assert(std::size(zboss_frames_prewalk) == FRAME_PRE_WALK_END - FRAME_PRE_WALK_START + 1);
static_assert(std::size(zboss_frames_walk) == FRAME_WALK_END - FRAME_WALK_START + 1);
static_assert(std::size(zboss_frames_prerun) == FRAME_PRE_WALK_END - FRAME_PRE_WALK_START + 1);
static_assert(std::size(zboss_frames_run) == FRAME_WALK_END - FRAME_WALK_START + 1);
static_assert(std::size(zboss_frames_pain1) == FRAME_PAIN1_END - FRAME_PAIN1_START + 1);
static_assert(std::size(zboss_frames_pain2) == FRAME_PAIN2_END - FRAME_PAIN2_START + 1);
static_assert(std::size(zboss_frames_pain3) == FRAME_PAIN3_END - FRAME_PAIN3_START + 1);
static_assert(std::size(zboss_frames_hook_melee) == FRAME_HOOK_MELEE_END - FRAME_HOOK_MELEE_START + 1);
static_assert(std::size(zboss_frames_premelee) == FRAME_PRE_HOOK_END - FRAME_PRE_HOOK_START + 1);
static_assert(std::size(zboss_frames_reload) == FRAME_RELOAD_END - FRAME_RELOAD_START + 1);
static_assert(std::size(zboss_frames_rocket_attack) == FRAME_ATTACK_ROCKET_END - FRAME_ATTACK_ROCKET_START + 1);
static_assert(std::size(zboss_frames_hook_reel) == FRAME_HOOK_REEL_END - FRAME_HOOK_REEL_START + 1);
static_assert(std::size(zboss_frames_hook_fire) == FRAME_HOOK_FIRE_END - FRAME_HOOK_FIRE_START + 1);
static_assert(std::size(zboss_frames_posthook) == FRAME_POST_HOOK_END - FRAME_POST_HOOK_START + 1);
static_assert(std::size(zboss_frames_prehook) == FRAME_PRE_HOOK_END - FRAME_PRE_HOOK_START + 1);
static_assert(std::size(zboss_frames_cannon_attack) == FRAME_ATTACK_CANNON_END - FRAME_ATTACK_CANNON_START + 1);
static_assert(std::size(zboss_frames_precannon) == FRAME_PRE_CANNON_END - FRAME_PRE_CANNON_START + 1);
static_assert(std::size(zboss_frames_postcannon) == FRAME_POST_CANNON_END - FRAME_POST_CANNON_START + 1);
static_assert(std::size(zboss_frames_hook_to_cannon) == FRAME_HOOK_TO_CANNON_END - FRAME_HOOK_TO_CANNON_START + 1);
static_assert(std::size(zboss_frames_cannon_to_hook) == FRAME_CANNON_TO_HOOK_END - FRAME_CANNON_TO_HOOK_START + 1);
static_assert(std::size(zboss_frames_death1) == FRAME_DEATH1_END - FRAME_DEATH1_START + 1);
static_assert(std::size(zboss_frames_death2) == FRAME_DEATH2_END - FRAME_DEATH2_START + 1);
} // namespace

void SP_monster_zboss(edict_t *self)
{
	if (!M_AllowSpawn(self))
	{
		G_FreeEdict(self);
		return;
	}
	zboss_precache();
	gi.modelindex(ZBOSS_PLASMA_MODEL);
	gi.modelindex(ZBOSS_EXPLOSION_MODEL);
	gi.soundindex("items/empnuke/emp_trg.wav");
	self->s.modelindex = gi.modelindex(ZBOSS_MECH_MODEL);
	self->s.modelindex2 = gi.modelindex(ZBOSS_PILOT_MODEL);
	self->s.modelindex3 = gi.modelindex(ZBOSS_GRAPPLE_MODEL);
	self->mins = { -32, -74, -30 };
	self->maxs = { 32, 50, 74 };
	self->movetype = MOVETYPE_STEP;
	self->solid = SOLID_BBOX;
	self->monsterinfo.aiflags |= AI_ZAERO_MONSTER_REDUCED_DAMAGE;
	self->monsterinfo.zaero_damage_scale = 0.25f;
	const int32_t skill_health = skill->integer <= 0 ? 3000 :
		(skill->integer == 1 ? 4500 : (skill->integer == 2 ? 6000 : 8000));
	self->health = skill_health * st.health_multiplier;
	self->gib_health = -700;
	self->mass = 1000;
	self->pain = zboss_pain;
	self->die = zboss_die;
	self->monsterinfo.stand = zboss_stand;
	self->monsterinfo.walk = zboss_walk;
	self->monsterinfo.run = zboss_run;
	self->monsterinfo.attack = zboss_attack_start;
	self->monsterinfo.melee = zboss_melee;
	self->monsterinfo.sight = zboss_sight;
	self->monsterinfo.idle = zboss_possible_taunt;
	self->monsterinfo.scale = 1.0f;
	self->monsterinfo.combat_style = COMBAT_MIXED;
	M_SetAnimation(self, &zboss_move_stand1);
	gi.linkentity(self);
	walkmonster_start(self);
}

// SPDX-License-Identifier: GPL-2.0-only

#include "../g_local.h"
#include "g_zaero_hound.h"

// FindTarget is intentionally internal to the native AI implementation but is
// the compatibility point used by Zaero's schooling movement callbacks.
bool FindTarget(edict_t *self);

namespace
{
constexpr spawnflags_t SPAWNFLAG_HOUND_SCHOOLING = 8_spawnflag;
constexpr float HOUND_SCHOOL_RADIUS = 500.0f;
constexpr float HOUND_NEIGHBOR_SCAN_RADIUS = 2000.0f;
constexpr float HOUND_SCHOOL_MAX_SPEED = 4.0f;
constexpr float HOUND_SCHOOL_MIN_SPEED = 3.0f;
constexpr float HOUND_SCHOOL_DECAY = 0.95f;
constexpr float HOUND_SCHOOL_MIN_DISTANCE = 100.0f;

constexpr int32_t FRAME_HANDLER_SEPARATE = 122;
constexpr int32_t FRAME_HANDLER_LEAP_LOOP = 124;
constexpr int32_t FRAME_HANDLER_LEAP_END = 125;
constexpr int32_t FRAME_HANDLER_RELEASE_END = 128;
constexpr int32_t FRAME_STAND1_START = 129;
constexpr int32_t FRAME_STAND1_END = 147;
constexpr int32_t FRAME_STAND2_START = 148;
constexpr int32_t FRAME_STAND2_END = 168;
constexpr int32_t FRAME_WALK_START = 169;
constexpr int32_t FRAME_WALK_END = 176;
constexpr int32_t FRAME_RUN_START = 177;
constexpr int32_t FRAME_RUN_END = 183;
constexpr int32_t FRAME_LEAP_START = 184;
constexpr int32_t FRAME_LEAP_LOOP = 187;
constexpr int32_t FRAME_LEAP_END_START = 188;
constexpr int32_t FRAME_LEAP_END = 190;
constexpr int32_t FRAME_ATTACK1_START = 191;
constexpr int32_t FRAME_ATTACK1_END = 194;
constexpr int32_t FRAME_ATTACK2_START = 195;
constexpr int32_t FRAME_ATTACK2_END = 207;
constexpr int32_t FRAME_PAIN1_START = 208;
constexpr int32_t FRAME_PAIN1_END = 211;
constexpr int32_t FRAME_PAIN2_START = 212;
constexpr int32_t FRAME_PAIN2_END = 219;
constexpr int32_t FRAME_DEATH_START = 220;
constexpr int32_t FRAME_DEATH_END = 231;

constexpr const char *HOUND_CLASSNAME = "monster_hound";
constexpr const char *HOUND_MODEL = "models/monsters/guard/hound/tris.md2";

static cached_soundindex sound_pain1;
static cached_soundindex sound_pain2;
static cached_soundindex sound_die;
static cached_soundindex sound_launch;
static cached_soundindex sound_impact;
static cached_soundindex sound_sight;
static cached_soundindex sound_bite;
static cached_soundindex sound_bite_miss;
static cached_soundindex sound_jump;

void hound_stand(edict_t *self);
void hound_walk(edict_t *self);
void hound_run(edict_t *self);

void hound_precache_internal()
{
	sound_pain1.assign("monsters/hound/hpain1.wav");
	sound_pain2.assign("monsters/hound/hpain2.wav");
	sound_die.assign("monsters/hound/hdeth1.wav");
	sound_launch.assign("monsters/hound/hlaunch.wav");
	sound_impact.assign("monsters/hound/himpact.wav");
	sound_sight.assign("monsters/hound/hsight1.wav");
	sound_jump.assign("monsters/hound/hjump.wav");
	sound_bite.assign("monsters/hound/hbite1.wav");
	sound_bite_miss.assign("monsters/hound/hbite2.wav");
}

bool hound_is_live_peer(edict_t *self, edict_t *candidate)
{
	return candidate != self && candidate->inuse && candidate->classname &&
		!strcmp(candidate->classname, HOUND_CLASSNAME) && candidate->health > 0;
}

bool hound_adjust_roam_yaw(edict_t *self, float distance)
{
	const float current = anglemod(self->s.angles[YAW]);
	if ((current <= self->ideal_yaw - 1.0f || current > self->ideal_yaw + 1.0f) &&
		fabs(current - self->ideal_yaw) <= 359.0f)
		return false;

	vec3_t forward;
	AngleVectors(self->s.angles, forward, nullptr, nullptr);
	vec3_t end = self->s.origin + (forward * distance);
	trace_t tr = gi.trace(self->s.origin, self->mins, self->maxs, end, self, MASK_SOLID);
	if (tr.fraction >= 1.0f)
		return false;

	if (frandom() > 0.75f)
	{
		self->ideal_yaw = vectoyaw(forward) + 180.0f;
		return true;
	}

	const float direction = frandom() > 0.5f ? -45.0f : 45.0f;
	vec3_t angles = self->s.angles;
	for (int32_t attempt = 0; attempt < 100 && tr.fraction < 1.0f; attempt++)
	{
		self->ideal_yaw = vectoyaw(forward) + (frandom() * direction);
		angles[YAW] = anglemod(self->ideal_yaw);
		AngleVectors(angles, forward, nullptr, nullptr);
		end = self->s.origin + (forward * distance);
		tr = gi.trace(self->s.origin, self->mins, self->maxs, end, self, MASK_SOLID);
	}
	return true;
}

int32_t hound_school(edict_t *self)
{
	int32_t visible_ahead = 0;
	float total_speed = 0.0f;
	float total_bearing = 0.0f;
	float nearest_distance = std::numeric_limits<float>::max();
	edict_t *nearest = nullptr;

	for (edict_t *peer = findradius(nullptr, self->s.origin, HOUND_NEIGHBOR_SCAN_RADIUS);
		 peer; peer = findradius(peer, self->s.origin, HOUND_NEIGHBOR_SCAN_RADIUS))
	{
		if (!hound_is_live_peer(self, peer))
			continue;
		const float distance = (self->s.origin - peer->s.origin).length();
		if (distance > HOUND_SCHOOL_RADIUS || !visible(self, peer) || !infront(self, peer))
			continue;

		// Legacy Zaero intentionally includes non-schooling Hounds and averages
		// yaw arithmetically, including the visible 359/1 degree wrap quirk.
		visible_ahead++;
		total_speed += peer->speed;
		total_bearing += anglemod(peer->s.angles[YAW]);
		if (distance < nearest_distance)
		{
			nearest_distance = distance;
			nearest = peer;
		}
	}

	if (visible_ahead > 0)
	{
		self->speed = (total_speed / visible_ahead) * 1.5f;
		self->ideal_yaw = total_bearing / visible_ahead;
		if (!hound_adjust_roam_yaw(self, 10.0f) &&
			nearest && nearest_distance <= HOUND_SCHOOL_MIN_DISTANCE)
		{
			// Preserve Zaero's observable proximity quirk: copy the nearest
			// Hound's heading instead of steering away from it.
			self->ideal_yaw = nearest->s.angles[YAW];
			self->speed = nearest->speed;
		}
	}
	else
	{
		self->speed *= HOUND_SCHOOL_DECAY;
		hound_adjust_roam_yaw(self, 100.0f);
		for (edict_t *peer = findradius(nullptr, self->s.origin, HOUND_NEIGHBOR_SCAN_RADIUS);
			 peer; peer = findradius(peer, self->s.origin, HOUND_NEIGHBOR_SCAN_RADIUS))
		{
			if (!hound_is_live_peer(self, peer))
				continue;
			const float distance = (self->s.origin - peer->s.origin).length();
			if (distance <= HOUND_SCHOOL_RADIUS && visible(self, peer))
				peer->ideal_yaw = self->ideal_yaw + frandom(-20.0f, 20.0f);
		}
	}

	self->speed = std::clamp(self->speed, HOUND_SCHOOL_MIN_SPEED, HOUND_SCHOOL_MAX_SPEED);
	if (self->speed <= 1.0f)
		return 0;
	if (self->speed <= 3.0f)
		return 1;
	return 2;
}

void hound_school_stand(edict_t *self, float dist)
{
	if (!(self->monsterinfo.aiflags & AI_ZAERO_SCHOOLING))
	{
		ai_stand(self, dist);
		return;
	}
	if (self->enemy || FindTarget(self))
	{
		ai_stand(self, dist);
		return;
	}
	const int32_t style = hound_school(self);
	if (style == 1)
		self->monsterinfo.walk(self);
	else if (style == 2)
		self->monsterinfo.run(self);
	if (dist)
		M_walkmove(self, self->ideal_yaw, dist);
}

void hound_school_walk(edict_t *self, float dist)
{
	if (!(self->monsterinfo.aiflags & AI_ZAERO_SCHOOLING))
	{
		ai_walk(self, dist);
		return;
	}
	if (self->enemy || FindTarget(self))
	{
		ai_walk(self, dist);
		return;
	}
	const int32_t style = hound_school(self);
	if (style == 0)
		self->monsterinfo.stand(self);
	else if (style == 2)
		self->monsterinfo.run(self);
	SV_StepDirection(self, self->ideal_yaw, dist, false);
}

void hound_school_run(edict_t *self, float dist)
{
	if (!(self->monsterinfo.aiflags & AI_ZAERO_SCHOOLING))
	{
		ai_run(self, dist);
		return;
	}
	if (self->enemy || FindTarget(self))
	{
		ai_run(self, dist);
		return;
	}
	const int32_t style = hound_school(self);
	if (style == 0)
		self->monsterinfo.stand(self);
	else if (style == 1)
		self->monsterinfo.walk(self);
	SV_StepDirection(self, self->ideal_yaw, dist, false);
}

void hound_launch_sound(edict_t *self)
{
	gi.sound(self, CHAN_WEAPON, sound_launch, 1, ATTN_NORM, 0);
}

MONSTERINFO_SIGHT(hound_sight) (edict_t *self, edict_t *other) -> void
{
	gi.sound(self, CHAN_WEAPON, sound_sight, 1, ATTN_NORM, 0);
}

mframe_t hound_frames_stand1[] = {
	{ hound_school_stand }, { hound_school_stand }, { hound_school_stand },
	{ hound_school_stand }, { hound_school_stand }, { hound_school_stand },
	{ hound_school_stand }, { hound_school_stand }, { hound_school_stand },
	{ hound_school_stand }, { hound_school_stand }, { hound_school_stand },
	{ hound_school_stand }, { hound_school_stand }, { hound_school_stand },
	{ hound_school_stand }, { hound_school_stand }, { hound_school_stand },
	{ hound_school_stand }
};
MMOVE_T(hound_move_stand1) = { FRAME_STAND1_START, FRAME_STAND1_END, hound_frames_stand1, hound_stand };

mframe_t hound_frames_stand2[] = {
	{ hound_school_stand }, { hound_school_stand }, { hound_school_stand },
	{ hound_school_stand }, { hound_school_stand }, { hound_school_stand },
	{ hound_school_stand }, { hound_school_stand }, { hound_school_stand },
	{ hound_school_stand }, { hound_school_stand }, { hound_school_stand },
	{ hound_school_stand }, { hound_school_stand }, { hound_school_stand },
	{ hound_school_stand }, { hound_school_stand }, { hound_school_stand },
	{ hound_school_stand }, { hound_school_stand }, { hound_school_stand }
};
MMOVE_T(hound_move_stand2) = { FRAME_STAND2_START, FRAME_STAND2_END, hound_frames_stand2, hound_stand };

MONSTERINFO_STAND(hound_stand) (edict_t *self) -> void
{
	M_SetAnimation(self, frandom() < 0.8f ? &hound_move_stand1 : &hound_move_stand2);
}

mframe_t hound_frames_run[] = {
	{ hound_school_run, 60 }, { hound_school_run, 60 }, { hound_school_run, 40 },
	{ hound_school_run, 30 }, { hound_school_run, 30 }, { hound_school_run, 30 },
	{ hound_school_run, 40 }
};
MMOVE_T(hound_move_run) = { FRAME_RUN_START, FRAME_RUN_END, hound_frames_run };

MONSTERINFO_RUN(hound_run) (edict_t *self) -> void
{
	if (self->monsterinfo.aiflags & AI_STAND_GROUND)
		hound_stand(self);
	else
		M_SetAnimation(self, &hound_move_run);
}

mframe_t hound_frames_walk[] = {
	{ hound_school_walk, 7 }, { hound_school_walk, 7 }, { hound_school_walk, 7 },
	{ hound_school_walk, 7 }, { hound_school_walk, 7 }, { hound_school_walk, 7 },
	{ hound_school_walk, 7 }, { hound_school_walk, 7 }
};
MMOVE_T(hound_move_walk) = { FRAME_WALK_START, FRAME_WALK_END, hound_frames_walk, hound_walk };

MONSTERINFO_WALK(hound_walk) (edict_t *self) -> void
{
	M_SetAnimation(self, &hound_move_walk);
}

mframe_t hound_frames_pain1[] = {
	{ ai_move, 6 }, { ai_move, 16 }, { ai_move, -6 }, { ai_move, -7 }
};
MMOVE_T(hound_move_pain1) = { FRAME_PAIN1_START, FRAME_PAIN1_END, hound_frames_pain1, hound_run };

mframe_t hound_frames_pain2[] = {
	{ ai_move }, { ai_move }, { ai_move }, { ai_move, 6 },
	{ ai_move, 16 }, { ai_move, -6 }, { ai_move, -7 }, { ai_move }
};
MMOVE_T(hound_move_pain2) = { FRAME_PAIN2_START, FRAME_PAIN2_END, hound_frames_pain2, hound_run };

PAIN(hound_pain) (edict_t *self, edict_t *other, float kick, int damage, const mod_t &mod) -> void
{
	gi.sound(self, CHAN_VOICE, brandom() ? sound_pain1 : sound_pain2, 1, ATTN_NORM, 0);
	if (level.time < self->pain_debounce_time)
		return;
	self->pain_debounce_time = level.time + 3_sec;
	if (!M_ShouldReactToPain(self, mod))
		return;
	M_SetAnimation(self, brandom() ? &hound_move_pain1 : &hound_move_pain2);
}

MONSTERINFO_SETSKIN(hound_setskin) (edict_t *self) -> void
{
	self->s.skinnum = self->health < (self->max_health / 2) ? 1 : 0;
}

void hound_bite(edict_t *self)
{
	const vec3_t aim = { MELEE_DISTANCE, self->mins[0], 8 };
	if (fire_hit(self, aim, irandom(30, 35), 100))
		gi.sound(self, CHAN_WEAPON, sound_bite, 1, ATTN_NORM, 0);
	else
		gi.sound(self, CHAN_WEAPON, sound_bite_miss, 1, ATTN_NORM, 0);
}

void hound_bite_followup(edict_t *self)
{
	const vec3_t aim = { MELEE_DISTANCE, self->mins[0], 8 };
	fire_hit(self, aim, irandom(30, 35), 100);
}

mframe_t hound_frames_attack1[] = {
	{ ai_charge, 0, hound_launch_sound }, { ai_charge },
	{ ai_charge, 0, hound_bite }, { ai_charge, 0, hound_bite_followup }
};
MMOVE_T(hound_move_attack1) = { FRAME_ATTACK1_START, FRAME_ATTACK1_END, hound_frames_attack1, hound_run };

mframe_t hound_frames_attack2[] = {
	{ ai_charge, 0, hound_launch_sound }, { ai_charge }, { ai_charge },
	{ ai_charge }, { ai_charge }, { ai_charge }, { ai_charge }, { ai_charge },
	{ ai_charge, 0, hound_bite }, { ai_charge, 0, hound_bite_followup },
	{ ai_charge, 0, hound_bite_followup }, { ai_charge, 0, hound_bite_followup },
	{ ai_charge }
};
MMOVE_T(hound_move_attack2) = { FRAME_ATTACK2_START, FRAME_ATTACK2_END, hound_frames_attack2, hound_run };

MONSTERINFO_MELEE(hound_melee) (edict_t *self) -> void
{
	M_SetAnimation(self, frandom() < 0.6f ? &hound_move_attack1 : &hound_move_attack2);
}

TOUCH(hound_jump_touch) (edict_t *self, edict_t *other, const trace_t &tr, bool other_touching_self) -> void
{
	if (self->health <= 0)
	{
		self->touch = nullptr;
		return;
	}

	if (other->takedamage && other->classname && strcmp(self->classname, other->classname))
	{
		if (self->velocity.length() > 400.0f)
		{
			vec3_t normal = self->velocity.normalized();
			const vec3_t point = self->s.origin + (normal * self->maxs[0]);
			const int32_t damage = irandom(40, 50);
			T_Damage(other, self, self, self->velocity, point, normal,
				damage, damage, DAMAGE_NONE, MOD_UNKNOWN);
		}
	}

	if (!M_CheckBottom(self))
	{
		if (self->groundentity)
		{
			self->monsterinfo.nextframe = FRAME_LEAP_LOOP;
			self->touch = nullptr;
		}
		return;
	}
	self->touch = nullptr;
}

void hound_jump_takeoff(edict_t *self)
{
	gi.sound(self, CHAN_VOICE, sound_jump, 1, ATTN_NORM, 0);
	vec3_t forward;
	AngleVectors(self->s.angles, forward, nullptr, nullptr);
	self->s.origin[2] += 1.0f;
	self->velocity = forward * 400.0f;
	self->velocity[2] = 200.0f;
	self->groundentity = nullptr;
	self->monsterinfo.attack_finished = level.time + 3_sec;
	self->touch = hound_jump_touch;
}

void hound_check_landing(edict_t *self)
{
	if (self->groundentity)
	{
		gi.sound(self, CHAN_WEAPON, sound_impact, 1, ATTN_NORM, 0);
		self->monsterinfo.attack_finished = 0_ms;
		return;
	}
	self->monsterinfo.nextframe = level.time > self->monsterinfo.attack_finished ?
		FRAME_LEAP_LOOP : FRAME_LEAP_END_START;
}

void hound_handler_check_landing(edict_t *self)
{
	self->owner = nullptr;
	if (self->groundentity)
	{
		gi.sound(self, CHAN_WEAPON, sound_impact, 1, ATTN_NORM, 0);
		self->monsterinfo.attack_finished = 0_ms;
		return;
	}
	self->monsterinfo.nextframe = level.time > self->monsterinfo.attack_finished ?
		FRAME_HANDLER_LEAP_LOOP : FRAME_HANDLER_LEAP_END;
}

mframe_t hound_frames_handler_jump[] = {
	{ ai_charge }, { ai_charge, 20, hound_jump_takeoff }, { ai_move, 40 },
	{ ai_move, 30, hound_handler_check_landing }, { ai_move }, { ai_move }, { ai_move }
};
MMOVE_T(hound_move_handler_jump) = {
	FRAME_HANDLER_SEPARATE, FRAME_HANDLER_RELEASE_END,
	hound_frames_handler_jump, hound_run
};

mframe_t hound_frames_jump[] = {
	{ ai_charge, 20 }, { ai_charge, 20, hound_jump_takeoff }, { ai_move, 40 },
	{ ai_move, 30, hound_check_landing }, { ai_move }, { ai_move }, { ai_move }
};
MMOVE_T(hound_move_jump) = { FRAME_LEAP_START, FRAME_LEAP_END, hound_frames_jump, hound_run };

MONSTERINFO_ATTACK(hound_jump) (edict_t *self) -> void
{
	M_SetAnimation(self, &hound_move_jump);
}

MONSTERINFO_CHECKATTACK(hound_checkattack) (edict_t *self) -> bool
{
	if (!self->enemy || self->enemy->health <= 0)
		return false;
	if (range_to(self, self->enemy) <= MELEE_DISTANCE)
	{
		self->monsterinfo.attack_state = AS_MELEE;
		return true;
	}

	if (self->absmin[2] > self->enemy->absmin[2] + (0.75f * self->enemy->size[2]) ||
		self->absmax[2] < self->enemy->absmin[2] + (0.25f * self->enemy->size[2]))
		return false;
	vec3_t delta = self->s.origin - self->enemy->s.origin;
	delta[2] = 0.0f;
	if (delta.length() < 100.0f || frandom() < 0.9f)
		return false;

	// Zaero deliberately has no upper range cap for this low-probability leap.
	self->monsterinfo.attack_state = AS_MISSILE;
	return true;
}

void hound_dead(edict_t *self)
{
	self->mins = { -16, -16, -24 };
	self->maxs = { 16, 16, -8 };
	self->movetype = MOVETYPE_TOSS;
	self->svflags |= SVF_DEADMONSTER;
	self->nextthink = 0_ms;
	gi.linkentity(self);
}

mframe_t hound_frames_death[] = {
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move },
	{ ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move }, { ai_move }
};
MMOVE_T(hound_move_death) = { FRAME_DEATH_START, FRAME_DEATH_END, hound_frames_death, hound_dead };

DIE(hound_die) (edict_t *self, edict_t *inflictor, edict_t *attacker, int damage,
	const vec3_t &point, const mod_t &mod) -> void
{
	if (M_CheckGib(self, mod))
	{
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
	gi.sound(self, CHAN_VOICE, sound_die, 1, ATTN_NORM, 0);
	self->deadflag = true;
	self->takedamage = true;
	M_SetAnimation(self, &hound_move_death);
}

void setup_hound(edict_t *self)
{
	hound_precache_internal();
	self->s.modelindex = gi.modelindex(HOUND_MODEL);
	self->mins = { -16, -16, -24 };
	self->maxs = { 16, 16, 24 };
	self->movetype = MOVETYPE_STEP;
	self->solid = SOLID_BBOX;
	self->yaw_speed = 30.0f;
	self->health = 175 * st.health_multiplier;
	self->gib_health = -50;
	self->mass = 250;
	self->pain = hound_pain;
	self->die = hound_die;
	self->monsterinfo.stand = hound_stand;
	self->monsterinfo.walk = hound_walk;
	self->monsterinfo.run = hound_run;
	self->monsterinfo.attack = hound_jump;
	self->monsterinfo.melee = hound_melee;
	self->monsterinfo.sight = hound_sight;
	self->monsterinfo.idle = hound_stand;
	self->monsterinfo.checkattack = hound_checkattack;
	self->monsterinfo.setskin = hound_setskin;
	self->monsterinfo.combat_style = COMBAT_MIXED;
	self->monsterinfo.scale = 1.0f;
	self->speed = HOUND_SCHOOL_MIN_SPEED;
	M_SetAnimation(self, &hound_move_stand1);
	gi.linkentity(self);
}
} // namespace

void ZaeroHoundPrecache()
{
	hound_precache_internal();
}

edict_t *ZaeroCreateHandlerHound(edict_t *handler)
{
	edict_t *hound = G_Spawn();
	hound->classname = HOUND_CLASSNAME;
	hound->s.origin = handler->s.origin;
	hound->s.old_origin = handler->s.old_origin;
	hound->s.angles = handler->s.angles;
	hound->owner = handler;
	hound->enemy = handler->enemy;
	hound->ideal_yaw = handler->ideal_yaw;

	setup_hound(hound);

	// The Handler reserved this child in level.total_monsters at initial map
	// spawn. Run the complete native lifecycle without incrementing that total a
	// second time, then restore ordinary death counting unless the parent itself
	// carried Zaero's no-count contract.
	const bool child_counts = !(handler->monsterinfo.aiflags & AI_DO_NOT_COUNT);
	hound->monsterinfo.aiflags |= AI_DO_NOT_COUNT;
	walkmonster_start(hound);
	if (child_counts)
		hound->monsterinfo.aiflags &= ~AI_DO_NOT_COUNT;

	hound->health = std::max(handler->health, 1);
	hound->max_health = std::max(handler->max_health, 1);
	hound->monsterinfo.base_health = handler->monsterinfo.base_health;
	hound->monsterinfo.nextframe = 0;
	hound->monsterinfo.next_move = nullptr;
	M_SetAnimation(hound, &hound_move_handler_jump);
	hound->s.frame = FRAME_HANDLER_SEPARATE - 1;
	gi.linkentity(hound);

	// The supplied release moves the newly detached Hound immediately before
	// its first scheduled animation frame.
	ai_move(hound, 20.0f);

	if (child_counts && g_debug_monster_kills->integer)
	{
		for (auto &registered : level.monsters_registered)
		{
			if (registered == handler)
			{
				registered = hound;
				break;
			}
		}
	}

	return hound;
}

void SP_monster_hound(edict_t *self)
{
	if (!M_AllowSpawn(self))
	{
		G_FreeEdict(self);
		return;
	}

	// Zaero uses low bit 8 for Hound schooling. Consume this mapper-only bit
	// before the entity enters the native monster lifecycle so it cannot leak
	// into later generic or classname-specific spawnflag handling.
	if (self->spawnflags.has(SPAWNFLAG_HOUND_SCHOOLING))
	{
		self->spawnflags &= ~SPAWNFLAG_HOUND_SCHOOLING;
		self->monsterinfo.aiflags |= AI_ZAERO_SCHOOLING;
	}

	setup_hound(self);
	walkmonster_start(self);
}

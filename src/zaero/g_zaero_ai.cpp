// SPDX-License-Identifier: GPL-2.0-only

#include "../g_local.h"
#include "g_zaero_ai.h"

namespace
{
constexpr gtime_t ZAERO_FLY_STRAFE_DURATION = 1_sec;
constexpr float ZAERO_FLY_STRAFE_DISTANCE = 96.0f;
constexpr float ZAERO_FLY_STRAFE_SCALE = 1.5f;
constexpr float ZAERO_FLY_STRAFE_ANGLE_STEP = 10.0f;
constexpr int32_t ZAERO_FLY_STRAFE_TRACE_COUNT = 37;

void Zaero_ResetFlyStrafe(edict_t *self)
{
	self->monsterinfo.attack_state = AS_STRAIGHT;
	self->monsterinfo.zaero_fly_strafe_timeout = 0_ms;
	self->monsterinfo.zaero_fly_strafe_roll = 0.0f;
}
} // namespace

void Zaero_BeginHoverFlyStrafe(edict_t *self)
{
	if (!level.zaero_mapper_contract || !self || !self->inuse || self->health <= 0 ||
		!self->classname || strcmp(self->classname, "monster_hover") != 0)
		return;

	self->monsterinfo.attack_state = AS_ZAERO_FLY_STRAFE;
	self->monsterinfo.zaero_fly_strafe_roll = crandom() * 180.0f;

	const float angle_step = frandom() < 0.5f
		? ZAERO_FLY_STRAFE_ANGLE_STEP
		: -ZAERO_FLY_STRAFE_ANGLE_STEP;
	vec3_t forward, right;
	AngleVectors(self->s.angles, forward, right, nullptr);

	// The supplied loop can issue one initial trace plus 36 rotated retries.
	// Keep that bounded order while retaining its final blocked direction.
	for (int32_t attempt = 0; attempt < ZAERO_FLY_STRAFE_TRACE_COUNT; ++attempt)
	{
		const vec3_t direction = RotatePointAroundVector(forward, right,
			self->monsterinfo.zaero_fly_strafe_roll);
		const vec3_t end = self->s.origin + (direction * ZAERO_FLY_STRAFE_DISTANCE);
		const trace_t tr = gi.trace(self->s.origin, self->mins, self->maxs,
			end, self, MASK_MONSTERSOLID);

		if (tr.fraction >= 1.0f || attempt + 1 == ZAERO_FLY_STRAFE_TRACE_COUNT)
			break;

		self->monsterinfo.zaero_fly_strafe_roll += angle_step;
	}

	// The source deliberately ignores ETA and always strafes for one second.
	self->monsterinfo.zaero_fly_strafe_timeout = level.time + ZAERO_FLY_STRAFE_DURATION;
}

bool Zaero_RunFlyStrafe(edict_t *self, float distance)
{
	if (!self || self->monsterinfo.attack_state != AS_ZAERO_FLY_STRAFE)
		return false;

	if (!level.zaero_mapper_contract || !self->inuse || self->health <= 0 || !self->enemy ||
		!self->enemy->inuse || self->monsterinfo.zaero_fly_strafe_timeout < level.time)
	{
		// FIX Q-013: the supplied source compares here instead of assigning,
		// which can leave an expired, unhandled attack state behind.
		Zaero_ResetFlyStrafe(self);
		return false;
	}

	self->ideal_yaw = vectoyaw(self->enemy->s.origin - self->s.origin);
	M_ChangeYaw(self);

	vec3_t forward, right;
	AngleVectors(self->s.angles, forward, right, nullptr);
	const vec3_t direction = RotatePointAroundVector(forward, right,
		self->monsterinfo.zaero_fly_strafe_roll);
	const vec3_t requested_velocity = direction *
		(distance * ZAERO_FLY_STRAFE_SCALE / FRAME_TIME_S.seconds());

	self->velocity = requested_velocity;
	SV_FlyMove(self, FRAME_TIME_S.seconds(), MASK_SHOT);

	if (!self->inuse)
		return true;

	// SV_FlyMove is void in the Rerelease API. A modified velocity is the
	// equivalent of the legacy non-zero clip flags used to end this dodge.
	if (self->velocity != requested_velocity)
		Zaero_ResetFlyStrafe(self);

	// The legacy direct call occurred after the normal physics link. Relink now
	// so Rerelease collision and safe-entity queries see the authoritative move.
	gi.linkentity(self);
	return true;
}

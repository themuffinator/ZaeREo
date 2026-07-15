// SPDX-License-Identifier: GPL-2.0-only

#include "../g_local.h"
#include "g_zaero_emp.h"
#include "g_zaero_plasma_shield.h"

namespace
{
constexpr int32_t ZAERO_PLASMA_SHIELD_HEALTH = 4000;
constexpr gtime_t ZAERO_PLASMA_SHIELD_LIFETIME = 10_sec;
constexpr float ZAERO_PLASMA_SHIELD_FORWARD_OFFSET = 50.0f;

constexpr const char *ZAERO_PLASMA_SHIELD_CLASSNAME = "PlasmaShield";
constexpr const char *ZAERO_PLASMA_SHIELD_MODEL = "sprites/plasmashield.sp2";
constexpr const char *ZAERO_PLASMA_SHIELD_DEPLOY_SOUND = "items/plasmashield/psfire.wav";
constexpr const char *ZAERO_PLASMA_SHIELD_ACTIVE_SOUND = "items/plasmashield/psactive.wav";
constexpr const char *ZAERO_PLASMA_SHIELD_DIE_SOUND = "items/plasmashield/psdie.wav";

bool Zaero_IsPlasmaShield(const edict_t *ent)
{
	return level.zaero_content_active && ent && ent->classname &&
		strcmp(ent->classname, ZAERO_PLASMA_SHIELD_CLASSNAME) == 0;
}

// Use activator only as generation-checked placer metadata. The supplied
// owner assignment is commented out, and setting owner would silently change
// projectile/collision contracts in the Rerelease substrate.
void Zaero_ClearStalePlasmaShieldPlacer(edict_t *self)
{
	if (self->activator &&
		(!self->activator->inuse || self->activator->spawn_count != self->count))
	{
		self->activator = nullptr;
		self->count = 0;
	}
}

THINK(Zaero_PlasmaShieldExpire) (edict_t *self) -> void
{
	Zaero_ClearStalePlasmaShieldPlacer(self);

	// The source gates both deployment and destruction sounds on deathmatch;
	// the active loop itself is present in every mode.
	if (deathmatch->integer)
		gi.sound(self, CHAN_VOICE, gi.soundindex(ZAERO_PLASMA_SHIELD_DIE_SOUND),
			1.0f, ATTN_NORM, 0.0f);

	G_FreeEdict(self);
}

DIE(Zaero_PlasmaShieldDie) (edict_t *self, edict_t *, edict_t *, int,
	const vec3_t &, const mod_t &) -> void
{
	Zaero_PlasmaShieldExpire(self);
}
} // namespace

void Use_ZaeroPlasmaShield(edict_t *ent, gitem_t *item)
{
	if (!level.zaero_content_active || !ent || !ent->client || !item)
		return;
	if (ent->client->pers.inventory[item->id] <= 0)
		return;

	// Placement is the one explicit Shield EMP query in the supplied call-site
	// matrix. A blocked use neither consumes inventory nor creates an entity.
	if (Zaero_EMPNukeCheck(ent, ent->s.origin))
	{
		Zaero_PlayEMPMisfire(ent);
		return;
	}

	if (!G_CheckInfiniteAmmo(item))
		ent->client->pers.inventory[item->id]--;

	if (deathmatch->integer)
		gi.sound(ent, CHAN_VOICE, gi.soundindex(ZAERO_PLASMA_SHIELD_DEPLOY_SOUND),
			1.0f, ATTN_NORM, 0.0f);

	vec3_t forward, right, up;
	AngleVectors(ent->client->v_angle, forward, right, up);

	edict_t *shield = G_Spawn();
	shield->classname = ZAERO_PLASMA_SHIELD_CLASSNAME;
	shield->movetype = MOVETYPE_PUSH;
	shield->solid = SOLID_BBOX;
	shield->s.modelindex = gi.modelindex(ZAERO_PLASMA_SHIELD_MODEL);
	shield->s.effects |= EF_POWERSCREEN;
	shield->s.sound = gi.soundindex(ZAERO_PLASMA_SHIELD_ACTIVE_SOUND);
	shield->s.angles = vectoangles(forward);
	shield->s.origin = ent->s.origin + (forward * ZAERO_PLASMA_SHIELD_FORWARD_OFFSET);

	// Preserve the source's two rotated diagonal points exactly. This is not a
	// conventional symmetric box and its yaw/pitch-dependent boundaries are a
	// gameplay-observable placement/collision quirk.
	const vec3_t front_bottom_left = (forward * 10.0f) - (right * 30.0f) - (up * 30.0f);
	const vec3_t back_top_right = (forward * 5.0f) + (right * 30.0f) + (up * 50.0f);
	ClearBounds(shield->mins, shield->maxs);
	AddPointToBounds(front_bottom_left, shield->mins, shield->maxs);
	AddPointToBounds(back_top_right, shield->mins, shield->maxs);

	shield->health = shield->max_health = ZAERO_PLASMA_SHIELD_HEALTH;
	shield->takedamage = true;
	shield->die = Zaero_PlasmaShieldDie;
	shield->think = Zaero_PlasmaShieldExpire;
	shield->nextthink = level.time + ZAERO_PLASMA_SHIELD_LIFETIME;

	// Stable placer metadata is deliberately not owner metadata. count records
	// the edict generation so a disconnected player's reused slot never becomes
	// the apparent placer after a save or during the ten-second lifetime.
	shield->activator = ent;
	shield->count = ent->spawn_count;
	gi.linkentity(shield);
}

bool Zaero_PlasmaShieldCheckPowerArmor(edict_t *ent, int damage, int &save)
{
	if (!Zaero_IsPlasmaShield(ent))
		return false;

	save = 0;
	if (ent->health <= 0 || damage <= 0)
		return true;

	// The supplied CheckPowerArmor treats health as a read-only power pool:
	// it computes two-thirds absorption, caps by health*2, and lets T_Damage
	// subtract only the unabsorbed remainder. The native seam emits the legacy
	// shield sparks; neither path separately spends health as power cells.
	const int shield_damage = (2 * damage) / 3;
	save = min(ent->health * 2, shield_damage);
	return true;
}

// SPDX-License-Identifier: GPL-2.0-only

#include "../g_local.h"
#include "g_zaero_emp.h"

namespace
{
constexpr int32_t ZAERO_EMP_PLAYER_RADIUS = 1024;
constexpr int32_t ZAERO_EMP_LAST_VISIBLE_FRAME = 5;
constexpr gtime_t ZAERO_EMP_ANIMATION_TICK = 100_ms;
constexpr gtime_t ZAERO_EMP_ACTIVE_LIFETIME = 30_sec;

constexpr int32_t ZAERO_EMP_ACTIVATE_LAST_FRAME = 9;
constexpr int32_t ZAERO_EMP_FIRE_LAST_FRAME = 16;
constexpr int32_t ZAERO_EMP_IDLE_LAST_FRAME = 43;
constexpr int32_t ZAERO_EMP_DEACTIVATE_LAST_FRAME = 47;

constexpr int32_t ZAERO_EMP_ACTIVATE_SOUND_FRAME = 0;
constexpr int32_t ZAERO_EMP_SPIN_SOUND_FRAME = 11;
constexpr int32_t ZAERO_EMP_IDLE_SOUND_FRAME = 35;

constexpr const char *ZAERO_EMP_CENTER_CLASSNAME = "EMPNukeCenter";
constexpr const char *ZAERO_EMP_BLAST_MODEL = "models/objects/b_explode/tris.md2";
constexpr const char *ZAERO_EMP_TRIGGER_SOUND = "items/empnuke/emp_trg.wav";
constexpr const char *ZAERO_EMP_ACTIVATE_SOUND = "items/empnuke/emp_act.wav";
constexpr const char *ZAERO_EMP_SPIN_SOUND = "items/empnuke/emp_spin.wav";
constexpr const char *ZAERO_EMP_IDLE_SOUND = "items/empnuke/emp_idle.wav";
// "missfire" is the shipped asset spelling and part of the runtime ABI.
constexpr const char *ZAERO_EMP_MISFIRE_SOUND = "items/empnuke/emp_missfire.wav";

THINK(Zaero_EMPNukeFinish) (edict_t *self) -> void
{
	G_FreeEdict(self);
}

THINK(Zaero_EMPBlastAnim) (edict_t *self) -> void
{
	self->s.frame++;
	self->s.skinnum++;

	if (self->s.frame > ZAERO_EMP_LAST_VISIBLE_FRAME)
	{
		// The supplied center remains queryable after its six visible frames.
		// It deliberately has no active loop sound despite the unused asset.
		self->svflags |= SVF_NOCLIENT;
		self->s.modelindex = 0;
		self->s.frame = 0;
		self->s.skinnum = 0;
		self->think = Zaero_EMPNukeFinish;
		self->nextthink = level.time + ZAERO_EMP_ACTIVE_LIFETIME;
	}
	else
	{
		self->nextthink = level.time + ZAERO_EMP_ANIMATION_TICK;
	}
}

void Zaero_EMPNukeFire(edict_t *ent)
{
	Zaero_FireEMPNuke(ent, ent->s.origin, ZAERO_EMP_PLAYER_RADIUS);

	// ammo_empnuke is intentionally unaffected by infinite-ammo settings.
	int32_t &ammo = ent->client->pers.inventory[ent->client->pers.weapon->ammo];
	ammo--;

	if (ammo != 0)
	{
		// This use-as-weapon replays its complete activation before the next
		// deployment instead of returning to its ordinary idle sequence.
		ent->client->weaponstate = WEAPON_ACTIVATING;
		ent->client->ps.gunframe = 0;
	}
	else
	{
		NoAmmoWeaponChange(ent, false);
		ChangeWeapon(ent);
	}
}

void Zaero_EMPPlayWeaponSound(edict_t *ent)
{
	if (!deathmatch->integer)
		return;

	const char *sound = nullptr;
	switch (ent->client->ps.gunframe)
	{
	case ZAERO_EMP_ACTIVATE_SOUND_FRAME:
		sound = ZAERO_EMP_ACTIVATE_SOUND;
		break;
	case ZAERO_EMP_SPIN_SOUND_FRAME:
		sound = ZAERO_EMP_SPIN_SOUND;
		break;
	case ZAERO_EMP_IDLE_SOUND_FRAME:
		sound = ZAERO_EMP_IDLE_SOUND;
		break;
	default:
		return;
	}

	gi.sound(ent, CHAN_AUTO, gi.soundindex(sound), 1.0f, ATTN_NORM, 0.0f);
}

// The supplied generic path compiled out its automatic Quad sound, and EMP
// has no equivalent per-fire powerup call.  Dispatching after the native frame
// advance preserves timing without adding Rerelease's generic powerup audio.
void Zaero_EMPNukeNoGenericFire(edict_t *)
{
}
} // namespace

edict_t *Zaero_FireEMPNuke(edict_t *owner, const vec3_t &center, int radius)
{
	if (!level.is_zaero)
		return nullptr;

	if (owner)
		gi.sound(owner, CHAN_VOICE, gi.soundindex(ZAERO_EMP_TRIGGER_SOUND), 1.0f, ATTN_NORM, 0.0f);

	edict_t *empnuke = G_Spawn();
	empnuke->owner = owner;
	// Existing, JSON-registered count records the owner's generation.  This
	// preserves the owner exemption without granting it to a player/monster
	// that later reuses the same edict slot.
	empnuke->count = owner ? owner->spawn_count : 0;
	empnuke->dmg = radius;
	empnuke->s.origin = center;
	empnuke->classname = ZAERO_EMP_CENTER_CLASSNAME;
	empnuke->movetype = MOVETYPE_NONE;
	empnuke->s.modelindex = gi.modelindex(ZAERO_EMP_BLAST_MODEL);
	empnuke->s.skinnum = 0;
	empnuke->think = Zaero_EMPBlastAnim;
	empnuke->nextthink = level.time + ZAERO_EMP_ANIMATION_TICK;
	gi.linkentity(empnuke);
	return empnuke;
}

bool Zaero_EMPNukeCheck(edict_t *subject, const vec3_t &position)
{
	if (!level.is_zaero)
		return false;

	edict_t *center = nullptr;
	while ((center = G_FindByString<&edict_t::classname>(center, ZAERO_EMP_CENTER_CLASSNAME)) != nullptr)
	{
		const bool is_owner = subject && center->owner == subject &&
			center->count == subject->spawn_count;
		if (!is_owner && (center->s.origin - position).length() <= center->dmg)
			return true;
	}

	return false;
}

void Zaero_PlayEMPMisfire(edict_t *subject)
{
	if (!level.is_zaero || !subject)
		return;

	gi.sound(subject, CHAN_AUTO, gi.soundindex(ZAERO_EMP_MISFIRE_SOUND), 1.0f, ATTN_NORM, 0.0f);
}

void Weapon_ZaeroEMPNuke(edict_t *ent)
{
	if (!level.is_zaero || !ent || !ent->client)
		return;

	// Think_Weapon runs at the server tick rate while Weapon_Generic advances
	// the supplied 10 Hz view model independently.  Gate the old frame sounds
	// to that advance so a 40 Hz server does not emit each sound four times.
	const bool animation_frame_due = ent->client->weapon_think_time <= level.time ||
		(g_instant_weapon_switch->integer && ent->client->weaponstate == WEAPON_ACTIVATING);
	if (animation_frame_due)
		Zaero_EMPPlayWeaponSound(ent);

	static const int pause_frames[] = {25, 34, 43, 0};
	static const int fire_frames[] = {0};
	const weaponstate_t old_state = ent->client->weaponstate;
	const int32_t old_frame = ent->client->ps.gunframe;
	Weapon_Generic(ent,
		ZAERO_EMP_ACTIVATE_LAST_FRAME,
		ZAERO_EMP_FIRE_LAST_FRAME,
		ZAERO_EMP_IDLE_LAST_FRAME,
		ZAERO_EMP_DEACTIVATE_LAST_FRAME,
		pause_frames,
		fire_frames,
		Zaero_EMPNukeNoGenericFire);

	if (old_state == WEAPON_FIRING &&
		ent->client->weaponstate == WEAPON_FIRING &&
		old_frame != ent->client->ps.gunframe &&
		ent->client->ps.gunframe == ZAERO_EMP_FIRE_LAST_FRAME)
	{
		Zaero_EMPNukeFire(ent);
	}
}

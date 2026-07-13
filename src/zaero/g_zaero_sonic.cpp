// SPDX-License-Identifier: GPL-2.0-only

#include "../g_local.h"
#include "g_zaero_sonic.h"

// SpawnDamage remains local to g_combat.cpp in the Rerelease baseline.
void SpawnDamage(int type, const vec3_t &origin, const vec3_t &normal, int damage);

namespace
{
constexpr gtime_t ZAERO_SONIC_MAX_CHARGE_TIME = 5_sec;
constexpr gtime_t ZAERO_SONIC_WARMUP_TIME = 400_ms;
constexpr gtime_t ZAERO_SONIC_EXPLOSION_STEP = 100_ms;
constexpr int32_t ZAERO_SONIC_BASE_DAMAGE = 10;
constexpr int32_t ZAERO_SONIC_DAMAGE_RANGE = 990;
constexpr float ZAERO_SONIC_MAX_RADIUS = 500.0f;
constexpr int32_t ZAERO_SONIC_MAX_CELLS = 100;
constexpr float ZAERO_SONIC_TRACE_DISTANCE = 8192.0f;

constexpr int32_t ZAERO_SONIC_CHARGE_FIRST_FRAME = 12;
constexpr int32_t ZAERO_SONIC_CHARGE_LAST_FRAME = 17;
constexpr int32_t ZAERO_SONIC_RELEASE_FRAME = 18;
// Rerelease Weapon_Generic advances before processing a fire frame. Returning
// to 11 therefore makes the next native weapon tick process frame 12, which
// is equivalent to the supplied 10 Hz code returning to frame 12 itself.
constexpr int32_t ZAERO_SONIC_RERELEASE_LOOP_FRAME = 11;

constexpr const char *ZAERO_SONIC_ACTIVATE_SOUND = "weapons/sonic/sc_act.wav";
constexpr const char *ZAERO_SONIC_DEACTIVATE_SOUND = "weapons/sonic/sc_dact.wav";
constexpr const char *ZAERO_SONIC_WARM_SOUND = "weapons/sonic/sc_warm.wav";
constexpr const char *ZAERO_SONIC_FIRE_SOUND = "weapons/sonic/sc_fire.wav";
constexpr const char *ZAERO_SONIC_COOL_SOUND = "weapons/sonic/sc_cool.wav";
constexpr const char *ZAERO_SONIC_EMP_MISFIRE_SOUND = "items/empnuke/emp_missfire.wav";

zaero_sonic_emp_check_t zaero_sonic_emp_check = nullptr;

struct zaero_sonic_trace_t
{
	vec3_t start;
	vec3_t forward;
	vec3_t right;
	vec3_t up;
	trace_t trace;
};

float Zaero_SonicSoundVolume()
{
	return is_silenced ? 0.4f : 1.0f;
}

bool Zaero_SonicEMPBlocked(edict_t *self)
{
	return zaero_sonic_emp_check && zaero_sonic_emp_check(self, self->s.origin);
}

void Zaero_SonicPlayEMPMisfire(edict_t *self)
{
	gi.sound(self, CHAN_AUTO, gi.soundindex(ZAERO_SONIC_EMP_MISFIRE_SOUND), 1.0f, ATTN_NORM, 0);
}

void Zaero_SonicResetCharge(edict_t *self)
{
	self->client->weapon_sound = 0;
	self->client->zaero_sonic_warmup_until = 0_ms;
	self->client->zaero_sonic_charge_start = 0_ms;
	self->dmg_radius = 0.0f;
}

zaero_sonic_trace_t Zaero_SonicTrace(edict_t *self)
{
	zaero_sonic_trace_t shot = {};
	AngleVectors(self->client->v_angle, shot.forward, shot.right, shot.up);

	// The old P_ProjectSource took the player origin and a world-Z offset.
	// G_ProjectSource (rather than the newer eye-relative P_ProjectSource)
	// preserves the exact origin + viewheight - 8 muzzle height.
	vec3_t offset = {0.0f, 7.0f, static_cast<float>(self->viewheight - 8)};
	if (self->client->pers.hand == LEFT_HANDED)
		offset.y *= -1.0f;
	else if (self->client->pers.hand == CENTER_HANDED)
		offset.y = 0.0f;
	shot.start = G_ProjectSource(self->s.origin, offset, shot.forward, shot.right);

	contents_t mask = MASK_PROJECTILE | CONTENTS_SLIME | CONTENTS_LAVA;
	if (!G_ShouldPlayersCollide(true))
		mask &= ~CONTENTS_PLAYER;
	shot.trace = gi.traceline(
		shot.start,
		shot.start + (shot.forward * ZAERO_SONIC_TRACE_DISTANCE),
		self,
		mask);
	return shot;
}

void Zaero_SonicChargeEffect(edict_t *self)
{
	const zaero_sonic_trace_t shot = Zaero_SonicTrace(self);
	P_AddWeaponKick(self, shot.forward * -3.0f, {-3.0f, 0.0f, 0.0f});

	const vec3_t effect_origin = shot.trace.endpos - (shot.forward * 5.0f);
	// All three components are intentionally biased negative by the supplied
	// expression: crandom() * 10 - 20.
	const vec3_t effect_normal = {
		(crandom() * 10.0f) - 20.0f,
		(crandom() * 10.0f) - 20.0f,
		(crandom() * 10.0f) - 20.0f
	};
	SpawnDamage(TE_SHIELD_SPARKS, effect_origin, effect_normal, 0);
}

void Zaero_SonicRadiusDamageAt(
	const vec3_t &origin,
	edict_t *inflictor,
	edict_t *attacker,
	float damage,
	edict_t *ignore,
	float radius)
{
	edict_t *target = nullptr;
	while ((target = findradius(target, origin, radius)) != nullptr)
	{
		if (target == ignore || !target->takedamage)
			continue;

		// Preserve Zaero's position-based falloff, including its visibility
		// quirk: CanDamage is evaluated from the player inflictor, not from a
		// temporary entity at the impact point.
		const vec3_t target_center = target->s.origin + ((target->mins + target->maxs) * 0.5f);
		const float distance = (origin - target_center).length();
		float points = damage - (0.5f * distance);
		if (target == attacker)
			points *= 0.5f;

		if (points > 0.0f && CanDamage(target, inflictor))
		{
			const vec3_t direction = target->s.origin - origin;
			T_Damage(
				target,
				inflictor,
				attacker,
				direction,
				origin,
				vec3_origin,
				static_cast<int32_t>(points),
				static_cast<int32_t>(points),
				DAMAGE_RADIUS,
				MOD_ZAERO_SONIC_CANNON);
		}
	}
}

THINK(Zaero_SonicExplosionThink) (edict_t *self) -> void
{
	gi.WriteByte(svc_temp_entity);
	gi.WriteByte(TE_ROCKET_EXPLOSION);
	gi.WritePosition(self->s.origin);
	gi.multicast(self->s.origin, MULTICAST_PHS, false);
	G_FreeEdict(self);
}

void Zaero_SonicFire(edict_t *self)
{
	const float charge_fraction = self->dmg_radius / static_cast<float>(ZAERO_SONIC_MAX_CELLS);
	const float radius = charge_fraction * ZAERO_SONIC_MAX_RADIUS;
	const float damage = ZAERO_SONIC_BASE_DAMAGE + (charge_fraction * ZAERO_SONIC_DAMAGE_RANGE);

	const zaero_sonic_trace_t shot = Zaero_SonicTrace(self);
	P_AddWeaponKick(self, shot.forward * -3.0f, {-3.0f, 0.0f, 0.0f});

	if (shot.trace.ent != self && shot.trace.ent && shot.trace.ent->takedamage)
	{
		T_Damage(
			shot.trace.ent,
			self,
			self,
			shot.forward,
			shot.trace.endpos,
			shot.trace.plane.normal,
			static_cast<int32_t>(damage),
			0,
			DAMAGE_NONE,
			MOD_ZAERO_SONIC_CANNON);
	}

	Zaero_SonicRadiusDamageAt(
		shot.trace.endpos,
		self,
		self,
		damage,
		shot.trace.ent,
		radius);

	const vec3_t primary_origin = shot.trace.endpos - (shot.forward * 5.0f);
	gi.WriteByte(svc_temp_entity);
	gi.WriteByte(TE_ROCKET_EXPLOSION);
	gi.WritePosition(primary_origin);
	// This is intentionally the shooter origin, as in the supplied source,
	// even though the event position is the trace endpoint.
	gi.multicast(self->s.origin, MULTICAST_PHS, false);

	float remaining_damage = damage - 100.0f;
	gtime_t delay = ZAERO_SONIC_EXPLOSION_STEP;
	while (remaining_damage > 0.0f)
	{
		vec3_t explosion_origin = primary_origin;
		explosion_origin += shot.forward * ((50.0f * crandom()) - 5.0f);
		explosion_origin += shot.right * ((50.0f * crandom()) - 5.0f);
		explosion_origin += shot.up * ((50.0f * crandom()) - 5.0f);

		edict_t *explosion = G_Spawn();
		explosion->classname = "sconnanExplode";
		explosion->s.origin = explosion_origin;
		explosion->nextthink = level.time + delay;
		explosion->think = Zaero_SonicExplosionThink;

		delay += ZAERO_SONIC_EXPLOSION_STEP;
		remaining_damage -= 100.0f;
	}

	// Supplied Zaero plays the Quad sound here but does not multiply Sonic
	// damage or radius. Do not route this through Weapon_PowerupSound: native
	// Weapon_Generic would otherwise repeat it on every charge frame.
	if (self->client->quad_time > level.time)
		gi.sound(self, CHAN_ITEM, gi.soundindex("items/damage3.wav"), 1.0f, ATTN_NORM, 0);
}

void Zaero_SonicRelease(edict_t *self)
{
	self->client->weapon_sound = 0;
	self->client->zaero_sonic_warmup_until = 0_ms;

	if (Zaero_SonicEMPBlocked(self))
		Zaero_SonicPlayEMPMisfire(self);
	else
	{
		gi.sound(
			self,
			CHAN_VOICE,
			gi.soundindex(ZAERO_SONIC_COOL_SOUND),
			Zaero_SonicSoundVolume(),
			ATTN_NORM,
			0);
		if (self->dmg_radius != 0.0f)
			Zaero_SonicFire(self);
	}

	self->dmg_radius = 0.0f;
	self->client->zaero_sonic_charge_start = 0_ms;
}

void Zaero_SonicNoAmmo(edict_t *self)
{
	if (level.time >= self->pain_debounce_time)
	{
		gi.sound(self, CHAN_VOICE, gi.soundindex("weapons/noammo.wav"), 1.0f, ATTN_NORM, 0);
		self->pain_debounce_time = level.time + 1_sec;
	}
	NoAmmoWeaponChange(self, false);
}

void Zaero_SonicUpdateCharge(edict_t *self, int32_t &ammo)
{
	const int32_t old_cells = static_cast<int32_t>(self->dmg_radius);
	const float elapsed = (level.time - self->client->zaero_sonic_charge_start).seconds();
	self->dmg_radius =
		(elapsed / ZAERO_SONIC_MAX_CHARGE_TIME.seconds()) * static_cast<float>(ZAERO_SONIC_MAX_CELLS);
	const int32_t charged_cells = static_cast<int32_t>(self->dmg_radius);

	if (old_cells >= charged_cells)
		return;

	const int32_t requested_cells = charged_cells - old_cells;
	if (ammo < requested_cells)
	{
		self->dmg_radius -= static_cast<float>(requested_cells - ammo);
		ammo = 0;
	}
	else
		ammo -= requested_cells;
}

void Zaero_SonicChargeFrame(edict_t *self)
{
	if (!(self->client->buttons & BUTTON_ATTACK))
	{
		if (self->client->weapon_sound || self->client->ps.gunframe == ZAERO_SONIC_CHARGE_LAST_FRAME)
			self->client->ps.gunframe = ZAERO_SONIC_RELEASE_FRAME;
		if (self->client->ps.gunframe == ZAERO_SONIC_RELEASE_FRAME)
			Zaero_SonicRelease(self);
		return;
	}

	if (Zaero_SonicEMPBlocked(self))
	{
		Zaero_SonicPlayEMPMisfire(self);
		self->client->ps.gunframe = ZAERO_SONIC_RELEASE_FRAME;
		Zaero_SonicResetCharge(self);
		return;
	}

	bool release = false;
	if (!self->client->zaero_sonic_charge_start)
		self->client->zaero_sonic_charge_start = level.time;
	else if ((level.time - self->client->zaero_sonic_charge_start) >= ZAERO_SONIC_MAX_CHARGE_TIME)
		release = true;
	else
	{
		int32_t &ammo = self->client->pers.inventory[self->client->pers.weapon->ammo];
		Zaero_SonicUpdateCharge(self, ammo);
	}

	int32_t &ammo = self->client->pers.inventory[self->client->pers.weapon->ammo];
	if (ammo <= 0)
	{
		release = true;
		Zaero_SonicNoAmmo(self);
	}
	else if (self->client->zaero_sonic_warmup_until < level.time)
		self->client->weapon_sound = gi.soundindex(ZAERO_SONIC_FIRE_SOUND);

	Zaero_SonicChargeEffect(self);

	if (release)
		self->client->ps.gunframe = ZAERO_SONIC_RELEASE_FRAME;
	else if (self->client->ps.gunframe == ZAERO_SONIC_CHARGE_LAST_FRAME)
		self->client->ps.gunframe = ZAERO_SONIC_RERELEASE_LOOP_FRAME;

	if (self->client->ps.gunframe == ZAERO_SONIC_RELEASE_FRAME)
		Zaero_SonicRelease(self);
}

// The actual charge callback is dispatched after Weapon_Generic advances a
// native frame. Keeping its fire list empty avoids Weapon_Generic's automatic
// Weapon_PowerupSound call on every charge frame.
void Zaero_SonicNoGenericFire(edict_t *)
{
}
} // namespace

void Zaero_SetSonicEMPCheck(zaero_sonic_emp_check_t check)
{
	zaero_sonic_emp_check = check;
}

void Weapon_ZaeroSonicCannon(edict_t *ent)
{
	static const int pause_frames[] = {32, 42, 52, 0};
	static const int fire_frames[] = {0};

	const bool weapon_frame_due =
		ent->client->weapon_think_time <= level.time || g_instant_weapon_switch->integer;
	if (ent->client->weaponstate == WEAPON_ACTIVATING && ent->client->ps.gunframe == 0)
	{
		if (weapon_frame_due)
		{
			if (deathmatch->integer)
			{
				gi.sound(
					ent,
					CHAN_VOICE,
					gi.soundindex(ZAERO_SONIC_ACTIVATE_SOUND),
					Zaero_SonicSoundVolume(),
					ATTN_NORM,
					0);
			}
			Zaero_SonicResetCharge(ent);
		}
	}
	else if (ent->client->weaponstate == WEAPON_DROPPING && ent->client->ps.gunframe == 53)
	{
		if (weapon_frame_due && deathmatch->integer)
		{
			gi.sound(
				ent,
				CHAN_VOICE,
				gi.soundindex(ZAERO_SONIC_DEACTIVATE_SOUND),
				Zaero_SonicSoundVolume(),
				ATTN_NORM,
				0);
		}
	}
	else if ((ent->client->buttons & BUTTON_ATTACK) &&
		!ent->client->zaero_sonic_warmup_until &&
		(weapon_frame_due ||
			(ent->client->weaponstate == WEAPON_READY && ent->client->weapon_fire_finished <= level.time)))
	{
		ent->client->zaero_sonic_warmup_until = level.time + ZAERO_SONIC_WARMUP_TIME;
		gi.sound(
			ent,
			CHAN_VOICE,
			gi.soundindex(ZAERO_SONIC_WARM_SOUND),
			Zaero_SonicSoundVolume(),
			ATTN_NORM,
			0);
	}

	const weaponstate_t old_state = ent->client->weaponstate;
	const int32_t old_frame = ent->client->ps.gunframe;
	Weapon_Generic(ent, 6, 22, 52, 57, pause_frames, fire_frames, Zaero_SonicNoGenericFire);

	const int32_t frame = ent->client->ps.gunframe;
	if (ent->client->weaponstate == WEAPON_FIRING &&
		(old_state != WEAPON_FIRING || frame != old_frame) &&
		frame >= ZAERO_SONIC_CHARGE_FIRST_FRAME &&
		frame <= ZAERO_SONIC_CHARGE_LAST_FRAME)
	{
		Zaero_SonicChargeFrame(ent);
	}
}

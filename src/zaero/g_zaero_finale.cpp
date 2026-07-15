// SPDX-License-Identifier: GPL-2.0-only

#include "../g_local.h"
#include "g_zaero_finale.h"

namespace
{
constexpr gtime_t ZAERO_FINALE_FADE_DURATION = 5_sec;

bool Zaero_IsFinaleLevel()
{
	return level.zaero_mapper_contract && !deathmatch->integer &&
		Q_strcasecmp(level.mapname, "zboss") == 0;
}
}

void Zaero_BeginFinaleFade()
{
	if (!Zaero_IsFinaleLevel())
		return;

	// Zaero begins its white fade as soon as intermission starts. This is
	// distinct from Rerelease's optional 1.3-second black fade on ExitLevel.
	level.intermission_fade = false;
	level.intermission_fading = true;
	level.intermission_fade_time = level.time + ZAERO_FINALE_FADE_DURATION;
}

zaero_finale_fade_state_t Zaero_UpdateFinaleFade()
{
	if (!Zaero_IsFinaleLevel() || !level.intermission_fading)
		return zaero_finale_fade_state_t::inactive;

	if (level.time >= level.intermission_fade_time)
	{
		level.intermission_fade = false;
		level.intermission_fading = false;
		level.intermission_fade_time = 0_ms;
		return zaero_finale_fade_state_t::complete;
	}

	const gtime_t elapsed = ZAERO_FINALE_FADE_DURATION -
		(level.intermission_fade_time - level.time);
	const float alpha = clamp(
		elapsed.seconds() / ZAERO_FINALE_FADE_DURATION.seconds(), 0.0f, 1.0f);

	for (auto player : active_players())
		player->client->ps.screen_blend = { 1.0f, 1.0f, 1.0f, alpha };

	return zaero_finale_fade_state_t::running;
}

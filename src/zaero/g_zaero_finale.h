// SPDX-License-Identifier: GPL-2.0-only
#pragma once

enum class zaero_finale_fade_state_t
{
	inactive,
	running,
	complete
};

void Zaero_BeginFinaleFade();
zaero_finale_fade_state_t Zaero_UpdateFinaleFade();

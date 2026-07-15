// Copyright (c) ZeniMax Media Inc.
// Licensed under the GNU General Public License 2.0.

#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <string_view>

using zaero_sha256_t = std::array<uint8_t, 32>;

// Hashes exactly the null-terminated entity text supplied to SpawnEntities.
// It cannot inspect the loaded BSP container; callers must never describe this
// value as a full-BSP hash.
zaero_sha256_t Zaero_EntityLumpSHA256(std::string_view entity_text);
bool Zaero_SHA256Equals(const zaero_sha256_t &left, const zaero_sha256_t &right);
std::string Zaero_SHA256Hex(const zaero_sha256_t &digest);

// Returns an audited retail record only when both the canonical map name and
// entity text match. Full BSP verification remains an engine API dependency.
const char *Zaero_FindShippedMapEntityIdentity(const char *mapname, const zaero_sha256_t &entity_hash);

// Copyright (c) ZeniMax Media Inc.
// Licensed under the GNU General Public License 2.0.

#include "../g_local.h"
#include "g_zaero_map_identity.h"
#include "g_zaero_shipped_map_identity.h"

namespace
{
constexpr std::array<uint32_t, 64> sha256_round_constants = {
	0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
	0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
	0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
	0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
	0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
	0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
	0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
	0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
};

constexpr uint32_t rotate_right(uint32_t value, uint32_t count)
{
	return (value >> count) | (value << (32 - count));
}

uint32_t read_big_endian(const uint8_t *data)
{
	return (static_cast<uint32_t>(data[0]) << 24) |
		(static_cast<uint32_t>(data[1]) << 16) |
		(static_cast<uint32_t>(data[2]) << 8) |
		static_cast<uint32_t>(data[3]);
}

void write_big_endian(uint8_t *data, uint32_t value)
{
	data[0] = static_cast<uint8_t>(value >> 24);
	data[1] = static_cast<uint8_t>(value >> 16);
	data[2] = static_cast<uint8_t>(value >> 8);
	data[3] = static_cast<uint8_t>(value);
}

void sha256_transform(std::array<uint32_t, 8> &state, const uint8_t *block)
{
	std::array<uint32_t, 64> schedule;
	for (size_t i = 0; i < 16; ++i)
		schedule[i] = read_big_endian(block + (i * 4));
	for (size_t i = 16; i < schedule.size(); ++i)
	{
		const uint32_t s0 = rotate_right(schedule[i - 15], 7) ^ rotate_right(schedule[i - 15], 18) ^ (schedule[i - 15] >> 3);
		const uint32_t s1 = rotate_right(schedule[i - 2], 17) ^ rotate_right(schedule[i - 2], 19) ^ (schedule[i - 2] >> 10);
		schedule[i] = schedule[i - 16] + s0 + schedule[i - 7] + s1;
	}

	uint32_t a = state[0];
	uint32_t b = state[1];
	uint32_t c = state[2];
	uint32_t d = state[3];
	uint32_t e = state[4];
	uint32_t f = state[5];
	uint32_t g = state[6];
	uint32_t h = state[7];
	for (size_t i = 0; i < schedule.size(); ++i)
	{
		const uint32_t s1 = rotate_right(e, 6) ^ rotate_right(e, 11) ^ rotate_right(e, 25);
		const uint32_t choose = (e & f) ^ (~e & g);
		const uint32_t temporary1 = h + s1 + choose + sha256_round_constants[i] + schedule[i];
		const uint32_t s0 = rotate_right(a, 2) ^ rotate_right(a, 13) ^ rotate_right(a, 22);
		const uint32_t majority = (a & b) ^ (a & c) ^ (b & c);
		const uint32_t temporary2 = s0 + majority;
		h = g;
		g = f;
		f = e;
		e = d + temporary1;
		d = c;
		c = b;
		b = a;
		a = temporary1 + temporary2;
	}
	state[0] += a;
	state[1] += b;
	state[2] += c;
	state[3] += d;
	state[4] += e;
	state[5] += f;
	state[6] += g;
	state[7] += h;
}
} // namespace

zaero_sha256_t Zaero_EntityLumpSHA256(std::string_view entity_text)
{
	std::array<uint32_t, 8> state = {
		0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
		0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
	};
	const auto *input = reinterpret_cast<const uint8_t *>(entity_text.data());
	const size_t full_blocks = entity_text.size() / 64;
	for (size_t block = 0; block < full_blocks; ++block)
		sha256_transform(state, input + (block * 64));

	std::array<uint8_t, 128> final_block{};
	const size_t tail_size = entity_text.size() % 64;
	if (tail_size)
		memcpy(final_block.data(), input + (full_blocks * 64), tail_size);
	final_block[tail_size] = 0x80;
	const uint64_t bit_length = static_cast<uint64_t>(entity_text.size()) * 8;
	const size_t final_blocks = tail_size >= 56 ? 2 : 1;
	for (size_t byte = 0; byte < 8; ++byte)
		final_block[(final_blocks * 64) - 1 - byte] = static_cast<uint8_t>(bit_length >> (byte * 8));
	for (size_t block = 0; block < final_blocks; ++block)
		sha256_transform(state, final_block.data() + (block * 64));

	zaero_sha256_t digest;
	for (size_t index = 0; index < state.size(); ++index)
		write_big_endian(digest.data() + (index * 4), state[index]);
	return digest;
}

bool Zaero_SHA256Equals(const zaero_sha256_t &left, const zaero_sha256_t &right)
{
	uint8_t difference = 0;
	for (size_t index = 0; index < left.size(); ++index)
		difference |= left[index] ^ right[index];
	return difference == 0;
}

std::string Zaero_SHA256Hex(const zaero_sha256_t &digest)
{
	static constexpr char hex[] = "0123456789abcdef";
	std::string result;
	result.resize(digest.size() * 2);
	for (size_t index = 0; index < digest.size(); ++index)
	{
		result[index * 2] = hex[digest[index] >> 4];
		result[(index * 2) + 1] = hex[digest[index] & 0x0f];
	}
	return result;
}

const char *Zaero_FindShippedMapEntityIdentity(const char *mapname, const zaero_sha256_t &entity_hash)
{
	for (const auto &candidate : zaero_shipped_map_identities)
		if (!Q_strcasecmp(mapname, candidate.mapname) && Zaero_SHA256Equals(entity_hash, candidate.entity_lump_sha256))
			return candidate.mapname;
	return nullptr;
}

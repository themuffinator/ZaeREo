"""Worldspawn music mapping, provenance, and native-isolation contracts."""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPAWN = (ROOT / "src" / "g_spawn.cpp").read_text(encoding="utf-8")
ASSET_AUDIT = json.loads(
    (ROOT / "docs" / "audits" / "assets.json").read_text(encoding="utf-8")
)
BSP_AUDIT = json.loads(
    (ROOT / "docs" / "audits" / "bsp-entities.json").read_text(encoding="utf-8")
)
SOURCE_AUDIT = json.loads(
    (ROOT / "docs" / "audits" / "source-delta.json").read_text(encoding="utf-8")
)

# Direct extraction from the worldspawn (entity zero) in each BSP from the
# same retail PAK revisions identified by docs/audits/assets.json.
WORLD_MUSIC = {
    "zbase1": 9,
    "zbase2": 6,
    "zboss": 11,
    "zdef1": 4,
    "zdef2": 9,
    "zdef3": 6,
    "zdef4": 3,
    "zdm1": 8,
    "zdm2": 4,
    "zdm3": 3,
    "zdm4": 5,
    "zdm5": 6,
    "zdm6": 1,
    "ztomb1": 5,
    "ztomb2": 6,
    "ztomb3": 3,
    "ztomb4": 11,
    "zwaste1": 6,
    "zwaste2": 9,
    "zwaste3": 11,
}


def function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : index]
    raise AssertionError(f"unterminated function: {signature}")


def resolve_zaero_track(track: int) -> str:
    """Executable model of D-010's stateless per-worldspawn selection."""

    if 2 <= track <= 11:
        return str(track)
    return "0"


class ZaeroWorldMusicTests(unittest.TestCase):
    def test_source_identity_and_all_worldspawn_values_are_locked(self) -> None:
        records = {
            record["path"]: record
            for record in SOURCE_AUDIT["comparison"]["file_records"]
        }
        self.assertEqual(
            records["g_spawn.c"]["zaero_sha256"],
            "60cf870a254e8f80aa5a2a28eb81b7522534f84c7221002247dfae9c091cc75b",
        )
        self.assertEqual(len(WORLD_MUSIC), BSP_AUDIT["summary"]["map_count"])
        self.assertEqual(set(WORLD_MUSIC.values()), {1, 3, 4, 5, 6, 8, 9, 11})
        self.assertEqual(
            [name for name, track in WORLD_MUSIC.items() if track == 1],
            ["zdm6"],
        )

        audited_maps = {record["map_name"]: record for record in BSP_AUDIT["maps"]}
        self.assertEqual(set(WORLD_MUSIC), set(audited_maps))
        for map_name, track in WORLD_MUSIC.items():
            self.assertIn(
                str(track),
                audited_maps[map_name]["value_counts"]["sounds"],
            )

    def test_zaero_distribution_contains_no_music_to_remap_or_publish(self) -> None:
        extensions = ASSET_AUDIT["summary"]["pak_entry_extension_counts"]
        for extension in (".ogg", ".mp3", ".flac", ".mid", ".midi"):
            self.assertNotIn(extension, extensions)
        runtime_paths = [
            entry["path"]
            for archive in ASSET_AUDIT["pak_layers"]
            for entry in archive["entries"]
        ]
        self.assertFalse(any(path.casefold().startswith("music/") for path in runtime_paths))

    def test_numeric_rerelease_mapping_and_logged_silent_fallback(self) -> None:
        helper = function_body(
            SPAWN, "static const char *G_ZaeroWorldMusic(const int32_t track)"
        )
        self.assertRegex(helper, r'case 0:\s*return "0";')
        self.assertRegex(
            helper,
            r'(?s)case 1:.*?unavailable CD track 1; using silence.*?return "0";',
        )
        for track in range(2, 12):
            self.assertRegex(
                helper,
                rf'case {track}:\s*return "{track}";',
            )
            self.assertEqual(resolve_zaero_track(track), str(track))
        self.assertIn("unsupported CD track {}", helper)
        self.assertIn("expected 1-11, using silence", helper)
        self.assertEqual(resolve_zaero_track(1), "0")
        for invalid in (-1, 12, 99):
            self.assertEqual(resolve_zaero_track(invalid), "0")

    def test_explicit_music_precedes_scope_and_native_maps_are_unchanged(self) -> None:
        world = function_body(SPAWN, "void SP_worldspawn(edict_t *ent)\n{")
        explicit = world.index("if (st.music && st.music[0])")
        zaero = world.index("else if (level.is_zaero)", explicit)
        native = world.index("else", zaero + len("else"))
        loop_count = world.index("CS_CD_LOOP_COUNT", native)
        self.assertLess(explicit, zaero)
        self.assertLess(zaero, native)
        self.assertLess(native, loop_count)
        self.assertIn("gi.configstring(CS_CDTRACK, st.music)", world[explicit:zaero])
        self.assertIn(
            "gi.configstring(CS_CDTRACK, G_ZaeroWorldMusic(ent->sounds))",
            world[zaero:native],
        )
        self.assertIn(
            'gi.configstring(CS_CDTRACK, G_Fmt("{}", ent->sounds).data())',
            world[native:loop_count],
        )

    def test_transitions_are_stateless_and_do_not_override_client_volume(self) -> None:
        sequence = [9, 6, 1, 11, 3]
        self.assertEqual(
            [resolve_zaero_track(track) for track in sequence],
            ["9", "6", "0", "11", "3"],
        )
        helper = function_body(
            SPAWN, "static const char *G_ZaeroWorldMusic(const int32_t track)"
        )
        self.assertNotRegex(helper, re.compile(r"volume|loop|static\s+[^c]", re.I))
        self.assertNotIn("gi.cvar", helper)
        self.assertNotIn("CS_CD_LOOP_COUNT", helper)


if __name__ == "__main__":
    unittest.main()

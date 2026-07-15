"""Zaero health sound selection without shared item-table mutation."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ITEMS = (ROOT / "src" / "g_items.cpp").read_text(encoding="utf-8")
BSP_AUDIT = json.loads(
    (ROOT / "docs" / "audits" / "bsp-entities.json").read_text(encoding="utf-8")
)
SOURCE_AUDIT = json.loads(
    (ROOT / "docs" / "audits" / "source-delta.json").read_text(encoding="utf-8")
)

# Direct entity-lump extraction from the BSP identities in the generated audit.
HEALTH_CLASS_COUNTS = {
    "item_health_small": 111,
    "item_health": 198,
    "item_health_large": 129,
    "item_health_mega": 9,
}
HEALTH_COUNT_OVERRIDES: tuple[tuple[str, int, str], ...] = ()
FIXED_ITEM_SOUNDS = {
    "item_health_small": "items/s_health.wav",
    "item_health": "items/n_health.wav",
    "item_health_large": "items/l_health.wav",
    "item_health_mega": "items/m_health.wav",
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


def zaero_health_sound(count: int) -> str:
    return {
        2: "items/s_health.wav",
        10: "items/n_health.wav",
        25: "items/l_health.wav",
    }.get(count, "items/m_health.wav")


class ZaeroHealthPickupTests(unittest.TestCase):
    def test_source_identity_and_all_447_shipped_placements_are_locked(self) -> None:
        records = {
            record["path"]: record
            for record in SOURCE_AUDIT["comparison"]["file_records"]
        }
        self.assertEqual(
            records["g_items.c"]["zaero_sha256"],
            "a02f4cfda2944ad36cf51eb928c82f13f4317d4198389ef63fac361795b0bf46",
        )
        self.assertEqual(
            {
                classname: BSP_AUDIT["global"]["classname_counts"][classname]
                for classname in HEALTH_CLASS_COUNTS
            },
            HEALTH_CLASS_COUNTS,
        )
        self.assertEqual(sum(HEALTH_CLASS_COUNTS.values()), 447)
        self.assertEqual(HEALTH_COUNT_OVERRIDES, ())

    def test_exact_count_to_sound_mapping_includes_legacy_default(self) -> None:
        expected = {
            2: "items/s_health.wav",
            10: "items/n_health.wav",
            25: "items/l_health.wav",
            100: "items/m_health.wav",
            0: "items/m_health.wav",
            7: "items/m_health.wav",
        }
        self.assertEqual(
            {count: zaero_health_sound(count) for count in expected}, expected
        )

        helper = function_body(
            ITEMS, "static const char *G_ZaeroHealthPickupSound(const edict_t *ent)"
        )
        self.assertIn(
            "const int32_t count = ent->count ? ent->count : ent->item->quantity",
            helper,
        )
        for count, sound in ((2, "s"), (10, "n"), (25, "l")):
            self.assertIn(f"case {count}:", helper)
            self.assertIn(f'return "items/{sound}_health.wav"', helper)
        self.assertIn("default:", helper)
        self.assertIn('return "items/m_health.wav"', helper)

    def test_pickup_is_local_and_never_mutates_shared_item_metadata(self) -> None:
        pickup = function_body(ITEMS, "bool Pickup_Health(edict_t *ent, edict_t *other)")
        helper = function_body(
            ITEMS, "static const char *G_ZaeroHealthPickupSound(const edict_t *ent)"
        )
        self.assertNotIn("pickup_sound =", pickup)
        self.assertNotIn("pickup_sound =", helper)

        before = FIXED_ITEM_SOUNDS.copy()
        observed = [zaero_health_sound(count) for count in (2, 25, 7, 10, 100, 2)]
        self.assertEqual(
            observed,
            [
                "items/s_health.wav",
                "items/l_health.wav",
                "items/m_health.wav",
                "items/n_health.wav",
                "items/m_health.wav",
                "items/s_health.wav",
            ],
        )
        self.assertEqual(FIXED_ITEM_SOUNDS, before)

    def test_explicit_noise_wins_and_native_maps_keep_fixed_item_sound(self) -> None:
        touch = function_body(
            ITEMS,
            "TOUCH(Touch_Item) (edict_t *ent, edict_t *other, const trace_t &tr, bool other_touching_self) -> void",
        )
        explicit = touch.index("if (ent->noise_index)")
        zaero = touch.index(
            "else if (level.is_zaero && ent->item->pickup == Pickup_Health)",
            explicit,
        )
        native = touch.index("else if (ent->item->pickup_sound)", zaero)
        self.assertLess(explicit, zaero)
        self.assertLess(zaero, native)
        self.assertIn("G_ZaeroHealthPickupSound(ent)", touch[zaero:native])
        self.assertIn("ent->item->pickup_sound", touch[native:])


if __name__ == "__main__":
    unittest.main()

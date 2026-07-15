"""Static contracts for AI-015 stock precache adaptation and D-043."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
AUDIT = json.loads(
    (ROOT / "docs" / "audits" / "stock-precaches.json").read_text(
        encoding="utf-8"
    )
)
SOURCE_DELTA = json.loads(
    (ROOT / "docs" / "audits" / "source-delta.json").read_text(encoding="utf-8")
)
BASELINES = json.loads(
    (ROOT / "docs" / "provenance" / "baselines.json").read_text(
        encoding="utf-8"
    )
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ZaeroStockPrecacheContractTests(unittest.TestCase):
    def test_all_22_added_helpers_and_19_owner_files_are_identity_locked(self) -> None:
        summary = AUDIT["summary"]
        self.assertEqual(summary["helper_count"], 22)
        self.assertEqual(summary["source_file_count"], 19)
        self.assertEqual(summary["helpers_by_source"]["m_soldier.c"], 4)
        self.assertTrue(
            all(count == 1 for path, count in summary["helpers_by_source"].items()
                if path != "m_soldier.c")
        )

        source_records = {
            record["path"]: record
            for record in SOURCE_DELTA["comparison"]["file_records"]
        }
        zaero_inputs = {
            record["path"]: record
            for record in AUDIT["inputs"]["zaero_sources"]
        }
        legacy_inputs = {
            record["path"]: record
            for record in AUDIT["inputs"]["legacy_sources"]
        }
        for owner in summary["helpers_by_source"]:
            self.assertEqual(
                zaero_inputs[owner]["sha256"], source_records[owner]["zaero_sha256"]
            )
            self.assertEqual(
                legacy_inputs[owner]["sha256"], source_records[owner]["legacy_sha256"]
            )

    def test_only_infantry_is_reused_across_legacy_source_files(self) -> None:
        external = [
            helper
            for helper in AUDIT["stock_precache_extractions"]
            if helper["external_call_sites"]
        ]
        self.assertEqual(AUDIT["summary"]["externally_reused_helper_count"], 1)
        self.assertEqual(AUDIT["summary"]["external_call_site_count"], 1)
        self.assertEqual(len(external), 1)
        self.assertEqual(external[0]["name"], "SP_monster_infantry_precache")
        self.assertEqual(
            external[0]["external_call_sites"],
            [
                {
                    "caller": "SP_monster_handler_precache",
                    "line": 404,
                    "path": "z_handler.c",
                }
            ],
        )

    def test_rerelease_already_owns_the_cross_module_precache_surface(self) -> None:
        calls = {
            (item["path"], item["caller"])
            for item in AUDIT["port_adaptation"]["native_rerelease_calls"]
        }
        self.assertEqual(
            calls,
            {
                ("g_turret.cpp", "SP_turret_driver"),
                ("m_infantry.cpp", "SP_monster_infantry"),
            },
        )
        baseline_files = {
            record["path"]: record
            for record in BASELINES["baselines"]["quake2_rerelease"]["files"]
        }
        for record in AUDIT["inputs"]["rerelease_sources"]:
            self.assertEqual(record["sha256"], baseline_files[record["path"]]["sha256"])

    def test_port_reuses_native_infantry_and_zaero_owned_hound_precaches(self) -> None:
        calls = {
            (item["path"], item["caller"])
            for item in AUDIT["port_adaptation"]["port_calls"]
        }
        self.assertEqual(
            calls,
            {
                ("g_turret.cpp", "SP_turret_driver"),
                ("m_infantry.cpp", "InfantryConvertFromZaeroHandler"),
                ("m_infantry.cpp", "SP_monster_infantry"),
                ("zaero/g_zaero_handler.cpp", "handler_precache"),
            },
        )
        self.assertEqual(
            AUDIT["port_adaptation"]["port_hound_calls"][0]["caller"],
            "handler_precache",
        )
        for record in AUDIT["inputs"]["port_sources"]:
            self.assertEqual(record["sha256"], sha256(ROOT / "src" / record["path"]))
        strategy = AUDIT["port_adaptation"]["sound_index_strategy"]
        self.assertTrue(strategy["uses_cached_assignments"])
        self.assertEqual(strategy["legacy_cache_interceptor_symbols_present"], [])

    def test_disabled_legacy_limit_workaround_is_not_ported(self) -> None:
        context = AUDIT["legacy_sound_index_context"]
        self.assertEqual(context["zaero_max_sounds"], 256)
        self.assertEqual(context["rerelease_legacy_compatibility_limit"], 256)
        self.assertEqual(context["rerelease_max_sounds"], 2048)
        cache = context["cache_sound_workaround"]
        self.assertFalse(cache["supplied_project_defines_cache_sound"])
        for fact in (
            "allocates_per_level_list_and_names",
            "intercepts_global_soundindex",
            "lowercases_caller_buffer_in_place",
            "rejects_at_legacy_limit_with_zero",
        ):
            self.assertTrue(cache[fact])
        self.assertIn("Other resource, AI, EMP, flash", AUDIT["scope_note"])


if __name__ == "__main__":
    unittest.main()

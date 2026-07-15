from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from audit_identifier_surface import (  # noqa: E402
    IdentifierSurfaceAuditError,
    build_identifier_surface_report,
    identifier_surface_markdown,
    require_complete,
)


class IdentifierSurfaceAuditTests(unittest.TestCase):
    def test_checked_in_audit_reproduces_current_identifier_contracts(self) -> None:
        report = build_identifier_surface_report(ROOT / "src")
        expected = json.loads((ROOT / "docs" / "audits" / "identifier-surface.json").read_text(encoding="utf-8"))
        self.assertEqual(report, expected)
        self.assertEqual(
            identifier_surface_markdown(report),
            (ROOT / "docs" / "audits" / "identifier-surface.md").read_text(encoding="utf-8"),
        )
        self.assertTrue(report["summary"]["complete"])
        self.assertEqual(report["violations"], [])
        self.assertEqual(report["wheel_capacities"]["runtime_guard_count"], 3)

    def test_item_enum_collision_fails_closed(self) -> None:
        source_root = ROOT / "src"
        broken_local = (source_root / "g_local.h").read_text(encoding="utf-8").replace(
            "IT_WEAPON_FLAREGUN,", "IT_WEAPON_FLAREGUN = IT_WEAPON_PUSH,", 1
        )
        with self.assertRaisesRegex(IdentifierSurfaceAuditError, "enumerator value collision"):
            build_identifier_surface_report(source_root, local_source=broken_local)

    def test_zaero_bit_namespaces_fail_closed_on_drift(self) -> None:
        source_root = ROOT / "src"
        original_local = (source_root / "g_local.h").read_text(encoding="utf-8")
        broken_ai = original_local.replace("AI_ZAERO_SCHOOLING = bit_v<40>", "AI_ZAERO_SCHOOLING = bit_v<44>", 1)
        report = build_identifier_surface_report(source_root, local_source=broken_ai)
        self.assertFalse(report["summary"]["complete"])
        self.assertIn("Zaero AI flags no longer use the reserved terminal bits 39 through 43", report["violations"])

        broken_spawnflags2 = original_local.replace(
            "ZAERO_SPAWNFLAG2_NOT_SINGLE = 1u << 2", "ZAERO_SPAWNFLAG2_NOT_SINGLE = 1u << 3", 1
        )
        report = build_identifier_surface_report(source_root, local_source=broken_spawnflags2)
        self.assertFalse(report["summary"]["complete"])
        self.assertIn("zaero_spawnflags2_t no longer uses its independent 0/1/2/4 namespace", report["violations"])

    def test_registry_and_capacity_drift_fail_closed(self) -> None:
        source_root = ROOT / "src"
        original_items = (source_root / "g_items.cpp").read_text(encoding="utf-8")
        broken_registry = original_items.replace("/* id */ IT_WEAPON_PUSH", "/* id */ IT_NULL", 1)
        report = build_identifier_surface_report(source_root, items_source=broken_registry)
        self.assertFalse(report["summary"]["complete"])
        self.assertIn("itemlist ID annotations no longer match item_id_t order exactly", report["violations"])

        broken_capacity = original_items.replace("ZAERO_WEAPON_WHEEL_SLOTS = 24", "ZAERO_WEAPON_WHEEL_SLOTS = 25", 1)
        report = build_identifier_surface_report(source_root, items_source=broken_capacity)
        self.assertFalse(report["summary"]["complete"])
        self.assertIn("ZAERO_WEAPON_WHEEL_SLOTS does not match the item registry", report["violations"])
        with self.assertRaisesRegex(IdentifierSurfaceAuditError, "incomplete identifier surface"):
            require_complete(report)


if __name__ == "__main__":
    unittest.main()

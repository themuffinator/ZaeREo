from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from audit_save_surface import (  # noqa: E402
    SaveSurfaceAuditError,
    build_save_surface_report,
    require_complete,
    save_surface_markdown,
)


class SaveSurfaceAuditTests(unittest.TestCase):
    def test_checked_in_audit_reproduces_and_covers_current_zaero_surface(self) -> None:
        report = build_save_surface_report(ROOT / "src")
        expected = json.loads((ROOT / "docs" / "audits" / "save-surface.json").read_text(encoding="utf-8"))
        self.assertEqual(report, expected)
        self.assertEqual(
            save_surface_markdown(report),
            (ROOT / "docs" / "audits" / "save-surface.md").read_text(encoding="utf-8"),
        )
        self.assertTrue(report["summary"]["complete"])
        self.assertEqual(report["missing_fields"], [])
        self.assertEqual(report["missing_callbacks"], [])
        self.assertGreaterEqual(report["summary"]["field_count"], 30)
        self.assertGreaterEqual(report["summary"]["callback_count"], 100)

    def test_missing_registration_fails_closed(self) -> None:
        source_root = ROOT / "src"
        broken_save = (source_root / "g_save.cpp").read_text(encoding="utf-8").replace(
            "FIELD_AUTO(zaero_content_active)", "/* missing Zaero field registration */", 1
        )
        report = build_save_surface_report(source_root, save_source=broken_save)
        self.assertFalse(report["summary"]["complete"])
        with self.assertRaisesRegex(SaveSurfaceAuditError, "incomplete registration"):
            require_complete(report)
        self.assertNotIn("FIELD_AUTO(zaero_content_active)", broken_save)

    def test_missing_callback_macro_registration_fails_closed(self) -> None:
        source_root = ROOT / "src"
        broken_local = (source_root / "g_local.h").read_text(encoding="utf-8").replace(
            "static const save_data_list_t save__##n(#n, SAVE_FUNC_THINK",
            "/* missing callback registration */",
            1,
        )
        report = build_save_surface_report(source_root, local_source=broken_local)
        self.assertFalse(report["summary"]["complete"])
        self.assertGreater(len(report["missing_callbacks"]), 0)
        with self.assertRaisesRegex(SaveSurfaceAuditError, "incomplete registration"):
            require_complete(report)


if __name__ == "__main__":
    unittest.main()

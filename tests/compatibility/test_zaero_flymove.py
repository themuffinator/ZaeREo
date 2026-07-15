"""Source and executable-golden contracts for Q-048/D-044."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from audit_common import sha256_file  # noqa: E402
from audit_flymove import golden_results  # noqa: E402


REPORT = json.loads(
    (ROOT / "docs" / "audits" / "flymove.json").read_text(encoding="utf-8")
)
PHYS = (ROOT / "src" / "g_phys.cpp").read_text(encoding="utf-8")
MOVE = (ROOT / "src" / "p_move.cpp").read_text(encoding="utf-8")


class ZaeroFlyMoveContractTests(unittest.TestCase):
    def test_supplied_and_target_sources_are_identity_locked(self) -> None:
        self.assertEqual(
            REPORT["inputs"]["legacy"][0]["sha256"],
            "31e3b813814c249734550d262d2b4766184849563960c0d9715005a6e5743481",
        )
        self.assertEqual(
            REPORT["inputs"]["zaero"][0]["sha256"],
            "21a0e0374a925c9de1ac9e5143de80a64c2f197702b4ec8cbab1ecea45d5d056",
        )
        current = {item["path"]: item["sha256"] for item in REPORT["inputs"]["port"]}
        self.assertEqual(current["g_phys.cpp"], sha256_file(ROOT / "src" / "g_phys.cpp"))
        self.assertEqual(current["p_move.cpp"], sha256_file(ROOT / "src" / "p_move.cpp"))

    def test_one_line_global_delta_is_exact(self) -> None:
        delta = REPORT["source_delta"]
        self.assertEqual(
            delta["legacy_suppression_condition"],
            "if ((j != i) && !VectorCompare (planes[i], planes[j]))",
        )
        self.assertEqual(delta["zaero_only_semantic_change"], "if (j != i)")
        self.assertTrue(delta["port_matches_rerelease_function"])
        self.assertTrue(delta["port_matches_rerelease_helper"])
        self.assertEqual(delta["rerelease_near_duplicate_threshold"], 0.99)
        self.assertEqual(delta["rerelease_overbounce"], 1.01)

    def test_checked_report_reproduces_all_float32_goldens(self) -> None:
        self.assertEqual(golden_results(), REPORT["golden_cases"])
        self.assertEqual(REPORT["summary"]["golden_case_count"], 7)
        differences = [
            case["id"]
            for case in REPORT["golden_cases"]
            if not case["legacy_equals_zaero"]
        ]
        self.assertEqual(differences, ["projectile-duplicate-plane"])

    def test_exact_duplicate_residual_explains_the_behavior_change(self) -> None:
        case = next(
            item
            for item in REPORT["golden_cases"]
            if item["id"] == "projectile-duplicate-plane"
        )
        self.assertEqual(
            case["legacy"]["final_velocity"],
            [305.685394, -6.345245, -216.150848],
        )
        self.assertEqual(case["legacy"]["suppressed_exact_duplicate_comparisons"], 1)
        self.assertEqual(case["zaero"]["exact_duplicate_negative_rejections"], 2)
        self.assertEqual(case["zaero"]["final_velocity"], [0.0, 0.0, 0.0])
        self.assertEqual(case["rerelease"]["duplicate_skips"], 1)
        self.assertNotEqual(case["rerelease"]["final_velocity"], [0.0, 0.0, 0.0])

    def test_native_solver_remains_shared_and_unforked(self) -> None:
        helper_calls = {
            (item["path"], item["caller"])
            for item in REPORT["call_graph"]["rerelease_shared_helper"]
        }
        self.assertEqual(
            helper_calls,
            {
                ("g_phys.cpp", "SV_FlyMove"),
                ("p_move.cpp", "PM_CheckSpecialMovement"),
                ("p_move.cpp", "PM_StepSlideMove_"),
            },
        )
        self.assertIn("PM_StepSlideMove_Generic", PHYS)
        self.assertIn("trace.plane.normal.dot(planes[i]) > 0.99f", MOVE)
        self.assertNotIn("VectorCompare (planes[i], planes[j])", PHYS + MOVE)
        self.assertNotIn("Zaero", PHYS[PHYS.index("void SV_FlyMove") : PHYS.index("void SV_AddGravity")])


if __name__ == "__main__":
    unittest.main()

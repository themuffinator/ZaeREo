"""Deterministic contracts for the Q-048 SV_FlyMove audit."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from audit_common import AuditError  # noqa: E402
from audit_flymove import build_report, markdown_report  # noqa: E402


LEGACY_FLYMOVE = """
void SV_FlyMove(void) {
 int i = 0, j = 0;
 vec3_t planes[2];
 if ((j != i) && !VectorCompare (planes[i], planes[j])) { use_plane(); }
}
"""

ZAERO_FLYMOVE = """
void SV_FlyMove(void) {
 int i = 0, j = 0;
 vec3_t planes[2];
 if (j != i) { use_plane(); }
}
"""

RERELEASE_FLYMOVE = """
void SV_FlyMove(void) { PM_StepSlideMove_Generic(); }
"""

RERELEASE_HELPER = """
void PM_StepSlideMove_Generic(void) {
 if (trace.plane.normal.dot(planes[i]) > 0.99f) { repeat(); }
 if (i < numplanes) { continue; }
 PM_ClipVelocity(velocity, planes[i], velocity, 1.01f);
}
void PM_StepSlideMove_(void) { PM_StepSlideMove_Generic(); }
void PM_CheckSpecialMovement(void) { PM_StepSlideMove_Generic(); }
"""


class FlyMoveAuditTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> tuple[Path, Path, Path, Path]:
        zaero = root / "zaero"
        legacy = root / "legacy"
        rerelease = root / "rerelease"
        port = root / "port"
        for path in (
            zaero,
            legacy,
            rerelease / "rogue",
            port / "rogue",
            port / "zaero",
        ):
            path.mkdir(parents=True)

        (legacy / "g_phys.c").write_text(
            LEGACY_FLYMOVE
            + "void SV_Physics_Step(void) { SV_FlyMove(); }\n",
            encoding="latin-1",
        )
        (zaero / "g_phys.c").write_text(
            ZAERO_FLYMOVE
            + "void SV_Physics_Step(void) { SV_FlyMove(); }\n"
            + "void SV_Physics_FallFloat(void) { SV_FlyMove(); }\n",
            encoding="latin-1",
        )
        (zaero / "g_ai.c").write_text(
            "void ai_fly_strafe(void) { SV_FlyMove(); }\n", encoding="latin-1"
        )

        (rerelease / "g_phys.cpp").write_text(
            RERELEASE_FLYMOVE
            + "void SV_Physics_Step(void) { SV_FlyMove(); }\n",
            encoding="latin-1",
        )
        (rerelease / "p_move.cpp").write_text(
            RERELEASE_HELPER, encoding="latin-1"
        )
        (rerelease / "rogue" / "g_rogue_phys.cpp").write_text(
            "void SV_Physics_NewToss(void) { SV_FlyMove(); }\n",
            encoding="latin-1",
        )

        (port / "g_phys.cpp").write_text(
            RERELEASE_FLYMOVE
            + "void SV_Physics_Step(void) { SV_FlyMove(); }\n"
            + "void SV_Physics_FallFloat(void) { SV_FlyMove(); }\n",
            encoding="latin-1",
        )
        (port / "p_move.cpp").write_text(RERELEASE_HELPER, encoding="latin-1")
        (port / "rogue" / "g_rogue_phys.cpp").write_text(
            "void SV_Physics_NewToss(void) { SV_FlyMove(); }\n",
            encoding="latin-1",
        )
        (port / "zaero" / "g_zaero_ai.cpp").write_text(
            "void Zaero_RunFlyStrafe(void) { SV_FlyMove(); }\n",
            encoding="latin-1",
        )
        return zaero, legacy, rerelease, port

    def test_report_isolates_one_line_and_native_shared_helper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            report = build_report(*self.make_fixture(Path(temporary_name)))

        self.assertEqual(report["summary"]["golden_case_count"], 7)
        self.assertEqual(report["summary"]["legacy_zaero_difference_case_count"], 1)
        self.assertTrue(report["source_delta"]["port_matches_rerelease_function"])
        self.assertTrue(report["source_delta"]["port_matches_rerelease_helper"])
        duplicate = next(
            case
            for case in report["golden_cases"]
            if case["id"] == "projectile-duplicate-plane"
        )
        self.assertEqual(duplicate["legacy"]["terminal"], "plane")
        self.assertEqual(duplicate["zaero"]["terminal"], "primal-stop")
        self.assertEqual(duplicate["rerelease"]["duplicate_skips"], 1)
        markdown = markdown_report(report)
        self.assertIn("one-line global", markdown)
        self.assertIn("not live BSP trace captures", markdown)

    def test_additional_legacy_function_change_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            inputs = self.make_fixture(Path(temporary_name))
            path = inputs[0] / "g_phys.c"
            path.write_text(
                path.read_text(encoding="latin-1").replace(
                    "void SV_FlyMove(void) {", "void SV_FlyMove(void) { changed();"
                ),
                encoding="latin-1",
            )
            with self.assertRaisesRegex(AuditError, "differs beyond the one plane"):
                build_report(*inputs)


if __name__ == "__main__":
    unittest.main()

"""Deterministic contracts for the legacy Visor trace-order audit."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from audit_common import AuditError  # noqa: E402
from audit_visor_trace_order import build_report, markdown_report  # noqa: E402


CAMERA = """
void zCam_TrackEntity(void) {
 player->movetype = MOVETYPE_FREEZE;
 e->classname = "VisorCopy";
 e->owner = player;
 e->movetype = MOVETYPE_NONE;
 e->solid = SOLID_BBOX;
 player->svflags |= SVF_NOCLIENT;
 gi.linkentity(e);
}
void zCam_Stop(void) { player->movetype = MOVETYPE_WALK; }
"""

CLIENT = """
void ClientThink(void) {
 if(ent->movetype == MOVETYPE_FREEZE) {
  client->ps.pmove.pm_type = PM_FREEZE;
  return;
 }
}
"""

PHYSICS = """
qboolean SV_Push(void) {
 if (check->movetype == MOVETYPE_PUSH
 || check->movetype == MOVETYPE_NOCLIP)
  continue;
 VectorAdd (check->s.origin, move, check->s.origin);
 gi.linkentity (check);
}
"""

WORLD = """
void SV_LinkEdict(void) {
 InsertLinkBefore (&ent->area, &node->solid_edicts);
}
void SV_ClipMoveToEntities(void) {
 SV_AreaEdicts (clip->boxmins, clip->boxmaxs, touchlist;
 if (trace.fraction < clip->trace.fraction) {}
}
"""


class VisorTraceOrderAuditTests(unittest.TestCase):
    def make_inputs(self, root: Path) -> tuple[Path, Path, Path]:
        zaero = root / "zaero"
        legacy = root / "legacy"
        (legacy / "server").mkdir(parents=True)
        zaero.mkdir()
        (zaero / "z_camera.c").write_text(CAMERA, encoding="latin-1")
        (zaero / "p_client.c").write_text(CLIENT, encoding="latin-1")
        (zaero / "g_phys.c").write_text(PHYSICS, encoding="latin-1")
        (legacy / "server" / "sv_world.c").write_text(WORLD, encoding="latin-1")
        binary = root / "gamex86.dll"
        binary.write_bytes(b"retail-fixture")
        return zaero, legacy, binary

    def test_report_proves_link_order_dependence_and_fix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            zaero, legacy, binary = self.make_inputs(Path(temporary))
            report = build_report(zaero, legacy, binary)

        facts = report["proof"]["facts"]
        self.assertEqual(facts["initial_equal_hit_winner"], "real_player")
        self.assertEqual(facts["post_pusher_equal_hit_winner"], "VisorCopy")
        self.assertTrue(facts["trace_ownership_is_link_order_dependent"])
        self.assertEqual(report["disposition"]["classification"], "FIX")
        self.assertEqual(
            report["disposition"]["implementation"]["visual_copy"],
            "visible, generation-owned, SOLID_NOT, not damageable",
        )
        markdown = markdown_report(report)
        self.assertIn("does not claim a live retail capture", markdown)
        self.assertIn("Live hitscan, projectile, mover, save/load", markdown)

    def test_audit_fails_if_frozen_players_become_excluded_from_pushers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            zaero, legacy, binary = self.make_inputs(Path(temporary))
            path = zaero / "g_phys.c"
            path.write_text(
                PHYSICS + "\ncheck->movetype == MOVETYPE_FREEZE;\n",
                encoding="latin-1",
            )
            with self.assertRaisesRegex(AuditError, "unexpectedly excludes"):
                build_report(zaero, legacy, binary)


if __name__ == "__main__":
    unittest.main()

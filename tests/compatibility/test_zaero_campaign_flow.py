"""Campaign changelevel closure and the unreachable ztomb1 tomb1 artifact."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TARGET = (ROOT / "src" / "g_target.cpp").read_text(encoding="utf-8")
UTILS = (ROOT / "src" / "g_utils.cpp").read_text(encoding="utf-8")
BSP_AUDIT = json.loads(
    (ROOT / "docs" / "audits" / "bsp-entities.json").read_text(encoding="utf-8")
)
SOURCE_AUDIT = json.loads(
    (ROOT / "docs" / "audits" / "source-delta.json").read_text(encoding="utf-8")
)


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


class ZaeroCampaignFlowTests(unittest.TestCase):
    def test_source_and_ztomb1_bsp_identities_are_locked(self) -> None:
        source_records = {
            record["path"]: record
            for record in SOURCE_AUDIT["comparison"]["file_records"]
        }
        self.assertEqual(
            source_records["g_target.c"]["zaero_sha256"],
            "25b0bab6a361b6682fdcea59c4b2e2f306b85a079f7ea52d7b869bfecb046af0",
        )
        self.assertEqual(
            source_records["g_utils.c"]["zaero_sha256"],
            "9f38a328cd489960933de750600781b4e89224bb37b38a97d021d45db3c1fcb9",
        )
        ztomb1 = next(
            record for record in BSP_AUDIT["maps"] if record["map_name"] == "ztomb1"
        )
        self.assertEqual(
            ztomb1["sha256"],
            "b19a7d4ec771d99e1fef9c754d4da89c51dc14f99e157a5eb2464c3a506c00eb",
        )

    def test_all_30_changelevels_have_deterministic_target_and_bsp_closure(self) -> None:
        summary = BSP_AUDIT["summary"]
        self.assertEqual(summary["target_changelevel_count"], 30)
        self.assertEqual(summary["orphan_changelevel_count"], 1)
        self.assertEqual(summary["missing_changelevel_bsp_count"], 1)

        changelevels = BSP_AUDIT["global"]["changelevels"]
        orphans = [
            item for item in changelevels if item["activation_reference_count"] == 0
        ]
        missing = [
            item
            for item in changelevels
            if item["destination_kind"] == "bsp"
            and not item["destination_present"]
        ]
        identity = lambda item: (item["map_name"], item["entity_index"], item["map"])
        self.assertEqual([identity(item) for item in orphans], [("ztomb1", 522, "tomb1")])
        self.assertEqual([identity(item) for item in missing], [("ztomb1", 522, "tomb1")])
        self.assertEqual(
            [item["activation_reference_count"] for item in changelevels].count(1),
            29,
        )
        self.assertTrue(
            all(
                item["destination_present"]
                for item in changelevels
                if item["destination_kind"] == "bsp" and item not in missing
            )
        )

    def test_tomb1_changelevel_has_no_reference_or_alternate_activation_path(self) -> None:
        artifact = next(
            item
            for item in BSP_AUDIT["global"]["changelevels"]
            if item["map_name"] == "ztomb1" and item["entity_index"] == 522
        )
        self.assertEqual(artifact["targetname"], "mainexit")
        self.assertEqual(artifact["destination_bsp"], "maps/tomb1.bsp")
        self.assertEqual(artifact["target_references"], [])
        self.assertEqual(artifact["activation_reference_count"], 0)
        self.assertEqual(artifact["other_reference_count"], 0)

        spawn = function_body(TARGET, "void SP_target_changelevel(edict_t *ent)")
        self.assertIn("ent->use = use_target_changelevel", spawn)
        self.assertIn("ent->svflags = SVF_NOCLIENT", spawn)
        self.assertNotIn("touch", spawn)
        self.assertNotIn("think", spawn)
        use_targets = function_body(UTILS, "void G_UseTargets(edict_t *ent, edict_t *activator)")
        self.assertIn(
            "G_FindByString<&edict_t::targetname>(t, ent->target)",
            use_targets,
        )
        self.assertIn("t->use(t, ent, activator)", use_targets)

        production_source = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in (ROOT / "src").rglob("*")
            if path.suffix in {".cpp", ".h"}
        )
        self.assertNotIn('"mainexit"', production_source)


if __name__ == "__main__":
    unittest.main()

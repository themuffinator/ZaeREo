from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "generate_editor_defs", ROOT / "tools" / "generate_editor_defs.py"
)
assert SPEC is not None and SPEC.loader is not None
GENERATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GENERATOR
SPEC.loader.exec_module(GENERATOR)


EXPECTED_CLASSNAMES = {
    "ammo_a2k",
    "ammo_empnuke",
    "ammo_flares",
    "ammo_ired",
    "ammo_plasmashield",
    "func_barrier",
    "item_visor",
    "key_clearancepass",
    "key_energy",
    "key_lab",
    "key_landing_area",
    "key_lava",
    "key_slime",
    "load_mirrorlevel",
    "misc_commdish",
    "misc_crate",
    "misc_crate_medium",
    "misc_crate_small",
    "misc_ired",
    "misc_seat",
    "misc_securitycamera",
    "monster_autocannon",
    "monster_autocannon_floor",
    "monster_handler",
    "monster_hound",
    "monster_sentien",
    "monster_zboss",
    "sound_echo",
    "target_zboss_target",
    "trigger_laser",
    "weapon_flaregun",
    "weapon_push",
    "weapon_sniperrifle",
    "weapon_soniccannon",
}


class EditorDefinitionTests(unittest.TestCase):
    def test_schema_locks_every_exact_source_facing_classname(self) -> None:
        entities = GENERATOR.load_schema(ROOT / "editor" / "entities.json")
        actual = {entity.classname for entity in entities}
        self.assertEqual(actual, EXPECTED_CLASSNAMES)
        self.assertEqual(len(entities), 34)
        self.assertIn("monster_sentien", actual)
        self.assertNotIn("monster_sentient", actual)

    def test_all_editor_outputs_are_byte_identical_and_current(self) -> None:
        entities = GENERATOR.load_schema(ROOT / "editor" / "entities.json")
        expected = GENERATOR.render_fgd(entities)
        contents = [path.read_text(encoding="utf-8") for path in GENERATOR.OUTPUTS]
        self.assertEqual(contents, [expected] * len(GENERATOR.OUTPUTS))
        self.assertEqual(GENERATOR.update_outputs(expected, GENERATOR.OUTPUTS, True), [])

    def test_generated_fgd_declares_each_class_once(self) -> None:
        fgd = (ROOT / "editor" / "common" / "ZaeREo.fgd").read_text(encoding="utf-8")
        for classname in EXPECTED_CLASSNAMES:
            self.assertEqual(fgd.count(f" = {classname} : "), 1, classname)
        self.assertIn("1 : \"Start off\" : 0", fgd)
        self.assertIn("4 : \"Respawn after 15 seconds outside deathmatch\" : 0", fgd)
        self.assertIn("8 : \"Cap pickup inventory to entity quantity\" : 0", fgd)
        self.assertIn("8 : \"Schooling\" : 0", fgd)
        self.assertIn('mins(vector) : "Runtime collision minimums;', fgd)

    def test_schema_rejects_duplicate_names_and_traversal_models(self) -> None:
        source = json.loads((ROOT / "editor" / "entities.json").read_text(encoding="utf-8"))
        source["entities"][1]["classname"] = source["entities"][0]["classname"]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "duplicate.json"
            path.write_text(json.dumps(source), encoding="utf-8")
            with self.assertRaisesRegex(GENERATOR.SchemaError, "duplicate classname"):
                GENERATOR.load_schema(path)

        source = json.loads((ROOT / "editor" / "entities.json").read_text(encoding="utf-8"))
        source["entities"][0]["model"] = "../outside.md2"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "traversal.json"
            path.write_text(json.dumps(source), encoding="utf-8")
            with self.assertRaisesRegex(GENERATOR.SchemaError, "relative runtime path"):
                GENERATOR.load_schema(path)


if __name__ == "__main__":
    unittest.main()

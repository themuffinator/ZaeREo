"""Deterministic contracts for the Zaero deathmatch-injection audit."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from audit_common import AuditError  # noqa: E402
from audit_dm_injection import (  # noqa: E402
    CANONICAL_MAPS,
    ITEMS,
    build_report,
    markdown_report,
)


class DeathmatchInjectionAuditTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> tuple[Path, Path, Path]:
        zaero = root / "zaero"
        port = root / "port"
        (port / "zaero").mkdir(parents=True)
        zaero.mkdir()

        quoted_items = ",\n".join(f'    "{item}"' for item in ITEMS)
        (zaero / "z_spawn.c").write_text(
            f"char *items[] = {{\n{quoted_items},\n NULL\n}};\n"
            "void Z_SpawnDMItems(void) {\n"
            " if (!deathmatch->value) return;\n"
            " if ((int)zdmflags->value & ZDM_ZAERO_ITEMS) return;\n"
            " if (e != NULL) return;\n"
            " for (j = 0; j < 4; j++) {}\n"
            " start[2] += 16;\n"
            " for (ang = startAng; ang < startAng + 360; ang += 15) {}\n"
            " VectorMA(start, 128, forward, end);\n"
            " tr = gi.trace(start, ent->mins, ent->maxs, end, NULL, MASK_SHOT);\n"
            " ent->movetype = MOVETYPE_BOUNCE;\n"
            ' gi.dprintf ("%i Zaero entities added\\n", added);\n'
            "}\n",
            encoding="latin-1",
        )
        (zaero / "g_local.h").write_text(
            "#define ZDM_NO_GL_POLYBLEND_DAMAGE 1\n"
            "#define ZDM_ZAERO_ITEMS 2\n",
            encoding="latin-1",
        )
        (zaero / "g_save.c").write_text(
            'zdmflags = gi.cvar ("zdmflags", "0", CVAR_SERVERINFO);\n',
            encoding="latin-1",
        )

        (port / "zaero" / "g_zaero_dm.h").write_text(
            "ZAERO_DMFLAG_DISABLE_FLARE_POLYBLEND_DAMAGE = 1 << 0,\n"
            "ZAERO_DMFLAG_DISABLE_ITEM_INJECTION = 1 << 1\n",
            encoding="utf-8",
        )
        (port / "zaero" / "g_zaero_dm.cpp").write_text(
            f"constexpr const char *ZAERO_DEATHMATCH_ITEMS[] = {{\n{quoted_items}\n}};\n"
            "ZAERO_ITEM_PLACEMENT_ATTEMPTS = 4;\n"
            "ZAERO_ITEM_ANGLE_STEP = 15;\n"
            "ZAERO_ITEM_PLACEMENT_RADIUS = 128.0f;\n"
            "ZAERO_ITEM_PLACEMENT_HEIGHT = 16.0f;\n"
            "void f() {\n"
            " if (!deathmatch->integer) return;\n"
            " if (zdmflags->integer & ZAERO_DMFLAG_DISABLE_ITEM_INJECTION) return;\n"
            " ent->movetype = MOVETYPE_BOUNCE;\n"
            " ED_CallSpawn(ent);\n"
            " if (!ent->inuse) return false;\n"
            " gi.trace(start, ent->mins, ent->maxs, end, nullptr, MASK_SHOT);\n"
            " G_FreeEdict(ent);\n"
            ' gi.Com_PrintFmt("{} Zaero entities added\\n", added);\n'
            "}\n",
            encoding="utf-8",
        )
        (port / "g_spawn.cpp").write_text(
            "G_FindTeams();\nZaero_SpawnDeathmatchItems();\nCTFSpawn();\n",
            encoding="utf-8",
        )
        (port / "g_main.cpp").write_text(
            'zdmflags = gi.cvar("zdmflags", "0", CVAR_SERVERINFO);\n',
            encoding="utf-8",
        )
        (port / "g_items.cpp").write_text(
            "TOUCH(Touch_Item) {}\nTHINK(droptofloor) {}\n"
            "void SpawnItem() { ent->think = droptofloor; }\n",
            encoding="utf-8",
        )
        (port / "zaero" / "g_zaero_weapons.cpp").write_text(
            "if (zdmflags->integer & "
            "ZAERO_DMFLAG_DISABLE_FLARE_POLYBLEND_DAMAGE) {}\n",
            encoding="utf-8",
        )
        (port / "game.vcxproj").write_text(
            '<ClInclude Include="zaero\\g_zaero_dm.h" />\n'
            '<ClCompile Include="zaero\\g_zaero_dm.cpp" />\n',
            encoding="utf-8",
        )

        maps = []
        names = sorted(CANONICAL_MAPS)
        for index, name in enumerate(names):
            maps.append(
                {
                    "map_name": name,
                    "map_kind": "deathmatch" if name.startswith("zdm") else "campaign",
                    "deathmatch_start_count": 21 if index == len(names) - 1 else 11,
                    "classname_counts": {ITEMS[0]: 1},
                }
            )
        bsp_audit = root / "bsp-entities.json"
        bsp_audit.write_text(json.dumps({"maps": maps}), encoding="utf-8")
        return zaero, port, bsp_audit

    def test_report_locks_bits_order_hook_and_retail_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = build_report(*self.make_fixture(Path(temporary)))

        self.assertEqual(report["legacy_contract"]["item_order"], list(ITEMS))
        self.assertEqual(report["port_contract"]["item_order"], list(ITEMS))
        self.assertFalse(report["disposition"]["mapper_classification_required"])
        self.assertEqual(report["summary"]["supplied_map_count"], 20)
        self.assertEqual(report["summary"]["supplied_deathmatch_start_count"], 230)
        self.assertEqual(report["summary"]["supplied_maps_eligible_for_injection"], 0)
        markdown = markdown_report(report)
        self.assertIn("precondition", markdown)
        self.assertIn("stock/community", markdown)

    def test_changed_port_item_order_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            inputs = self.make_fixture(Path(temporary))
            source = inputs[1] / "zaero" / "g_zaero_dm.cpp"
            text = source.read_text(encoding="utf-8")
            text = text.replace(ITEMS[0], "swap", 1).replace(ITEMS[1], ITEMS[0], 1)
            text = text.replace("swap", ITEMS[1], 1)
            source.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(AuditError, "item order differs"):
                build_report(*inputs)


if __name__ == "__main__":
    unittest.main()

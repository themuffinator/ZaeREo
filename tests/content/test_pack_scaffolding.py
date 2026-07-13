from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "pack"


class PackScaffoldingTests(unittest.TestCase):
    def test_mapdb_declares_all_shipped_bsp_maps_once(self) -> None:
        database = json.loads((PACK / "mapdb.json").read_text(encoding="utf-8"))
        expected = {
            "zbase1", "zbase2", "zdef1", "zdef2", "zdef3", "zdef4",
            "zwaste1", "zwaste2", "zwaste3", "ztomb1", "ztomb2", "ztomb3",
            "ztomb4", "zboss", "zdm1", "zdm2", "zdm3", "zdm4", "zdm5", "zdm6",
        }
        actual = [item["bsp"] for item in database["maps"] if item["bsp"] in expected]
        self.assertEqual(set(actual), expected)
        self.assertEqual(len(actual), len(expected))
        self.assertEqual(database["episodes"][0]["command"], "exec zaerostart.cfg")

    def test_start_chain_uses_rerelease_gamemap(self) -> None:
        start = (PACK / "zaerostart.cfg").read_text(encoding="utf-8")
        self.assertIn('gamemap "*elogo.cin+intro.cin+zlogo.cin+zbase1"', start)
        self.assertNotIn("unbindall", start.casefold())

    def test_optional_config_does_not_run_binding_aliases(self) -> None:
        config = (PACK / "zaero.cfg").read_text(encoding="utf-8")
        active_lines = [
            line.strip().casefold()
            for line in config.splitlines()
            if line.strip() and not line.lstrip().startswith("//")
        ]
        self.assertFalse(any(line.startswith("unbindall") for line in active_lines))
        self.assertFalse(any(line == "zwepas_on" for line in active_lines))


if __name__ == "__main__":
    unittest.main()

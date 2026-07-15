"""Behavior and integration contracts for SYS-012/Q-028."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
DM_SOURCE = (ROOT / "src" / "zaero" / "g_zaero_dm.cpp").read_text(encoding="utf-8")
DM_HEADER = (ROOT / "src" / "zaero" / "g_zaero_dm.h").read_text(encoding="utf-8")
SPAWN_SOURCE = (ROOT / "src" / "g_spawn.cpp").read_text(encoding="utf-8")
SVCMD_SOURCE = (ROOT / "src" / "g_svcmds.cpp").read_text(encoding="utf-8")
ITEM_SOURCE = (ROOT / "src" / "g_items.cpp").read_text(encoding="utf-8")
WEAPON_SOURCE = (ROOT / "src" / "zaero" / "g_zaero_weapons.cpp").read_text(encoding="utf-8")
AUDIT = json.loads((ROOT / "docs" / "audits" / "dm-injection.json").read_text(encoding="utf-8"))
RELEASE_POLICY = json.loads(
    (ROOT / "docs" / "provenance" / "release-surface-policy.json").read_text(
        encoding="utf-8"
    )
)

ITEMS = (
    "weapon_soniccannon",
    "weapon_sniperrifle",
    "weapon_flaregun",
    "ammo_ired",
    "ammo_a2k",
    "ammo_flares",
    "ammo_empnuke",
    "ammo_plasmashield",
)


@dataclass(frozen=True)
class PlacementAttempt:
    item: str
    ordinal: int
    spot: int


def model_injection(
    *,
    deathmatch: bool,
    zdmflags: int,
    existing: set[str],
    spawn_count: int,
    clear_sweeps: set[tuple[str, int]],
) -> tuple[list[tuple[str, int]], list[PlacementAttempt]]:
    """Model source ordering; clear_sweeps identifies (item, ordinal) successes."""

    if not deathmatch or zdmflags & 2 or existing.intersection(ITEMS):
        return [], []
    placed: list[tuple[str, int]] = []
    attempts: list[PlacementAttempt] = []
    ordinal = 1
    for item in ITEMS:
        for _ in range(4):
            current = ordinal
            ordinal += 1
            if spawn_count <= 0:
                break
            spot = (current - 1) % spawn_count
            attempts.append(PlacementAttempt(item, current, spot))
            if (item, current) in clear_sweeps:
                placed.append((item, spot))
                break
    return placed, attempts


class ZaeroDeathmatchInjectionTests(unittest.TestCase):
    def test_numeric_cvar_semantics_cover_all_four_values(self) -> None:
        expected_injection = {0: True, 1: True, 2: False, 3: False}
        expected_flare_compensation = {0: True, 1: False, 2: True, 3: False}
        clear = {(item, index + 1) for index, item in enumerate(ITEMS)}
        for flags in range(4):
            placed, _ = model_injection(
                deathmatch=True,
                zdmflags=flags,
                existing=set(),
                spawn_count=16,
                clear_sweeps=clear,
            )
            self.assertEqual(bool(placed), expected_injection[flags])
            self.assertEqual(not bool(flags & 1), expected_flare_compensation[flags])

        self.assertRegex(
            DM_HEADER,
            r"ZAERO_DMFLAG_DISABLE_FLARE_POLYBLEND_DAMAGE\s*=\s*1\s*<<\s*0",
        )
        self.assertRegex(
            DM_HEADER,
            r"ZAERO_DMFLAG_DISABLE_ITEM_INJECTION\s*=\s*1\s*<<\s*1",
        )
        self.assertIn("ZAERO_DMFLAG_DISABLE_FLARE_POLYBLEND_DAMAGE", WEAPON_SOURCE)
        self.assertNotIn("ZDM_ZAERO_ITEMS", DM_HEADER + DM_SOURCE + WEAPON_SOURCE)

    def test_non_deathmatch_and_each_existing_member_suppress_the_pass(self) -> None:
        all_clear = {(item, index + 1) for index, item in enumerate(ITEMS)}
        placed, attempts = model_injection(
            deathmatch=False,
            zdmflags=0,
            existing=set(),
            spawn_count=8,
            clear_sweeps=all_clear,
        )
        self.assertEqual((placed, attempts), ([], []))
        for existing in ITEMS:
            placed, attempts = model_injection(
                deathmatch=True,
                zdmflags=0,
                existing={existing},
                spawn_count=8,
                clear_sweeps=all_clear,
            )
            self.assertEqual((placed, attempts), ([], []), existing)

    def test_successes_follow_item_order_and_wrap_successive_starts(self) -> None:
        clear = {(item, index + 1) for index, item in enumerate(ITEMS)}
        placed, attempts = model_injection(
            deathmatch=True,
            zdmflags=0,
            existing=set(),
            spawn_count=3,
            clear_sweeps=clear,
        )
        self.assertEqual([item for item, _ in placed], list(ITEMS))
        self.assertEqual([spot for _, spot in placed], [0, 1, 2, 0, 1, 2, 0, 1])
        self.assertEqual([attempt.ordinal for attempt in attempts], list(range(1, 9)))

    def test_geometry_failure_is_partial_not_transactional(self) -> None:
        # The first item exhausts four starts. Every later item succeeds on its
        # first ordinal; the seven successes remain rather than rolling back.
        clear = {(item, index + 4) for index, item in enumerate(ITEMS[1:], start=1)}
        placed, attempts = model_injection(
            deathmatch=True,
            zdmflags=0,
            existing=set(),
            spawn_count=2,
            clear_sweeps=clear,
        )
        self.assertEqual([item for item, _ in placed], list(ITEMS[1:]))
        self.assertEqual([attempt.ordinal for attempt in attempts[:5]], [1, 2, 3, 4, 5])
        self.assertEqual(len(placed), 7)

    def test_no_deathmatch_starts_adds_nothing_without_spawning_items(self) -> None:
        placed, attempts = model_injection(
            deathmatch=True,
            zdmflags=0,
            existing=set(),
            spawn_count=0,
            clear_sweeps=set(),
        )
        self.assertEqual(placed, [])
        self.assertEqual(attempts, [])

    def test_source_preserves_sweep_geometry_and_native_item_lifecycle(self) -> None:
        for fragment in (
            "ZAERO_ITEM_PLACEMENT_ATTEMPTS = 4",
            "ZAERO_ITEM_ANGLE_STEP = 15",
            "ZAERO_ITEM_PLACEMENT_RADIUS = 128.0f",
            "ZAERO_ITEM_PLACEMENT_HEIGHT = 16.0f",
            "MOVETYPE_BOUNCE",
            "MASK_SHOT",
            "ED_CallSpawn(ent);",
            "if (!ent->inuse)",
            "RF_IR_VISIBLE",
            'Com_PrintFmt("{} Zaero entities added\\n", added)',
        ):
            self.assertIn(fragment, DM_SOURCE)
        self.assertIn("THINK(droptofloor)", ITEM_SOURCE)
        self.assertIn("TOUCH(Touch_Item)", ITEM_SOURCE)
        self.assertNotRegex(DM_SOURCE, r"\b(?:THINK|TOUCH|USE|PAIN|DIE)\s*\(")

    def test_content_activation_does_not_enable_mapper_semantics(self) -> None:
        self.assertNotIn("level.is_zaero", DM_SOURCE)
        team = SPAWN_SOURCE.index("G_FindTeams();")
        injection = SPAWN_SOURCE.index("Zaero_SpawnDeathmatchItems();")
        ctf = SPAWN_SOURCE.index("CTFSpawn();")
        self.assertLess(team, injection)
        self.assertLess(injection, ctf)

    def test_live_placement_probe_is_debug_only_read_only_and_release_denied(self) -> None:
        self.assertRegex(
            DM_HEADER,
            r"(?s)#if defined\(_DEBUG\).*Zaero_DebugDumpDeathmatchItems\(\);.*#endif",
        )
        self.assertRegex(
            SVCMD_SOURCE,
            r'(?s)#if defined\(_DEBUG\).*Q_strcasecmp\(cmd, "zaereo_dm_probe"\)'
            r".*Zaero_DebugDumpDeathmatchItems\(\);.*#endif",
        )
        self.assertIn("ZAEREO_DM_PROBE_BEGIN", DM_SOURCE)
        self.assertIn("ZAEREO_DM_PROBE_ITEM", DM_SOURCE)
        self.assertIn("ZAEREO_DM_PROBE_END", DM_SOURCE)
        self.assertIn("entity_spawn_count", DM_SOURCE)
        self.assertIn("candidate->spawn_count == placement.entity_spawn_count", DM_SOURCE)
        self.assertLess(
            DM_SOURCE.index("Zaero_ResetDeathmatchProbe();"),
            DM_SOURCE.index("if (!deathmatch->integer)"),
        )
        forbidden = RELEASE_POLICY["release_binary"]["forbidden_ascii_strings"]
        self.assertEqual(RELEASE_POLICY["revision"], 2)
        self.assertIn("zaereo_dm_probe", forbidden)
        self.assertIn("ZAEREO_DM_PROBE_", forbidden)

    def test_normalized_retail_inventory_proves_historical_suppression(self) -> None:
        self.assertEqual(AUDIT["summary"]["supplied_map_count"], 20)
        self.assertEqual(AUDIT["summary"]["dedicated_deathmatch_map_count"], 6)
        self.assertEqual(AUDIT["summary"]["supplied_deathmatch_start_count"], 230)
        self.assertEqual(AUDIT["summary"]["supplied_maps_eligible_for_injection"], 0)
        self.assertTrue(
            all(entry["injection_suppressed_by_existing_member"] for entry in AUDIT["maps"])
        )
        zdm5 = next(entry for entry in AUDIT["maps"] if entry["map_name"] == "zdm5")
        self.assertEqual(zdm5["missing_items"], ["ammo_a2k"])


if __name__ == "__main__":
    unittest.main()

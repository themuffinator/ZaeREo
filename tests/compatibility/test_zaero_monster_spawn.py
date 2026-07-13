from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCAL = (ROOT / "src" / "g_local.h").read_text(encoding="utf-8")
MONSTER = (ROOT / "src" / "g_monster.cpp").read_text(encoding="utf-8")
TARGET = (ROOT / "src" / "g_target.cpp").read_text(encoding="utf-8")
UTILS = (ROOT / "src" / "g_utils.cpp").read_text(encoding="utf-8")


def zaero_spawn_resolution(overlaps: tuple[str, ...]) -> tuple[tuple[str, ...], bool]:
    """Small executable model of the source-facing spawn collision contract."""
    telefragged = tuple(kind for kind in overlaps if kind != "live_player")
    monster_survives = "live_player" not in overlaps
    return telefragged, monster_survives


class ZaeroMonsterAccountingTests(unittest.TestCase):
    def test_low_bit_16_is_distinct_from_rerelease_spawn_dead(self) -> None:
        self.assertIn(
            "SPAWNFLAG_ZAERO_MONSTER_NO_COUNT = 16_spawnflag", LOCAL
        )
        self.assertIn("SPAWNFLAG_MONSTER_DEAD = 16_spawnflag_bit", LOCAL)

        start = MONSTER.index("bool monster_start(edict_t *self)")
        body = MONSTER[start : MONSTER.index("void monster_start_go", start)]
        self.assertIn("level.is_zaero", body)
        self.assertIn("SPAWNFLAG_ZAERO_MONSTER_NO_COUNT", body)
        self.assertIn("AI_DO_NOT_COUNT", body)
        self.assertLess(
            body.index("SPAWNFLAG_ZAERO_MONSTER_NO_COUNT"),
            body.index("level.total_monsters++"),
        )

    def test_shipped_no_count_pattern_is_locked(self) -> None:
        # Parsed from the hash-pinned retail BSP entity lumps.  These are the
        # only monster placements with Zaero's low 0x10 bit.
        shipped = (
            ("zbase1", "monster_tank", 20),
            ("zdef4", "monster_sentien", 18),
        )
        self.assertEqual([flags & 16 for _, _, flags in shipped], [16, 16])


class ZaeroMonsterKillBoxTests(unittest.TestCase):
    def test_player_is_protected_and_spawned_monster_is_sacrificed(self) -> None:
        killed, survives = zaero_spawn_resolution(
            ("live_player", "monster", "breakable")
        )
        self.assertEqual(killed, ("monster", "breakable"))
        self.assertFalse(survives)

        start = UTILS.index("bool Zaero_MonsterKillBox(edict_t *ent)")
        body = UTILS[start:]
        player_gate = body.index("hit->client && hit->health > 0")
        blocker_damage = body.index("T_Damage(hit")
        self_damage = body.index("T_Damage(ent")
        self.assertLess(player_gate, blocker_damage)
        self.assertLess(blocker_damage, self_damage)
        self.assertIn("DAMAGE_NO_PROTECTION, MOD_TELEFRAG", body)
        self.assertIn("return !live_player_overlap", body)

    def test_native_policy_is_isolated_and_both_spawn_paths_use_helper(self) -> None:
        self.assertIn(
            "if (!level.is_zaero || !(ent->svflags & SVF_MONSTER))", UTILS
        )
        self.assertIn("return KillBox(ent, false)", UTILS)

        triggered = MONSTER[
            MONSTER.index("THINK(monster_triggered_spawn)") :
            MONSTER.index("USE(monster_triggered_spawn_use)")
        ]
        self.assertIn("if (level.is_zaero)", triggered)
        self.assertIn("Zaero_MonsterKillBox(self)", triggered)
        self.assertIn("KillBox(self, false)", triggered)

        spawner = TARGET[
            TARGET.index("USE(use_target_spawner)") :
            TARGET.index("void SP_target_spawner")
        ]
        self.assertIn("level.is_zaero && (ent->svflags & SVF_MONSTER)", spawner)
        self.assertIn("Zaero_MonsterKillBox(ent)", spawner)
        self.assertIn("KillBox(ent, false)", spawner)


if __name__ == "__main__":
    unittest.main()

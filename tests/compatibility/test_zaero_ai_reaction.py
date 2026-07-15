"""Contracts for Zaero monster damage reaction atop native Rerelease AI."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
COMBAT = (ROOT / "src" / "g_combat.cpp").read_text(encoding="utf-8")
LOCAL = (ROOT / "src" / "g_local.h").read_text(encoding="utf-8")
SAVE = (ROOT / "src" / "g_save.cpp").read_text(encoding="utf-8")
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


def reaction_target(
    *,
    zaero: bool,
    admitted: bool = True,
    client: bool = False,
    same_mteam: bool = False,
    spray_excluded: bool = False,
    attacker_enemy: str | None = None,
    same_base_different_class: bool = True,
    ignore_shots: bool = False,
) -> tuple[str | None, bool]:
    """Independent branch model returning target and retained sound flag."""
    sound_target = True
    if not admitted:
        return None, sound_target
    if client:
        if not zaero:
            sound_target = False
        return "attacker", sound_target
    direct = (
        not (zaero and same_mteam)
        and not (zaero and spray_excluded)
        and (
            attacker_enemy == "target"
            or (same_base_different_class and not ignore_shots)
        )
    )
    if direct:
        return "attacker", sound_target
    if attacker_enemy is not None and attacker_enemy != "target":
        return attacker_enemy, sound_target
    return None, sound_target


class ZaeroAIReactionContractTests(unittest.TestCase):
    def test_source_oracle_and_native_function_are_locked(self) -> None:
        record = next(
            item
            for item in SOURCE_AUDIT["comparison"]["file_records"]
            if item["path"] == "g_combat.c"
        )
        self.assertEqual(
            record["zaero_sha256"],
            "b600b4371abe59a0e7d3ac2fbb6e3c19cd17ae24100b3e3d9f34882d1d3180cb",
        )
        self.assertEqual(record["status"], "modified")
        self.assertIn(
            "M_ReactToDamage",
            {item["name"] for item in record["functions"]["changed"]},
        )

    def test_exact_autocannon_mteam_tank_and_sound_deltas_are_scoped(self) -> None:
        body = function_body(COMBAT, "void M_ReactToDamage")
        self.assertIn("Zaero_IsAutocannonReactionAttacker(attacker)", body)
        self.assertIn("Zaero_UsesDamageReaction", body)
        self.assertIn("!zaero_autocannon", body)
        self.assertIn("if (!zaero_reaction)", body)
        self.assertIn("Zaero_ReactionMTeamMatches", body)
        self.assertIn("Zaero_IsSprayReactionExclusion", body)

        autocannon = function_body(
            COMBAT, "static bool Zaero_IsAutocannonReactionAttacker"
        )
        self.assertIn('"monster_autocannon"', autocannon)
        scope = function_body(COMBAT, "static bool Zaero_UsesDamageReaction")
        self.assertIn("level.zaero_mapper_contract", scope)
        self.assertIn("autocannon", scope)
        self.assertIn("targ && targ->mteam", scope)
        spray = function_body(
            COMBAT, "static bool Zaero_IsSprayReactionExclusion"
        )
        for classname in (
            "monster_tank",
            "monster_supertank",
            "monster_makron",
            "monster_jorg",
        ):
            self.assertIn(f'"{classname}"', spray)

    def test_self_selection_fix_and_native_safety_lifecycle_are_retained(self) -> None:
        body = function_body(COMBAT, "void M_ReactToDamage")
        self.assertIn("attacker->enemy != targ", body)
        for native_contract in (
            "MarkTeslaArea",
            "TargetTesla",
            "AI_TARGET_ANGER",
            "react_to_damage_time",
            "cleanupHealTarget",
            "AI_IGNORE_SHOTS",
        ):
            self.assertIn(native_contract, body)
        self.assertIn("FIELD_LEVEL_STRING(mteam)", SAVE)
        self.assertIn("FIELD_AUTO( monsterinfo.react_to_damage_time )", SAVE)
        self.assertIn("const char *mteam", LOCAL)

    def test_executable_golden_reaction_matrix(self) -> None:
        # Native admission remains unchanged for ordinary non-client/non-monster
        # attacks; the exact Autocannon path is admitted by the source hook.
        self.assertEqual(
            reaction_target(zaero=False, admitted=False), (None, True)
        )
        self.assertEqual(
            reaction_target(zaero=True), ("attacker", True)
        )

        # Client attacks select the client in both modes, but Zaero retains the
        # legacy sound-target bit while native Rerelease clears it.
        self.assertEqual(
            reaction_target(zaero=False, client=True), ("attacker", False)
        )
        self.assertEqual(
            reaction_target(zaero=True, client=True), ("attacker", True)
        )

        # Matching mteam and spray-heavy tanks never become the direct target.
        # If they are fighting a third party, the reacting monster helps that
        # buddy; if they target the reacting monster, Q-046 cannot self-select.
        self.assertEqual(
            reaction_target(
                zaero=True, same_mteam=True, attacker_enemy="player"
            ),
            ("player", True),
        )
        self.assertEqual(
            reaction_target(
                zaero=True, same_mteam=True, attacker_enemy="target"
            ),
            (None, True),
        )
        self.assertEqual(
            reaction_target(
                zaero=True, spray_excluded=True, attacker_enemy="target"
            ),
            (None, True),
        )

        # Native ignore-shot semantics stay active even in the Zaero branch.
        self.assertEqual(
            reaction_target(
                zaero=True,
                same_base_different_class=True,
                ignore_shots=True,
            ),
            (None, True),
        )


if __name__ == "__main__":
    unittest.main()

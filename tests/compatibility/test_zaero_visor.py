"""Static and executable contracts for the active Zaero Visor port."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


SOURCE = read("src/zaero/g_zaero_visor.cpp")
HEADER = read("src/zaero/g_zaero_visor.h")
LOCAL = read("src/g_local.h")
SAVE = read("src/g_save.cpp")
ITEMS = read("src/g_items.cpp")
COMMANDS = read("src/g_cmds.cpp")
CLIENT = read("src/p_client.cpp")
COMBAT = read("src/g_combat.cpp")
VIEW = read("src/p_view.cpp")
HUD = read("src/p_hud.cpp")
SPAWN = read("src/g_spawn.cpp")
BG = read("src/bg_local.h")
ENTITIES = read("src/zaero/g_zaero_entities.cpp")
WEAPONS = read("src/zaero/g_zaero_weapons.cpp")
PROJECT = read("src/game.vcxproj")
FILTERS = read("src/game.vcxproj.filters")
SOURCE_AUDIT = json.loads(read("docs/audits/source-delta.json"))
TRACE_AUDIT = json.loads(read("docs/audits/visor-trace-order.json"))


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


def item_block(item_id: str) -> str:
    start = ITEMS.index(f"/* id */ {item_id}")
    end = ITEMS.index("\n\t},", start)
    return ITEMS[start:end]


def find_next(cameras: list[bool], current: int) -> int | None:
    """Independent golden model for the two bounded source passes."""
    visits = 0
    for index in list(range(current + 1, len(cameras))) + list(range(len(cameras))):
        visits += 1
        if index == current:
            return None
        if cameras[index]:
            return index
        if visits > len(cameras):
            raise AssertionError("camera traversal exceeded its finite bound")
    return None


class ZaeroVisorContractTests(unittest.TestCase):
    def test_supplied_source_oracles_are_identity_locked(self) -> None:
        expected = {
            "g_items.c": (
                "a02f4cfda2944ad36cf51eb928c82f13f4317d4198389ef63fac361795b0bf46",
                "modified",
            ),
            "z_item.c": (
                "23dcc0fda023260c73e26260bb86d2c78d6edfc29f0486a4b6472568561f94ae",
                "zaero_only",
            ),
            "z_camera.c": (
                "5a4b802772d4bf6d7b1f1b80e3df9bebe12f9001f96f544f7e10c237e712c5b8",
                "zaero_only",
            ),
            "g_cmds.c": (
                "ea6fd0c0e44bbc4c3849dda0e0002167a54fa835e31fa89489a44e16ac6a3500",
                "modified",
            ),
            "p_client.c": (
                "f0e871b588fb4527bcafb42458bc810f4eef748c32f245646de760e9036db6a4",
                "modified",
            ),
            "p_view.c": (
                "918b00ebd2e851a10685f4fd8169fe7aa5a432291c667aea181518d2258c11bd",
                "modified",
            ),
        }
        records = {
            record["path"]: record
            for record in SOURCE_AUDIT["comparison"]["file_records"]
        }
        for path, (digest, status) in expected.items():
            self.assertEqual(records[path]["zaero_sha256"], digest)
            self.assertEqual(records[path]["status"], status)

    def test_inventory_duration_preserves_legacy_pickup_and_drop_rules(self) -> None:
        self.assertIn("ZAERO_VISOR_DEFAULT_DURATION = 30_sec", SOURCE)
        self.assertEqual(30 * 10, 300)
        self.assertEqual(30 * 40, 1200)

        pickup = function_body(SOURCE, "bool Pickup_ZaeroVisor")
        for contract in (
            "inventory == 1 && remaining == ZAERO_VISOR_DEFAULT_DURATION",
            "ent->spawnflags.has(SPAWNFLAG_ITEM_DROPPED)",
            "remaining += ent->zaero_visor_remaining",
            "remaining = ZAERO_VISOR_DEFAULT_DURATION",
            "SetRespawn(ent, ZAERO_VISOR_DEFAULT_DURATION)",
        ):
            self.assertIn(contract, pickup)

        drop = function_body(SOURCE, "void Drop_ZaeroVisor")
        stop = drop.index("Zaero_VisorStop(ent, true)")
        transfer = drop.index(
            "dropped->zaero_visor_remaining = ent->client->pers.zaero_visor_remaining"
        )
        clear = drop.index("pers.zaero_visor_remaining = 0_ms", transfer)
        self.assertLess(stop, transfer)
        self.assertLess(transfer, clear)
        self.assertIn("SPAWNFLAG_ITEM_DROPPED_PLAYER", drop)
        self.assertIn("dropped->svflags &= ~SVF_INSTANCED", drop)

    def test_item_and_project_use_the_active_callback(self) -> None:
        item = item_block("IT_ITEM_VISOR")
        for callback in ("Pickup_ZaeroVisor", "Drop_ZaeroVisor", "Use_ZaeroVisor"):
            self.assertIn(callback, item)
        self.assertNotIn("Use_ZaeroVisorPending", ITEMS + WEAPONS + SOURCE)

        for declaration in (
            "bool Pickup_ZaeroVisor",
            "void Drop_ZaeroVisor",
            "void Use_ZaeroVisor",
            "bool Zaero_VisorClientThink",
            "void Zaero_VisorStop",
            "void Zaero_VisorRegisterCameraMessage",
        ):
            self.assertIn(declaration, HEADER)
        for manifest in (PROJECT, FILTERS):
            self.assertIn(r"zaero\g_zaero_visor.cpp", manifest)
            self.assertIn(r"zaero\g_zaero_visor.h", manifest)

    def test_camera_traversal_is_bounded_for_zero_one_inactive_and_wrap(self) -> None:
        traversal = function_body(SOURCE, "edict_t *Zaero_FindNextActiveCamera")
        self.assertIn("pass < 2", traversal)
        self.assertIn("camera == current", traversal)
        self.assertIn("camera->active", traversal)

        self.assertIsNone(find_next([True], 0))
        self.assertIsNone(find_next([False], 0))
        self.assertIsNone(find_next([False, False, False], 1))
        self.assertEqual(find_next([True, False, True, False], 0), 2)
        self.assertEqual(find_next([True, False, False, True], 3), 0)
        self.assertIsNone(find_next([], 0))

    def test_copy_fix_preserves_real_player_vulnerability_and_generation_safety(self) -> None:
        create = function_body(SOURCE, "edict_t *Zaero_CreateVisorCopy")
        self.assertIn("copy->classname = ZAERO_VISOR_COPY_CLASSNAME", create)
        self.assertIn("copy->owner = player", create)
        self.assertIn("copy->count = player->spawn_count", create)
        self.assertIn("copy->solid = SOLID_NOT", create)
        self.assertIn("copy->takedamage = false", create)
        self.assertNotIn("player->solid", create)

        select = function_body(SOURCE, "void Zaero_VisorSelectCamera")
        self.assertIn("ent->svflags |= SVF_NOCLIENT", select)
        matches = function_body(SOURCE, "bool Zaero_VisorEntityMatches")
        self.assertIn("ent->spawn_count == spawn_count", matches)
        copy = function_body(SOURCE, "edict_t *Zaero_VisorCopy")
        self.assertIn("copy->owner != ent", copy)
        self.assertIn("copy->count != ent->spawn_count", copy)

        facts = TRACE_AUDIT["proof"]["facts"]
        self.assertEqual(facts["initial_equal_hit_winner"], "real_player")
        self.assertEqual(facts["post_pusher_equal_hit_winner"], "VisorCopy")
        self.assertTrue(facts["trace_ownership_is_link_order_dependent"])
        self.assertEqual(TRACE_AUDIT["disposition"]["classification"], "FIX")
        self.assertEqual(
            TRACE_AUDIT["inputs"]["retail_binary"]["sha256"],
            "9f530380d2202b03e252726478894a27f57ac7d5e54e97da106ecde199a2d786",
        )

    def test_freeze_view_static_and_elapsed_time_are_40hz_safe(self) -> None:
        think = function_body(SOURCE, "bool Zaero_VisorClientThink")
        self.assertIn("ps.pmove.pm_type = PM_FREEZE", think)
        self.assertNotIn("ent->movetype =", think)

        view = function_body(SOURCE, "void Zaero_VisorApplyView")
        for contract in (
            "ps.pmove.origin = camera->move_origin",
            "ps.viewangles = camera->move_angles",
            "ZAERO_VISOR_SWAY_PERIOD_SECONDS",
            "ZAERO_VISOR_SWAY_DEGREES",
            "ps.gunindex = 0",
            "ps.fov = 90.0f",
        ):
            self.assertIn(contract, view)
        self.assertIn("ZAERO_VISOR_SWAY_PERIOD_SECONDS = 6.4f", SOURCE)
        self.assertIn("ZAERO_VISOR_SWAY_DEGREES = 15.0f", SOURCE)
        self.assertIn("ZAERO_VISOR_STATIC_DURATION = 200_ms", SOURCE)

        run = function_body(SOURCE, "void Zaero_VisorRunFrame")
        self.assertIn("level.time - last_update", run)
        self.assertIn("max(0_ms", run)
        self.assertNotIn("FRAMETIME", run)
        for integration in (
            "Zaero_VisorRunFrame(ent)",
            "Zaero_VisorApplyView(ent)",
            "Zaero_VisorApplyStatic(ent)",
            "Zaero_VisorUpdateCopy(ent)",
        ):
            self.assertIn(integration, VIEW)

    def test_save_lifecycle_and_exact_prior_state_restoration_are_registered(self) -> None:
        fields = (
            "zaero_visor_camera",
            "zaero_visor_camera_spawn_count",
            "zaero_visor_copy",
            "zaero_visor_copy_spawn_count",
            "zaero_visor_last_update",
            "zaero_visor_static_until",
            "zaero_visor_saved_pm_type",
            "zaero_visor_saved_fov",
            "zaero_visor_saved_gunindex",
            "zaero_visor_saved_gunskin",
            "zaero_visor_saved_noclient",
        )
        for field in fields:
            self.assertIn(field, LOCAL)
            self.assertIn(f"FIELD_AUTO({field})", SAVE)
        self.assertEqual(LOCAL.count("gtime_t zaero_visor_remaining"), 2)
        self.assertEqual(SAVE.count("FIELD_AUTO(zaero_visor_remaining)"), 2)

        stop = function_body(SOURCE, "void Zaero_VisorStop")
        for field in (
            "zaero_visor_saved_pm_type",
            "zaero_visor_saved_fov",
            "zaero_visor_saved_gunindex",
            "zaero_visor_saved_gunskin",
            "zaero_visor_saved_noclient",
        ):
            self.assertIn(field, stop)
        for signature in (
            "DIE(player_die)",
            "void PutClientInServer",
            "void ClientDisconnect",
        ):
            self.assertIn("Zaero_VisorStop", function_body(CLIENT, signature))
        self.assertIn(
            "Zaero_VisorStop(player, false)",
            function_body(HUD, "void BeginIntermission"),
        )
        damage = function_body(COMBAT, "void T_Damage")
        cancel = damage.index("if (take)\n\t\t\tZaero_VisorStop(targ, true)")
        accumulate = damage.index("client->damage_parmor += psave")
        self.assertLess(cancel, accumulate)

    def test_camera_labels_timer_and_hud_are_private_per_client(self) -> None:
        register = function_body(SOURCE, "void Zaero_VisorRegisterCameraMessage")
        self.assertIn("MAX_ZAERO_CAMERA_MESSAGES", register)
        self.assertIn("gi.get_configstring", register)
        self.assertIn("camera->sounds = index", register)
        camera_spawn = function_body(ENTITIES, "void SP_misc_securitycamera")
        self.assertLess(
            camera_spawn.index("Zaero_VisorRegisterCameraMessage(self)"),
            camera_spawn.index("gi.linkentity(self)"),
        )
        for stat in (
            "STAT_ZAERO_CAMERA_ICON",
            "STAT_ZAERO_CAMERA_TIMER",
            "STAT_ZAERO_CAMERA_LABEL",
        ):
            self.assertIn(stat, BG)
            self.assertIn(stat, SOURCE)
            self.assertIn(stat, SPAWN)
        self.assertIn("stat_string(STAT_ZAERO_CAMERA_LABEL)", SPAWN)
        self.assertIn("Zaero_VisorSetStats(ent)", HUD)

    def test_active_command_gate_keeps_gameplay_locked_but_routes_native_chat(self) -> None:
        command = function_body(COMMANDS, "void ClientCommand")
        gate = command.index("Zaero_VisorIsActive(ent)")
        player_commands = command.index('Q_strcasecmp(cmd, "players") == 0')
        self.assertLess(gate, player_commands)
        for allowed in (
            '"say"',
            '"say_team"',
            '"steam"',
            '"putaway"',
            '"invuse"',
            '"invnext"',
            '"invprev"',
        ):
            self.assertIn(allowed, command)
        targets = function_body(
            COMMANDS, "static bool Zaero_VisorUseCommandTargetsVisor"
        )
        self.assertIn("IT_ITEM_VISOR", targets)
        self.assertIn('"use_index"', targets)
        self.assertIn('"use_only"', targets)
        self.assertIn("return;", command[gate:player_commands])


if __name__ == "__main__":
    unittest.main()

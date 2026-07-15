from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ITEMS = (ROOT / "src" / "g_items.cpp").read_text(encoding="utf-8")
LOCAL = (ROOT / "src" / "g_local.h").read_text(encoding="utf-8")
BOT_UTILS = (ROOT / "src" / "bots" / "bot_utils.cpp").read_text(encoding="utf-8")
BOT_EXPORTS = (ROOT / "src" / "bots" / "bot_exports.cpp").read_text(
    encoding="utf-8"
)
IRED = (ROOT / "src" / "zaero" / "g_zaero_ired.cpp").read_text(encoding="utf-8")
EMP = (ROOT / "src" / "zaero" / "g_zaero_emp.cpp").read_text(encoding="utf-8")
SENTIEN = (ROOT / "src" / "zaero" / "g_zaero_sentien.cpp").read_text(
    encoding="utf-8"
)
WEAPONS = (ROOT / "src" / "zaero" / "g_zaero_weapons.cpp").read_text(
    encoding="utf-8"
)
ZBOSS = (ROOT / "src" / "zaero" / "g_zaero_zboss.cpp").read_text(
    encoding="utf-8"
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


class ZaeroBotIntegrationTests(unittest.TestCase):
    def test_all_appended_items_stay_in_the_generic_native_bot_registry(self) -> None:
        appended = (
            ("IT_WEAPON_PUSH", "weapon_push"),
            ("IT_WEAPON_FLAREGUN", "weapon_flaregun"),
            ("IT_AMMO_IRED", "ammo_ired"),
            ("IT_WEAPON_SNIPERRIFLE", "weapon_sniperrifle"),
            ("IT_WEAPON_SONICCANNON", "weapon_soniccannon"),
            ("IT_AMMO_A2K", "ammo_a2k"),
            ("IT_AMMO_FLARES", "ammo_flares"),
            ("IT_AMMO_EMPNUKE", "ammo_empnuke"),
            ("IT_ITEM_VISOR", "item_visor"),
            ("IT_AMMO_PLASMASHIELD", "ammo_plasmashield"),
            ("IT_KEY_LANDING_AREA", "key_landing_area"),
            ("IT_KEY_LAB", "key_lab"),
            ("IT_KEY_CLEARANCE_PASS", "key_clearancepass"),
            ("IT_KEY_ENERGY", "key_energy"),
            ("IT_KEY_LAVA", "key_lava"),
            ("IT_KEY_SLIME", "key_slime"),
        )
        item_abi = ITEMS[ITEMS.index("// ZAERO item ABI.") :]
        for identifier, classname in appended:
            self.assertIn(identifier, LOCAL)
            record = item_abi[item_abi.index(f"/* id */ {identifier}") :]
            record_end = record.find("\n\t},")
            if record_end < 0:
                record_end = record.index("\n};")
            record = record[:record_end]
            self.assertIn(f'/* classname */ "{classname}"', record)

        get_id = function_body(BOT_EXPORTS, "int32_t Bot_GetItemID")
        self.assertIn("for ( int i = 0; i < IT_TOTAL; ++i )", get_id)
        self.assertIn("if ( Q_strcasecmp( item->classname, classname ) == 0 )", get_id)
        self.assertIn("return item->id;", get_id)

        update_item = function_body(BOT_UTILS, "void Item_UpdateState")
        self.assertIn("item->sv.item_id = item->item->id;", update_item)
        self.assertIn("gi.Bot_RegisterEdict( item );", update_item)

    def test_external_bot_item_entrypoints_reject_all_invalid_ids_before_indexing(self) -> None:
        set_weapon = function_body(BOT_EXPORTS, "void Bot_SetWeapon")
        self.assertIn("weaponIndex <= IT_NULL || weaponIndex >= IT_TOTAL", set_weapon)
        self.assertLess(
            set_weapon.index("weaponIndex <= IT_NULL || weaponIndex >= IT_TOTAL"),
            set_weapon.index("client->pers.inventory[ weaponIndex ]"),
        )
        self.assertLess(
            set_weapon.index("weaponIndex <= IT_NULL || weaponIndex >= IT_TOTAL"),
            set_weapon.index("&itemlist[ weaponIndex ]"),
        )

        use_item = function_body(BOT_EXPORTS, "void Bot_UseItem")
        self.assertIn("itemID <= IT_NULL || itemID >= IT_TOTAL", use_item)
        self.assertLess(
            use_item.index("itemID <= IT_NULL || itemID >= IT_TOTAL"),
            use_item.index("const item_id_t desiredItemID"),
        )
        self.assertLess(
            use_item.index("itemID <= IT_NULL || itemID >= IT_TOTAL"),
            use_item.index("ValidateSelectedItem( bot )"),
        )

    def test_custom_dangers_use_native_trap_or_laser_field_metadata(self) -> None:
        flare = function_body(WEAPONS, "edict_t *Zaero_SpawnFlare")
        self.assertIn("flare->svflags |= SVF_PROJECTILE;", flare)
        self.assertIn("flare->flags |= FL_DODGE | FL_TRAP;", flare)

        setup_bomb = function_body(IRED, "void Zaero_SetupIREDBomb")
        self.assertIn("bomb->flags |= FL_IMMORTAL | FL_TRAP;", setup_bomb)
        ired_beam = function_body(IRED, "THINK(Zaero_CreateIREDLaser)")
        self.assertIn("laser->flags |= FL_TRAP_LASER_FIELD;", ired_beam)
        ired_explode = function_body(IRED, "THINK(Zaero_IREDExplode)")
        self.assertIn("shrapnel->flags |= FL_TRAP;", ired_explode)

        emp = function_body(EMP, "edict_t *Zaero_FireEMPNuke")
        self.assertIn("empnuke->flags |= FL_TRAP;", emp)

        sentien = function_body(SENTIEN, "void sentien_create_laser")
        self.assertIn("laser->flags |= FL_TRAP_LASER_FIELD;", sentien)
        self.assertNotIn("laser->flags |= FL_TRAP;", function_body(SENTIEN, "void sentien_laser_on"))

        self.assertEqual(ZBOSS.count("hook->flags |= FL_TRAP;"), 2)
        plasma = function_body(ZBOSS, "void zboss_fire_plasma")
        self.assertIn("plasma->flags |= FL_TRAP;", plasma)

        trap_update = function_body(BOT_UTILS, "void Trap_UpdateState")
        self.assertIn("danger->sv.ent_flags = SVFL_TRAP_DANGER;", trap_update)
        self.assertIn("danger->sv.start_origin = danger->s.origin;", trap_update)
        self.assertIn("danger->sv.end_origin = danger->s.old_origin;", trap_update)
        self.assertIn("gi.Bot_RegisterEdict( danger );", trap_update)

    def test_trap_metadata_precedes_generic_edict_state_and_unregisters_on_free(self) -> None:
        dispatch = function_body(BOT_UTILS, "void Entity_UpdateState")
        self.assertLess(
            dispatch.index("edict->flags & FL_TRAP || edict->flags & FL_TRAP_LASER_FIELD"),
            dispatch.index("else if ( edict->item != nullptr )"),
        )
        free = (ROOT / "src" / "g_utils.cpp").read_text(encoding="utf-8")
        self.assertIn("gi.Bot_UnRegisterEdict( ed );", free)


if __name__ == "__main__":
    unittest.main()

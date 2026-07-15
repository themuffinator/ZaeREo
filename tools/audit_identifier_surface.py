#!/usr/bin/env python3
"""Fail-closed static audit of ZaeREo's protocol-facing identifier surface.

This verifies the current append-only Zaero item, ammo, powerup, MOD, HUD-stat,
camera-configstring, and wheel registry contracts against the Rerelease source.
It is not a substitute for compiled stock/expansion or live UI/split-screen
smokes; it prevents a source edit from silently colliding with those contracts.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import re
import sys
from typing import Any

from audit_common import stable_json_text


ROOT = Path(__file__).resolve().parents[1]

ZAERO_ITEM_IDS = (
    "IT_WEAPON_PUSH",
    "IT_WEAPON_FLAREGUN",
    "IT_AMMO_IRED",
    "IT_WEAPON_SNIPERRIFLE",
    "IT_WEAPON_SONICCANNON",
    "IT_AMMO_A2K",
    "IT_AMMO_FLARES",
    "IT_AMMO_EMPNUKE",
    "IT_ITEM_VISOR",
    "IT_AMMO_PLASMASHIELD",
    "IT_KEY_LANDING_AREA",
    "IT_KEY_LAB",
    "IT_KEY_CLEARANCE_PASS",
    "IT_KEY_ENERGY",
    "IT_KEY_LAVA",
    "IT_KEY_SLIME",
)
ZAERO_AMMO_IDS = (
    "AMMO_FLARES",
    "AMMO_IRED",
    "AMMO_EMPNUKE",
    "AMMO_A2K",
    "AMMO_PLASMASHIELD",
)
ZAERO_POWERUP_IDS = ("POWERUP_ZAERO_VISOR",)
ZAERO_MOD_IDS = (
    "MOD_ZAERO_FLARE",
    "MOD_ZAERO_GL_POLYBLEND",
    "MOD_ZAERO_SONIC_CANNON",
    "MOD_ZAERO_AUTOCANNON",
    "MOD_ZAERO_TRIPBOMB",
    "MOD_ZAERO_SNIPER_RIFLE",
    "MOD_ZAERO_A2K",
)
ZAERO_STAT_IDS = (
    "STAT_ZAERO_SHOW_ORIGIN",
    "STAT_ZAERO_ORIGIN_X",
    "STAT_ZAERO_ORIGIN_Y",
    "STAT_ZAERO_ORIGIN_Z",
    "STAT_ZAERO_CAMERA_ICON",
    "STAT_ZAERO_CAMERA_TIMER",
    "STAT_ZAERO_CAMERA_LABEL",
)
ZAERO_CONFIG_IDS = (
    "CONFIG_ZAERO_CAMERA_MESSAGE",
    "MAX_ZAERO_CAMERA_MESSAGES",
    "CONFIG_ZAERO_CAMERA_MESSAGE_END",
)
ZAERO_AI_FLAG_IDS = (
    "AI_ZAERO_ONESHOT_TARGET",
    "AI_ZAERO_SCHOOLING",
    "AI_ZAERO_REDUCED_DAMAGE",
    "AI_ZAERO_MONSTER_REDUCED_DAMAGE",
    "AI_ZAERO_DODGE_TIMEOUT",
)
ZAERO_AI_FLAG_EXPRESSIONS = {
    "AI_ZAERO_ONESHOT_TARGET": "bit_v<39>",
    "AI_ZAERO_SCHOOLING": "bit_v<40>",
    "AI_ZAERO_REDUCED_DAMAGE": "bit_v<41>",
    "AI_ZAERO_MONSTER_REDUCED_DAMAGE": "bit_v<42>",
    "AI_ZAERO_DODGE_TIMEOUT": "bit_v<43>",
}
ZAERO_SPAWNFLAGS2 = {
    "ZAERO_SPAWNFLAG2_NONE": 0,
    "ZAERO_SPAWNFLAG2_MIRRORLEVEL": 1,
    "ZAERO_SPAWNFLAG2_NOT_COOP": 2,
    "ZAERO_SPAWNFLAG2_NOT_SINGLE": 4,
}
# These ordinary spawnflag values intentionally reuse native bits.  The
# mapper-contract classifier, rather than global bit uniqueness, owns their
# isolation.  Keep the exact declaration path/value inventory explicit.
ZAERO_MAPPER_SPAWNFLAGS = {
    ("g_func.cpp", "SPAWNFLAG_PLAT_ZAERO_LOW_TRIGGER_2", 2),
    ("g_func.cpp", "SPAWNFLAG_TRAIN_ZAERO_REVERSE", 8),
    ("g_func.cpp", "SPAWNFLAG_TRAIN_ZAERO_X_AXIS", 16),
    ("g_func.cpp", "SPAWNFLAG_TRAIN_ZAERO_Y_AXIS", 32),
    ("g_func.cpp", "SPAWNFLAG_TRAIN_ZAERO_Z_AXIS", 64),
    ("g_func.cpp", "SPAWNFLAG_PATH_CORNER_ZAERO_AUTO_SMOOTH", 2),
    ("g_func.cpp", "SPAWNFLAG_PATH_CORNER_ZAERO_CUSTOM_SMOOTH", 4),
    ("g_local.h", "SPAWNFLAG_ZAERO_MONSTER_NO_COUNT", 16),
    ("g_misc.cpp", "SPAWNFLAG_VIPER_ZAERO_SMOKE", 1),
    ("g_misc.cpp", "SPAWNFLAG_VIPER_ZAERO_SOLID", 2),
    ("g_misc.cpp", "SPAWNFLAG_VIPER_ZAERO_CUSTOM_BOUNDS", 4),
    ("g_target.cpp", "SPAWNFLAG_TARGET_EXPLOSION_ZAERO_A2K_STYLE", 1),
    ("g_trigger.cpp", "SPAWNFLAG_PUSH_ZAERO_START_OFF", 2),
}


class IdentifierSurfaceAuditError(RuntimeError):
    """The source no longer proves the current identifier compatibility ABI."""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _enum_body(source: str, declaration: str) -> str:
    match = re.search(declaration, source)
    if not match:
        raise IdentifierSurfaceAuditError(f"could not find enum declaration: {declaration}")
    opening = source.find("{", match.start())
    if opening < 0:
        raise IdentifierSurfaceAuditError(f"could not find enum body: {declaration}")
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : index]
    raise IdentifierSurfaceAuditError(f"unterminated enum: {declaration}")


def _without_disabled_blocks(source: str) -> str:
    """Remove simple `#if 0` compatibility notes from the compiled view."""
    return re.sub(r"(?ms)^\s*#if\s+0\b.*?^\s*#endif[^\n]*(?:\n|$)", "", source)


def _enumerators(body: str) -> list[tuple[str, str | None]]:
    # Keep disabled historical entries out of the compiled ABI inventory. The
    # current item enum retains one `#if 0` compatibility note.
    body = _without_disabled_blocks(body)
    without_comments = re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL)
    without_comments = re.sub(r"//[^\n]*", "", without_comments)
    entries: list[tuple[str, str | None]] = []
    for raw_entry in without_comments.split(","):
        entry = raw_entry.strip()
        if not entry:
            continue
        match = re.fullmatch(
            r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:\s*=\s*(?P<value>.+))?", entry, flags=re.DOTALL
        )
        if not match:
            raise IdentifierSurfaceAuditError(f"unsupported enumerator syntax: {entry!r}")
        entries.append((match.group("name"), match.group("value")))
    if not entries:
        raise IdentifierSurfaceAuditError("empty enum")
    return entries


def _integer_expression(expression: str, values: dict[str, int]) -> int:
    expression = re.sub(r"(?<=\d)[uUlL]+\b", "", expression)

    def evaluate(node: ast.AST) -> int:
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return node.value
        if isinstance(node, ast.Name) and node.id in values:
            return values[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub, ast.Invert)):
            value = evaluate(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value if isinstance(node.op, ast.USub) else ~value
        if isinstance(node, ast.BinOp):
            left, right = evaluate(node.left), evaluate(node.right)
            operations = {
                ast.Add: lambda: left + right,
                ast.Sub: lambda: left - right,
                ast.Mult: lambda: left * right,
                ast.FloorDiv: lambda: left // right,
                ast.Mod: lambda: left % right,
                ast.LShift: lambda: left << right,
                ast.RShift: lambda: left >> right,
                ast.BitOr: lambda: left | right,
                ast.BitAnd: lambda: left & right,
                ast.BitXor: lambda: left ^ right,
            }
            for operation, implementation in operations.items():
                if isinstance(node.op, operation):
                    return implementation()
        raise IdentifierSurfaceAuditError(f"unsupported integer expression: {expression!r}")

    try:
        return evaluate(ast.parse(expression, mode="eval").body)
    except SyntaxError as error:
        raise IdentifierSurfaceAuditError(f"invalid integer expression: {expression!r}") from error


def _enum_values(entries: list[tuple[str, str | None]]) -> dict[str, int]:
    values: dict[str, int] = {}
    next_value = 0
    for name, expression in entries:
        value = next_value if expression is None else _integer_expression(expression, values)
        if value in values.values():
            collides_with = next(key for key, existing in values.items() if existing == value)
            raise IdentifierSurfaceAuditError(
                f"enumerator value collision: {name} and {collides_with} both use {value}"
            )
        values[name] = value
        next_value = value + 1
    return values


def _tail_contract(
    entries: list[tuple[str, str | None]], anchor: str, appended: tuple[str, ...], terminator: str | None
) -> dict[str, Any]:
    names = [name for name, _ in entries]
    if anchor not in names:
        raise IdentifierSurfaceAuditError(f"missing append anchor {anchor}")
    tail = names[names.index(anchor) + 1 :]
    expected = list(appended) + ([] if terminator is None else [terminator])
    return {
        "anchor": anchor,
        "entries": list(appended),
        "terminator": terminator,
        "tail": tail,
        "append_only": tail == expected,
    }


def _item_records(items_source: str) -> list[dict[str, str | None]]:
    items_source = _without_disabled_blocks(items_source)
    matches = list(re.finditer(r"/\*\s*id\s*\*/\s*(IT_[A-Z0-9_]+)", items_source))
    if not matches:
        raise IdentifierSurfaceAuditError("could not find itemlist ID annotations")
    records: list[dict[str, str | None]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(items_source)
        block = items_source[match.end() : end]
        classname = re.search(r'/\*\s*classname\s*\*/\s*(nullptr|"([^"]+)")', block)
        flags = re.search(
            r"/\*\s*flags\s*\*/\s*(.*?)(?=\n\s*(?:/\*\s*[A-Za-z_]+\s*\*/|\}\s*[,;]?))",
            block,
            re.DOTALL,
        )
        if not classname or not flags:
            raise IdentifierSurfaceAuditError(f"could not parse itemlist record {match.group(1)}")
        records.append(
            {
                "id": match.group(1),
                "classname": None if classname.group(1) == "nullptr" else classname.group(2),
                "flags": re.sub(r"\s+", " ", flags.group(1)).strip(),
            }
        )
    return records


def _constant_value(source: str, name: str) -> int:
    match = re.search(rf"constexpr\s+size_t\s+{re.escape(name)}\s*=\s*(\d+)\s*;", source)
    if not match:
        raise IdentifierSurfaceAuditError(f"could not read {name}")
    return int(match.group(1))


def _contains_assertion(source: str, expression: str) -> bool:
    normalized = re.sub(r"\s+", "", source)
    return re.sub(r"\s+", "", expression) in normalized


def _normalized_expression(expression: str | None) -> str:
    if expression is None:
        raise IdentifierSurfaceAuditError("expected an explicit identifier expression")
    return re.sub(r"\s+", "", expression)


def _mapper_spawnflag_records(source_root: Path, local_source: str) -> list[dict[str, Any]]:
    sources = {"g_local.h": local_source}
    sources.update({path.name: _read(path) for path in sorted(source_root.glob("*.cpp"))})
    records: list[dict[str, Any]] = []
    pattern = re.compile(
        r"constexpr\s+spawnflags_t\s+(SPAWNFLAG_[A-Z0-9_]*ZAERO[A-Z0-9_]*)\s*=\s*([^;]+);"
    )
    for path, source in sources.items():
        for name, expression in pattern.findall(source):
            value = re.fullmatch(r"\s*(0x[0-9A-Fa-f]+|\d+)_spawnflag(?:_bit)?\s*", expression)
            if not value:
                raise IdentifierSurfaceAuditError(f"unsupported Zaero spawnflag expression for {name}: {expression}")
            records.append({"source": path, "name": name, "value": int(value.group(1), 0)})
    return sorted(records, key=lambda record: (record["source"], record["name"]))


def _without_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", source)


def _legacy_protocol_adaptations(source_root: Path) -> dict[str, Any]:
    sniper = _without_comments(_read(source_root / "zaero" / "g_zaero_sniper.cpp"))
    all_code = "\n".join(
        _without_comments(_read(path)) for path in sorted(source_root.rglob("*.cpp"))
    )
    forbidden_symbols = ("EF_BOOMER", "MZ_BOOMERGUN", "TE_PLASMATRAIL")
    return {
        "sniper_channel": {
            "legacy": "CHAN_WEAPON2",
            "native": "CHAN_AUX",
            "adapted": "CHAN_AUX" in sniper and "CHAN_WEAPON2" not in sniper,
        },
        "sniper_mask": {
            "legacy": "MASK_SHOT_NO_WINDOW",
            "native": "MASK_SHOT & ~CONTENTS_WINDOW",
            "adapted": "MASK_SHOT & ~CONTENTS_WINDOW" in sniper and "MASK_SHOT_NO_WINDOW" not in sniper,
        },
        "unused_legacy_symbols": [
            {"symbol": symbol, "present_in_compiled_port_code": symbol in all_code}
            for symbol in forbidden_symbols
        ],
    }


def build_identifier_surface_report(
    source_root: Path = ROOT / "src",
    *,
    local_source: str | None = None,
    bg_source: str | None = None,
    items_source: str | None = None,
    game_source: str | None = None,
) -> dict[str, Any]:
    """Build the static compatibility inventory and all fail-closed findings."""
    source_root = source_root.resolve()
    local = _read(source_root / "g_local.h") if local_source is None else local_source
    bg = _read(source_root / "bg_local.h") if bg_source is None else bg_source
    items = _read(source_root / "g_items.cpp") if items_source is None else items_source
    game = _read(source_root / "game.h") if game_source is None else game_source

    item_entries = _enumerators(_enum_body(local, r"enum\s+item_id_t\s*:\s*int32_t"))
    ammo_entries = _enumerators(_enum_body(bg, r"enum\s+ammo_t\s*:\s*uint8_t"))
    powerup_entries = _enumerators(_enum_body(bg, r"enum\s+powerup_t\s*:\s*uint8_t"))
    mod_entries = _enumerators(_enum_body(local, r"enum\s+mod_id_t\s*:\s*uint8_t"))
    stat_entries = _enumerators(_enum_body(bg, r"enum\s+player_stat_t"))
    config_entries = _enumerators(_enum_body(bg, r"// reserved general CS ranges\s*enum\s*"))
    spawnflags2_entries = _enumerators(_enum_body(local, r"enum\s+zaero_spawnflags2_t\s*:\s*uint32_t"))
    ai_entries = _enumerators(_enum_body(local, r"enum\s+monster_ai_flags_t\s*:\s*uint64_t"))

    item_values = _enum_values(item_entries)
    ammo_values = _enum_values(ammo_entries)
    powerup_values = _enum_values(powerup_entries)
    mod_values = _enum_values(mod_entries)
    spawnflags2_values = _enum_values(spawnflags2_entries)

    enum_contracts = {
        "item_ids": _tail_contract(item_entries, "IT_ITEM_COMPASS", ZAERO_ITEM_IDS, "IT_TOTAL"),
        "ammo_ids": _tail_contract(ammo_entries, "AMMO_PROX", ZAERO_AMMO_IDS, "AMMO_MAX"),
        "powerup_ids": _tail_contract(powerup_entries, "POWERUP_TECH4", ZAERO_POWERUP_IDS, "POWERUP_MAX"),
        "mod_ids": _tail_contract(mod_entries, "MOD_BLUEBLASTER", ZAERO_MOD_IDS, None),
        "hud_stats": _tail_contract(stat_entries, "STAT_ACTIVE_WEAPON", ZAERO_STAT_IDS, "STAT_LAST"),
        "camera_configstrings": _tail_contract(config_entries, "CONFIG_STORY", ZAERO_CONFIG_IDS, "CONFIG_LAST"),
        "monster_ai_flags": _tail_contract(ai_entries, "AI_THIRD_EYE", ZAERO_AI_FLAG_IDS, None),
    }
    ai_expressions = {
        name: _normalized_expression(expression)
        for name, expression in ai_entries
        if name in ZAERO_AI_FLAG_IDS
    }
    ai_bits = {
        name: int(re.fullmatch(r"bit_v<(\d+)>", expression).group(1))
        for name, expression in ai_expressions.items()
        if re.fullmatch(r"bit_v<(\d+)>", expression)
    }
    mapper_spawnflags = _mapper_spawnflag_records(source_root, local)
    legacy_protocol = _legacy_protocol_adaptations(source_root)

    records = _item_records(items)
    item_ids = [name for name, _ in item_entries if name not in {"IT_NULL", "IT_TOTAL"}]
    registry_ids = [record["id"] for record in records]
    zaero_records = [record for record in records if record["id"] in ZAERO_ITEM_IDS]
    wheel_counts = {
        "ammo": sum("IF_AMMO" in record["flags"] for record in records),
        "weapon": sum(
            "IF_WEAPON" in record["flags"] and "IF_NO_WEAPON_SELECTION" not in record["flags"]
            for record in records
        ),
        "powerup": sum(
            "IF_POWERUP_WHEEL" in record["flags"] and "IF_WEAPON" not in record["flags"]
            for record in records
        ),
    }
    wheel_capacities = {
        "maximum": _constant_value(game, "MAX_WHEEL_ITEMS"),
        "declared_ammo_slots": _constant_value(items, "ZAERO_AMMO_WHEEL_SLOTS"),
        "declared_weapon_slots": _constant_value(items, "ZAERO_WEAPON_WHEEL_SLOTS"),
        "registered": wheel_counts,
        "runtime_guard_count": items.count("if (cs_index >= MAX_WHEEL_ITEMS)"),
    }

    violations: list[str] = []
    for surface, contract in enum_contracts.items():
        if not contract["append_only"]:
            violations.append(f"{surface} is no longer a terminal append-only Zaero range")
    if ai_expressions != ZAERO_AI_FLAG_EXPRESSIONS or len(ai_bits) != len(ZAERO_AI_FLAG_IDS):
        violations.append("Zaero AI flags no longer use the reserved terminal bits 39 through 43")
    if spawnflags2_values != ZAERO_SPAWNFLAGS2:
        violations.append("zaero_spawnflags2_t no longer uses its independent 0/1/2/4 namespace")
    mapper_spawnflag_tuples = {
        (record["source"], record["name"], record["value"]) for record in mapper_spawnflags
    }
    if mapper_spawnflag_tuples != ZAERO_MAPPER_SPAWNFLAGS:
        violations.append("Zaero mapper spawnflag declaration inventory drifted")
    if len({record["name"] for record in mapper_spawnflags}) != len(mapper_spawnflags):
        violations.append("Zaero mapper spawnflag names are not unique")
    if not legacy_protocol["sniper_channel"]["adapted"]:
        violations.append("Sniper must adapt legacy CHAN_WEAPON2 through native CHAN_AUX")
    if not legacy_protocol["sniper_mask"]["adapted"]:
        violations.append("Sniper must adapt MASK_SHOT_NO_WINDOW through native contents")
    if any(item["present_in_compiled_port_code"] for item in legacy_protocol["unused_legacy_symbols"]):
        violations.append("unused legacy protocol identifiers entered compiled port code")
    if registry_ids != item_ids:
        violations.append("itemlist ID annotations no longer match item_id_t order exactly")
    if len(registry_ids) != len(set(registry_ids)):
        violations.append("itemlist has duplicate item IDs")
    if len(zaero_records) != len(ZAERO_ITEM_IDS):
        violations.append("itemlist does not register every Zaero item ID exactly once")
    if len({record["classname"] for record in zaero_records}) != len(zaero_records):
        violations.append("Zaero item classnames are not unique")
    if wheel_capacities["declared_ammo_slots"] != wheel_counts["ammo"]:
        violations.append("ZAERO_AMMO_WHEEL_SLOTS does not match the item registry")
    if wheel_capacities["declared_weapon_slots"] != wheel_counts["weapon"]:
        violations.append("ZAERO_WEAPON_WHEEL_SLOTS does not match the item registry")
    if any(count > wheel_capacities["maximum"] for count in wheel_counts.values()):
        violations.append("at least one wheel registry exceeds MAX_WHEEL_ITEMS")
    if wheel_capacities["runtime_guard_count"] != 3:
        violations.append("ammo, weapon, and powerup wheel loops must each retain a MAX_WHEEL_ITEMS guard")

    required_assertions = {
        "item_protocol_capacity": _contains_assertion(local, "static_assert(IT_TOTAL <= MAX_ITEMS"),
        "stat_protocol_capacity": _contains_assertion(bg, "static_assert(STAT_ZAERO_CAMERA_LABEL < MAX_STATS"),
        "camera_configstring_capacity": _contains_assertion(bg, "static_assert(CONFIG_LAST <= CS_GENERAL + MAX_GENERAL"),
        "ammo_wheel_capacity": _contains_assertion(items, "static_assert(ZAERO_AMMO_WHEEL_SLOTS <= MAX_WHEEL_ITEMS"),
        "weapon_wheel_capacity": _contains_assertion(items, "static_assert(ZAERO_WEAPON_WHEEL_SLOTS <= MAX_WHEEL_ITEMS"),
        "ammo_wheel_identity": _contains_assertion(items, "static_assert(AMMO_MAX == ZAERO_AMMO_WHEEL_SLOTS"),
    }
    for assertion, present in required_assertions.items():
        if not present:
            violations.append(f"missing compile-time capacity assertion: {assertion}")

    type_capacities = {
        "item_ids": {"last_value": item_values["IT_TOTAL"] - 1, "capacity": _constant_value(game, "MAX_ITEMS")},
        "ammo_ids": {"last_value": ammo_values["AMMO_MAX"] - 1, "capacity": 255},
        "powerup_ids": {"last_value": powerup_values["POWERUP_MAX"] - 1, "capacity": 255},
        "mod_ids": {"last_value": max(mod_values.values()), "capacity": 255},
        "monster_ai_flags": {"last_value": max(ai_bits.values()), "capacity": 64},
    }
    for surface, capacity in type_capacities.items():
        if capacity["last_value"] >= capacity["capacity"]:
            violations.append(f"{surface} exceeds its protocol/underlying-type capacity")

    return {
        "schema": "zaereo.identifier-surface-audit/v1",
        "source_root": "src",
        "enum_contracts": enum_contracts,
        "type_capacities": type_capacities,
        "bit_namespaces": {
            "spawnflags2": spawnflags2_values,
            "monster_ai_flags": ai_bits,
        },
        "mapper_spawnflags": mapper_spawnflags,
        "legacy_protocol_adaptations": legacy_protocol,
        "item_registry": {
            "entry_count": len(records),
            "zaero_entries": [{"id": record["id"], "classname": record["classname"]} for record in zaero_records],
            "matches_item_enum": registry_ids == item_ids,
        },
        "wheel_capacities": wheel_capacities,
        "compile_time_assertions": required_assertions,
        "violations": violations,
        "summary": {
            "zaero_item_count": len(ZAERO_ITEM_IDS),
            "zaero_ammo_count": len(ZAERO_AMMO_IDS),
            "zaero_mod_count": len(ZAERO_MOD_IDS),
            "zaero_stat_count": len(ZAERO_STAT_IDS),
            "zaero_ai_flag_count": len(ZAERO_AI_FLAG_IDS),
            "zaero_mapper_spawnflag_count": len(ZAERO_MAPPER_SPAWNFLAGS),
            "complete": not violations,
        },
    }


def require_complete(report: dict[str, Any]) -> None:
    if not report["summary"]["complete"]:
        raise IdentifierSurfaceAuditError("incomplete identifier surface: " + "; ".join(report["violations"]))


def identifier_surface_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# ZaeREo identifier-surface audit",
        "",
        "This file is generated by `tools/audit_identifier_surface.py`; do not edit it by hand.",
        "It proves only the current source-level append, uniqueness, registry, and capacity contracts.",
        "Compiled stock/expansion and live wheel/HUD validation remain required.",
        "",
        "## Summary",
        "",
        f"- Zaero item IDs: `{summary['zaero_item_count']}`",
        f"- Zaero ammo IDs: `{summary['zaero_ammo_count']}`",
        f"- Zaero MOD IDs: `{summary['zaero_mod_count']}`",
        f"- Zaero HUD stats: `{summary['zaero_stat_count']}`",
        f"- Zaero AI flags: `{summary['zaero_ai_flag_count']}`",
        f"- Mapper-scoped ordinary spawnflags: `{summary['zaero_mapper_spawnflag_count']}`",
        f"- Complete: `{str(summary['complete']).lower()}`",
        "",
        "## Append-only enum contracts",
        "",
        "| Surface | Anchor | Zaero entries | Terminator | Append-only |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for surface, contract in report["enum_contracts"].items():
        lines.append(
            f"| `{surface}` | `{contract['anchor']}` | `{len(contract['entries'])}` | "
            f"`{contract['terminator'] or 'end of enum'}` | `{str(contract['append_only']).lower()}` |"
        )

    lines.extend(
        [
            "",
            "## Independent and appended bit namespaces",
            "",
            "| `spawnflags2` name | Value |",
            "| --- | ---: |",
        ]
    )
    for name, value in report["bit_namespaces"]["spawnflags2"].items():
        lines.append(f"| `{name}` | `{value}` |")
    lines.extend(["", "| Zaero AI flag | Bit |", "| --- | ---: |"])
    for name, bit in report["bit_namespaces"]["monster_ai_flags"].items():
        lines.append(f"| `{name}` | `{bit}` |")

    lines.extend(["", "## Capacity", "", "| Surface | Last value | Capacity |", "| --- | ---: | ---: |"])
    for surface, capacity in report["type_capacities"].items():
        lines.append(f"| `{surface}` | {capacity['last_value']} | {capacity['capacity']} |")
    wheels = report["wheel_capacities"]
    lines.extend(
        [
            "",
            "## Wheel registry",
            "",
            f"- Maximum entries per wheel: `{wheels['maximum']}`",
            f"- Ammo: `{wheels['registered']['ammo']}` registered / `{wheels['declared_ammo_slots']}` declared",
            f"- Weapon: `{wheels['registered']['weapon']}` registered / `{wheels['declared_weapon_slots']}` declared",
            f"- Powerup: `{wheels['registered']['powerup']}` registered",
            f"- Runtime overflow guards: `{wheels['runtime_guard_count']}`",
            "",
            "## Zaero item registry",
            "",
            "| Item ID | Classname |",
            "| --- | --- |",
        ]
    )
    for record in report["item_registry"]["zaero_entries"]:
        lines.append(f"| `{record['id']}` | `{record['classname']}` |")
    lines.extend(
        [
            "",
            "## Mapper-scoped ordinary spawnflags",
            "",
            "These values intentionally reuse native bits; the mapper-contract classifier owns their interpretation.",
            "",
            "| Source | Name | Value |",
            "| --- | --- | ---: |",
        ]
    )
    for record in report["mapper_spawnflags"]:
        lines.append(f"| `{record['source']}` | `{record['name']}` | `{record['value']}` |")
    protocol = report["legacy_protocol_adaptations"]
    lines.extend(
        [
            "",
            "## Legacy protocol adaptations",
            "",
            f"- `{protocol['sniper_channel']['legacy']}` → `{protocol['sniper_channel']['native']}`: `{str(protocol['sniper_channel']['adapted']).lower()}`",
            f"- `{protocol['sniper_mask']['legacy']}` → `{protocol['sniper_mask']['native']}`: `{str(protocol['sniper_mask']['adapted']).lower()}`",
        ]
    )
    for item in protocol["unused_legacy_symbols"]:
        lines.append(
            f"- `{item['symbol']}` appears in compiled port code: "
            f"`{str(item['present_in_compiled_port_code']).lower()}`"
        )
    lines.append("")
    return "\n".join(lines)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=ROOT / "src")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--check", action="store_true", help="Check outputs instead of writing them.")
    args = parser.parse_args()

    try:
        report = build_identifier_surface_report(args.source_root)
        require_complete(report)
        outputs = ((args.json_output, stable_json_text(report)), (args.markdown_output, identifier_surface_markdown(report)))
        for path, text in outputs:
            if path is None:
                continue
            if args.check:
                if not path.is_file() or path.read_text(encoding="utf-8") != text:
                    raise IdentifierSurfaceAuditError(f"generated output is stale: {path}")
            else:
                _write(path, text)
    except (OSError, IdentifierSurfaceAuditError) as error:
        print(f"audit_identifier_surface.py: {error}", file=sys.stderr)
        return 2

    print(
        "identifier surface complete: "
        f"items={report['summary']['zaero_item_count']} mods={report['summary']['zaero_mod_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

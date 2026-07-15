#!/usr/bin/env python3
"""Create private, deterministic DM-injection fixtures from a local BSP."""

from __future__ import annotations

import argparse
import hashlib
import itertools
from pathlib import Path
import re
import struct
from typing import Sequence

from audit_common import (
    AuditError,
    BSP_HEADER,
    BSP_LUMP,
    PAK_ENTRY,
    PAK_HEADER,
    Q2_BSP_LUMP_COUNT,
    Q2_BSP_VERSION,
    checked_range,
    normalize_runtime_path,
    parse_bsp_entity_lump,
    sha256_file,
    stable_json_text,
)


ROOT = Path(__file__).resolve().parents[1]
OWNED_ROOT = ROOT / ".install" / "runtime-fixtures"
FIXTURE_NAME_RE = re.compile(r"^zaereo_fixture_[a-z0-9_]+$")
Q2_PLANE = struct.Struct("<4fi")
Q2_NODE = struct.Struct("<i2i3h3h2H")
Q2_LEAF = struct.Struct("<ihh3h3h4H")
Q2_MODEL = struct.Struct("<9f3i")
Q2_BRUSH = struct.Struct("<iii")
Q2_BRUSHSIDE = struct.Struct("<Hh")
CONTENTS_SOLID = 1
DM_ITEM_CLASSNAMES = (
    "weapon_soniccannon",
    "weapon_sniperrifle",
    "weapon_flaregun",
    "ammo_ired",
    "ammo_a2k",
    "ammo_flares",
    "ammo_empnuke",
    "ammo_plasmashield",
)


def _strict_child(parent: Path, child: Path, description: str) -> Path:
    parent = parent.resolve()
    child = child.resolve()
    try:
        relative = child.relative_to(parent)
    except ValueError as error:
        raise AuditError(f"{description} must remain below {parent}: {child}") from error
    if not relative.parts:
        raise AuditError(f"{description} must be a strict child of {parent}")
    return child


def _read_pak_member(pak_path: Path, member: str) -> tuple[bytes, dict[str, object]]:
    pak_path = pak_path.resolve(strict=True)
    member = normalize_runtime_path(member, "source PAK member")
    size = pak_path.stat().st_size
    with pak_path.open("rb") as stream:
        header = stream.read(PAK_HEADER.size)
        if len(header) != PAK_HEADER.size:
            raise AuditError("source PAK header is truncated")
        magic, directory_offset, directory_length = PAK_HEADER.unpack(header)
        if magic != b"PACK":
            raise AuditError(f"source archive has invalid PAK magic {magic!r}")
        checked_range(directory_offset, directory_length, size, "source PAK directory")
        if directory_length % PAK_ENTRY.size:
            raise AuditError("source PAK directory length is not a multiple of 64")
        stream.seek(directory_offset)
        directory = stream.read(directory_length)
        if len(directory) != directory_length:
            raise AuditError("source PAK directory is truncated")

        found: tuple[int, int] | None = None
        for offset in range(0, directory_length, PAK_ENTRY.size):
            raw_name, entry_offset, entry_size = PAK_ENTRY.unpack_from(directory, offset)
            name = raw_name.partition(b"\0")[0].decode("ascii")
            runtime_path = normalize_runtime_path(name, "source PAK entry")
            checked_range(entry_offset, entry_size, size, f"source PAK:{runtime_path}")
            if runtime_path == member:
                if found is not None:
                    raise AuditError(f"source PAK contains duplicate member {member}")
                found = (entry_offset, entry_size)
        if found is None:
            raise AuditError(f"source PAK does not contain {member}")

        entry_offset, entry_size = found
        stream.seek(entry_offset)
        data = stream.read(entry_size)
        if len(data) != entry_size:
            raise AuditError(f"source PAK member {member} is truncated")

    return data, {
        "archive_basename": pak_path.name,
        "archive_size": size,
        "archive_sha256": sha256_file(pak_path),
        "member": member,
        "member_size": len(data),
        "member_sha256": hashlib.sha256(data).hexdigest(),
    }


def _entity_dict(entity: Sequence[tuple[str, str]]) -> dict[str, str]:
    return {key: value for key, value in entity}


def _first_deathmatch_start(bsp: bytes) -> tuple[str, str]:
    parsed = parse_bsp_entity_lump(bsp)
    for entity in parsed.entities:
        values = _entity_dict(entity)
        if values.get("classname") == "info_player_deathmatch" and values.get("origin"):
            return values["origin"], values.get("angle", "0")
    raise AuditError("source BSP has no info_player_deathmatch with an origin")


def _bsp_lumps(bsp: bytes) -> list[tuple[int, int]]:
    return [
        BSP_LUMP.unpack_from(bsp, BSP_HEADER.size + index * BSP_LUMP.size)
        for index in range(Q2_BSP_LUMP_COUNT)
    ]


def _point_inside_solid_brush(bsp: bytes, point: tuple[float, float, float]) -> bool:
    lumps = _bsp_lumps(bsp)
    plane_offset, plane_length = lumps[1]
    brush_offset, brush_length = lumps[14]
    side_offset, side_length = lumps[15]
    for offset, length, label in (
        (plane_offset, plane_length, "plane lump"),
        (brush_offset, brush_length, "brush lump"),
        (side_offset, side_length, "brushside lump"),
    ):
        checked_range(offset, length, len(bsp), label)
    if (
        plane_length % Q2_PLANE.size
        or brush_length % Q2_BRUSH.size
        or side_length % Q2_BRUSHSIDE.size
    ):
        raise AuditError("source BSP collision lump has an invalid record size")

    plane_count = plane_length // Q2_PLANE.size
    side_count = side_length // Q2_BRUSHSIDE.size
    for brush_index in range(brush_length // Q2_BRUSH.size):
        first_side, num_sides, contents = Q2_BRUSH.unpack_from(
            bsp, brush_offset + brush_index * Q2_BRUSH.size
        )
        if not contents & CONTENTS_SOLID:
            continue
        if first_side < 0 or num_sides <= 0 or first_side + num_sides > side_count:
            raise AuditError("source BSP brush side range is invalid")
        inside = True
        for side_index in range(first_side, first_side + num_sides):
            plane_index, _ = Q2_BRUSHSIDE.unpack_from(
                bsp, side_offset + side_index * Q2_BRUSHSIDE.size
            )
            if plane_index >= plane_count:
                raise AuditError("source BSP brush plane index is out of range")
            plane = Q2_PLANE.unpack_from(
                bsp, plane_offset + plane_index * Q2_PLANE.size
            )
            distance = (
                point[0] * plane[0]
                + point[1] * plane[1]
                + point[2] * plane[2]
                - plane[3]
            )
            if distance > -0.5:
                inside = False
                break
        if inside:
            return True
    return False


def _find_solid_trace_origin(bsp: bytes, valid_origin: str) -> tuple[float, float, float]:
    try:
        origin = tuple(float(value) for value in valid_origin.split())
    except ValueError as error:
        raise AuditError(f"invalid source deathmatch origin {valid_origin!r}") from error
    if len(origin) != 3:
        raise AuditError(f"invalid source deathmatch origin {valid_origin!r}")

    for radius in range(16, 2049, 16):
        for delta in itertools.product((-radius, 0, radius), repeat=3):
            if delta == (0, 0, 0):
                continue
            candidate = (
                origin[0] + delta[0],
                origin[1] + delta[1],
                origin[2] + delta[2],
            )
            if _point_inside_solid_brush(bsp, candidate):
                return candidate
    raise AuditError("could not derive a solid collision point near the source DM start")


def _format_origin(origin: tuple[float, float, float]) -> str:
    return " ".join(f"{value:.3f}" for value in origin)


def _render_entities(valid_origin: str, valid_angle: str, blocked_origin: str) -> bytes:
    blocked_origins = (blocked_origin,) * 4
    entities: list[tuple[tuple[str, str], ...]] = [
        (
            ("classname", "worldspawn"),
            ("message", "ZaeREo private DM partial-placement fixture"),
        ),
        (
            ("classname", "info_player_deathmatch"),
            ("origin", valid_origin),
            ("angle", valid_angle),
        ),
    ]
    entities.extend(
        (
            ("classname", "info_player_deathmatch"),
            ("origin", origin),
            ("angle", "0"),
        )
        for origin in blocked_origins
    )
    entities.append(
        (
            ("classname", "info_player_start"),
            ("origin", valid_origin),
            ("angle", valid_angle),
        )
    )
    text = "".join(
        "{\n" + "".join(f'"{key}" "{value}"\n' for key, value in entity) + "}\n"
        for entity in entities
    )
    return text.encode("ascii") + b"\0"


def _replace_entity_lump(source_bsp: bytes, entity_data: bytes) -> bytes:
    header_size = BSP_HEADER.size + Q2_BSP_LUMP_COUNT * BSP_LUMP.size
    if len(source_bsp) < header_size:
        raise AuditError("source BSP header is truncated")
    magic, version = BSP_HEADER.unpack_from(source_bsp, 0)
    if magic != b"IBSP" or version != Q2_BSP_VERSION:
        raise AuditError(f"expected Quake II IBSP version {Q2_BSP_VERSION}")
    entity_offset, entity_capacity = BSP_LUMP.unpack_from(source_bsp, BSP_HEADER.size)
    checked_range(entity_offset, entity_capacity, len(source_bsp), "source BSP entity lump")
    if len(entity_data) > entity_capacity:
        raise AuditError(
            f"fixture entity lump needs {len(entity_data)} bytes; source capacity is {entity_capacity}"
        )

    output = bytearray(source_bsp)
    output[entity_offset : entity_offset + entity_capacity] = (
        entity_data + b"\0" * (entity_capacity - len(entity_data))
    )
    BSP_LUMP.pack_into(output, BSP_HEADER.size, entity_offset, len(entity_data))
    return bytes(output)


def build_fixture_bsp(source_bsp: bytes) -> tuple[bytes, dict[str, object]]:
    valid_origin, valid_angle = _first_deathmatch_start(source_bsp)
    solid_trace_origin = _find_solid_trace_origin(source_bsp, valid_origin)
    blocked_start = (
        solid_trace_origin[0],
        solid_trace_origin[1],
        solid_trace_origin[2] - 16.0,
    )
    blocked_origin = _format_origin(blocked_start)
    entity_data = _render_entities(valid_origin, valid_angle, blocked_origin)
    return _replace_entity_lump(source_bsp, entity_data), {
        "mode": "alternating-open-blocked-starts",
        "valid_start_origin": valid_origin,
        "solid_trace_origin": _format_origin(solid_trace_origin),
        "blocked_start_origins": [blocked_origin] * 4,
        "expected_added_count": 4,
        "expected_set_indices": [0, 2, 4, 6],
        "expected_success_ordinals": [1, 6, 11, 16],
        "expected_success_attempts": [1, 1, 1, 1],
    }


def _render_existing_member_entities(
    valid_origin: str, valid_angle: str, item_classname: str
) -> bytes:
    entities: tuple[tuple[tuple[str, str], ...], ...] = (
        (
            ("classname", "worldspawn"),
            ("message", "ZaeREo private DM existing-member control"),
        ),
        (
            ("classname", "info_player_deathmatch"),
            ("origin", valid_origin),
            ("angle", valid_angle),
        ),
        (
            ("classname", "info_player_start"),
            ("origin", valid_origin),
            ("angle", valid_angle),
        ),
        (
            ("classname", item_classname),
            ("origin", valid_origin),
        ),
    )
    text = "".join(
        "{\n" + "".join(f'"{key}" "{value}"\n' for key, value in entity) + "}\n"
        for entity in entities
    )
    return text.encode("ascii") + b"\0"


def build_existing_member_fixture_bsp(
    source_bsp: bytes, item_classname: str
) -> tuple[bytes, dict[str, object]]:
    if item_classname not in DM_ITEM_CLASSNAMES:
        raise AuditError(f"unsupported DM item classname {item_classname!r}")
    valid_origin, valid_angle = _first_deathmatch_start(source_bsp)
    entity_data = _render_existing_member_entities(
        valid_origin, valid_angle, item_classname
    )
    return _replace_entity_lump(source_bsp, entity_data), {
        "mode": "existing-member-suppression",
        "valid_start_origin": valid_origin,
        "existing_member_classname": item_classname,
        "expected_added_count": 0,
        "expected_probe_record_count": 0,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-pak", required=True, type=Path)
    parser.add_argument("--source-member", default="maps/q2dm1.bsp")
    parser.add_argument("--fixture-name", default="zaereo_fixture_dm_partial")
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--manifest-output", required=True, type=Path)
    parser.add_argument(
        "--include-existing-member-controls",
        action="store_true",
        help="also emit one zero-injection control BSP for each historical item",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_args(argv)
    if not FIXTURE_NAME_RE.fullmatch(arguments.fixture_name):
        raise AuditError("fixture name must match zaereo_fixture_[a-z0-9_]+")

    output_root = _strict_child(OWNED_ROOT, arguments.output_root, "fixture output root")
    manifest_path = _strict_child(OWNED_ROOT, arguments.manifest_output, "fixture manifest")
    if output_root.name != arguments.fixture_name:
        raise AuditError("fixture output directory basename must equal --fixture-name")
    try:
        manifest_path.relative_to(output_root)
    except ValueError:
        pass
    else:
        raise AuditError("fixture manifest must remain outside the install overlay root")

    source_bsp, source = _read_pak_member(arguments.source_pak, arguments.source_member)
    fixture_bsp, fixture = build_fixture_bsp(source_bsp)
    generated: list[tuple[str, bytes, dict[str, object]]] = [
        (arguments.fixture_name, fixture_bsp, fixture)
    ]
    member_controls: list[dict[str, object]] = []
    if arguments.include_existing_member_controls:
        for index, item_classname in enumerate(DM_ITEM_CLASSNAMES):
            map_name = f"zaereo_fixture_dm_m{index}"
            control_bsp, control = build_existing_member_fixture_bsp(
                source_bsp, item_classname
            )
            generated.append((map_name, control_bsp, control))
            member_controls.append(
                {
                    **control,
                    "set_index": index,
                    "map": map_name,
                }
            )

    map_directory = output_root / "maps"
    map_directory.mkdir(parents=True, exist_ok=True)
    expected_paths = {map_directory / f"{map_name}.bsp" for map_name, _, _ in generated}
    for stale_path in map_directory.glob("zaereo_fixture_*.bsp"):
        if stale_path not in expected_paths:
            stale_path.unlink()

    outputs: list[dict[str, object]] = []
    for map_name, bsp_data, contract in generated:
        map_path = map_directory / f"{map_name}.bsp"
        map_path.write_bytes(bsp_data)
        outputs.append(
            {
                "runtime_path": f"maps/{map_name}.bsp",
                "size": len(bsp_data),
                "sha256": hashlib.sha256(bsp_data).hexdigest(),
                "fixture": contract,
            }
        )

    report = {
        "schema": "zaereo.private-dm-runtime-fixture/v1",
        "schema_version": 1,
        "publication_status": "private-local-only",
        "source": source,
        "fixture": fixture,
        "member_controls": member_controls,
        "output": {key: value for key, value in outputs[0].items() if key != "fixture"},
        "outputs": outputs,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(stable_json_text(report), encoding="utf-8", newline="\n")
    for output in outputs:
        print(
            f"Created private DM fixture {output_root / output['runtime_path']} "
            f"(sha256 {output['sha256']})"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as error:
        raise SystemExit(f"error: {error}") from error

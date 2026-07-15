#!/usr/bin/env python3
"""Prove why legacy Visor trace ownership depends on entity link order."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_common import (  # noqa: E402
    AuditError,
    checked_file,
    checked_root,
    sha256_file,
    stable_json_text,
    write_text,
)


def require_fragment(text: str, fragment: str, label: str) -> None:
    if fragment not in text:
        raise AuditError(f"{label} no longer contains the expected source fragment")


def require_order(text: str, fragments: tuple[str, ...], label: str) -> None:
    cursor = -1
    for fragment in fragments:
        position = text.find(fragment, cursor + 1)
        if position < 0:
            raise AuditError(f"{label} no longer contains the expected ordered fragment")
        cursor = position


def identity(path: Path, root: Path | None = None) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix() if root else path.name,
        "sha256": sha256_file(path),
        "size": path.stat().st_size,
    }


def build_report(
    zaero_root: Path, legacy_root: Path, zaero_binary: Path
) -> dict[str, Any]:
    zaero_root = checked_root(zaero_root, "Zaero source root")
    legacy_root = checked_root(legacy_root, "legacy Quake II root")
    zaero_binary = checked_file(zaero_binary, "retail Zaero game binary")

    camera_path = checked_file(zaero_root / "z_camera.c", "Zaero z_camera.c")
    client_path = checked_file(zaero_root / "p_client.c", "Zaero p_client.c")
    physics_path = checked_file(zaero_root / "g_phys.c", "Zaero g_phys.c")
    world_path = checked_file(
        legacy_root / "server" / "sv_world.c", "legacy server/sv_world.c"
    )

    camera = camera_path.read_text(encoding="latin-1")
    client = client_path.read_text(encoding="latin-1")
    physics = physics_path.read_text(encoding="latin-1")
    world = world_path.read_text(encoding="latin-1")

    require_order(
        camera,
        (
            'e->classname = "VisorCopy";',
            "e->owner = player;",
            "e->movetype = MOVETYPE_NONE;",
            "e->solid = SOLID_BBOX;",
            "player->svflags |= SVF_NOCLIENT;",
            "gi.linkentity(e);",
        ),
        "zCam_TrackEntity",
    )
    require_fragment(camera, "player->movetype = MOVETYPE_FREEZE;", "zCam_TrackEntity")
    require_fragment(camera, "player->movetype = MOVETYPE_WALK;", "zCam_Stop")
    require_order(
        world,
        (
            "InsertLinkBefore (&ent->area, &node->solid_edicts);",
            "SV_AreaEdicts (clip->boxmins, clip->boxmaxs, touchlist",
            "trace.fraction < clip->trace.fraction",
        ),
        "legacy world linking and trace",
    )
    require_order(
        client,
        (
            "if(ent->movetype == MOVETYPE_FREEZE)",
            "client->ps.pmove.pm_type = PM_FREEZE;",
            "return;",
        ),
        "legacy frozen ClientThink",
    )
    require_order(
        physics,
        (
            "if (check->movetype == MOVETYPE_PUSH",
            "|| check->movetype == MOVETYPE_NOCLIP)",
            "VectorAdd (check->s.origin, move, check->s.origin);",
            "gi.linkentity (check);",
        ),
        "legacy SV_Push",
    )
    if "check->movetype == MOVETYPE_FREEZE" in physics:
        raise AuditError("legacy SV_Push unexpectedly excludes MOVETYPE_FREEZE")

    facts = {
        "copy_created_after_player": True,
        "copy_is_solid_bbox": True,
        "copy_takedamage_assignment_present": "e->takedamage" in camera,
        "equal_fraction_replaces_winner": False,
        "frozen_clientthink_relinks_player": False,
        "initial_equal_hit_winner": "real_player",
        "pusher_can_relink_frozen_player": True,
        "post_pusher_equal_hit_winner": "VisorCopy",
        "real_player_hidden_not_desolidified": True,
        "solid_links_append_at_tail": True,
        "solid_trace_walk_is_oldest_first": True,
        "trace_ownership_is_link_order_dependent": True,
    }
    return {
        "audit": "zaero-visor-trace-order",
        "schema_version": 1,
        "inputs": {
            "legacy_source": identity(world_path, legacy_root),
            "retail_binary": identity(zaero_binary),
            "zaero_sources": [
                identity(camera_path, zaero_root),
                identity(client_path, zaero_root),
                identity(physics_path, zaero_root),
            ],
        },
        "proof": {
            "facts": facts,
            "initial_order": ["real_player", "VisorCopy"],
            "post_pusher_order": ["VisorCopy", "real_player"],
            "reasoning": [
                "The player is already linked before zCam_TrackEntity creates and links the overlapping copy.",
                "Legacy solid-area insertion appends to the list and area queries preserve traversal order.",
                "An equal-fraction entity trace does not replace the first winner.",
                "MOVETYPE_FREEZE returns before normal client movement can relink the player.",
                "SV_Push does not exclude MOVETYPE_FREEZE and relinks a successfully moved player.",
            ],
        },
        "disposition": {
            "classification": "FIX",
            "decision": "D-021",
            "implementation": {
                "real_player": "solid, damageable, hidden while active",
                "visual_copy": "visible, generation-owned, SOLID_NOT, not damageable",
            },
            "rationale": "Legacy damage ownership changes with mover-driven relinking; it is not a stable combat contract.",
        },
    }


def markdown_report(report: dict[str, Any]) -> str:
    facts = report["proof"]["facts"]
    inputs = report["inputs"]
    lines = [
        "# Zaero Visor trace-order audit",
        "",
        "This normalized audit proves the source-level mechanism behind D-021.",
        "It does not claim a live retail capture or live Rerelease verification.",
        "",
        "## Identity",
        "",
        "| Input | SHA-256 | Bytes |",
        "| --- | --- | ---: |",
    ]
    records = list(inputs["zaero_sources"]) + [
        inputs["legacy_source"],
        inputs["retail_binary"],
    ]
    for record in records:
        lines.append(
            f'| {record["path"]} | {record["sha256"]} | {record["size"]} |'
        )
    lines.extend(
        [
            "",
            "## Proof",
            "",
            "| Fact | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in sorted(facts.items()):
        lines.append(f"| {key} | {str(value).lower()} |")
    lines.extend(
        [
            "",
            "Initial equal-hit order: real_player, VisorCopy.",
            "",
            "After a mover relinks the frozen player: VisorCopy, real_player.",
            "",
            "## D-021 disposition",
            "",
            "Classify the port as FIX: preserve the hidden real player as solid and",
            "damageable, but make the generation-owned presentation copy SOLID_NOT.",
            "This removes link-order-dependent trace absorption without weakening the",
            "player. Live hitscan, projectile, mover, save/load, and multiplayer",
            "verification remain open.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zaero-root", required=True, type=Path)
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--zaero-binary", required=True, type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = build_report(args.zaero_root, args.legacy_root, args.zaero_binary)
        write_text(args.json_output, stable_json_text(report))
        write_text(args.markdown_output, markdown_report(report))
    except (AuditError, OSError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

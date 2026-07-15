#!/usr/bin/env python3
"""Audit Q-048's one-line legacy SV_FlyMove plane-resolution delta."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import struct
import sys
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_common import (  # noqa: E402
    AuditError,
    checked_file,
    checked_root,
    sha256_file,
    stable_json_text,
    write_text,
)
from audit_stock_precaches import (  # noqa: E402
    _call_sites,
    _function_records,
)


LEGACY_CONDITION = "if((j!=i)&&!VectorCompare(planes[i],planes[j]))"
ZAERO_CONDITION = "if(j!=i)"


def _identity(path: Path, root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256_file(path),
        "size": path.stat().st_size,
    }


def _read(path: Path) -> str:
    return path.read_text(encoding="latin-1")


def _function_text(path: Path, name: str) -> tuple[str, list[int]]:
    records = [record for record in _function_records(path) if record.name == name]
    if len(records) != 1:
        raise AuditError(
            f"{path.name} must contain exactly one {name} definition; found {len(records)}"
        )
    record = records[0]
    lines = _read(path).splitlines()
    return "\n".join(lines[record.start_line - 1 : record.end_line]), [
        record.start_line,
        record.end_line,
    ]


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _source_files(root: Path, suffix: str) -> list[Path]:
    return sorted(
        (path for path in root.rglob(f"*{suffix}") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix().encode("utf-8"),
    )


def _require_calls(
    calls: list[dict[str, Any]], expected: set[tuple[str, str]], label: str
) -> None:
    actual = {(item["path"], item["caller"]) for item in calls}
    if actual != expected:
        raise AuditError(
            f"{label} call graph changed: expected {sorted(expected)}, found {sorted(actual)}"
        )


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def _vec(values: Iterable[float]) -> tuple[float, float, float]:
    result = tuple(_f32(value) for value in values)
    if len(result) != 3:
        raise AuditError("golden vector must have three components")
    return result  # type: ignore[return-value]


def _dot(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return _f32(_f32(_f32(a[0] * b[0]) + _f32(a[1] * b[1])) + _f32(a[2] * b[2]))


def _cross(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> tuple[float, float, float]:
    return _vec(
        (
            _f32(a[1] * b[2] - a[2] * b[1]),
            _f32(a[2] * b[0] - a[0] * b[2]),
            _f32(a[0] * b[1] - a[1] * b[0]),
        )
    )


def _scale(
    value: tuple[float, float, float], scale: float
) -> tuple[float, float, float]:
    return _vec(_f32(component * scale) for component in value)


def _clip(
    velocity: tuple[float, float, float],
    normal: tuple[float, float, float],
    overbounce: float,
) -> tuple[float, float, float]:
    backoff = _f32(_dot(velocity, normal) * _f32(overbounce))
    result = []
    for component, plane_component in zip(velocity, normal):
        clipped = _f32(component - _f32(plane_component * backoff))
        result.append(0.0 if -0.1 < clipped < 0.1 else clipped)
    return _vec(result)


def simulate_legacy_planes(
    initial_velocity: Iterable[float],
    normals: Iterable[Iterable[float]],
    *,
    suppress_exact_duplicates: bool,
) -> dict[str, Any]:
    """Model fraction-zero clip-plane accumulation using C float operations."""

    original = _vec(initial_velocity)
    current = original
    planes: list[tuple[float, float, float]] = []
    exact_duplicate_comparisons = 0
    exact_duplicate_negative_rejections = 0
    suppressed_exact_duplicate_comparisons = 0
    terminal = "open"
    for raw_normal in normals:
        planes.append(_vec(raw_normal))
        accepted_velocity: tuple[float, float, float] | None = None
        for i, plane in enumerate(planes):
            candidate = _clip(original, plane, 1.0)
            valid = True
            for j, other in enumerate(planes):
                if j == i:
                    continue
                if plane == other:
                    if suppress_exact_duplicates:
                        suppressed_exact_duplicate_comparisons += 1
                        continue
                    exact_duplicate_comparisons += 1
                if _dot(candidate, other) < 0:
                    if plane == other:
                        exact_duplicate_negative_rejections += 1
                    valid = False
                    break
            if valid:
                accepted_velocity = candidate
                break
        if accepted_velocity is not None:
            current = accepted_velocity
            terminal = "plane"
        elif len(planes) != 2:
            current = (0.0, 0.0, 0.0)
            terminal = "dead-stop"
        else:
            crease = _cross(planes[0], planes[1])
            current = _scale(crease, _dot(crease, current))
            terminal = "crease"
        if _dot(current, original) <= 0:
            current = (0.0, 0.0, 0.0)
            terminal = "primal-stop"
            break
    return {
        "exact_duplicate_comparisons": exact_duplicate_comparisons,
        "exact_duplicate_negative_rejections": exact_duplicate_negative_rejections,
        "final_velocity": _report_vec(current),
        "plane_count": len(planes),
        "suppressed_exact_duplicate_comparisons": suppressed_exact_duplicate_comparisons,
        "terminal": terminal,
    }


def simulate_rerelease_planes(
    initial_velocity: Iterable[float], normals: Iterable[Iterable[float]]
) -> dict[str, Any]:
    """Model the native helper's plane accumulation and 0.99 duplicate gate."""

    primal = _vec(initial_velocity)
    current = primal
    planes: list[tuple[float, float, float]] = []
    duplicate_skips = 0
    terminal = "open"
    for raw_normal in normals:
        normal = _vec(raw_normal)
        if any(_dot(normal, plane) > 0.99 for plane in planes):
            duplicate_skips += 1
            terminal = "near-duplicate-skip"
            continue
        planes.append(normal)
        accepted = False
        for i, plane in enumerate(planes):
            current = _clip(current, plane, 1.01)
            if all(j == i or _dot(current, other) >= 0 for j, other in enumerate(planes)):
                accepted = True
                break
        if accepted:
            terminal = "plane"
        elif len(planes) != 2:
            current = (0.0, 0.0, 0.0)
            terminal = "dead-stop"
        else:
            crease = _cross(planes[0], planes[1])
            current = _scale(crease, _dot(crease, current))
            terminal = "crease"
        if _dot(current, primal) <= 0:
            current = (0.0, 0.0, 0.0)
            terminal = "primal-stop"
            break
    return {
        "duplicate_skips": duplicate_skips,
        "final_velocity": _report_vec(current),
        "plane_count": len(planes),
        "terminal": terminal,
    }


def _report_vec(value: Iterable[float]) -> list[float]:
    result = []
    for component in value:
        rounded = round(float(component), 6)
        result.append(0.0 if abs(rounded) < 0.0000005 else rounded)
    return result


GOLDEN_CASES: tuple[dict[str, Any], ...] = (
    {
        "id": "open-control",
        "role": "unobstructed control",
        "velocity": (100.0, 20.0, 0.0),
        "normals": (),
    },
    {
        "id": "wall-slide",
        "role": "single axial wall",
        "velocity": (100.0, 20.0, 0.0),
        "normals": ((-1.0, 0.0, 0.0),),
    },
    {
        "id": "corner-crease",
        "role": "perpendicular corner",
        "velocity": (100.0, 100.0, 20.0),
        "normals": ((-1.0, 0.0, 0.0), (0.0, -1.0, 0.0)),
    },
    {
        "id": "stair-riser-floor",
        "role": "vertical riser plus floor",
        "velocity": (100.0, 25.0, -50.0),
        "normals": ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    },
    {
        "id": "three-plane-wedge",
        "role": "three unique blocking planes",
        "velocity": (100.0, 100.0, -100.0),
        "normals": (
            (-1.0, 0.0, 0.0),
            (0.0, -1.0, 0.0),
            (0.0, 0.0, 1.0),
        ),
    },
    {
        "id": "projectile-duplicate-plane",
        "role": "fraction-zero repeat on an exact non-axial plane",
        "velocity": (366.290771484375, 288.7452697753906, -139.10398864746094),
        "normals": (
            (-0.19490621984004974, -0.9490077495574951, -0.24778178334236145),
            (-0.19490621984004974, -0.9490077495574951, -0.24778178334236145),
        ),
    },
    {
        "id": "monster-near-duplicate-plane",
        "role": "two nearly parallel curved-surface contacts",
        "velocity": (120.0, 45.0, 10.0),
        "normals": ((-1.0, 0.0, 0.0), (-0.999, 0.0447, 0.0)),
    },
)


def golden_results() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in GOLDEN_CASES:
        legacy = simulate_legacy_planes(
            case["velocity"], case["normals"], suppress_exact_duplicates=True
        )
        zaero = simulate_legacy_planes(
            case["velocity"], case["normals"], suppress_exact_duplicates=False
        )
        rerelease = simulate_rerelease_planes(case["velocity"], case["normals"])
        results.append(
            {
                "id": case["id"],
                "legacy": legacy,
                "legacy_equals_zaero": legacy["final_velocity"] == zaero["final_velocity"],
                "normals": [_report_vec(normal) for normal in case["normals"]],
                "rerelease": rerelease,
                "role": case["role"],
                "velocity": _report_vec(case["velocity"]),
                "zaero": zaero,
            }
        )
    differences = [item["id"] for item in results if not item["legacy_equals_zaero"]]
    if differences != ["projectile-duplicate-plane"]:
        raise AuditError(f"Q-048 golden difference set changed: {differences}")
    duplicate = next(item for item in results if item["id"] == differences[0])
    if duplicate["legacy"]["terminal"] != "plane":
        raise AuditError("legacy duplicate-plane golden no longer preserves the slide")
    if duplicate["zaero"]["terminal"] != "primal-stop":
        raise AuditError("Zaero duplicate-plane golden no longer dead-stops")
    if duplicate["rerelease"]["duplicate_skips"] != 1:
        raise AuditError("Rerelease duplicate-plane golden no longer uses its native skip")
    return results


def build_report(
    zaero_root: Path,
    legacy_root: Path,
    rerelease_root: Path,
    port_root: Path,
) -> dict[str, Any]:
    zaero_root = checked_root(zaero_root, "Zaero source root")
    legacy_root = checked_root(legacy_root, "legacy Quake II game root")
    rerelease_root = checked_root(rerelease_root, "Rerelease source root")
    port_root = checked_root(port_root, "ZaeREo source root")

    zaero_phys = checked_file(zaero_root / "g_phys.c", "Zaero g_phys.c")
    legacy_phys = checked_file(legacy_root / "g_phys.c", "legacy g_phys.c")
    rerelease_phys = checked_file(rerelease_root / "g_phys.cpp", "Rerelease g_phys.cpp")
    rerelease_move = checked_file(rerelease_root / "p_move.cpp", "Rerelease p_move.cpp")
    port_phys = checked_file(port_root / "g_phys.cpp", "port g_phys.cpp")
    port_move = checked_file(port_root / "p_move.cpp", "port p_move.cpp")

    legacy_function, legacy_lines = _function_text(legacy_phys, "SV_FlyMove")
    zaero_function, zaero_lines = _function_text(zaero_phys, "SV_FlyMove")
    rerelease_function, rerelease_lines = _function_text(rerelease_phys, "SV_FlyMove")
    port_function, port_lines = _function_text(port_phys, "SV_FlyMove")
    rerelease_helper, rerelease_helper_lines = _function_text(
        rerelease_move, "PM_StepSlideMove_Generic"
    )
    port_helper, port_helper_lines = _function_text(port_move, "PM_StepSlideMove_Generic")

    legacy_compact = _compact(legacy_function)
    zaero_compact = _compact(zaero_function)
    if legacy_compact.count(LEGACY_CONDITION) != 1:
        raise AuditError("legacy SV_FlyMove duplicate-plane condition changed")
    if zaero_compact.count(ZAERO_CONDITION) != 1:
        raise AuditError("Zaero SV_FlyMove plane condition changed")
    if legacy_compact.replace(LEGACY_CONDITION, ZAERO_CONDITION, 1) != zaero_compact:
        raise AuditError("Zaero SV_FlyMove now differs beyond the one plane condition")
    if rerelease_function != port_function:
        raise AuditError("port SV_FlyMove no longer matches the Rerelease baseline")
    if rerelease_helper != port_helper:
        raise AuditError("port PM_StepSlideMove_Generic no longer matches the baseline")
    for fragment in (
        "trace.plane.normal.dot(planes[i]) > 0.99f",
        "if (i < numplanes)",
        "continue;",
        "PM_ClipVelocity(velocity, planes[i], velocity, 1.01f)",
    ):
        if fragment not in port_helper:
            raise AuditError(f"Rerelease helper no longer contains {fragment!r}")

    zaero_calls = _call_sites(_source_files(zaero_root, ".c"), "SV_FlyMove", zaero_root)
    legacy_calls = _call_sites(_source_files(legacy_root, ".c"), "SV_FlyMove", legacy_root)
    rerelease_cpp = _source_files(rerelease_root, ".cpp")
    port_cpp = _source_files(port_root, ".cpp")
    rerelease_calls = _call_sites(rerelease_cpp, "SV_FlyMove", rerelease_root)
    port_calls = _call_sites(port_cpp, "SV_FlyMove", port_root)
    helper_calls = _call_sites(port_cpp, "PM_StepSlideMove_Generic", port_root)
    _require_calls(legacy_calls, {("g_phys.c", "SV_Physics_Step")}, "legacy SV_FlyMove")
    _require_calls(
        zaero_calls,
        {
            ("g_ai.c", "ai_fly_strafe"),
            ("g_phys.c", "SV_Physics_FallFloat"),
            ("g_phys.c", "SV_Physics_Step"),
        },
        "Zaero SV_FlyMove",
    )
    _require_calls(
        rerelease_calls,
        {
            ("g_phys.cpp", "SV_Physics_Step"),
            ("rogue/g_rogue_phys.cpp", "SV_Physics_NewToss"),
        },
        "Rerelease SV_FlyMove",
    )
    _require_calls(
        port_calls,
        {
            ("g_phys.cpp", "SV_Physics_FallFloat"),
            ("g_phys.cpp", "SV_Physics_Step"),
            ("rogue/g_rogue_phys.cpp", "SV_Physics_NewToss"),
            ("zaero/g_zaero_ai.cpp", "Zaero_RunFlyStrafe"),
        },
        "port SV_FlyMove",
    )
    _require_calls(
        helper_calls,
        {
            ("g_phys.cpp", "SV_FlyMove"),
            ("p_move.cpp", "PM_CheckSpecialMovement"),
            ("p_move.cpp", "PM_StepSlideMove_"),
        },
        "port PM_StepSlideMove_Generic",
    )

    goldens = golden_results()
    return {
        "audit": "zaero-sv-flymove-plane-resolution",
        "call_graph": {
            "legacy": legacy_calls,
            "port": port_calls,
            "rerelease": rerelease_calls,
            "rerelease_shared_helper": helper_calls,
            "zaero": zaero_calls,
        },
        "disposition": {
            "classification": "ADAPT",
            "decision": "D-044",
            "implementation": (
                "Retain the unmodified Rerelease shared step-slide helper for stock, "
                "expansion, FallFloat, and Hover callers; do not import the one-line "
                "global Zaero plane-comparison removal."
            ),
            "live_clip_fixtures_remaining": True,
        },
        "golden_cases": goldens,
        "inputs": {
            "legacy": [_identity(legacy_phys, legacy_root)],
            "port": [_identity(path, port_root) for path in (port_phys, port_move)],
            "rerelease": [
                _identity(path, rerelease_root)
                for path in (rerelease_phys, rerelease_move)
            ],
            "zaero": [_identity(zaero_phys, zaero_root)],
        },
        "schema_version": 1,
        "source_delta": {
            "legacy_function_lines": legacy_lines,
            "legacy_suppression_condition": (
                "if ((j != i) && !VectorCompare (planes[i], planes[j]))"
            ),
            "port_function_lines": port_lines,
            "port_helper_lines": port_helper_lines,
            "port_matches_rerelease_function": True,
            "port_matches_rerelease_helper": True,
            "rerelease_function_lines": rerelease_lines,
            "rerelease_helper_lines": rerelease_helper_lines,
            "rerelease_near_duplicate_threshold": 0.99,
            "rerelease_overbounce": 1.01,
            "zaero_function_lines": zaero_lines,
            "zaero_only_semantic_change": "if (j != i)",
        },
        "summary": {
            "golden_case_count": len(goldens),
            "legacy_zaero_difference_case_count": sum(
                not item["legacy_equals_zaero"] for item in goldens
            ),
            "port_sv_flymove_caller_count": len(port_calls),
            "rerelease_shared_helper_caller_count": len(helper_calls),
            "zaero_sv_flymove_caller_count": len(zaero_calls),
        },
        "scope_note": (
            "These are deterministic float32 plane-resolution goldens, not live BSP "
            "trace captures. Windowed corner/wedge/stair/projectile/monster fixtures "
            "remain before Q-048 is verified."
        ),
    }


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    delta = report["source_delta"]
    lines = [
        "# Q-048 SV_FlyMove plane-resolution audit",
        "",
        "This identity-locked audit isolates Zaero's one-line global plane-comparison",
        "change and compares it with the Rerelease shared step-slide solver.",
        "",
        "## Source result",
        "",
        "- Legacy Quake II suppresses exact duplicate-plane comparisons while testing",
        "  a clipped candidate; Zaero removes only that suppression condition.",
        "- The change is inside global `SV_FlyMove`, so it affects Step, FallFloat, and",
        "  direct fly-strafe callers rather than a Zaero-only entity type.",
        f'- Rerelease instead rejects accumulated planes whose normal dot product is above **{delta["rerelease_near_duplicate_threshold"]}**, nudges on repeat contact, and clips with **{delta["rerelease_overbounce"]}** overbounce.',
        "- The current port keeps the Rerelease `SV_FlyMove` function exact and",
        "  `PM_StepSlideMove_Generic` byte-for-byte unchanged.",
        "- That helper is shared by server entities, ordinary player step-slide, and",
        "  special/water-jump movement; a global Zaero transplant would alter native",
        "  players and expansion entities.",
        "",
        "## Executable float32 goldens",
        "",
        "| Case | Role | Legacy final | Zaero final | Rerelease final | Native duplicate skips |",
        "| --- | --- | --- | --- | --- | ---: |",
    ]
    for case in report["golden_cases"]:
        lines.append(
            f'| `{case["id"]}` | {case["role"]} | '
            f'`{case["legacy"]["final_velocity"]}` | '
            f'`{case["zaero"]["final_velocity"]}` | '
            f'`{case["rerelease"]["final_velocity"]}` | '
            f'{case["rerelease"]["duplicate_skips"]} |'
        )
    lines.extend(
        [
            "",
            f'Only **{summary["legacy_zaero_difference_case_count"]}** of the **{summary["golden_case_count"]}** cases distinguishes the two legacy algorithms: an exact repeated non-axial plane produces a small negative float32 residual. Legacy skips that duplicate comparison and continues sliding; Zaero tests it and dead-stops. Rerelease recognizes the repeated plane through its native near-duplicate gate.',
            "",
            "## D-044 disposition",
            "",
            report["disposition"]["implementation"],
            "",
            report["scope_note"],
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zaero-root", required=True, type=Path)
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--rerelease-root", required=True, type=Path)
    parser.add_argument("--port-root", required=True, type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = build_report(
            args.zaero_root,
            args.legacy_root,
            args.rerelease_root,
            args.port_root,
        )
        write_text(args.json_output, stable_json_text(report))
        write_text(args.markdown_output, markdown_report(report))
    except (AuditError, OSError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

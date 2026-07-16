#!/usr/bin/env python3
"""Audit every src/ difference against the pinned Rerelease integration policy."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any, Sequence

from audit_common import (
    AuditError,
    checked_root,
    markdown_cell,
    normalize_runtime_path,
    stable_json_text,
    tree_manifest,
    write_text,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINES = ROOT / "docs" / "provenance" / "baselines.json"
DEFAULT_POLICY = ROOT / "docs" / "provenance" / "upstream-integration-policy.json"


class IntegrationAuditError(AuditError):
    """Raised when the integration policy or source comparison is inconsistent."""


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise IntegrationAuditError(f"invalid {label} {path}: {error}") from error
    if not isinstance(value, dict):
        raise IntegrationAuditError(f"{label} must contain a JSON object: {path}")
    return value


def _validate_policy(
    policy: dict[str, Any],
    baseline: dict[str, Any],
    repository_root: Path,
) -> dict[tuple[str, str], dict[str, Any]]:
    if policy.get("schema") != "zaereo.upstream-integration-policy/v1":
        raise IntegrationAuditError("unsupported upstream integration policy schema")
    if not isinstance(policy.get("policy_id"), str) or not policy["policy_id"]:
        raise IntegrationAuditError("upstream integration policy has no policy_id")
    if not isinstance(policy.get("revision"), int) or policy["revision"] < 1:
        raise IntegrationAuditError("upstream integration policy revision is invalid")
    identity = policy.get("baseline")
    if not isinstance(identity, dict):
        raise IntegrationAuditError("upstream integration policy has no baseline")
    expected_identity = {
        "key": "quake2_rerelease",
        "tree_sha256": baseline["tree_sha256"],
        "official_commit": baseline.get("official_git", {}).get("commit"),
        "official_subtree": baseline.get("official_git", {}).get("subtree"),
    }
    if identity != expected_identity:
        raise IntegrationAuditError("integration policy baseline differs from the pinned baseline")

    categories = policy.get("categories")
    if not isinstance(categories, list) or not categories:
        raise IntegrationAuditError("integration policy categories must be a non-empty array")
    assignments: dict[tuple[str, str], dict[str, Any]] = {}
    category_ids: set[str] = set()
    for category in categories:
        if not isinstance(category, dict):
            raise IntegrationAuditError("integration policy category is not an object")
        identifier = category.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in category_ids:
            raise IntegrationAuditError(f"invalid or duplicate integration category id: {identifier!r}")
        category_ids.add(identifier)
        description = category.get("description")
        evidence = category.get("evidence")
        if not isinstance(description, str) or not description:
            raise IntegrationAuditError(f"category {identifier} has no description")
        if not isinstance(evidence, list) or not evidence or any(not isinstance(item, str) for item in evidence):
            raise IntegrationAuditError(f"category {identifier} has no exact evidence list")
        for reference in evidence:
            relative = reference.split("#", 1)[0]
            candidate = repository_root / Path(normalize_runtime_path(relative, "integration evidence"))
            if not candidate.exists():
                raise IntegrationAuditError(
                    f"category {identifier} evidence does not exist: {reference}"
                )
        for status in ("modified", "added", "removed"):
            paths = category.get(status)
            if not isinstance(paths, list):
                raise IntegrationAuditError(f"category {identifier}.{status} must be an array")
            for raw_path in paths:
                if not isinstance(raw_path, str):
                    raise IntegrationAuditError(f"category {identifier}.{status} has a non-string path")
                path = normalize_runtime_path(raw_path, "integration path")
                if path != raw_path:
                    raise IntegrationAuditError(f"integration path is not canonical: {raw_path}")
                key = (status, path)
                if key in assignments:
                    raise IntegrationAuditError(f"integration path is assigned twice: {status} {path}")
                assignments[key] = {
                    "category": identifier,
                    "description": description,
                    "evidence": evidence,
                }
    return assignments


def build_integration_report(
    source_root: Path,
    baselines_path: Path = DEFAULT_BASELINES,
    policy_path: Path = DEFAULT_POLICY,
    *,
    repository_root: Path = ROOT,
) -> dict[str, Any]:
    source_root = checked_root(source_root, "current source root")
    baseline_document = _read_json(baselines_path.resolve(), "baseline manifest")
    try:
        baseline = baseline_document["baselines"]["quake2_rerelease"]
    except (KeyError, TypeError) as error:
        raise IntegrationAuditError("baseline manifest has no quake2_rerelease entry") from error
    if not isinstance(baseline, dict) or not isinstance(baseline.get("files"), list):
        raise IntegrationAuditError("Rerelease baseline entry is invalid")
    policy = _read_json(policy_path.resolve(), "upstream integration policy")
    assignments = _validate_policy(policy, baseline, repository_root.resolve())

    # src/maps/ holds decompiled map sources (content), not upstream-integrated
    # C++ code, so it is outside this audit's surface.
    current = tree_manifest(source_root, exclude_prefixes=("maps/",))
    baseline_files = {record["path"]: record for record in baseline["files"]}
    current_files = {record["path"]: record for record in current["files"]}
    all_paths = sorted(set(baseline_files) | set(current_files), key=lambda path: path.encode("utf-8"))
    differences: list[dict[str, Any]] = []
    observed_keys: set[tuple[str, str]] = set()
    unclassified: list[dict[str, str]] = []
    for path in all_paths:
        old = baseline_files.get(path)
        new = current_files.get(path)
        if old is not None and new is not None and old["sha256"] == new["sha256"]:
            continue
        status = "added" if old is None else "removed" if new is None else "modified"
        key = (status, path)
        observed_keys.add(key)
        assignment = assignments.get(key)
        if assignment is None:
            unclassified.append({"path": path, "status": status})
        differences.append(
            {
                "path": path,
                "status": status,
                "category": assignment["category"] if assignment else None,
                "evidence": assignment["evidence"] if assignment else [],
                "baseline": old,
                "current": new,
            }
        )
    stale = [
        {"status": status, "path": path, "category": assignments[(status, path)]["category"]}
        for status, path in sorted(set(assignments) - observed_keys)
    ]
    status_counts = Counter(record["status"] for record in differences)
    category_counts = Counter(record["category"] or "UNCLASSIFIED" for record in differences)
    return {
        "format": "ZaeREo upstream integration audit",
        "schema_version": 1,
        "baseline": {
            "key": "quake2_rerelease",
            "official_commit": baseline["official_git"]["commit"],
            "official_subtree": baseline["official_git"]["subtree"],
            "tree_sha256": baseline["tree_sha256"],
            "file_count": baseline["file_count"],
        },
        "policy": {
            "id": policy["policy_id"],
            "revision": policy["revision"],
        },
        "current": {
            "tree_sha256": current["tree_sha256"],
            "file_count": current["file_count"],
            "total_size": current["total_size"],
        },
        "summary": {
            "unchanged": baseline["file_count"] - status_counts["modified"] - status_counts["removed"],
            "modified": status_counts["modified"],
            "added": status_counts["added"],
            "removed": status_counts["removed"],
            "difference_count": len(differences),
            "category_counts": dict(sorted(category_counts.items())),
            "unclassified_count": len(unclassified),
            "stale_policy_count": len(stale),
            "policy_complete": not unclassified and not stale,
        },
        "differences": differences,
        "unclassified": unclassified,
        "stale_policy": stale,
    }


def integration_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Rerelease upstream integration audit",
        "",
        "This file is generated by `tools/audit_upstream_integration.py`; do not edit it by hand.",
        "It classifies every byte-level `src/` difference from the pinned official Rerelease baseline.",
        "A classification is review routing, not proof of gameplay completion.",
        "",
        "## Identity and summary",
        "",
        "| Measure | Value |",
        "| --- | --- |",
        f"| Official commit | `{report['baseline']['official_commit']}` |",
        f"| Baseline aggregate | `{report['baseline']['tree_sha256']}` |",
        f"| Current `src/` aggregate | `{report['current']['tree_sha256']}` |",
        f"| Unchanged | {summary['unchanged']} |",
        f"| Modified | {summary['modified']} |",
        f"| Added | {summary['added']} |",
        f"| Removed/relocated | {summary['removed']} |",
        f"| Unclassified | {summary['unclassified_count']} |",
        f"| Stale policy records | {summary['stale_policy_count']} |",
        f"| Policy complete | `{str(summary['policy_complete']).lower()}` |",
        "",
        "## Classified paths",
        "",
        "| Path | Status | Category | Baseline SHA-256 | Current SHA-256 | Evidence |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for record in report["differences"]:
        old_hash = record["baseline"]["sha256"] if record["baseline"] else "—"
        new_hash = record["current"]["sha256"] if record["current"] else "—"
        evidence = ", ".join(f"`{markdown_cell(item)}`" for item in record["evidence"])
        lines.append(
            f"| `{markdown_cell(record['path'])}` | {record['status']} | "
            f"{record['category'] or '**UNCLASSIFIED**'} | `{old_hash}` | `{new_hash}` | {evidence} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=ROOT / "src")
    parser.add_argument("--baselines", type=Path, default=DEFAULT_BASELINES)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = build_integration_report(
            args.source_root,
            args.baselines,
            args.policy,
        )
        write_text(args.json_output, stable_json_text(report))
        if args.markdown_output:
            write_text(args.markdown_output, integration_markdown(report))
    except (OSError, IntegrationAuditError) as error:
        print(f"audit_upstream_integration.py: {error}", file=sys.stderr)
        return 2
    if not report["summary"]["policy_complete"]:
        print(
            "audit_upstream_integration.py: integration policy is incomplete: "
            f"unclassified={report['summary']['unclassified_count']} "
            f"stale={report['summary']['stale_policy_count']}",
            file=sys.stderr,
        )
        return 3
    print(
        "upstream integration policy complete: "
        f"differences={report['summary']['difference_count']} "
        f"current_tree={report['current']['tree_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

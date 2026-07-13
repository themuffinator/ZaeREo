#!/usr/bin/env python3
"""Create an immutable, non-default Git tree ref after repository audit.

The command uses a temporary index, so it never stages the user's real index or
switches branches. The default ref namespace is not included by ordinary
``git push``/``git push --all``; D-003 still forbids mirroring it publicly.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Sequence

from audit_repository import audit_repository


def _git(
    root: Path,
    *arguments: str,
    env: dict[str, str] | None = None,
    text: bool = True,
) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=text,
    )
    if result.returncode:
        stderr = result.stderr if text else result.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"git {' '.join(arguments)} failed: {stderr.strip()}")
    return result.stdout


def create_snapshot(root: Path, ref: str) -> dict[str, object]:
    root = root.resolve()
    if not ref.startswith("refs/zaereo-private/"):
        raise ValueError("evidence ref must be under refs/zaereo-private/")
    if any(character.isspace() for character in ref):
        raise ValueError("evidence ref may not contain whitespace")

    audit = audit_repository(root)
    summary = audit["summary"]
    assert isinstance(summary, dict)
    if not summary["ready_for_private_snapshot"]:
        raise RuntimeError("repository audit rejected the candidate tree")

    expected_paths = [record["path"] for record in audit["files"]]
    with tempfile.TemporaryDirectory(prefix="zaereo-evidence-index-") as temporary:
        index_path = Path(temporary) / "index"
        env = os.environ.copy()
        env["GIT_INDEX_FILE"] = str(index_path)
        _git(root, "read-tree", "HEAD", env=env)
        _git(root, "add", "--all", "--", ".", env=env)
        tree = str(_git(root, "write-tree", env=env)).strip()

    raw_paths = _git(root, "ls-tree", "-r", "--name-only", "-z", tree, text=False)
    assert isinstance(raw_paths, bytes)
    actual_paths = sorted(
        (part.decode("utf-8") for part in raw_paths.split(b"\0") if part),
        key=lambda value: value.encode("utf-8"),
    )
    if actual_paths != expected_paths:
        raise RuntimeError("temporary Git tree does not match audited candidate paths")

    object_format = str(_git(root, "rev-parse", "--show-object-format")).strip()
    zero_oid = "0" * (64 if object_format == "sha256" else 40)
    _git(root, "update-ref", ref, tree, zero_oid)
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "format": "ZaeREo private evidence snapshot",
        "schema_version": 1,
        "created_utc": created,
        "ref": ref,
        "git_tree": tree,
        "base_head": audit["head"],
        "candidate_tree_sha256": audit["candidate_tree_sha256"],
        "candidate_file_count": summary["candidate_file_count"],
        "candidate_total_bytes": summary["candidate_total_bytes"],
        "audit_violation_count": summary["violation_count"],
        "publication_status": "private-local-only; D-003 forbids public push",
    }


def _git_directory(root: Path) -> Path:
    value = str(_git(root, "rev-parse", "--git-dir")).strip()
    path = Path(value)
    return path if path.is_absolute() else (root / path).resolve()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--ref", required=True, help="new refs/zaereo-private/... ref")
    parser.add_argument("--report-output", type=Path)
    arguments = parser.parse_args(argv)

    try:
        report = create_snapshot(arguments.root, arguments.ref)
        output = arguments.report_output
        if output is None:
            output = _git_directory(arguments.root.resolve()) / "zaereo-evidence" / "phase0-snapshot.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Private evidence report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

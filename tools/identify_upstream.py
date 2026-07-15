#!/usr/bin/env python3
"""Match a recorded source baseline to immutable trees in an official Git repository."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Sequence

from audit_common import AuditError, normalize_runtime_path, stable_json_text, write_text


DEFAULT_BASELINE = Path(__file__).resolve().parents[1] / "docs" / "provenance" / "baselines.json"


class UpstreamError(AuditError):
    """Raised when Git or the baseline cannot provide trustworthy identity evidence."""


def _git(repository: Path, arguments: Sequence[str], *, check: bool = True) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise UpstreamError(f"git {' '.join(arguments)} failed: {detail}")
    return result.stdout


def _load_baseline(path: Path, key: str) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        baseline = document["baselines"][key]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise UpstreamError(f"invalid baseline {path}: {error}") from error

    required = ("files", "file_count", "total_size", "tree_sha256")
    missing = [name for name in required if name not in baseline]
    if missing:
        raise UpstreamError(f"baseline {key!r} is missing: {', '.join(missing)}")

    files = baseline["files"]
    if not isinstance(files, list) or len(files) != baseline["file_count"]:
        raise UpstreamError(f"baseline {key!r} has an inconsistent file count")
    paths: set[str] = set()
    folded_paths: set[str] = set()
    total_size = 0
    for index, record in enumerate(files):
        try:
            path_value = normalize_runtime_path(record["path"], f"baseline file {index}")
            size = record["size"]
            digest = record["sha256"]
        except (KeyError, TypeError, AuditError) as error:
            raise UpstreamError(f"invalid baseline file {index}: {error}") from error
        if path_value in paths or path_value.casefold() in folded_paths:
            raise UpstreamError(f"baseline contains a duplicate/case-colliding path: {path_value}")
        if not isinstance(size, int) or size < 0:
            raise UpstreamError(f"baseline file has invalid size: {path_value}")
        if not isinstance(digest, str) or len(digest) != 64:
            raise UpstreamError(f"baseline file has invalid SHA-256: {path_value}")
        try:
            bytes.fromhex(digest)
        except ValueError as error:
            raise UpstreamError(f"baseline file has invalid SHA-256: {path_value}") from error
        paths.add(path_value)
        folded_paths.add(path_value.casefold())
        total_size += size
    if total_size != baseline["total_size"]:
        raise UpstreamError(f"baseline {key!r} has an inconsistent total size")
    return baseline


def _parse_tree(repository: Path, tree_oid: str) -> list[dict[str, Any]]:
    raw = _git(repository, ["ls-tree", "-r", "-l", "-z", tree_oid])
    records: list[dict[str, Any]] = []
    paths: set[str] = set()
    folded_paths: set[str] = set()
    for index, raw_entry in enumerate(raw.split(b"\0")):
        if not raw_entry:
            continue
        try:
            metadata, raw_path = raw_entry.split(b"\t", 1)
            mode, object_type, oid, raw_size = metadata.split()
            path = normalize_runtime_path(
                raw_path.decode("utf-8", errors="strict"), f"Git tree entry {index}"
            )
            size = int(raw_size)
        except (ValueError, UnicodeDecodeError, AuditError) as error:
            raise UpstreamError(f"invalid Git tree entry {index}: {error}") from error
        if object_type != b"blob" or mode not in (b"100644", b"100755"):
            raise UpstreamError(f"unsupported Git object at {path}: {mode!r} {object_type!r}")
        if path in paths or path.casefold() in folded_paths:
            raise UpstreamError(f"Git tree contains a duplicate/case-colliding path: {path}")
        paths.add(path)
        folded_paths.add(path.casefold())
        records.append({"path": path, "oid": oid.decode("ascii"), "size": size})
    records.sort(key=lambda record: record["path"].encode("utf-8"))
    return records


def _hash_git_tree(repository: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    aggregate = hashlib.sha256()
    files: list[dict[str, Any]] = []
    for record in records:
        content = _git(repository, ["cat-file", "blob", record["oid"]])
        if len(content) != record["size"]:
            raise UpstreamError(f"Git blob size changed while reading {record['path']}")
        digest = hashlib.sha256(content).hexdigest()
        path = record["path"]
        size = record["size"]
        aggregate.update(path.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(str(size).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\n")
        files.append({"path": path, "sha256": digest, "size": size})
    return {
        "file_count": len(files),
        "files": files,
        "total_size": sum(record["size"] for record in files),
        "tree_sha256": aggregate.hexdigest(),
    }


def _commit_metadata(repository: Path, commit: str) -> dict[str, str]:
    raw = _git(
        repository,
        ["show", "-s", "--format=%H%x00%aI%x00%cI%x00%s", commit],
    ).rstrip(b"\n")
    parts = raw.split(b"\0", 3)
    if len(parts) != 4:
        raise UpstreamError(f"could not parse metadata for commit {commit}")
    return {
        "commit": parts[0].decode("ascii"),
        "author_date": parts[1].decode("utf-8", errors="replace"),
        "committer_date": parts[2].decode("utf-8", errors="replace"),
        "subject": parts[3].decode("utf-8", errors="replace"),
    }


def identify_upstream(
    repository: Path,
    baseline: dict[str, Any],
    *,
    subtree: str,
    preferred_ref: str,
    baseline_key: str,
    verified_on: str | None = None,
) -> dict[str, Any]:
    repository = repository.resolve()
    _git(repository, ["rev-parse", "--git-dir"])
    commits = [line for line in _git(repository, ["rev-list", "--all", "--topo-order"]).decode("ascii").splitlines() if line]
    if not commits:
        raise UpstreamError("official repository has no commits")

    preferred_commit = _git(repository, ["rev-parse", "--verify", f"{preferred_ref}^{{commit}}"], check=False).decode("ascii").strip()
    remote_url = _git(repository, ["remote", "get-url", "origin"], check=False).decode("utf-8", errors="replace").strip()
    baseline_by_path = {record["path"]: record for record in baseline["files"]}
    tree_commits: dict[str, list[str]] = {}
    commit_trees: dict[str, str] = {}
    for commit in commits:
        result = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "--verify", f"{commit}:{subtree}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode:
            continue
        tree_oid = result.stdout.decode("ascii").strip()
        commit_trees[commit] = tree_oid
        tree_commits.setdefault(tree_oid, []).append(commit)

    exact_tree_records: dict[str, dict[str, Any]] = {}
    size_candidates = 0
    for tree_oid in sorted(tree_commits):
        records = _parse_tree(repository, tree_oid)
        if len(records) != baseline["file_count"]:
            continue
        if sum(record["size"] for record in records) != baseline["total_size"]:
            continue
        size_candidates += 1
        if set(record["path"] for record in records) != set(baseline_by_path):
            continue
        if any(record["size"] != baseline_by_path[record["path"]]["size"] for record in records):
            continue
        hashed = _hash_git_tree(repository, records)
        if hashed["tree_sha256"] != baseline["tree_sha256"]:
            continue
        if hashed["files"] != baseline["files"]:
            raise UpstreamError(
                f"aggregate collision or non-canonical baseline ordering for tree {tree_oid}"
            )
        exact_tree_records[tree_oid] = hashed

    exact_commits = [commit for commit in commits if commit_trees.get(commit) in exact_tree_records]
    selected_commit = preferred_commit if preferred_commit in exact_commits else (exact_commits[0] if exact_commits else None)
    exact_matches: list[dict[str, Any]] = []
    for commit in exact_commits:
        match = _commit_metadata(repository, commit)
        match["subtree_tree_oid"] = commit_trees[commit]
        match["preferred_ref_match"] = commit == preferred_commit
        exact_matches.append(match)

    selected = None
    if selected_commit is not None:
        selected = next(match for match in exact_matches if match["commit"] == selected_commit)
        selected = {
            **selected,
            "selection_rule": (
                "preferred-ref-exact-match"
                if selected_commit == preferred_commit
                else "first-topological-exact-match"
            ),
        }

    return {
        "format": "ZaeREo official upstream identity match",
        "schema_version": 1,
        "repository": {
            "origin_url": remote_url or None,
            "preferred_ref": preferred_ref,
            "preferred_commit": preferred_commit or None,
            "subtree": subtree,
        },
        "verification": {
            "verified_on": verified_on,
            "method": "SHA-256 comparison of every baseline path and blob plus the canonical aggregate",
            "match_status": "verified-exact-content-match" if selected is not None else "no-exact-match",
        },
        "baseline": {
            "key": baseline_key,
            "file_count": baseline["file_count"],
            "total_size": baseline["total_size"],
            "tree_sha256": baseline["tree_sha256"],
        },
        "scan": {
            "commit_count": len(commits),
            "commit_count_with_subtree": len(commit_trees),
            "distinct_subtree_tree_count": len(tree_commits),
            "size_candidate_tree_count": size_candidates,
            "exact_tree_count": len(exact_tree_records),
            "exact_commit_count": len(exact_commits),
        },
        "selected_match": selected,
        "exact_matches": exact_matches,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True, help="official Git checkout or bare mirror")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--baseline-key", default="quake2_rerelease")
    parser.add_argument("--subtree", default="rerelease")
    parser.add_argument("--preferred-ref", default="refs/heads/main")
    parser.add_argument(
        "--verified-on",
        help="explicit ISO calendar date for a retained verification record",
    )
    parser.add_argument("--json-output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.verified_on:
            try:
                date.fromisoformat(args.verified_on)
            except ValueError as error:
                raise UpstreamError("--verified-on must be an ISO date (YYYY-MM-DD)") from error
        baseline = _load_baseline(args.baseline.resolve(), args.baseline_key)
        report = identify_upstream(
            args.repository,
            baseline,
            subtree=args.subtree,
            preferred_ref=args.preferred_ref,
            baseline_key=args.baseline_key,
            verified_on=args.verified_on,
        )
        write_text(args.json_output, stable_json_text(report))
    except (OSError, UpstreamError) as error:
        print(f"identify_upstream.py: {error}", file=sys.stderr)
        return 2
    if report["selected_match"] is None:
        print("identify_upstream.py: no exact official subtree matches the baseline", file=sys.stderr)
        return 3
    selected = report["selected_match"]
    print(
        "official upstream exact match: "
        f"commit={selected['commit']} subtree_tree={selected['subtree_tree_oid']} "
        f"baseline_sha256={report['baseline']['tree_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

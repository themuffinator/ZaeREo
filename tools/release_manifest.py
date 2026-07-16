#!/usr/bin/env python3
"""Create or verify the canonical manifest for a staged ZaeREo release."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from audit_common import AuditError, normalize_runtime_path, sha256_file, stable_json_text


SCHEMA_VERSION = 1
DEFAULT_MANIFEST_NAME = "MANIFEST.json"


class ReleaseManifestError(ValueError):
    """Raised when a release stage does not match its declared payload."""


def _payload_files(root: Path, manifest_path: Path) -> list[tuple[str, Path]]:
    resolved_root = root.resolve()
    resolved_manifest = manifest_path.resolve(strict=False)
    records: list[tuple[str, Path]] = []
    seen_case: dict[str, str] = {}
    for candidate in root.rglob("*"):
        if candidate.is_symlink():
            raise ReleaseManifestError(f"Release stage contains a symbolic link: {candidate}")
        if not candidate.is_file():
            continue
        resolved = candidate.resolve()
        if resolved == resolved_manifest:
            continue
        try:
            relative = resolved.relative_to(resolved_root).as_posix()
        except ValueError as exc:
            raise ReleaseManifestError(f"Release file escapes stage: {candidate}") from exc
        relative = normalize_runtime_path(relative, "release path")
        previous = seen_case.get(relative.casefold())
        if previous is not None and previous != relative:
            raise ReleaseManifestError(
                f"Release contains case-colliding paths: {previous!r} and {relative!r}"
            )
        seen_case[relative.casefold()] = relative
        records.append((relative, resolved))
    records.sort(key=lambda record: record[0].encode("utf-8"))
    return records


def create_manifest(
    root: Path,
    manifest_path: Path,
    *,
    version: str,
    commit: str,
    distribution_mode: str,
) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise ReleaseManifestError(f"Release stage is not a directory: {root}")
    files: list[dict[str, object]] = []
    aggregate = hashlib.sha256()
    total_size = 0
    for relative, path in _payload_files(root, manifest_path):
        size = path.stat().st_size
        digest = sha256_file(path)
        record = {"path": relative, "sha256": digest, "size": size}
        files.append(record)
        total_size += size
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(str(size).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\n")
    if not files:
        raise ReleaseManifestError("Release stage contains no payload files")
    return {
        "schema_version": SCHEMA_VERSION,
        "product": "ZaeREo",
        "version": version,
        "source_commit": commit,
        "distribution_mode": distribution_mode,
        "aggregate_algorithm": "sha256(path_utf8 + NUL + decimal_size + NUL + sha256 + LF)",
        "tree_sha256": aggregate.hexdigest(),
        "file_count": len(files),
        "total_size": total_size,
        "files": files,
    }


def verify_manifest(root: Path, manifest_path: Path) -> dict[str, Any]:
    root = root.resolve()
    try:
        declared = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseManifestError(f"Could not read release manifest: {exc}") from exc
    required = {"version", "source_commit", "distribution_mode"}
    if declared.get("schema_version") != SCHEMA_VERSION or not required.issubset(declared):
        raise ReleaseManifestError("Unsupported or incomplete release manifest")
    actual = create_manifest(
        root,
        manifest_path,
        version=str(declared["version"]),
        commit=str(declared["source_commit"]),
        distribution_mode=str(declared["distribution_mode"]),
    )
    if actual != declared:
        declared_by_path = {entry["path"]: entry for entry in declared.get("files", [])}
        actual_by_path = {entry["path"]: entry for entry in actual["files"]}
        missing = sorted(set(declared_by_path) - set(actual_by_path))
        extra = sorted(set(actual_by_path) - set(declared_by_path))
        changed = sorted(
            path
            for path in set(declared_by_path) & set(actual_by_path)
            if declared_by_path[path] != actual_by_path[path]
        )
        raise ReleaseManifestError(
            f"Release stage differs from manifest: missing={missing}, extra={extra}, changed={changed}"
        )
    return actual


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create", help="Write a deterministic manifest")
    create.add_argument("--root", type=Path, required=True)
    create.add_argument("--output", type=Path)
    create.add_argument("--version", required=True)
    create.add_argument("--commit", required=True)
    create.add_argument(
        "--distribution-mode",
        choices=("tools-only", "importer-kit", "asset-full", "local-full"),
        required=True,
    )
    verify = subparsers.add_parser("verify", help="Verify an existing manifest")
    verify.add_argument("--root", type=Path, required=True)
    verify.add_argument("--manifest", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "create":
            output = (args.output or args.root / DEFAULT_MANIFEST_NAME).resolve()
            manifest = create_manifest(
                args.root,
                output,
                version=args.version,
                commit=args.commit,
                distribution_mode=args.distribution_mode,
            )
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(stable_json_text(manifest), encoding="utf-8", newline="\n")
            print(output)
        else:
            manifest_path = (args.manifest or args.root / DEFAULT_MANIFEST_NAME).resolve()
            manifest = verify_manifest(args.root, manifest_path)
            print(f"verified {manifest['file_count']} files; tree_sha256={manifest['tree_sha256']}")
    except (AuditError, OSError, ReleaseManifestError) as exc:
        raise SystemExit(f"error: {exc}") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

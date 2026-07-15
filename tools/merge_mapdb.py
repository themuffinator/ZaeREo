#!/usr/bin/env python3
"""Merge the tracked Zaero mapdb fragment into a hash-pinned local base mapdb."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile
from typing import Any

from audit_common import AuditError, parse_pak


SCHEMA = "zaereo.mapdb-merge/v1"
SCHEMA_VERSION = 1
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def parse_json_bytes(data: bytes, description: str) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"could not parse {description}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{description} must contain a JSON object")
    return value


def parse_json(path: Path) -> dict[str, Any]:
    try:
        return parse_json_bytes(path.read_bytes(), str(path))
    except OSError as exc:
        raise ValueError(f"could not read {path}: {exc}") from exc


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require_file(path: Path, description: str) -> None:
    if not path.is_file():
        raise ValueError(f"{description} does not exist or is not a file: {path}")


def require_directory(path: Path, description: str) -> None:
    if not path.is_dir():
        raise ValueError(f"{description} does not exist or is not a directory: {path}")


def strict_child(root: Path, path: Path, description: str) -> Path:
    root = root.resolve()
    path = path.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{description} must remain below {root}: {path}") from exc
    if path == root:
        raise ValueError(f"{description} must be a file below {root}, not the root itself")
    return path


def object_array(document: dict[str, Any], field: str, description: str) -> list[dict[str, Any]]:
    value = document.get(field)
    if not isinstance(value, list):
        raise ValueError(f"{description}.{field} must be an array")
    if not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{description}.{field} must contain only objects")
    return value


def identity_index(
    records: list[dict[str, Any]],
    key: str,
    description: str,
    *,
    allow_exact_duplicates: bool = False,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        value = record.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"{description} has a missing or invalid {key!r}")
        identity = value.casefold()
        if identity in result:
            prior_value = result[identity][key]
            if not allow_exact_duplicates or prior_value != value:
                raise ValueError(f"{description} has duplicate or case-colliding {key!r}: {value}")
            continue
        result[identity] = record
    return result


def referenced_runtime_paths(bsp: str) -> list[str]:
    if not bsp:
        raise ValueError("map record has an empty bsp value")
    parts = bsp.removeprefix("*").split("+")
    if not parts or any(not part for part in parts):
        raise ValueError(f"malformed map start chain: {bsp!r}")
    paths: list[str] = []
    for part in parts:
        if "/" in part or "\\" in part or part in {".", ".."}:
            raise ValueError(f"unsafe mapdb path segment: {part!r}")
        suffix = Path(part).suffix.casefold()
        if suffix == ".cin":
            paths.append(f"video/{part}")
        elif suffix:
            raise ValueError(f"unsupported mapdb media segment: {part!r}")
        else:
            paths.append(f"maps/{part}.bsp")
    return paths


def validate_fragment_media(records: list[dict[str, Any]], content_root: Path) -> None:
    for record in records:
        bsp = record.get("bsp")
        if not isinstance(bsp, str):
            raise ValueError("Zaero map record must have a string bsp value")
        for relative in referenced_runtime_paths(bsp):
            candidate = strict_child(content_root, content_root / relative, "Zaero mapdb media path")
            if not candidate.is_file():
                raise ValueError(f"Zaero mapdb references missing imported runtime content: {relative}")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as temporary:
        temporary.write(data)
        temporary_path = Path(temporary.name)
    try:
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def read_base_pak_member(pak_path: Path, member: str) -> tuple[bytes, str, str]:
    if not member or member.startswith(("/", "\\")) or "\\" in member or ".." in member.split("/"):
        raise ValueError(f"unsafe --base-member: {member!r}")
    try:
        archive = parse_pak(pak_path, label="base mapdb PAK")
    except AuditError as exc:
        raise ValueError(str(exc)) from exc
    matching = [entry for entry in archive.entries if entry.runtime_path.casefold() == member.casefold()]
    if len(matching) != 1:
        raise ValueError(f"base mapdb PAK must contain exactly one {member!r} member")
    entry = matching[0]
    try:
        return archive.read_entry(entry, max_size=16 * 1024 * 1024), archive.sha256, entry.runtime_path
    except AuditError as exc:
        raise ValueError(str(exc)) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    base_input = parser.add_mutually_exclusive_group(required=True)
    base_input.add_argument("--base", type=Path, help="selected full loose Rerelease mapdb.json")
    base_input.add_argument("--base-pak", type=Path, help="selected Rerelease PAK containing mapdb.json")
    parser.add_argument("--base-member", default="mapdb.json", help="mapdb member path when --base-pak is used")
    parser.add_argument("--fragment", default=Path("pack/mapdb.json"), type=Path, help="tracked Zaero-only fragment")
    parser.add_argument("--content-root", required=True, type=Path, help="validated imported Zaero content root")
    parser.add_argument("--expected-base-sha256", required=True, help="pinned SHA-256 of --base")
    parser.add_argument("--data-build", required=True, help="reviewed Rerelease data-build identifier")
    parser.add_argument("--episode-index", required=True, type=int, help="explicit insertion index in base episodes")
    parser.add_argument("--map-index", required=True, type=int, help="explicit insertion index in base maps")
    parser.add_argument("--output", required=True, type=Path, help="generated merged mapdb below --generated-root")
    parser.add_argument("--report", required=True, type=Path, help="generated merge report below --generated-root")
    parser.add_argument("--generated-root", default=Path(".install"), type=Path, help="private generated-output root")
    parser.add_argument("--dry-run", action="store_true", help="validate without writing output or report")
    args = parser.parse_args()

    fragment_path = args.fragment.resolve()
    content_root = args.content_root.resolve()
    generated_root = args.generated_root.resolve()
    output = strict_child(generated_root, args.output.resolve(), "merged mapdb output")
    report_path = strict_child(generated_root, args.report.resolve(), "mapdb merge report")
    if output == report_path:
        raise ValueError("--output and --report must be different files")
    require_file(fragment_path, "Zaero mapdb fragment")
    require_directory(content_root, "imported Zaero content root")
    if not args.data_build.strip():
        raise ValueError("--data-build must not be empty")
    expected_hash = args.expected_base_sha256.casefold()
    if not SHA256_RE.fullmatch(expected_hash):
        raise ValueError("--expected-base-sha256 must be a lowercase-or-uppercase SHA-256")
    base_container_sha256: str | None
    base_member: str | None
    if args.base is not None:
        base = args.base.resolve()
        require_file(base, "base mapdb")
        base_bytes = base.read_bytes()
        base_description = str(base)
        base_source = "file"
        base_container_sha256 = None
        base_member = None
    else:
        base_pak = args.base_pak.resolve()
        require_file(base_pak, "base mapdb PAK")
        base_bytes, base_container_sha256, base_member = read_base_pak_member(base_pak, args.base_member)
        base_description = f"{base_pak}:{base_member}"
        base_source = "pak-member"
    base_hash = sha256_bytes(base_bytes)
    if base_hash != expected_hash:
        raise ValueError(f"base mapdb SHA-256 mismatch: expected {expected_hash}, got {base_hash}")

    base_document = parse_json_bytes(base_bytes, base_description)
    fragment = parse_json(fragment_path)
    base_episodes = object_array(base_document, "episodes", "base mapdb")
    base_maps = object_array(base_document, "maps", "base mapdb")
    fragment_episodes = object_array(fragment, "episodes", "Zaero fragment")
    fragment_maps = object_array(fragment, "maps", "Zaero fragment")
    if not fragment_episodes or not fragment_maps:
        raise ValueError("Zaero fragment must contain episodes and maps")
    if not 0 <= args.episode_index <= len(base_episodes):
        raise ValueError(f"--episode-index must be in [0, {len(base_episodes)}]")
    if not 0 <= args.map_index <= len(base_maps):
        raise ValueError(f"--map-index must be in [0, {len(base_maps)}]")

    base_episode_ids = identity_index(base_episodes, "id", "base mapdb episodes")
    fragment_episode_ids = identity_index(fragment_episodes, "id", "Zaero fragment episodes")
    base_map_ids = identity_index(
        base_maps,
        "bsp",
        "base mapdb maps",
        allow_exact_duplicates=True,
    )
    fragment_map_ids = identity_index(fragment_maps, "bsp", "Zaero fragment maps")
    overlaps = sorted(set(base_episode_ids) & set(fragment_episode_ids))
    if overlaps:
        raise ValueError(f"Zaero fragment conflicts with existing episode IDs: {', '.join(overlaps)}")
    overlaps = sorted(set(base_map_ids) & set(fragment_map_ids))
    if overlaps:
        raise ValueError(f"Zaero fragment conflicts with existing map ownership: {', '.join(overlaps)}")
    for record in fragment_maps:
        episode = record.get("episode")
        if episode is not None and (not isinstance(episode, str) or episode.casefold() not in fragment_episode_ids):
            raise ValueError(f"Zaero map {record.get('bsp')!r} references an unknown fragment episode {episode!r}")
    validate_fragment_media(fragment_maps, content_root)

    merged = copy.deepcopy(base_document)
    merged["episodes"] = (
        copy.deepcopy(base_episodes[:args.episode_index])
        + copy.deepcopy(fragment_episodes)
        + copy.deepcopy(base_episodes[args.episode_index:])
    )
    merged["maps"] = (
        copy.deepcopy(base_maps[:args.map_index])
        + copy.deepcopy(fragment_maps)
        + copy.deepcopy(base_maps[args.map_index:])
    )

    reconstructed = copy.deepcopy(merged)
    reconstructed["episodes"] = [
        record for record in reconstructed["episodes"] if record["id"].casefold() not in fragment_episode_ids
    ]
    reconstructed["maps"] = [
        record for record in reconstructed["maps"] if record["bsp"].casefold() not in fragment_map_ids
    ]
    inverse_reconstructs_base = canonical_json(reconstructed) == canonical_json(base_document)
    if not inverse_reconstructs_base:
        raise ValueError("removing merged Zaero records did not reconstruct the canonical base mapdb")

    merged_bytes = canonical_json(merged)
    report = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "base_mapdb_sha256": base_hash,
        "base_source": base_source,
        "base_container_sha256": base_container_sha256,
        "base_member": base_member,
        "fragment_sha256": sha256(fragment_path),
        "data_build": args.data_build,
        "episode_insert_index": args.episode_index,
        "map_insert_index": args.map_index,
        "added_episode_ids": [record["id"] for record in fragment_episodes],
        "added_map_bsps": [record["bsp"] for record in fragment_maps],
        "merged_sha256": hashlib.sha256(merged_bytes).hexdigest(),
        "inverse_reconstructs_base": inverse_reconstructs_base,
        "publication_status": "private-local-only",
    }
    if args.dry_run:
        print(f"Validated private mapdb merge: {len(fragment_episodes)} episodes, {len(fragment_maps)} maps")
        return 0

    atomic_write(output, merged_bytes)
    atomic_write(report_path, canonical_json(report))
    print(f"Merged private mapdb: {len(fragment_episodes)} episodes, {len(fragment_maps)} maps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

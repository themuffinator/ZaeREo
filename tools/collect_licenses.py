#!/usr/bin/env python3
"""Validate the pinned vcpkg dependency closure and harvest exact license bytes."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Sequence

from audit_common import AuditError, normalize_runtime_path, stable_json_text
from validate_distribution_policy import (
    PolicyError,
    check_schema,
    validate_schema_instance,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "docs" / "provenance" / "dependency-policy.json"


class LicenseCollectionError(AuditError):
    """Raised when dependency identity or license evidence is incomplete."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LicenseCollectionError(f"invalid {label} {path}: {error}") from error
    if not isinstance(value, dict):
        raise LicenseCollectionError(f"{label} must contain a JSON object: {path}")
    return value


def _safe_repository_file(repository_root: Path, relative: str, label: str) -> Path:
    normalized = normalize_runtime_path(relative, label)
    root = repository_root.resolve()
    candidate = (root / Path(normalized)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise LicenseCollectionError(f"{label} escapes the repository: {relative}") from error
    if candidate.is_symlink() or not candidate.is_file():
        raise LicenseCollectionError(f"{label} is missing or not a regular file: {relative}")
    return candidate


def load_dependency_policy(
    policy_path: Path = DEFAULT_POLICY,
    *,
    repository_root: Path | None = None,
) -> tuple[dict[str, Any], Path]:
    policy_path = policy_path.resolve()
    root = repository_root.resolve() if repository_root else policy_path.parents[2]
    policy = _read_json(policy_path, "dependency policy")
    schema_relative = policy.get("$schema")
    if not isinstance(schema_relative, str):
        raise LicenseCollectionError("dependency policy has no $schema")
    schema_path = (policy_path.parent / schema_relative).resolve()
    schema = _read_json(schema_path, "dependency policy schema")
    try:
        check_schema(schema, "dependency policy schema")
        validate_schema_instance(policy, schema, "dependency policy")
    except PolicyError as error:
        raise LicenseCollectionError(str(error)) from error

    spdx_schema = _safe_repository_file(root, policy["spdx"]["schema_path"], "SPDX schema")
    actual_schema_hash = sha256_bytes(spdx_schema.read_bytes())
    if actual_schema_hash != policy["spdx"]["schema_sha256"]:
        raise LicenseCollectionError(
            f"SPDX schema hash mismatch: expected {policy['spdx']['schema_sha256']}, got {actual_schema_hash}"
        )
    try:
        spdx_document = json.loads(spdx_schema.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise LicenseCollectionError(f"pinned SPDX schema is invalid JSON: {error}") from error
    if spdx_document.get("$id") != "http://spdx.org/rdf/terms/2.3" or spdx_document.get("title") != "SPDX 2.3":
        raise LicenseCollectionError("pinned SPDX schema does not identify SPDX 2.3")

    manifest_path = _safe_repository_file(root, policy["vcpkg"]["manifest"], "vcpkg manifest")
    manifest = _read_json(manifest_path, "vcpkg manifest")
    if manifest.get("builtin-baseline") != policy["vcpkg"]["builtin_baseline"]:
        raise LicenseCollectionError("vcpkg manifest baseline differs from dependency policy")
    direct_dependencies: set[str] = set()
    for dependency in manifest.get("dependencies", []):
        name = dependency if isinstance(dependency, str) else dependency.get("name") if isinstance(dependency, dict) else None
        if not isinstance(name, str) or not name:
            raise LicenseCollectionError("vcpkg manifest contains an invalid dependency")
        direct_dependencies.add(name)
    policy_direct = {package["name"] for package in policy["packages"] if package["direct"]}
    if direct_dependencies != policy_direct:
        raise LicenseCollectionError(
            f"direct dependency mismatch: manifest={sorted(direct_dependencies)}, policy={sorted(policy_direct)}"
        )

    package_keys: set[tuple[str, str]] = set()
    spdx_ids: set[str] = {policy["project"]["spdx_id"]}
    license_names: set[str] = set()
    for package in policy["packages"]:
        key = (package["name"], package["architecture"])
        if key in package_keys:
            raise LicenseCollectionError(f"duplicate dependency policy package: {key}")
        package_keys.add(key)
        if package["spdx_id"] in spdx_ids:
            raise LicenseCollectionError(f"duplicate SPDX identifier: {package['spdx_id']}")
        spdx_ids.add(package["spdx_id"])
        folded_license = package["license_filename"].casefold()
        if folded_license in license_names:
            raise LicenseCollectionError(
                f"duplicate/case-colliding license filename: {package['license_filename']}"
            )
        license_names.add(folded_license)
        normalized = normalize_runtime_path(package["copyright_path"], "copyright path")
        if normalized != package["copyright_path"]:
            raise LicenseCollectionError(f"copyright path is not canonical: {package['copyright_path']}")
    for component in policy["toolchain_components"]:
        if component["spdx_id"] in spdx_ids:
            raise LicenseCollectionError(f"duplicate SPDX identifier: {component['spdx_id']}")
        spdx_ids.add(component["spdx_id"])

    upstream_match_path = root / "docs" / "provenance" / "upstream-match.json"
    if upstream_match_path.is_file():
        upstream_match = _read_json(upstream_match_path, "upstream match")
        selected = upstream_match.get("selected_match") or {}
        if selected.get("commit") != policy["project"]["official_commit"]:
            raise LicenseCollectionError("dependency policy project commit differs from upstream match")
    return policy, root


def parse_vcpkg_status(text: str) -> list[dict[str, str]]:
    paragraphs: list[dict[str, str]] = []
    current: dict[str, str] = {}
    previous_key: str | None = None
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line:
            if current:
                paragraphs.append(current)
                current = {}
                previous_key = None
            continue
        if line[0].isspace():
            if previous_key is None:
                raise LicenseCollectionError(f"vcpkg status line {line_number} has an orphan continuation")
            current[previous_key] += "\n" + line.strip()
            continue
        if ":" not in line:
            raise LicenseCollectionError(f"vcpkg status line {line_number} has no field separator")
        key, value = line.split(":", 1)
        if key in current:
            raise LicenseCollectionError(f"vcpkg status paragraph repeats field {key!r}")
        current[key] = value.strip()
        previous_key = key
    if current:
        paragraphs.append(current)
    return paragraphs


def _created_from_epoch(epoch: int) -> str:
    if epoch < 0:
        raise LicenseCollectionError("source date epoch must be non-negative")
    try:
        return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (OverflowError, OSError, ValueError) as error:
        raise LicenseCollectionError(f"invalid source date epoch: {epoch}") from error


def collect_license_bundle(
    policy: dict[str, Any],
    repository_root: Path,
    installed_root: Path,
    output_root: Path,
    *,
    source_date_epoch: int,
) -> dict[str, Any]:
    installed_root = installed_root.resolve()
    if installed_root.is_symlink() or not installed_root.is_dir():
        raise LicenseCollectionError(f"vcpkg installed root is missing or unsafe: {installed_root}")
    status_relative = normalize_runtime_path(policy["vcpkg"]["status_file"], "vcpkg status path")
    status_path = (installed_root / Path(status_relative)).resolve()
    try:
        status_path.relative_to(installed_root)
    except ValueError as error:
        raise LicenseCollectionError("vcpkg status path escapes installed root") from error
    if status_path.is_symlink() or not status_path.is_file():
        raise LicenseCollectionError(f"vcpkg status file is missing: {status_path}")

    installed_records = parse_vcpkg_status(status_path.read_text(encoding="utf-8"))
    installed: dict[tuple[str, str], dict[str, str]] = {}
    for record in installed_records:
        required = ("Package", "Version", "Architecture", "Status", "Abi")
        missing = [name for name in required if not record.get(name)]
        if missing:
            raise LicenseCollectionError(f"vcpkg status record is missing: {', '.join(missing)}")
        key = (record["Package"], record["Architecture"])
        if key in installed:
            raise LicenseCollectionError(f"duplicate installed package: {key}")
        if record["Status"] != "install ok installed":
            raise LicenseCollectionError(f"package is not fully installed: {key}")
        installed[key] = record

    expected = {(package["name"], package["architecture"]): package for package in policy["packages"]}
    unknown = sorted(set(installed) - set(expected))
    missing = sorted(set(expected) - set(installed))
    if unknown or missing:
        raise LicenseCollectionError(
            f"vcpkg closure differs from policy; unknown={unknown}, missing={missing}"
        )

    output_root = output_root.resolve()
    if output_root.exists():
        if output_root.is_symlink() or not output_root.is_dir():
            raise LicenseCollectionError(f"license output is not a safe directory: {output_root}")
        if any(output_root.iterdir()):
            raise LicenseCollectionError(f"license output must be absent or empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    licenses_root = output_root / "licenses"
    licenses_root.mkdir()

    package_records: list[dict[str, Any]] = []
    for key in sorted(expected):
        package = expected[key]
        status = installed[key]
        if status["Version"] != package["version"]:
            raise LicenseCollectionError(
                f"version mismatch for {key}: expected {package['version']}, got {status['Version']}"
            )
        copyright_relative = normalize_runtime_path(package["copyright_path"], "copyright path")
        source_path = (installed_root / Path(copyright_relative)).resolve()
        try:
            source_path.relative_to(installed_root)
        except ValueError as error:
            raise LicenseCollectionError(f"copyright path escapes installed root: {copyright_relative}") from error
        if source_path.is_symlink() or not source_path.is_file():
            raise LicenseCollectionError(f"copyright file is missing or unsafe: {copyright_relative}")
        data = source_path.read_bytes()
        digest = sha256_bytes(data)
        if digest != package["copyright_sha256"]:
            raise LicenseCollectionError(
                f"copyright hash mismatch for {key}: expected {package['copyright_sha256']}, got {digest}"
            )
        destination = licenses_root / package["license_filename"]
        destination.write_bytes(data)
        package_records.append(
            {
                "abi": status["Abi"],
                "architecture": package["architecture"],
                "direct": package["direct"],
                "license_concluded": package["license_concluded"],
                "license_declared": package["license_declared"],
                "license_file": {
                    "path": f"licenses/{package['license_filename']}",
                    "sha256": digest,
                    "size": len(data),
                },
                "name": package["name"],
                "role": package["role"],
                "spdx_id": package["spdx_id"],
                "version": package["version"],
            }
        )

    manifest = {
        "format": "ZaeREo dependency license bundle",
        "schema_version": 1,
        "policy_id": policy["policy_id"],
        "policy_revision": policy["revision"],
        "source_date_epoch": source_date_epoch,
        "created": _created_from_epoch(source_date_epoch),
        "vcpkg_builtin_baseline": policy["vcpkg"]["builtin_baseline"],
        "packages": package_records,
    }
    manifest_path = output_root / "LICENSE-MANIFEST.json"
    manifest_path.write_text(stable_json_text(manifest), encoding="utf-8", newline="\n")
    return manifest


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--installed-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-date-epoch", type=int, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        policy, root = load_dependency_policy(args.policy)
        manifest = collect_license_bundle(
            policy,
            root,
            args.installed_root,
            args.output,
            source_date_epoch=args.source_date_epoch,
        )
    except (OSError, LicenseCollectionError) as error:
        print(f"collect_licenses.py: {error}", file=sys.stderr)
        return 2
    print(
        f"license bundle valid: packages={len(manifest['packages'])} "
        f"output={args.output.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

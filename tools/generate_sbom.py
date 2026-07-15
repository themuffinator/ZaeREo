#!/usr/bin/env python3
"""Generate a deterministic SPDX 2.3 substrate SBOM from verified license evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Sequence

from audit_common import AuditError, normalize_runtime_path, stable_json_text
from collect_licenses import (
    DEFAULT_POLICY,
    LicenseCollectionError,
    load_dependency_policy,
)


class SbomError(AuditError):
    """Raised when SBOM inputs disagree or the generated SPDX profile is invalid."""


SPDX_ID_RE = re.compile(r"^SPDXRef-[A-Za-z0-9.-]+$")


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SbomError(f"invalid {label} {path}: {error}") from error
    if not isinstance(value, dict):
        raise SbomError(f"{label} must contain a JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def validate_license_manifest(
    policy: dict[str, Any],
    manifest_path: Path,
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = _read_json(manifest_path, "license manifest")
    expected_header = {
        "format": "ZaeREo dependency license bundle",
        "schema_version": 1,
        "policy_id": policy["policy_id"],
        "policy_revision": policy["revision"],
        "vcpkg_builtin_baseline": policy["vcpkg"]["builtin_baseline"],
    }
    for key, expected in expected_header.items():
        if manifest.get(key) != expected:
            raise SbomError(f"license manifest {key} differs from dependency policy")
    if not isinstance(manifest.get("source_date_epoch"), int) or manifest["source_date_epoch"] < 0:
        raise SbomError("license manifest source_date_epoch is invalid")
    if not isinstance(manifest.get("created"), str) or not manifest["created"].endswith("Z"):
        raise SbomError("license manifest created timestamp is invalid")

    policy_packages = {
        (package["name"], package["architecture"]): package
        for package in policy["packages"]
    }
    records = manifest.get("packages")
    if not isinstance(records, list):
        raise SbomError("license manifest packages must be an array")
    record_packages: dict[tuple[str, str], dict[str, Any]] = {}
    root = manifest_path.parent.resolve()
    for record in records:
        if not isinstance(record, dict):
            raise SbomError("license manifest package record is not an object")
        key = (record.get("name"), record.get("architecture"))
        if key in record_packages:
            raise SbomError(f"license manifest repeats package {key}")
        record_packages[key] = record
        package = policy_packages.get(key)
        if package is None:
            raise SbomError(f"license manifest contains unknown package {key}")
        for field in (
            "version",
            "role",
            "direct",
            "spdx_id",
            "license_concluded",
            "license_declared",
        ):
            if record.get(field) != package[field]:
                raise SbomError(f"license manifest {key} field {field} differs from policy")
        abi = record.get("abi")
        if not isinstance(abi, str) or not re.fullmatch(r"[0-9a-f]{64}", abi):
            raise SbomError(f"license manifest {key} has invalid ABI")
        license_file = record.get("license_file")
        if not isinstance(license_file, dict):
            raise SbomError(f"license manifest {key} has no license file record")
        relative = normalize_runtime_path(license_file.get("path", ""), "license bundle path")
        if relative != f"licenses/{package['license_filename']}":
            raise SbomError(f"license manifest {key} uses the wrong license path")
        path = (root / Path(relative)).resolve()
        try:
            path.relative_to(root)
        except ValueError as error:
            raise SbomError(f"license bundle path escapes its root: {relative}") from error
        if path.is_symlink() or not path.is_file():
            raise SbomError(f"license bundle file is missing or unsafe: {relative}")
        if path.stat().st_size != license_file.get("size") or _sha256(path) != license_file.get("sha256"):
            raise SbomError(f"license bundle file identity mismatch: {relative}")
        if license_file["sha256"] != package["copyright_sha256"]:
            raise SbomError(f"license bundle hash differs from policy: {relative}")
    if set(record_packages) != set(policy_packages):
        raise SbomError(
            f"license manifest package closure differs from policy; "
            f"missing={sorted(set(policy_packages) - set(record_packages))}"
        )
    return manifest


def build_sbom(
    policy: dict[str, Any],
    license_manifest: dict[str, Any],
    *,
    document_name: str,
    document_namespace: str,
) -> dict[str, Any]:
    if not document_name.strip():
        raise SbomError("document name must not be empty")
    if not re.fullmatch(r"https://[^\s]+", document_namespace):
        raise SbomError("document namespace must be a stable HTTPS URI")

    project = policy["project"]
    packages: list[dict[str, Any]] = [
        {
            "SPDXID": project["spdx_id"],
            "name": project["name"],
            "versionInfo": project["official_commit"],
            "downloadLocation": f"{project['official_repository']}@{project['official_commit']}",
            "filesAnalyzed": False,
            "licenseConcluded": project["license_concluded"],
            "licenseDeclared": project["license_declared"],
            "copyrightText": project["copyright_text"],
            "primaryPackagePurpose": "SOURCE",
        }
    ]
    relationships: list[dict[str, str]] = [
        {
            "spdxElementId": "SPDXRef-DOCUMENT",
            "relationshipType": "DESCRIBES",
            "relatedSpdxElement": project["spdx_id"],
        }
    ]
    manifest_records = {
        (record["name"], record["architecture"]): record
        for record in license_manifest["packages"]
    }
    for dependency in sorted(policy["packages"], key=lambda item: (item["name"], item["architecture"])):
        evidence = manifest_records[(dependency["name"], dependency["architecture"])]
        packages.append(
            {
                "SPDXID": dependency["spdx_id"],
                "name": dependency["name"],
                "versionInfo": dependency["version"],
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": dependency["license_concluded"],
                "licenseDeclared": dependency["license_declared"],
                "copyrightText": "NOASSERTION",
                "primaryPackagePurpose": (
                    "LIBRARY" if dependency["role"] == "runtime-static" else "OTHER"
                ),
                "comment": (
                    f"vcpkg architecture={dependency['architecture']}; "
                    f"abi={evidence['abi']}; license evidence={evidence['license_file']['path']}"
                ),
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": f"pkg:vcpkg/{dependency['name']}@{dependency['version']}",
                    }
                ],
            }
        )
        relationships.append(
            {
                "spdxElementId": dependency["spdx_id"],
                "relationshipType": (
                    "STATIC_LINK" if dependency["role"] == "runtime-static" else "BUILD_DEPENDENCY_OF"
                ),
                "relatedSpdxElement": project["spdx_id"],
            }
        )

    for component in sorted(policy["toolchain_components"], key=lambda item: item["spdx_id"]):
        packages.append(
            {
                "SPDXID": component["spdx_id"],
                "name": component["name"],
                "versionInfo": component["version"],
                "supplier": component["supplier"],
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": component["license_concluded"],
                "licenseDeclared": component["license_declared"],
                "copyrightText": "NOASSERTION",
                "primaryPackagePurpose": (
                    "LIBRARY" if component["role"] == "runtime-library" else "OTHER"
                ),
                "comment": (
                    f"linkage={component['linkage']}; scope_status={component['scope_status']}; "
                    "NOASSERTION is an explicit unresolved distribution-scope record."
                ),
            }
        )
        relationships.append(
            {
                "spdxElementId": component["spdx_id"],
                "relationshipType": (
                    "STATIC_LINK" if component["linkage"] == "static" else "BUILD_DEPENDENCY_OF"
                ),
                "relatedSpdxElement": project["spdx_id"],
            }
        )

    packages.sort(key=lambda package: package["SPDXID"])
    relationships.sort(
        key=lambda relationship: (
            relationship["spdxElementId"],
            relationship["relationshipType"],
            relationship["relatedSpdxElement"],
        )
    )
    sbom = {
        "SPDXID": "SPDXRef-DOCUMENT",
        "spdxVersion": policy["spdx"]["version"],
        "dataLicense": policy["spdx"]["data_license"],
        "name": document_name,
        "documentNamespace": document_namespace,
        "creationInfo": {
            "created": license_manifest["created"],
            "creators": [
                f"Tool: {policy['spdx']['generator']}-{policy['spdx']['generator_version']}"
            ],
        },
        "packages": packages,
        "relationships": relationships,
        "hasExtractedLicensingInfos": [
            {
                "licenseId": "LicenseRef-Public-Domain",
                "name": "Public-domain dedication alternative recorded by JsonCpp",
                "extractedText": (
                    "The exact JsonCpp copyright file in the adjacent license bundle records "
                    "the public-domain dedication and MIT alternative."
                ),
            }
        ],
    }
    validate_sbom_profile(sbom, policy)
    return sbom


def validate_sbom_profile(sbom: dict[str, Any], policy: dict[str, Any]) -> None:
    if sbom.get("SPDXID") != "SPDXRef-DOCUMENT":
        raise SbomError("SBOM document SPDXID is invalid")
    if sbom.get("spdxVersion") != "SPDX-2.3" or sbom.get("dataLicense") != "CC0-1.0":
        raise SbomError("SBOM does not use the pinned SPDX 2.3 document profile")
    packages = sbom.get("packages")
    relationships = sbom.get("relationships")
    if not isinstance(packages, list) or not packages or not isinstance(relationships, list):
        raise SbomError("SBOM packages/relationships are incomplete")
    identifiers = [package.get("SPDXID") for package in packages]
    if any(not isinstance(identifier, str) or not SPDX_ID_RE.fullmatch(identifier) for identifier in identifiers):
        raise SbomError("SBOM contains an invalid package SPDXID")
    if len(identifiers) != len(set(identifiers)):
        raise SbomError("SBOM contains duplicate package SPDXIDs")
    expected = {
        policy["project"]["spdx_id"],
        *(package["spdx_id"] for package in policy["packages"]),
        *(component["spdx_id"] for component in policy["toolchain_components"]),
    }
    if set(identifiers) != expected:
        raise SbomError("SBOM package closure differs from dependency policy")
    for relationship in relationships:
        if relationship.get("spdxElementId") not in expected | {"SPDXRef-DOCUMENT"}:
            raise SbomError("SBOM relationship has an unknown source SPDXID")
        if relationship.get("relatedSpdxElement") not in expected:
            raise SbomError("SBOM relationship has an unknown target SPDXID")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--license-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--document-name", default="ZaeREo Quake II Rerelease substrate SBOM")
    parser.add_argument("--document-namespace", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        policy, _ = load_dependency_policy(args.policy)
        manifest = validate_license_manifest(policy, args.license_manifest)
        sbom = build_sbom(
            policy,
            manifest,
            document_name=args.document_name,
            document_namespace=args.document_namespace,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(stable_json_text(sbom), encoding="utf-8", newline="\n")
    except (OSError, LicenseCollectionError, SbomError) as error:
        print(f"generate_sbom.py: {error}", file=sys.stderr)
        return 2
    print(f"SPDX SBOM valid: packages={len(sbom['packages'])} output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

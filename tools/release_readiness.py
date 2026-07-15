#!/usr/bin/env python3
"""Generate or validate fail-closed ZaeREo release-readiness evidence.

This tool performs no packaging, tagging, upload, or other remote action.  A
blocked record is useful evidence: it makes the current policy and missing
release-candidate proof explicit instead of leaving a publisher to infer it.
Only future evidence collectors may add gates; no command-line override can
turn a blocked policy or missing proof into a ready record.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence

from validate_distribution_policy import (
    PolicyError,
    check_schema,
    load_policy,
    load_schema,
    validate_policy_document,
    validate_schema_instance,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ID = "zaereo.release-readiness/v1"
SCHEMA_VERSION = 1
DEFAULT_POLICY_RELATIVE = Path("docs/provenance/distribution-policy.json")
DEFAULT_SCHEMA_RELATIVE = Path("docs/provenance/schemas/release-readiness.schema.json")
INPUTS: tuple[tuple[str, str], ...] = (
    ("version", "VERSION"),
    ("baseline-lock", "docs/provenance/baselines.json"),
    ("upstream-match", "docs/provenance/upstream-match.json"),
    ("distribution-policy", "docs/provenance/distribution-policy.json"),
    ("asset-inventory", "docs/audits/assets.json"),
    ("source-delta", "docs/audits/source-delta.json"),
    ("upstream-integration", "docs/audits/upstream-integration.json"),
    ("release-surfaces", "docs/audits/release-surfaces.json"),
    ("runtime-scenarios", "tools/runtime-scenarios.json"),
    ("runtime-scenarios-dm", "tools/runtime-scenarios-dm.json"),
    ("runtime-scenarios-dm-fixtures", "tools/runtime-scenarios-dm-fixtures.json"),
    ("feature-matrix", "docs/compatibility/feature-matrix.md"),
    ("entity-matrix", "docs/compatibility/entity-matrix.md"),
    ("map-matrix", "docs/compatibility/map-matrix.md"),
    ("quirks", "docs/compatibility/quirks.md"),
    ("decisions", "docs/compatibility/decisions.md"),
)
STATUS_VALUES = frozenset({"passed", "failed", "missing", "not-applicable", "blocked"})


class ReadinessError(ValueError):
    """Raised for malformed readiness input or an unsafe request."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path, description: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ReadinessError(f"could not read {description} {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ReadinessError(
            f"invalid JSON in {description} {path}:{exc.lineno}:{exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(value, dict):
        raise ReadinessError(f"{description} {path} must contain a JSON object")
    return value


def strict_child(root: Path, candidate: Path, description: str) -> Path:
    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve()
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ReadinessError(
            f"{description} must remain below {resolved_root}: {resolved_candidate}"
        ) from exc
    if resolved_candidate == resolved_root:
        raise ReadinessError(f"{description} must name a file below {resolved_root}")
    return resolved_candidate


def relative_input_path(workspace: Path, path: Path, description: str) -> str:
    try:
        return path.resolve().relative_to(workspace.resolve()).as_posix()
    except ValueError as exc:
        raise ReadinessError(f"{description} must remain below workspace {workspace}: {path}") from exc


def git_state(workspace: Path) -> dict[str, Any]:
    try:
        commit_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace,
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
        status_result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=normal"],
            cwd=workspace,
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"git_available": False, "commit": "unavailable", "working_tree_clean": False}

    commit = commit_result.stdout.strip().lower()
    if commit_result.returncode != 0 or len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        return {"git_available": False, "commit": "unavailable", "working_tree_clean": False}
    if status_result.returncode != 0:
        return {"git_available": True, "commit": commit, "working_tree_clean": False}
    return {
        "git_available": True,
        "commit": commit,
        "working_tree_clean": not bool(status_result.stdout.strip()),
    }


def load_validated_policy(policy_path: Path, workspace: Path) -> dict[str, Any]:
    policy_schema_path = policy_path.parent / "schemas" / "distribution-policy.schema.json"
    asset_schema_path = policy_path.parent / "schemas" / "asset-policy.schema.json"
    try:
        policy = load_policy(policy_path)
        policy_schema = load_schema(policy_schema_path)
        asset_schema = load_schema(asset_schema_path)
        check_schema(asset_schema, "asset policy schema")
        validate_policy_document(policy, policy_schema, repository_root=workspace.resolve())
    except PolicyError as exc:
        raise ReadinessError(f"distribution policy is invalid: {exc}") from exc
    return policy


def required_inputs(workspace: Path) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for identifier, relative in INPUTS:
        path = strict_child(workspace, workspace / relative, f"readiness input {identifier}")
        if not path.is_file():
            raise ReadinessError(f"required readiness input is missing: {relative}")
        result.append({"id": identifier, "path": relative, "sha256": sha256_file(path)})
    return result


def gate(identifier: str, required: bool, status: str, detail: str) -> dict[str, Any]:
    if status not in STATUS_VALUES:
        raise ValueError(f"unsupported readiness gate status: {status}")
    return {"id": identifier, "required": required, "status": status, "detail": detail}


def non_waivable_status(
    identifier: str,
    profile: str,
    source: Mapping[str, Any],
    mode: Mapping[str, Any],
    channel: str,
) -> tuple[str, str]:
    """Return today's evidence state without inferring any unavailable proof."""

    if identifier == "distribution-mode-provenance-channel":
        allowed = channel in mode["permitted_channel_ids"]
        eligible = bool(mode["publication_permitted"])
        if allowed and eligible:
            return "missing", "Selected mode/channel still lacks the complete exact-component and artifact evidence."
        return "blocked", "The selected distribution mode or channel is not policy-permitted."
    if identifier == "local-full-permanent-private":
        if mode["id"] == "local-full":
            return "passed", "The selected local-full mode remains private-local-only and non-publishable."
        return "missing", "No provenance record proves the candidate is independent of local-full input lineage."
    if identifier == "clean-exact-source-commit":
        if source["git_available"] and source["working_tree_clean"]:
            return "missing", "The working tree is clean but no exact reviewed distribution-root record exists."
        return "failed", "The current workspace is unavailable to Git or has uncommitted/untracked bytes."
    if identifier == "tag-version-identity":
        return "missing", "No exact tag, package metadata, manifest, and release-note identity record exists."
    if identifier == "archive-checksum-file-allowlist":
        return "missing", "No reviewed exact archive/member manifest and checksum record exists."
    if identifier == "critical-security-results":
        return "missing", "No exact-candidate security and path-safety result set was supplied."
    if identifier == "corresponding-source-license":
        if profile in {"playable-candidate", "playable-stable"}:
            return "missing", "No exact DLL/source/notices license evidence exists."
        return "not-applicable", "The selected profile does not ship a playable DLL candidate."
    if identifier == "required-compatibility-gates":
        if profile in {"playable-candidate", "playable-stable"}:
            return "missing", "No exact-candidate compatibility, map, save, multiplayer, and live-run closure exists."
        return "not-applicable", "Gameplay compatibility closure is not a tools-only readiness gate."
    return "missing", "No evaluator is implemented for this policy rule."


def build_record(
    workspace: Path,
    policy_path: Path,
    mode_id: str,
    channel_id: str,
    profile: str,
) -> dict[str, Any]:
    policy = load_validated_policy(policy_path, workspace)
    modes = {entry["id"]: entry for entry in policy["modes"]}
    channels = {entry["id"]: entry for entry in policy["channels"]}
    if mode_id not in modes:
        raise ReadinessError(f"unknown distribution mode: {mode_id}")
    if channel_id not in channels:
        raise ReadinessError(f"unknown distribution channel: {channel_id}")
    mode = modes[mode_id]
    if profile not in mode["readiness_profiles"]:
        raise ReadinessError(f"profile {profile!r} is not allowed for distribution mode {mode_id!r}")

    source = git_state(workspace)
    version_path = workspace / "VERSION"
    version = version_path.read_text(encoding="utf-8").strip()
    if not version:
        raise ReadinessError("VERSION must not be empty")
    gates = [
        gate("policy-valid", True, "passed", "The selected distribution policy and schemas validated."),
        gate("mode-profile", True, "passed", "The selected mode/profile pair is policy-defined."),
        gate(
            "mode-publication-permitted",
            True,
            "passed" if mode["publication_permitted"] else "blocked",
            "The selected mode is policy-permitted for publication."
            if mode["publication_permitted"]
            else "The selected mode is not policy-permitted for publication.",
        ),
        gate(
            "mode-channel-permitted",
            True,
            "passed" if channel_id in mode["permitted_channel_ids"] else "blocked",
            "The selected channel is permitted for this mode."
            if channel_id in mode["permitted_channel_ids"]
            else "The selected channel is not permitted for this mode.",
        ),
        gate(
            "public-distribution-enabled",
            True,
            "passed" if policy["public_distribution_enabled"] else "blocked",
            "The distribution policy enables public distribution."
            if policy["public_distribution_enabled"]
            else "The distribution policy currently enables no public distribution mode.",
        ),
        gate(
            "clean-workspace",
            True,
            "passed" if source["git_available"] and source["working_tree_clean"] else "failed",
            "Git reports a clean workspace."
            if source["git_available"] and source["working_tree_clean"]
            else "Git is unavailable or the workspace contains uncommitted/untracked bytes.",
        ),
        gate("release-identity", True, "missing", "No exact tag/version/package/manifest/release-note identity evidence was supplied."),
        gate("artifact-manifests", True, "missing", "No exact package, checksum, SBOM, source-bundle, or per-file allowlist evidence was supplied."),
        gate("candidate-build-test-results", True, "missing", "No exact-candidate Debug/Release/export/test result set was supplied."),
    ]
    if profile in {"playable-candidate", "playable-stable"}:
        gates.extend(
            [
                gate("corresponding-source-license", True, "missing", "No exact DLL/source/notices license evidence was supplied."),
                gate("compatibility-map-live-evidence", True, "missing", "No exact feature/entity/quirk/map/mode/save/live evidence closure was supplied."),
            ]
        )
    elif profile == "local-full-private":
        gates.append(
            gate("private-import-ownership", True, "missing", "No local import, install ownership, and validation evidence was supplied."),
        )
    else:
        gates.append(
            gate("tools-only-artifact-evidence", True, "missing", "No history-clean tools-root, exact allowlist, SBOM, checksum, and security evidence was supplied."),
        )

    non_waivable: list[dict[str, str]] = []
    for rule in policy["waiver_policy"]["non_waivable_rules"]:
        if profile not in rule["applies_to_profiles"]:
            continue
        status, detail = non_waivable_status(rule["id"], profile, source, mode, channel_id)
        non_waivable.append(
            {"id": rule["id"], "status": status, "description": f"{rule['description']} {detail}"}
        )

    unmet = [
        f"{item['id']}: {item['detail']}"
        for item in gates
        if item["required"] and item["status"] != "passed"
    ]
    unmet.extend(f"policy: {entry}" for entry in mode["unmet_requirements"])
    unmet.extend(
        f"non-waivable:{item['id']}: {item['description']}"
        for item in non_waivable
        if item["status"] != "passed"
    )
    if not unmet:
        # This branch is retained for later evaluators; current policy always leaves
        # at least one non-waivable or required gate unresolved.
        unmet.append("No exact-candidate evaluator has established promotion eligibility.")

    ready = False
    publication_status = "private-local-only" if mode_id == "local-full" else "blocked"
    policy_relative = relative_input_path(workspace, policy_path, "distribution policy")
    record = {
        "schema": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "generated_utc": utc_now(),
        "generator": {"path": "tools/release_readiness.py", "sha256": sha256_file(Path(__file__))},
        "source": source,
        "version": {"value": version, "sha256": sha256_file(version_path)},
        "mode": mode_id,
        "channel": channel_id,
        "profile": profile,
        "ready": ready,
        "publication_status": publication_status,
        "publication_attempted": False,
        "policy": {
            "path": policy_relative,
            "sha256": sha256_file(policy_path),
            "policy_id": policy["policy_id"],
            "revision": policy["revision"],
        },
        "inputs": required_inputs(workspace),
        "gates": gates,
        "non_waivable_rules": non_waivable,
        "unmet_requirements": unmet,
    }
    return record


def validate_record(
    record: Mapping[str, Any],
    schema: Mapping[str, Any],
    workspace: Path,
    policy: Mapping[str, Any],
) -> None:
    try:
        validate_schema_instance(record, schema, "release-readiness record")
    except PolicyError as exc:
        raise ReadinessError(str(exc)) from exc
    if record["schema"] != SCHEMA_ID or record["schema_version"] != SCHEMA_VERSION:
        raise ReadinessError("release-readiness record uses an unsupported schema identity")
    expected_inputs = dict(INPUTS)
    actual_inputs: dict[str, Mapping[str, Any]] = {}
    for item in record["inputs"]:
        identifier = item["id"]
        if identifier in actual_inputs:
            raise ReadinessError(f"release-readiness record has duplicate input id: {identifier}")
        actual_inputs[identifier] = item
    if set(actual_inputs) != set(expected_inputs):
        raise ReadinessError("release-readiness record does not fingerprint the exact required input set")
    for identifier, relative in expected_inputs.items():
        item = actual_inputs[identifier]
        if item["path"] != relative:
            raise ReadinessError(f"release-readiness input {identifier} has a non-canonical path")
        path = strict_child(workspace, workspace / relative, f"readiness input {identifier}")
        if not path.is_file() or item["sha256"] != sha256_file(path):
            raise ReadinessError(f"release-readiness input {identifier} hash does not match the workspace")
    if record["policy"]["path"] != DEFAULT_POLICY_RELATIVE.as_posix():
        raise ReadinessError("release-readiness record must name the canonical distribution policy path")
    policy_path = workspace / DEFAULT_POLICY_RELATIVE
    if record["policy"]["sha256"] != sha256_file(policy_path):
        raise ReadinessError("release-readiness policy hash does not match the workspace")
    if record["policy"]["policy_id"] != policy["policy_id"] or record["policy"]["revision"] != policy["revision"]:
        raise ReadinessError("release-readiness policy identity does not match the workspace")

    modes = {mode["id"]: mode for mode in policy["modes"]}
    if record["mode"] not in modes or record["profile"] not in modes[record["mode"]]["readiness_profiles"]:
        raise ReadinessError("release-readiness mode/profile no longer matches policy")
    if record["channel"] not in {channel["id"] for channel in policy["channels"]}:
        raise ReadinessError("release-readiness channel no longer matches policy")
    gate_ids = [item["id"] for item in record["gates"]]
    if len(gate_ids) != len(set(gate_ids)):
        raise ReadinessError("release-readiness record has duplicate gate ids")
    rule_ids = [item["id"] for item in record["non_waivable_rules"]]
    if len(rule_ids) != len(set(rule_ids)):
        raise ReadinessError("release-readiness record has duplicate non-waivable rule ids")
    if record["ready"]:
        if any(item["required"] and item["status"] != "passed" for item in record["gates"]):
            raise ReadinessError("ready record has an unresolved required gate")
        if any(item["status"] != "passed" for item in record["non_waivable_rules"]):
            raise ReadinessError("ready record has an unresolved non-waivable rule")
        if not modes[record["mode"]]["publication_permitted"] or not policy["public_distribution_enabled"]:
            raise ReadinessError("ready record conflicts with the fail-closed distribution policy")
    elif record["publication_status"] == "eligible":
        raise ReadinessError("non-ready record must not claim publication eligibility")


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


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--validate", type=Path, help="validate an existing readiness record without writing output")
    parser.add_argument("--mode", choices=("tools-only", "importer-kit", "asset-full", "local-full"))
    parser.add_argument("--channel")
    parser.add_argument("--profile", choices=("tools-progress", "playable-candidate", "playable-stable", "local-full-private"))
    parser.add_argument("--output", type=Path, help="generated output below workspace dist/")
    parser.add_argument("--require-ready", action="store_true", help="return nonzero when the generated record is blocked")
    return parser.parse_args(argv)


def resolve_argument_path(workspace: Path, value: Path | None, default_relative: Path, description: str) -> Path:
    candidate = value if value is not None else workspace / default_relative
    if not candidate.is_absolute():
        candidate = workspace / candidate
    return strict_child(workspace, candidate, description)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    workspace = args.workspace_root.resolve()
    if not workspace.is_dir():
        print(f"release-readiness error: workspace does not exist: {workspace}", file=sys.stderr)
        return 2
    try:
        policy_path = resolve_argument_path(workspace, args.policy, DEFAULT_POLICY_RELATIVE, "distribution policy")
        schema_path = resolve_argument_path(workspace, args.schema, DEFAULT_SCHEMA_RELATIVE, "release-readiness schema")
        policy = load_validated_policy(policy_path, workspace)
        schema = read_json(schema_path, "release-readiness schema")
        check_schema(schema, "release-readiness schema")
        if args.validate is not None:
            validate_path = args.validate if args.validate.is_absolute() else workspace / args.validate
            validate_path = strict_child(workspace, validate_path, "readiness record")
            record = read_json(validate_path, "release-readiness record")
            validate_record(record, schema, workspace, policy)
            print(f"release-readiness record valid: ready={str(record['ready']).lower()} path={validate_path}")
            return 0
        if not all((args.mode, args.channel, args.profile)):
            raise ReadinessError("--mode, --channel, and --profile are required when generating a record")
        output_value = args.output if args.output is not None else workspace / "dist" / "release-readiness.json"
        if not output_value.is_absolute():
            output_value = workspace / output_value
        output_path = strict_child(workspace / "dist", output_value, "release-readiness output")
        record = build_record(workspace, policy_path, args.mode, args.channel, args.profile)
        validate_record(record, schema, workspace, policy)
        atomic_write(output_path, (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    except (ReadinessError, OSError, ValueError) as exc:
        print(f"release-readiness error: {exc}", file=sys.stderr)
        return 2

    print(
        "release-readiness generated: "
        f"ready={str(record['ready']).lower()} status={record['publication_status']} path={output_path}"
    )
    if args.require_ready and not record["ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

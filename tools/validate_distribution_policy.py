#!/usr/bin/env python3
"""Validate ZaeREo distribution policy structure and fail-closed semantics.

This command is deliberately read-only and has no override switch.  JSON Schema
validation establishes record shape; the checks below enforce relationships that
the schema cannot express safely, including derived summaries, exact tools-only
paths, channel roots, expiry, and the permanent local-full prohibition.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "docs" / "provenance" / "distribution-policy.json"
DEFAULT_SCHEMA = (
    ROOT / "docs" / "provenance" / "schemas" / "distribution-policy.schema.json"
)
DEFAULT_ASSET_SCHEMA = (
    ROOT / "docs" / "provenance" / "schemas" / "asset-policy.schema.json"
)

_WILDCARD_RE = re.compile(r"[*?\[\]]")
_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_CODE_KINDS = frozenset({"substrate-source", "zaero-code"})
_PUBLIC_GIT_KINDS = frozenset(
    {"public-git-tree", "public-git-history", "public-source-archives"}
)
_REQUIRED_MODE_IDS = frozenset(
    {"tools-only", "importer-kit", "asset-full", "local-full"}
)
_MODE_READINESS_PROFILES = {
    "tools-only": frozenset({"tools-progress"}),
    "importer-kit": frozenset({"playable-candidate", "playable-stable"}),
    "asset-full": frozenset({"playable-candidate", "playable-stable"}),
    "local-full": frozenset({"local-full-private"}),
}
_REQUIRED_NON_WAIVABLE_IDS = frozenset(
    {
        "distribution-mode-provenance-channel",
        "local-full-permanent-private",
        "clean-exact-source-commit",
        "tag-version-identity",
        "archive-checksum-file-allowlist",
        "critical-security-results",
        "corresponding-source-license",
        "required-compatibility-gates",
    }
)
_SCHEMA_TYPES = frozenset(
    {"array", "boolean", "integer", "null", "number", "object", "string"}
)
_SCHEMA_KEYWORDS = frozenset(
    {
        "$defs",
        "$id",
        "$ref",
        "$schema",
        "additionalProperties",
        "allOf",
        "anyOf",
        "const",
        "contains",
        "description",
        "else",
        "enum",
        "format",
        "if",
        "items",
        "maxItems",
        "maxLength",
        "maximum",
        "minItems",
        "minLength",
        "minimum",
        "oneOf",
        "pattern",
        "properties",
        "required",
        "then",
        "title",
        "type",
        "uniqueItems",
    }
)


class PolicyError(ValueError):
    """Raised when a policy is malformed or semantically unsafe."""


def _read_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PolicyError(f"unable to read {label} {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise PolicyError(
            f"invalid JSON in {label} {path}:{exc.lineno}:{exc.colno}: {exc.msg}"
        ) from exc


def load_policy(path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    policy = _read_json(path, "policy")
    if not isinstance(policy, dict):
        raise PolicyError(f"policy {path} must contain a JSON object")
    return policy


def load_schema(path: Path = DEFAULT_SCHEMA) -> dict[str, Any]:
    schema = _read_json(path, "schema")
    if not isinstance(schema, dict):
        raise PolicyError(f"schema {path} must contain a JSON object")
    return schema


def check_schema(schema: Mapping[str, Any], label: str) -> None:
    """Check the self-contained Draft 2020-12 subset used by this repository.

    The project intentionally avoids a network-installed validation dependency.
    Both policy schemas use a small, audited keyword set implemented below.
    Unknown keywords and non-local references are rejected instead of ignored.
    """

    errors: list[str] = []
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        errors.append("$schema must select Draft 2020-12")
    definitions = schema.get("$defs")
    if not isinstance(definitions, Mapping):
        errors.append("$defs must be an object")
        definitions = {}

    def walk(node: Any, path: tuple[Any, ...]) -> None:
        location = _json_path(path)
        if not isinstance(node, Mapping):
            errors.append(f"{location} must be a schema object")
            return
        unknown = sorted(set(node) - _SCHEMA_KEYWORDS)
        if unknown:
            errors.append(f"{location} uses unsupported keywords: {unknown}")

        reference = node.get("$ref")
        if reference is not None:
            if not isinstance(reference, str) or not reference.startswith("#/$defs/"):
                errors.append(f"{location} has a non-local or invalid $ref")
            else:
                name = reference.removeprefix("#/$defs/")
                if not name or "/" in name or name not in definitions:
                    errors.append(f"{location} references missing definition {name!r}")

        declared_type = node.get("type")
        if declared_type is not None:
            types = declared_type if isinstance(declared_type, list) else [declared_type]
            if (
                not types
                or any(not isinstance(item, str) or item not in _SCHEMA_TYPES for item in types)
                or len(types) != len(set(types))
            ):
                errors.append(f"{location}.type is invalid")

        pattern = node.get("pattern")
        if pattern is not None:
            if not isinstance(pattern, str):
                errors.append(f"{location}.pattern must be a string")
            else:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    errors.append(f"{location}.pattern is invalid: {exc}")

        required = node.get("required")
        if required is not None and (
            not isinstance(required, list)
            or not required
            or any(not isinstance(item, str) for item in required)
            or len(required) != len(set(required))
        ):
            errors.append(f"{location}.required must be a non-empty unique string array")

        enum = node.get("enum")
        if enum is not None and (not isinstance(enum, list) or not enum):
            errors.append(f"{location}.enum must be a non-empty array")

        properties = node.get("properties")
        if properties is not None:
            if not isinstance(properties, Mapping):
                errors.append(f"{location}.properties must be an object")
            else:
                for name, child in properties.items():
                    walk(child, path + ("properties", name))

        child_map = node.get("$defs")
        if child_map is not None:
            if not isinstance(child_map, Mapping):
                errors.append(f"{location}.$defs must be an object")
            else:
                for name, child in child_map.items():
                    walk(child, path + ("$defs", name))

        for keyword in ("allOf", "anyOf", "oneOf"):
            children = node.get(keyword)
            if children is not None:
                if not isinstance(children, list) or not children:
                    errors.append(f"{location}.{keyword} must be a non-empty array")
                else:
                    for index, child in enumerate(children):
                        walk(child, path + (keyword, index))

        for keyword in ("contains", "else", "if", "items", "then"):
            child = node.get(keyword)
            if child is not None:
                walk(child, path + (keyword,))

        additional = node.get("additionalProperties")
        if additional is not None and not isinstance(additional, bool):
            walk(additional, path + ("additionalProperties",))

        for keyword in (
            "maxItems",
            "maxLength",
            "maximum",
            "minItems",
            "minLength",
            "minimum",
        ):
            value = node.get(keyword)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0
            ):
                errors.append(f"{location}.{keyword} must be a non-negative number")

        format_name = node.get("format")
        if format_name is not None and format_name not in {"date", "date-time"}:
            errors.append(f"{location}.format is unsupported: {format_name!r}")

    walk(schema, ())
    if errors:
        raise PolicyError(f"invalid {label}:\n- " + "\n- ".join(errors))


def _json_path(parts: Iterable[Any]) -> str:
    rendered = "$"
    for part in parts:
        if isinstance(part, int):
            rendered += f"[{part}]"
        else:
            rendered += f".{part}"
    return rendered


def _json_equal(left: Any, right: Any) -> bool:
    """JSON equality without Python's ``False == 0`` shortcut."""

    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if left is None or right is None:
        return left is None and right is None
    return left == right


def _matches_type(instance: Any, expected: str) -> bool:
    if expected == "null":
        return instance is None
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "object":
        return isinstance(instance, Mapping)
    return False


def _resolve_local_ref(reference: str, root: Mapping[str, Any]) -> Mapping[str, Any]:
    name = reference.removeprefix("#/$defs/")
    target = root["$defs"][name]
    if not isinstance(target, Mapping):  # checked by check_schema; retain fail-closed guard
        raise PolicyError(f"schema definition {name!r} is not an object")
    return target


def _schema_errors(
    instance: Any,
    schema: Mapping[str, Any],
    root: Mapping[str, Any],
    path: tuple[Any, ...] = (),
) -> list[str]:
    """Evaluate the repository's self-contained JSON Schema keyword subset."""

    errors: list[str] = []
    location = _json_path(path)

    reference = schema.get("$ref")
    if isinstance(reference, str):
        errors.extend(_schema_errors(instance, _resolve_local_ref(reference, root), root, path))

    declared_type = schema.get("type")
    if declared_type is not None:
        expected = declared_type if isinstance(declared_type, list) else [declared_type]
        if not any(_matches_type(instance, item) for item in expected):
            errors.append(f"{location}: expected type {' or '.join(expected)}")
            return errors

    if "const" in schema and not _json_equal(instance, schema["const"]):
        errors.append(f"{location}: value does not equal required constant {schema['const']!r}")
    if "enum" in schema and not any(_json_equal(instance, item) for item in schema["enum"]):
        errors.append(f"{location}: value is not one of the permitted enum values")

    all_of = schema.get("allOf", [])
    for child in all_of:
        errors.extend(_schema_errors(instance, child, root, path))

    any_of = schema.get("anyOf")
    if any_of is not None:
        matches = [not _schema_errors(instance, child, root, path) for child in any_of]
        if not any(matches):
            errors.append(f"{location}: value does not satisfy any anyOf branch")

    one_of = schema.get("oneOf")
    if one_of is not None:
        matches = sum(not _schema_errors(instance, child, root, path) for child in one_of)
        if matches != 1:
            errors.append(f"{location}: value satisfies {matches} oneOf branches instead of exactly one")

    conditional = schema.get("if")
    if conditional is not None:
        branch = "then" if not _schema_errors(instance, conditional, root, path) else "else"
        selected = schema.get(branch)
        if selected is not None:
            errors.extend(_schema_errors(instance, selected, root, path))

    if isinstance(instance, Mapping):
        required = schema.get("required", [])
        for name in required:
            if name not in instance:
                errors.append(f"{location}: missing required property {name!r}")

        properties = schema.get("properties", {})
        for name, child in properties.items():
            if name in instance:
                errors.extend(_schema_errors(instance[name], child, root, path + (name,)))

        extras = set(instance) - set(properties)
        additional = schema.get("additionalProperties", True)
        if additional is False and extras:
            errors.append(f"{location}: unexpected properties {sorted(extras)}")
        elif isinstance(additional, Mapping):
            for name in extras:
                errors.extend(
                    _schema_errors(instance[name], additional, root, path + (name,))
                )

    if isinstance(instance, list):
        minimum_items = schema.get("minItems")
        if minimum_items is not None and len(instance) < minimum_items:
            errors.append(f"{location}: array has fewer than {minimum_items} items")
        maximum_items = schema.get("maxItems")
        if maximum_items is not None and len(instance) > maximum_items:
            errors.append(f"{location}: array has more than {maximum_items} items")
        if schema.get("uniqueItems"):
            encoded = [
                json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                for item in instance
            ]
            if len(encoded) != len(set(encoded)):
                errors.append(f"{location}: array items are not unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, Mapping):
            for index, item in enumerate(instance):
                errors.extend(_schema_errors(item, item_schema, root, path + (index,)))
        contains = schema.get("contains")
        if isinstance(contains, Mapping) and not any(
            not _schema_errors(item, contains, root, path + (index,))
            for index, item in enumerate(instance)
        ):
            errors.append(f"{location}: array has no item satisfying contains")

    if isinstance(instance, str):
        minimum_length = schema.get("minLength")
        if minimum_length is not None and len(instance) < minimum_length:
            errors.append(f"{location}: string is shorter than {minimum_length}")
        maximum_length = schema.get("maxLength")
        if maximum_length is not None and len(instance) > maximum_length:
            errors.append(f"{location}: string is longer than {maximum_length}")
        pattern = schema.get("pattern")
        if pattern is not None and re.search(pattern, instance) is None:
            errors.append(f"{location}: string does not match required pattern")
        format_name = schema.get("format")
        if format_name == "date":
            try:
                date.fromisoformat(instance)
            except ValueError:
                errors.append(f"{location}: value is not an ISO-8601 date")
        elif format_name == "date-time":
            try:
                parsed = datetime.fromisoformat(instance.replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"{location}: value is not an ISO-8601 date-time")
            else:
                if parsed.tzinfo is None:
                    errors.append(f"{location}: date-time lacks an explicit time zone")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        minimum = schema.get("minimum")
        if minimum is not None and instance < minimum:
            errors.append(f"{location}: number is less than minimum {minimum}")
        maximum = schema.get("maximum")
        if maximum is not None and instance > maximum:
            errors.append(f"{location}: number exceeds maximum {maximum}")

    return errors


def validate_schema_instance(
    instance: Any, schema: Mapping[str, Any], label: str = "document"
) -> None:
    """Validate one instance without network access or third-party packages."""

    check_schema(schema, f"{label} schema")
    errors = _schema_errors(instance, schema, schema)
    if errors:
        raise PolicyError(f"{label} schema validation failed:\n- " + "\n- ".join(errors))


def _validate_against_schema(
    policy: Mapping[str, Any], schema: Mapping[str, Any]
) -> list[str]:
    return _schema_errors(policy, schema, schema)


def _index_unique(
    records: Sequence[Mapping[str, Any]], label: str, errors: list[str]
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for index, record in enumerate(records):
        identifier = record.get("id")
        if not isinstance(identifier, str):
            continue
        if identifier in result:
            errors.append(f"duplicate {label} id {identifier!r} at index {index}")
        else:
            result[identifier] = record
    return result


def _check_exact_path(value: str, label: str, errors: list[str]) -> None:
    if (
        not value
        or "\\" in value
        or value.startswith("/")
        or _DRIVE_RE.match(value)
        or _WILDCARD_RE.search(value)
        or "//" in value
    ):
        errors.append(f"{label} is not an exact normalized relative path: {value!r}")
        return
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        errors.append(f"{label} contains an unsafe path segment: {value!r}")
        return
    if PurePosixPath(value).as_posix() != value:
        errors.append(f"{label} is not canonically normalized: {value!r}")


def _check_narrow_glob(value: str, label: str, errors: list[str]) -> None:
    if (
        not value
        or "\\" in value
        or value.startswith("/")
        or _DRIVE_RE.match(value)
        or value in {"*", "**", "*/**"}
        or "//" in value
    ):
        errors.append(f"{label} is not a narrow normalized repository glob: {value!r}")
        return
    if any(part in {"", ".", ".."} for part in value.split("/")):
        errors.append(f"{label} contains an unsafe path segment: {value!r}")


def _check_refs(
    refs: Sequence[str],
    known: Mapping[str, Any],
    label: str,
    errors: list[str],
) -> None:
    for reference in refs:
        if reference not in known:
            errors.append(f"{label} references unknown id {reference!r}")


def _parse_timestamp(value: str, label: str, errors: list[str]) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{label} is not an ISO-8601 timestamp: {value!r}")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{label} must include an explicit time zone")
        return None
    return parsed.astimezone(timezone.utc)


def _check_expiry(
    record: Mapping[str, Any], label: str, now: datetime, errors: list[str]
) -> None:
    expiry = record.get("expires_at")
    if expiry is None:
        return
    if not isinstance(expiry, str):
        return
    parsed = _parse_timestamp(expiry, f"{label}.expires_at", errors)
    if parsed is not None and parsed <= now:
        errors.append(f"{label} expired at {expiry}")


def validate_policy_document(
    policy: Mapping[str, Any],
    schema: Mapping[str, Any],
    *,
    repository_root: Path = ROOT,
    now: datetime | None = None,
) -> None:
    """Validate schema and cross-record invariants or raise :class:`PolicyError`."""

    check_schema(schema, "distribution-policy schema")
    errors = _validate_against_schema(policy, schema)
    if errors:
        raise PolicyError("distribution policy schema validation failed:\n- " + "\n- ".join(errors))

    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    else:
        current_time = current_time.astimezone(timezone.utc)

    evidence_records = policy["evidence"]
    component_records = policy["components"]
    channel_records = policy["channels"]
    mode_records = policy["modes"]

    evidence = _index_unique(evidence_records, "evidence", errors)
    components = _index_unique(component_records, "component", errors)
    channels = _index_unique(channel_records, "channel", errors)
    modes = _index_unique(mode_records, "mode", errors)

    for identifier, record in evidence.items():
        path = record["path"]
        _check_exact_path(path, f"evidence {identifier}.path", errors)
        candidate = (repository_root / path).resolve()
        try:
            candidate.relative_to(repository_root.resolve())
        except ValueError:
            errors.append(f"evidence {identifier}.path escapes the repository: {path!r}")
        else:
            if not candidate.is_file():
                errors.append(f"evidence {identifier}.path does not exist: {path!r}")

    review = policy["review"]
    review_until = review.get("valid_until")
    if isinstance(review_until, str):
        parsed = _parse_timestamp(review_until, "review.valid_until", errors)
        if parsed is not None and parsed <= current_time:
            errors.append(f"policy review expired at {review_until}")

    for identifier, component in components.items():
        _check_refs(
            component["evidence_refs"], evidence, f"component {identifier}", errors
        )
        _check_expiry(component, f"component {identifier}", current_time, errors)

        selectors = component["selectors"]
        exact_paths = selectors["exact_paths"]
        globs = selectors["narrow_globs"]
        folded_exact: set[str] = set()
        for path in exact_paths:
            _check_exact_path(path, f"component {identifier}.exact_paths", errors)
            folded = path.casefold()
            if folded in folded_exact:
                errors.append(
                    f"component {identifier} has a duplicate/case-colliding exact path {path!r}"
                )
            folded_exact.add(folded)
            if not (repository_root / path).is_file():
                errors.append(
                    f"component {identifier} exact path does not exist in the repository: {path!r}"
                )
        folded_globs: set[str] = set()
        for pattern in globs:
            _check_narrow_glob(pattern, f"component {identifier}.narrow_globs", errors)
            folded = pattern.casefold()
            if folded in folded_globs:
                errors.append(
                    f"component {identifier} has a duplicate/case-colliding glob {pattern!r}"
                )
            folded_globs.add(folded)

        decision = component["license"]
        if component["distribution_status"] == "permitted" and decision["no_grant"]:
            errors.append(
                f"component {identifier} is permitted but its license decision records no grant"
            )

    for identifier, channel in channels.items():
        _check_refs(
            channel["covered_component_ids"],
            components,
            f"channel {identifier}.covered_component_ids",
            errors,
        )
        _check_refs(
            channel["prohibited_component_ids"],
            components,
            f"channel {identifier}.prohibited_component_ids",
            errors,
        )
        _check_refs(channel["evidence_refs"], evidence, f"channel {identifier}", errors)
        _check_expiry(channel, f"channel {identifier}", current_time, errors)

        if channel["kind"] == "private-local-filesystem":
            if channel["audience"] != "private" or channel["distribution_root"] != "user-local-machine":
                errors.append(
                    f"private-local-filesystem channel {identifier} must be private and user-local"
                )
        elif channel["audience"] != "public":
            errors.append(f"non-local channel {identifier} must have public audience")

        if channel["audience"] == "public" and channel["status"] == "permitted":
            contradictory = set(channel["covered_component_ids"]) & set(
                channel["prohibited_component_ids"]
            )
            if contradictory:
                errors.append(
                    f"public channel {identifier} both covers and prohibits components: "
                    + ", ".join(sorted(contradictory))
                )
            unresolved = [
                component_id
                for component_id in channel["covered_component_ids"]
                if components[component_id]["distribution_status"] != "permitted"
            ]
            if unresolved:
                errors.append(
                    f"public channel {identifier} is permitted with unresolved components: "
                    + ", ".join(sorted(unresolved))
                )

    for identifier, mode in modes.items():
        _check_refs(
            mode["required_component_ids"],
            components,
            f"mode {identifier}.required_component_ids",
            errors,
        )
        _check_refs(
            mode["prohibited_component_ids"],
            components,
            f"mode {identifier}.prohibited_component_ids",
            errors,
        )
        _check_refs(
            mode["required_channel_ids"],
            channels,
            f"mode {identifier}.required_channel_ids",
            errors,
        )
        _check_refs(
            mode["permitted_channel_ids"],
            channels,
            f"mode {identifier}.permitted_channel_ids",
            errors,
        )

        overlap = set(mode["required_component_ids"]) & set(
            mode["prohibited_component_ids"]
        )
        if overlap:
            errors.append(
                f"mode {identifier} both requires and prohibits components: "
                + ", ".join(sorted(overlap))
            )
        if not set(mode["permitted_channel_ids"]).issubset(
            mode["required_channel_ids"]
        ):
            errors.append(
                f"mode {identifier}.permitted_channel_ids must be a subset of required_channel_ids"
            )
        mislabeled_channels = [
            channel_id
            for channel_id in mode["permitted_channel_ids"]
            if channel_id in channels and channels[channel_id]["status"] != "permitted"
        ]
        if mislabeled_channels:
            errors.append(
                f"mode {identifier} lists non-permitted channels as permitted: "
                + ", ".join(sorted(mislabeled_channels))
            )

        artifact_paths: set[str] = set()
        for index, decision in enumerate(mode["file_allowlist"]):
            label = f"mode {identifier}.file_allowlist[{index}]"
            artifact_path = decision["artifact_path"]
            _check_exact_path(artifact_path, f"{label}.artifact_path", errors)
            folded = artifact_path.casefold()
            if folded in artifact_paths:
                errors.append(
                    f"mode {identifier} has a duplicate/case-colliding artifact path {artifact_path!r}"
                )
            artifact_paths.add(folded)

            source_path = decision["source_path"]
            if source_path is not None:
                _check_exact_path(source_path, f"{label}.source_path", errors)
                if not (repository_root / source_path).is_file():
                    errors.append(f"{label}.source_path does not exist: {source_path!r}")
            if decision["component_id"] not in components:
                errors.append(
                    f"{label}.component_id references unknown id {decision['component_id']!r}"
                )
            elif decision["component_id"] not in mode["required_component_ids"]:
                errors.append(
                    f"{label}.component_id is not required by mode {identifier}: "
                    f"{decision['component_id']!r}"
                )
            _check_refs(decision["evidence_refs"], evidence, label, errors)

        if mode["publication_permitted"]:
            if not mode["public_mode"] or mode["status"] != "eligible":
                errors.append(
                    f"mode {identifier} permits publication without public_mode=true and status=eligible"
                )
            if mode["permanent_private"]:
                errors.append(f"mode {identifier} is permanently private but permits publication")
            if mode["unmet_requirements"]:
                errors.append(f"mode {identifier} permits publication with unmet requirements")
            if not mode["file_allowlist"]:
                errors.append(
                    f"mode {identifier} permits publication without an exact per-file allowlist"
                )
            unresolved_components = [
                component_id
                for component_id in mode["required_component_ids"]
                if components[component_id]["distribution_status"] != "permitted"
            ]
            if unresolved_components:
                errors.append(
                    f"mode {identifier} permits publication with unresolved components: "
                    + ", ".join(sorted(unresolved_components))
                )
            unresolved_files = [
                decision["artifact_path"]
                for decision in mode["file_allowlist"]
                if decision["distribution_status"] != "permitted"
            ]
            if unresolved_files:
                errors.append(
                    f"mode {identifier} permits publication with unresolved file decisions: "
                    + ", ".join(sorted(unresolved_files))
                )
            unresolved_channels = [
                channel_id
                for channel_id in mode["required_channel_ids"]
                if channels[channel_id]["status"] != "permitted"
            ]
            if unresolved_channels:
                errors.append(
                    f"mode {identifier} permits publication with unresolved channels: "
                    + ", ".join(sorted(unresolved_channels))
                )
            if set(mode["permitted_channel_ids"]) != set(mode["required_channel_ids"]):
                errors.append(
                    f"mode {identifier} permits publication without permitting every required channel"
                )
        elif mode["status"] == "eligible":
            errors.append(f"mode {identifier} is eligible but publication_permitted is false")

        if mode["public_mode"] and mode["status"] == "private-only":
            errors.append(f"public mode {identifier} cannot have private-only status")

        if mode["stable_eligible"] and not mode["publication_permitted"]:
            errors.append(
                f"mode {identifier} is stable-eligible without being publication-permitted"
            )
        expected_profiles = _MODE_READINESS_PROFILES[identifier]
        if set(mode["readiness_profiles"]) != expected_profiles:
            errors.append(
                f"mode {identifier} has non-canonical readiness profiles; "
                f"expected={sorted(expected_profiles)}"
            )
        if mode["stable_eligible"] and "playable-stable" not in mode["readiness_profiles"]:
            errors.append(
                f"mode {identifier} is stable-eligible without the playable-stable profile"
            )

    if set(modes) != _REQUIRED_MODE_IDS:
        missing = sorted(_REQUIRED_MODE_IDS - set(modes))
        extra = sorted(set(modes) - _REQUIRED_MODE_IDS)
        errors.append(f"policy modes differ from the four canonical modes; missing={missing}, extra={extra}")

    tools = modes.get("tools-only")
    if tools is not None:
        if not tools["file_allowlist"]:
            errors.append("tools-only must enumerate an exact per-file candidate allowlist")
        for component_id in tools["required_component_ids"]:
            if components[component_id]["kind"] in _CODE_KINDS | {"media"}:
                errors.append(
                    f"tools-only requires prohibited code/media component {component_id!r}"
                )
        for channel_id in tools["required_channel_ids"]:
            if channels[channel_id]["distribution_root"] != "history-clean-tools":
                errors.append(
                    f"tools-only channel {channel_id!r} is not rooted in history-clean-tools"
                )

    importer = modes.get("importer-kit")
    if importer is not None and not any(
        components[component_id]["kind"] == "media"
        for component_id in importer["prohibited_component_ids"]
    ):
        errors.append("importer-kit must explicitly prohibit the runtime media component")

    asset_full = modes.get("asset-full")
    if asset_full is not None and not any(
        components[component_id]["kind"] == "media"
        for component_id in asset_full["required_component_ids"]
    ):
        errors.append("asset-full must explicitly require a media component")

    local_full = modes.get("local-full")
    if local_full is not None:
        if local_full["status"] != "private-only":
            errors.append("local-full must have private-only status")
        if local_full["public_mode"]:
            errors.append("local-full must never be a public mode")
        if local_full["publication_permitted"]:
            errors.append("local-full publication is permanently prohibited")
        if not local_full["permanent_private"]:
            errors.append("local-full must be marked permanent_private")
        if local_full["stable_eligible"]:
            errors.append("local-full cannot be stable-publication eligible")
        for channel_id in local_full["permitted_channel_ids"]:
            if channels[channel_id]["audience"] != "private":
                errors.append(
                    f"local-full permits non-private channel {channel_id!r}"
                )

    code_components = [
        component
        for component in components.values()
        if component["kind"] in _CODE_KINDS
    ]
    derived_code = bool(code_components) and all(
        component["distribution_status"] == "permitted"
        for component in code_components
    )
    if policy["code_distribution_permitted"] != derived_code:
        errors.append(
            "code_distribution_permitted does not equal the validated summary of all code components"
        )

    media_components = [
        component
        for component in components.values()
        if component["kind"] == "media"
    ]
    derived_media = bool(media_components) and all(
        component["distribution_status"] == "permitted"
        for component in media_components
    )
    if policy["media_distribution_permitted"] != derived_media:
        errors.append(
            "media_distribution_permitted does not equal the validated summary of all media components"
        )

    gameplay_git_channels = [
        channel
        for channel in channels.values()
        if channel["distribution_root"] == "gameplay-tree"
        and channel["kind"] in _PUBLIC_GIT_KINDS
    ]
    derived_gameplay_tree = derived_code and bool(gameplay_git_channels) and all(
        channel["status"] == "permitted" for channel in gameplay_git_channels
    )
    if policy["public_gameplay_tree_permitted"] != derived_gameplay_tree:
        errors.append(
            "public_gameplay_tree_permitted does not equal the code and public Git channel summary"
        )

    derived_publication = any(
        mode["public_mode"] and mode["publication_permitted"]
        for mode in modes.values()
    )
    if policy["public_distribution_enabled"] != derived_publication:
        errors.append(
            "public_distribution_enabled does not equal the public mode publication summary"
        )

    waiver_rules = policy["waiver_policy"]["non_waivable_rules"]
    waiver_index = _index_unique(waiver_rules, "non-waivable rule", errors)
    if set(waiver_index) != _REQUIRED_NON_WAIVABLE_IDS:
        missing = sorted(_REQUIRED_NON_WAIVABLE_IDS - set(waiver_index))
        extra = sorted(set(waiver_index) - _REQUIRED_NON_WAIVABLE_IDS)
        errors.append(
            f"non-waivable rules differ from roadmap section 13.11; missing={missing}, extra={extra}"
        )
    if policy["waiver_policy"]["optional_waiver_may_change_ready_false"]:
        errors.append("an optional waiver must never change ready=false to true")

    if errors:
        raise PolicyError("distribution policy semantic validation failed:\n- " + "\n- ".join(errors))


def validate_policy_files(
    policy_path: Path = DEFAULT_POLICY,
    schema_path: Path = DEFAULT_SCHEMA,
    asset_schema_path: Path = DEFAULT_ASSET_SCHEMA,
) -> dict[str, Any]:
    """Load and validate the distribution policy and both Phase-0 schemas."""

    policy = load_policy(policy_path)
    schema = load_schema(schema_path)
    asset_schema = load_schema(asset_schema_path)
    check_schema(asset_schema, "asset-policy schema")
    validate_policy_document(
        policy,
        schema,
        repository_root=policy_path.resolve().parents[2],
    )
    return policy


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the fail-closed ZaeREo distribution policy"
    )
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--asset-schema", type=Path, default=DEFAULT_ASSET_SCHEMA)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        policy = validate_policy_files(args.policy, args.schema, args.asset_schema)
    except PolicyError as exc:
        print(f"distribution policy invalid: {exc}", file=sys.stderr)
        return 2

    modes = {mode["id"]: mode for mode in policy["modes"]}
    enabled = [
        identifier
        for identifier, mode in sorted(modes.items())
        if mode["publication_permitted"]
    ]
    print(
        "distribution policy valid: "
        f"schema={policy['schema']} revision={policy['revision']} "
        f"code={str(policy['code_distribution_permitted']).lower()} "
        f"media={str(policy['media_distribution_permitted']).lower()} "
        f"public_modes={','.join(enabled) if enabled else 'none'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

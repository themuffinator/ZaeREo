#!/usr/bin/env python3
"""Audit the exact Git candidate tree before a private evidence snapshot.

The audit deliberately examines tracked files plus untracked, non-ignored files.
Ignored build/import/release output is not silently trusted: if any such path is
already tracked or otherwise enters the candidate set, it is rejected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Iterable, Sequence


SCHEMA_VERSION = 1
FORBIDDEN_DIRECTORIES = {
    ".audit-work",
    ".install",
    ".vs",
    "build",
    "dist",
    "vcpkg_installed",
}
FORBIDDEN_SUFFIXES = {
    ".7z",
    ".bsp",
    ".cin",
    ".dll",
    ".dm2",
    ".exe",
    ".lib",
    ".md2",
    ".obj",
    ".pak",
    ".pdb",
    ".pcx",
    ".sp2",
    ".ssv",
    ".tga",
    ".wal",
    ".wav",
    ".zip",
}
FORBIDDEN_BASENAMES = {
    ".env",
    ".zaereo.local.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
}
MAX_CANDIDATE_BYTES = 5 * 1024 * 1024

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("github-token", re.compile(r"(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}")),
    ("aws-access-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    (
        "private-key",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
    ("openai-key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    (
        "credential-url",
        re.compile(r"https?://[^/@\s:]+:[^/@\s]+@", re.IGNORECASE),
    ),
    (
        "bearer-token",
        re.compile(r"Authorization\s*:\s*Bearer\s+[A-Za-z0-9._~+/-]{20,}", re.IGNORECASE),
    ),
)

EXECUTABLE_SUFFIXES = {
    ".cmd",
    ".cpp",
    ".h",
    ".json",
    ".ps1",
    ".py",
    ".vcxproj",
    ".yaml",
    ".yml",
}
LOCAL_PATH_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("source-drive", re.compile(r"[A-Za-z]:\\_SOURCE(?:\\|$)", re.IGNORECASE)),
    ("windows-user", re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+\\", re.IGNORECASE)),
    ("unix-home", re.compile(r"/(?:home|Users)/[^/\s]+/")),
)


def _run_git(root: Path, *arguments: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(arguments)} failed: {message}")
    return result.stdout


def git_candidate_paths(root: Path) -> list[str]:
    output = _run_git(
        root,
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
    )
    paths = [part.decode("utf-8") for part in output.split(b"\0") if part]
    return sorted(set(paths), key=lambda value: value.encode("utf-8"))


def git_head(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_digest(records: Iterable[dict[str, object]]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(str(record["path"]).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(record["sha256"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(record["size"]).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def audit_paths(
    root: Path,
    relative_paths: Sequence[str],
    *,
    head: str | None = None,
) -> dict[str, object]:
    root = root.resolve()
    records: list[dict[str, object]] = []
    violations: list[dict[str, str]] = []

    for raw_relative in sorted(set(relative_paths), key=lambda value: value.encode("utf-8")):
        normalized = raw_relative.replace("\\", "/")
        relative = PurePosixPath(normalized)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            violations.append(
                {"code": "unsafe-path", "path": normalized, "detail": "path is not a safe relative path"}
            )
            continue

        lexical_path = root / Path(*relative.parts)
        if lexical_path.is_symlink():
            violations.append(
                {"code": "symlink", "path": normalized, "detail": "candidate symlinks require explicit review and are not permitted"}
            )
            continue
        path = lexical_path.resolve()
        try:
            path.relative_to(root)
        except ValueError:
            violations.append(
                {"code": "path-escape", "path": normalized, "detail": "resolved path escapes repository"}
            )
            continue

        if not path.is_file():
            violations.append(
                {"code": "missing-file", "path": normalized, "detail": "candidate is not a regular file"}
            )
            continue

        lower_parts = {part.lower() for part in relative.parts[:-1]}
        suffix = path.suffix.lower()
        basename = path.name.lower()
        size = path.stat().st_size

        if lower_parts & FORBIDDEN_DIRECTORIES:
            violations.append(
                {"code": "generated-directory", "path": normalized, "detail": "generated/private directory entered candidate tree"}
            )
        if suffix in FORBIDDEN_SUFFIXES:
            violations.append(
                {"code": "forbidden-binary", "path": normalized, "detail": f"{suffix} is not permitted before rights review"}
            )
        if basename in FORBIDDEN_BASENAMES or (basename.startswith(".env.") and basename != ".env.example"):
            violations.append(
                {"code": "local-secret-file", "path": normalized, "detail": "local credential/path file entered candidate tree"}
            )
        if size > MAX_CANDIDATE_BYTES:
            violations.append(
                {"code": "oversized-file", "path": normalized, "detail": f"file exceeds {MAX_CANDIDATE_BYTES} bytes"}
            )

        sha256 = _sha256(path)
        records.append({"path": normalized, "sha256": sha256, "size": size})

        with path.open("rb") as stream:
            sample = stream.read(MAX_CANDIDATE_BYTES)
        if b"\0" in sample[:8192] and suffix not in FORBIDDEN_SUFFIXES:
            violations.append(
                {"code": "unclassified-binary", "path": normalized, "detail": "NUL bytes found in an unclassified candidate"}
            )
            continue
        text = sample.decode("utf-8", errors="replace")
        for pattern_name, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                violations.append(
                    {"code": "secret-pattern", "path": normalized, "detail": pattern_name}
                )
        if suffix in EXECUTABLE_SUFFIXES and path.name != ".zaereo.local.example.json":
            for pattern_name, pattern in LOCAL_PATH_PATTERNS:
                if pattern.search(text):
                    violations.append(
                        {"code": "hardcoded-local-path", "path": normalized, "detail": pattern_name}
                    )

    violations.sort(key=lambda item: (item["path"].encode("utf-8"), item["code"], item["detail"]))
    return {
        "format": "ZaeREo repository candidate audit",
        "schema_version": SCHEMA_VERSION,
        "head": head,
        "candidate_tree_sha256": _tree_digest(records),
        "files": records,
        "violations": violations,
        "summary": {
            "candidate_file_count": len(records),
            "candidate_total_bytes": sum(int(record["size"]) for record in records),
            "violation_count": len(violations),
            "ready_for_private_snapshot": not violations,
        },
    }


def audit_repository(root: Path) -> dict[str, object]:
    root = root.resolve()
    return audit_paths(root, git_candidate_paths(root), head=git_head(root))


def stable_json(report: dict[str, object]) -> str:
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--json-output", type=Path)
    arguments = parser.parse_args(argv)

    try:
        report = audit_repository(arguments.root)
    except (OSError, RuntimeError, UnicodeError) as error:
        parser.error(str(error))

    rendered = stable_json(report)
    if arguments.json_output:
        arguments.json_output.parent.mkdir(parents=True, exist_ok=True)
        arguments.json_output.write_text(rendered, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(rendered)

    summary = report["summary"]
    assert isinstance(summary, dict)
    return 0 if summary["ready_for_private_snapshot"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

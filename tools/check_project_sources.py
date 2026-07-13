#!/usr/bin/env python3
"""Verify that every C++ source/header under src is listed by game.vcxproj."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx"}
HEADER_SUFFIXES = {".h", ".hh", ".hpp", ".hxx"}
MSBUILD_NS = {"m": "http://schemas.microsoft.com/developer/msbuild/2003"}


def normalized_relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix().casefold()


def project_entries(project_path: Path, tag: str) -> set[str]:
    root = ET.parse(project_path).getroot()
    entries: set[str] = set()
    for node in root.findall(f".//m:{tag}", MSBUILD_NS):
        include = node.get("Include")
        if include:
            entries.add(include.replace("\\", "/").casefold())
    return entries


def check_project(src_root: Path, project_path: Path) -> list[str]:
    errors: list[str] = []
    compiled = project_entries(project_path, "ClCompile")
    headers = project_entries(project_path, "ClInclude")

    disk_sources = {
        normalized_relative(path, src_root)
        for path in src_root.rglob("*")
        if path.is_file() and path.suffix.casefold() in SOURCE_SUFFIXES
    }
    disk_headers = {
        normalized_relative(path, src_root)
        for path in src_root.rglob("*")
        if path.is_file() and path.suffix.casefold() in HEADER_SUFFIXES
    }

    for label, disk, declared in (
        ("source", disk_sources, compiled),
        ("header", disk_headers, headers),
    ):
        for path in sorted(disk - declared):
            errors.append(f"unlisted {label}: {path}")
        for path in sorted(declared - disk):
            errors.append(f"missing declared {label}: {path}")

    return errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, default=Path("src"))
    parser.add_argument("--project", type=Path, default=Path("src/game.vcxproj"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    src_root = args.src.resolve()
    project_path = args.project.resolve()
    if not src_root.is_dir():
        print(f"source directory not found: {src_root}", file=sys.stderr)
        return 2
    if not project_path.is_file():
        print(f"project file not found: {project_path}", file=sys.stderr)
        return 2

    errors = check_project(src_root, project_path)
    if errors:
        print("Visual Studio project manifest is incomplete:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1

    print("Visual Studio project lists every C++ source and header.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


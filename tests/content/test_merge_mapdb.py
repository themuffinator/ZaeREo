from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import struct
import sys
import tempfile
import unittest

try:
    import jsonschema
except ImportError:  # pragma: no cover - optional test dependency
    jsonschema = None


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "merge_mapdb.py"
SCHEMA = ROOT / "docs" / "provenance" / "schemas" / "mapdb-merge.schema.json"


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def base_mapdb() -> dict[str, object]:
    return {
        "episodes": [
            {"id": "base", "name": "Base", "unknown": {"retained": True}},
            {"id": "rogue", "name": "Rogue"},
        ],
        "maps": [
            {"bsp": "base1", "episode": "base", "title": "Stock Base"},
            {"bsp": "rogue1", "episode": "rogue", "title": "Stock Rogue"},
        ],
        "unrecognized_top_level": ["preserve", {"this": "too"}],
    }


def fragment_mapdb() -> dict[str, object]:
    return {
        "episodes": [{"id": "zaero", "name": "Zaero", "command": "exec zaerostart.cfg"}],
        "maps": [
            {"bsp": "zbase1", "episode": "zaero", "title": "Outer Perimeter"},
            {"bsp": "intro.cin", "episode": "zaero", "title": "Introduction"},
            {"bsp": "*intro.cin+zbase1", "episode": "zaero", "title": "Start"},
        ],
    }


class MergeMapdbTests(unittest.TestCase):
    def prepare(self, workspace: Path) -> tuple[Path, Path, Path, Path, Path]:
        base = workspace / "base-mapdb.json"
        fragment = workspace / "fragment.json"
        content = workspace / "content"
        generated = workspace / ".install"
        output = generated / "mapdb" / "mapdb.json"
        report = generated / "mapdb" / "report.json"
        write_json(base, base_mapdb())
        write_json(fragment, fragment_mapdb())
        (content / "maps").mkdir(parents=True)
        (content / "video").mkdir()
        (content / "maps" / "zbase1.bsp").write_bytes(b"bsp")
        (content / "video" / "intro.cin").write_bytes(b"cin")
        return base, fragment, content, output, report

    def invoke(
        self,
        workspace: Path,
        base: Path,
        fragment: Path,
        content: Path,
        output: Path,
        report: Path,
        expected_hash: str | None = None,
        *extra: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "--base",
                str(base),
                "--fragment",
                str(fragment),
                "--content-root",
                str(content),
                "--expected-base-sha256",
                expected_hash or hashlib.sha256(base.read_bytes()).hexdigest(),
                "--data-build",
                "synthetic-rerelease-build",
                "--episode-index",
                "1",
                "--map-index",
                "1",
                "--output",
                str(output),
                "--report",
                str(report),
                "--generated-root",
                str(workspace / ".install"),
                *extra,
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_merges_at_explicit_indices_preserving_unknown_base_data(self) -> None:
        with tempfile.TemporaryDirectory(prefix="zaereo-mapdb-") as temporary:
            workspace = Path(temporary)
            base, fragment, content, output, report = self.prepare(workspace)
            result = self.invoke(workspace, base, fragment, content, output, report)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            merged = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual([item["id"] for item in merged["episodes"]], ["base", "zaero", "rogue"])
            self.assertEqual(
                [item["bsp"] for item in merged["maps"]],
                ["base1", "zbase1", "intro.cin", "*intro.cin+zbase1", "rogue1"],
            )
            self.assertEqual(merged["episodes"][0]["unknown"], {"retained": True})
            self.assertEqual(merged["unrecognized_top_level"], ["preserve", {"this": "too"}])
            merge_report = json.loads(report.read_text(encoding="utf-8"))
            self.assertTrue(merge_report["inverse_reconstructs_base"])
            self.assertEqual(merge_report["publication_status"], "private-local-only")
            if jsonschema is None:
                self.skipTest("jsonschema is not installed")
            jsonschema.Draft202012Validator(
                json.loads(SCHEMA.read_text(encoding="utf-8"))
            ).validate(merge_report)

    def test_rejects_unpinned_base_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="zaereo-mapdb-") as temporary:
            workspace = Path(temporary)
            base, fragment, content, output, report = self.prepare(workspace)
            result = self.invoke(
                workspace,
                base,
                fragment,
                content,
                output,
                report,
                "0" * 64,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SHA-256 mismatch", result.stdout + result.stderr)
            self.assertFalse(output.exists())
            self.assertFalse(report.exists())

    def test_reads_hash_pinned_mapdb_member_from_a_pak(self) -> None:
        with tempfile.TemporaryDirectory(prefix="zaereo-mapdb-") as temporary:
            workspace = Path(temporary)
            base, fragment, content, output, report = self.prepare(workspace)
            member_bytes = base.read_bytes()
            pak = workspace / "base.pak"
            entry_name = b"mapdb.json".ljust(56, b"\0")
            directory_offset = 12 + len(member_bytes)
            pak.write_bytes(
                struct.pack("<4sII", b"PACK", directory_offset, 64)
                + member_bytes
                + struct.pack("<56sII", entry_name, 12, len(member_bytes))
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--base-pak",
                    str(pak),
                    "--base-member",
                    "mapdb.json",
                    "--fragment",
                    str(fragment),
                    "--content-root",
                    str(content),
                    "--expected-base-sha256",
                    hashlib.sha256(member_bytes).hexdigest(),
                    "--data-build",
                    "synthetic-rerelease-build",
                    "--episode-index",
                    "1",
                    "--map-index",
                    "1",
                    "--output",
                    str(output),
                    "--report",
                    str(report),
                    "--generated-root",
                    str(workspace / ".install"),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            merge_report = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(merge_report["base_source"], "pak-member")
            self.assertEqual(merge_report["base_member"], "mapdb.json")
            self.assertEqual(merge_report["base_container_sha256"], hashlib.sha256(pak.read_bytes()).hexdigest())

    def test_rejects_case_colliding_fragment_map_and_missing_media(self) -> None:
        with tempfile.TemporaryDirectory(prefix="zaereo-mapdb-") as temporary:
            workspace = Path(temporary)
            base, fragment, content, output, report = self.prepare(workspace)
            conflicting = fragment_mapdb()
            conflicting["maps"][0]["bsp"] = "BASE1"
            write_json(fragment, conflicting)
            result = self.invoke(workspace, base, fragment, content, output, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("conflicts with existing map ownership", result.stdout + result.stderr)

            write_json(fragment, fragment_mapdb())
            (content / "video" / "intro.cin").unlink()
            result = self.invoke(workspace, base, fragment, content, output, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing imported runtime content", result.stdout + result.stderr)

    def test_preserves_exact_upstream_map_duplicates_but_rejects_case_only_duplicates(self) -> None:
        with tempfile.TemporaryDirectory(prefix="zaereo-mapdb-") as temporary:
            workspace = Path(temporary)
            base, fragment, content, output, report = self.prepare(workspace)
            duplicated = base_mapdb()
            duplicated["maps"].append(
                {"bsp": "base1", "episode": "base", "title": "Stock Base Variant"}
            )
            write_json(base, duplicated)
            result = self.invoke(workspace, base, fragment, content, output, report)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            merged = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual([item["bsp"] for item in merged["maps"]].count("base1"), 2)

            case_only = base_mapdb()
            case_only["maps"].append(
                {"bsp": "BASE1", "episode": "base", "title": "Invalid Case Variant"}
            )
            write_json(base, case_only)
            result = self.invoke(workspace, base, fragment, content, output, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicate or case-colliding", result.stdout + result.stderr)

    def test_dry_run_validates_without_creating_generated_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="zaereo-mapdb-") as temporary:
            workspace = Path(temporary)
            base, fragment, content, output, report = self.prepare(workspace)
            result = self.invoke(workspace, base, fragment, content, output, report, None, "--dry-run")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Validated private mapdb merge", result.stdout)
            self.assertFalse(output.exists())
            self.assertFalse(report.exists())

    def test_schema_is_strict(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["$id"], "https://zaereo.invalid/schemas/mapdb-merge/v1")
        self.assertEqual(schema["properties"]["inverse_reconstructs_base"], {"const": True})
        self.assertEqual(schema["properties"]["base_source"]["enum"], ["file", "pak-member"])
        if jsonschema is None:
            self.skipTest("jsonschema is not installed")
        jsonschema.Draft202012Validator.check_schema(schema)


if __name__ == "__main__":
    unittest.main()

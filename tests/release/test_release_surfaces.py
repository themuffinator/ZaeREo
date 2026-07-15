"""Fail-closed D-015 contracts for source-only and Release surfaces."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
POLICY_PATH = ROOT / "docs" / "provenance" / "release-surface-policy.json"
REPORT_PATH = ROOT / "docs" / "audits" / "release-surfaces.json"
MARKDOWN_PATH = ROOT / "docs" / "audits" / "release-surfaces.md"
sys.path.insert(0, str(TOOLS))

from audit_common import AuditError, PAK_ENTRY, PAK_HEADER, sha256_file  # noqa: E402
from audit_release_surfaces import (  # noqa: E402
    audit_port,
    load_policy,
    validate_archive,
    validate_binary,
)


PROJECT_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <ItemDefinitionGroup Condition="'$(Configuration)|$(Platform)'=='Debug|x64'">
    <ClCompile>
      <PreprocessorDefinitions>_DEBUG;%(PreprocessorDefinitions)</PreprocessorDefinitions>
    </ClCompile>
  </ItemDefinitionGroup>
  <ItemDefinitionGroup Condition="'$(Configuration)|$(Platform)'=='Release|x64'">
    <ClCompile>
      <PreprocessorDefinitions>NDEBUG;%(PreprocessorDefinitions)</PreprocessorDefinitions>
    </ClCompile>
  </ItemDefinitionGroup>
</Project>
"""


def make_pak(entries: list[tuple[str, bytes]]) -> bytes:
    payload = bytearray(PAK_HEADER.size)
    directory: list[bytes] = []
    for name, data in entries:
        offset = len(payload)
        payload.extend(data)
        encoded = name.encode("ascii")
        directory.append(PAK_ENTRY.pack(encoded.ljust(56, b"\0"), offset, len(data)))
    directory_offset = len(payload)
    packed_directory = b"".join(directory)
    payload.extend(packed_directory)
    PAK_HEADER.pack_into(payload, 0, b"PACK", directory_offset, len(packed_directory))
    return bytes(payload)


class ReleaseSurfacePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy_path, cls.policy = load_policy(POLICY_PATH)

    def make_port(self, root: Path) -> Path:
        port = root / "src"
        (port / "zaero").mkdir(parents=True)
        (port / "game.vcxproj").write_text(PROJECT_TEMPLATE, encoding="utf-8")
        (port / "game.h").write_text(
            "enum { TE_GRAPPLE_CABLE, TE_GRAPPLE_CABLE_2 };\n",
            encoding="utf-8",
        )
        (port / "safe.cpp").write_text("void safe_surface() {}\n", encoding="utf-8")
        (port / "zaero" / "g_zaero_zboss.cpp").write_text(
            "void zaero_zboss_surface() {}\n", encoding="utf-8"
        )
        return port

    def test_checked_report_matches_current_port_and_policy(self) -> None:
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(report["audit"], "zaero-release-surfaces")
        self.assertEqual(report["policy"]["decision"], "D-015")
        self.assertEqual(report["policy"]["revision"], self.policy["revision"])
        self.assertEqual(report["policy"]["sha256"], sha256_file(POLICY_PATH))
        self.assertEqual(report["summary"]["legacy_identity_file_count"], 15)
        self.assertEqual(report["summary"]["legacy_probe_count"], 32)
        self.assertEqual(report["summary"]["animated_rocket_guard_count"], 2)
        self.assertEqual(report["summary"]["disabled_grapple_block_count"], 2)
        self.assertEqual(report["summary"]["port_forbidden_source_hit_count"], 0)
        self.assertEqual(audit_port(self.policy, ROOT / "src"), report["port"])
        markdown = MARKDOWN_PATH.read_text(encoding="utf-8")
        self.assertIn("static evidence", markdown)
        self.assertIn("retained live Release smoke that closes Q-039/SYS-018", markdown)
        self.assertIn("Runtime evidence boundary", markdown)

    def test_current_release_configuration_cannot_enable_developer_guards(self) -> None:
        port = audit_port(self.policy, ROOT / "src")
        release = port["project"]["configurations"]["Release|x64"]
        debug = port["project"]["configurations"]["Debug|x64"]
        self.assertIn("NDEBUG", release["definitions"])
        self.assertNotIn("_DEBUG", release["definitions"])
        self.assertIn("_DEBUG", debug["definitions"])
        for configuration in (release, debug):
            self.assertEqual(configuration["forbidden_definitions_present"], [])

    def test_global_legacy_token_and_module_name_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            port = self.make_port(Path(temporary_name))
            audit_port(self.policy, port)
            (port / "safe.cpp").write_text(
                "void InitTestWeapon() {}\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(AuditError, "forbidden legacy surface"):
                audit_port(self.policy, port)
            (port / "safe.cpp").write_text("void safe_surface() {}\n", encoding="utf-8")
            (port / "z_mtest.cpp").write_text("void safe() {}\n", encoding="utf-8")
            with self.assertRaisesRegex(AuditError, "forbidden legacy debug modules"):
                audit_port(self.policy, port)

    def test_grapple_token_is_denied_only_in_zaero_zboss_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            port = self.make_port(Path(temporary_name))
            report = audit_port(self.policy, port)
            self.assertEqual(
                report["native_unscoped_exact_identifier_counts"]["TE_GRAPPLE_CABLE"],
                1,
            )
            (port / "zaero" / "g_zaero_zboss.cpp").write_text(
                "void cable() { int effect = TE_GRAPPLE_CABLE; }\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(AuditError, "scoped port source"):
                audit_port(self.policy, port)

    def test_binary_validator_rejects_ascii_and_utf16_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            clean = root / "clean.dll"
            clean.write_bytes(b"MZ\0release-safe")
            result = validate_binary(self.policy, clean)
            self.assertEqual(result["forbidden_string_hits"], [])

            ascii_bad = root / "ascii-bad.dll"
            ascii_bad.write_bytes(b"MZ\0weapon_linedraw\0")
            with self.assertRaisesRegex(AuditError, "forbidden D-015 strings"):
                validate_binary(self.policy, ascii_bad)

            utf16_bad = root / "utf16-bad.dll"
            utf16_bad.write_bytes("testitem.cfg".encode("utf-16-le"))
            with self.assertRaisesRegex(AuditError, "utf-16-le"):
                validate_binary(self.policy, utf16_bad)

    def test_archive_validator_rejects_names_and_embedded_binary_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            clean = root / "clean.zip"
            with zipfile.ZipFile(clean, "w") as archive:
                archive.writestr("zaereo/game_x64.dll", b"MZ\0release-safe")
                archive.writestr(
                    "zaereo/pak0.pak", make_pak([("maps/safe.bsp", b"safe")])
                )
                archive.writestr("zaereo/zaero.cfg", b"echo safe")
            result = validate_archive(self.policy, clean)
            self.assertEqual(result["binary_members_scanned"], ["zaereo/game_x64.dll"])
            self.assertEqual(
                result["pak_members_scanned"],
                [{"entry_count": 1, "path": "zaereo/pak0.pak"}],
            )

            named_bad = root / "named-bad.zip"
            with zipfile.ZipFile(named_bad, "w") as archive:
                archive.writestr("zaereo/testweapon.cfg", b"test")
            with self.assertRaisesRegex(AuditError, "forbidden D-015 member"):
                validate_archive(self.policy, named_bad)

            binary_bad = root / "binary-bad.zip"
            with zipfile.ZipFile(binary_bad, "w") as archive:
                archive.writestr("zaereo/game_x64.dll", b"MZ\0item_test\0")
            with self.assertRaisesRegex(AuditError, "archive binary"):
                validate_archive(self.policy, binary_bad)

            pak_bad = root / "pak-bad.zip"
            with zipfile.ZipFile(pak_bad, "w") as archive:
                archive.writestr(
                    "zaereo/pak0.pak",
                    make_pak([("tools/testitem.cfg", b"test")]),
                )
            with self.assertRaisesRegex(AuditError, "PAK contains forbidden"):
                validate_archive(self.policy, pak_bad)


if __name__ == "__main__":
    unittest.main()

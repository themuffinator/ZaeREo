from __future__ import annotations

from html.parser import HTMLParser
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"


class _ReleaseHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.external_resources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        for name in ("src", "href"):
            value = values.get(name)
            if value and (value.startswith("http://") or value.startswith("https://")):
                self.external_resources.append(value)


class PowerShellReleaseToolingTests(unittest.TestCase):
    scripts = (
        "install_dev.ps1",
        "complete_importer_kit.ps1",
        "package_windows.ps1",
        "publish_github_release.ps1",
    )

    def test_scripts_parse_with_powershell(self) -> None:
        pwsh = shutil.which("pwsh")
        if not pwsh:
            self.skipTest("PowerShell 7 is not installed")
        paths = ",".join("'" + str(TOOLS / name).replace("'", "''") + "'" for name in self.scripts)
        command = rf"""
$failed = $false
foreach ($path in @({paths})) {{
  $tokens = $null
  $errors = $null
  [void][System.Management.Automation.Language.Parser]::ParseFile(
    $path, [ref]$tokens, [ref]$errors
  )
  foreach ($error in $errors) {{
    [Console]::Error.WriteLine("{{0}}:{{1}}: {{2}}", $path, $error.Extent.StartLineNumber, $error.Message)
    $failed = $true
  }}
}}
if ($failed) {{ exit 2 }}
"""
        result = subprocess.run(
            [pwsh, "-NoLogo", "-NoProfile", "-Command", command],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_importer_kit_package_whatif_is_non_mutating(self) -> None:
        pwsh = shutil.which("pwsh")
        if not pwsh:
            self.skipTest("PowerShell 7 is not installed")
        result = subprocess.run(
            [
                pwsh,
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(TOOLS / "package_windows.ps1"),
                "-WorkspaceRoot",
                str(ROOT),
                "-DistributionMode",
                "importer-kit",
                "-AllowDirty",
                "-SkipBuild",
                "-SkipTests",
                "-WhatIf",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("preflight completed", result.stdout)
        self.assertIn("not playable", result.stdout)

    def test_hash_and_path_safety_contracts_are_not_bypassable(self) -> None:
        install = (TOOLS / "install_dev.ps1").read_text(encoding="utf-8")
        resolver = (TOOLS / "zaereo_paths.ps1").read_text(encoding="utf-8")
        complete = (TOOLS / "complete_importer_kit.ps1").read_text(encoding="utf-8")
        package = (TOOLS / "package_windows.ps1").read_text(encoding="utf-8")
        publish = (TOOLS / "publish_github_release.ps1").read_text(encoding="utf-8")

        combined_local_full = install + complete + package
        self.assertNotIn("allow-unknown-hashes", combined_local_full.lower())
        self.assertNotIn("allow-unknown-source-hashes", combined_local_full.lower())
        self.assertIn('"--manifest", $manifestPath', install)
        self.assertIn('"--strict"', install)
        self.assertIn("KNOWN", (TOOLS / "import_legacy_assets.py").read_text(encoding="utf-8"))
        self.assertIn('. (Join-Path $PSScriptRoot "zaereo_paths.ps1")', install)
        self.assertIn("Assert-StrictChildPath", install)
        self.assertIn(".zaereo-managed-files.json", install)
        self.assertIn("ownership = [ordered]@", install)
        self.assertIn('"pak0.pak"', install)
        self.assertIn('"pak1.pak"', install)
        self.assertIn('"pak2.pak"', install)
        self.assertIn("Assert-NoTreeCollisions", install)
        self.assertIn('"--stage", $stagePath', install)
        self.assertIn("Never target baseq2", resolver)
        self.assertIn("Test-ZaeREoProgramRoot", resolver)
        self.assertIn('. (Join-Path $PSScriptRoot "zaereo_paths.ps1")', package)
        self.assertIn("Get-ZaeREoLocalConfiguration", package)
        self.assertIn("Resolve-ZaeREoPath", package)

        self.assertNotIn("Compress-Archive", package)
        self.assertIn("make_release_zip.py", package)
        self.assertIn("release_manifest.py", package)
        self.assertIn("collect_licenses.py", package)
        self.assertIn("generate_sbom.py", package)
        self.assertIn("SBOM.spdx.json", package)
        self.assertIn("LICENSE-MANIFEST.json", package)
        self.assertIn("LICENSE_SCOPE.md", package)
        self.assertIn("source_date_epoch", package)
        self.assertIn("ZIP determinism check failed", package)
        self.assertIn('ValidateSet("importer-kit", "local-full")', package)
        self.assertIn("Assert-NoTreeCollisions", package)
        self.assertNotIn("$contentWork", package)
        self.assertIn('New-DeterministicPak $projectWork "pak0.pak"', package)
        self.assertIn('New-DeterministicPak $importWork "pak1.pak" $loosePaths', package)
        self.assertIn("RUNTIME-OWNERSHIP.json", package)
        self.assertIn('"--stage", $stagePath', package)

        self.assertIn("publication_eligible = $false", package)
        self.assertIn("Local verification output only", package)
        self.assertIn("REMOTE_PUBLICATION_DISABLED", publish)
        self.assertNotIn("Get-Command gh", publish)
        self.assertNotIn("& git", publish)
        self.assertNotIn("release create", publish.lower())
        self.assertNotIn("--clobber", publish)

        release_readme = (ROOT / "docs" / "release-readme.html").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("-EngineRoot \"D:\\Games\\Quake II Rerelease\"", release_readme)
        self.assertNotIn(".zaereo-install/import-ownership.json", release_readme)
        self.assertIn("tools/run_game.ps1", release_readme)

    def test_manual_publisher_fails_before_git_or_github_access(self) -> None:
        pwsh = shutil.which("pwsh")
        if not pwsh:
            self.skipTest("PowerShell 7 is not installed")
        with tempfile.TemporaryDirectory() as temporary_name:
            temporary = Path(temporary_name)
            marker = temporary / "external-command-invoked.txt"
            shim = (
                "@echo off\r\n"
                f'>>"{marker}" echo external command invoked\r\n'
                "exit /b 99\r\n"
            )
            for executable in ("git.cmd", "gh.cmd"):
                (temporary / executable).write_text(shim, encoding="utf-8")
            environment = os.environ.copy()
            environment["PATH"] = str(temporary) + os.pathsep + environment.get("PATH", "")
            environment["GH_TOKEN"] = "must-not-be-read"
            result = subprocess.run(
                [
                    pwsh,
                    "-NoLogo",
                    "-NoProfile",
                    "-File",
                    str(TOOLS / "publish_github_release.ps1"),
                    "-Version",
                    "0.0.0",
                    "-Tag",
                    "v0.0.0",
                    "-ArchivePath",
                    str(temporary / "missing.zip"),
                    "-ManifestPath",
                    str(temporary / "missing.manifest.json"),
                    "-ChecksumPath",
                    str(temporary / "missing.sha256"),
                    "-WorkspaceRoot",
                    str(temporary),
                    "-Repository",
                    "example/forbidden",
                    "-Publish",
                    "-UseExistingTag",
                    "-AllowDetachedHead",
                    "-ReplaceExistingAssets",
                    "-ConfirmRecovery",
                ],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            output = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0, output)
            self.assertIn("REMOTE_PUBLICATION_DISABLED", output)
            self.assertFalse(marker.exists(), "publisher invoked git or gh before containment")

    def test_explicit_environment_config_discovery_precedence_is_ordered(self) -> None:
        paths = (TOOLS / "zaereo_paths.ps1").read_text(encoding="utf-8")
        resolver = paths[
            paths.index("function Resolve-ZaeREoPath") :
            paths.index("function Find-ZaeREoRereleaseRoot")
        ]
        resolver = resolver[resolver.index("if ($ExplicitValue.Trim())") :]
        positions = [
            resolver.index("if ($ExplicitValue.Trim())"),
            resolver.index("GetEnvironmentVariable"),
            resolver.index("Get-ZaeREoConfigurationValue"),
            resolver.index("if ($null -ne $Discovery)"),
        ]
        self.assertEqual(positions, sorted(positions))


class ReleaseSurfaceTests(unittest.TestCase):
    def test_vscode_tasks_are_valid_json_and_expose_release_actions(self) -> None:
        tasks = json.loads((ROOT / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        labels = {task["label"] for task in tasks["tasks"]}
        self.assertIn("ZaeREo: Install developer build", labels)
        self.assertIn("ZaeREo: Package importer kit (local verification)", labels)

    def test_workflows_are_read_only_and_never_upload_or_publish(self) -> None:
        workflow_root = ROOT / ".github" / "workflows"
        workflows = {
            path.name: path.read_text(encoding="utf-8")
            for path in sorted(workflow_root.glob("*.yml"))
        }
        self.assertTrue(workflows)
        forbidden = (
            "contents: write",
            "actions/upload-artifact",
            "actions/cache",
            "actions/github-script",
            "create-release",
            "release-action",
            "publish_github_release.ps1",
            "GH_TOKEN",
            "github.token",
            "secrets.",
            "gh release",
            "git push",
            "git tag",
        )
        allowed_actions = {
            "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683",
            "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        }
        for name, workflow in workflows.items():
            self.assertIn("contents: read", workflow, name)
            self.assertIn("persist-credentials: false", workflow, name)
            for token in forbidden:
                self.assertNotIn(token.lower(), workflow.lower(), f"{name}: {token}")
            used_actions = {
                line.split("uses:", 1)[1].split("#", 1)[0].strip()
                for line in workflow.splitlines()
                if line.strip().startswith("uses:")
            }
            self.assertLessEqual(used_actions, allowed_actions, name)
            self.assertTrue(used_actions, name)
            for action in used_actions:
                self.assertRegex(action, r"^[^@]+@[0-9a-f]{40}$", name)

        package = workflows["package-windows.yml"]
        nightly = workflows["nightly-windows.yml"]
        stable = workflows["release-windows.yml"]
        for workflow in (package, nightly, stable):
            self.assertIn("-DistributionMode importer-kit", workflow)
            self.assertNotIn("ZAERO_LEGACY_ROOT", workflow)
            self.assertNotIn("local-full", workflow)
            self.assertIn("lfs: false", workflow)
        self.assertNotIn("publish_release", nightly)
        self.assertNotIn("push:", stable)

        for path in (
            "CHANGELOG.md",
            "LICENSE*",
            "THIRD_PARTY_NOTICES.md",
            "docs/provenance/**",
            ".github/workflows/**",
        ):
            self.assertIn(f'      - "{path}"', package)
        self.assertNotIn("publish_release", stable)

    def test_release_readme_is_standalone_and_honest(self) -> None:
        text = (ROOT / "docs" / "release-readme.html").read_text(encoding="utf-8")
        parser = _ReleaseHtmlParser()
        parser.feed(text)
        self.assertEqual(parser.external_resources, [])
        self.assertIn("compatibility is incomplete", text)
        self.assertIn("not playable until completed", text)
        self.assertIn("Do not redistribute a local-full archive", text)


if __name__ == "__main__":
    unittest.main()

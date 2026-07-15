from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

try:
    import jsonschema
except ImportError:  # pragma: no cover - optional test dependency
    jsonschema = None


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "run_runtime_matrix.ps1"
SCENARIOS = ROOT / "tools" / "runtime-scenarios.json"
DM_SCENARIOS = ROOT / "tools" / "runtime-scenarios-dm.json"
DM_FIXTURE_SCENARIOS = ROOT / "tools" / "runtime-scenarios-dm-fixtures.json"
SCHEMA = ROOT / "docs" / "provenance" / "schemas" / "runtime-matrix.schema.json"
RESULT_SCHEMA = ROOT / "docs" / "provenance" / "schemas" / "runtime-matrix-result.schema.json"
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


def scenario_document() -> dict[str, object]:
    return {
        "schema": "zaereo.runtime-matrix/v1",
        "schema_version": 1,
        "scenarios": [
            {
                "id": "fixture-load",
                "map": "zbase1",
                "deathmatch": False,
                "zdmflags": 0,
                "probe_deathmatch_items": False,
                "wait_frames": 4,
                "timeout_seconds": 10,
                "requires_private_content": True,
            }
        ],
    }


def passing_runner_script(*, require_manual_delivery: bool = False) -> str:
    manual_check = (
        "if (@($Rest) -notcontains '-ManualCommandDelivery') { throw 'manual delivery was not forwarded' }\n"
        if require_manual_delivery
        else ""
    )
    return (
        "param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Rest)\n"
        "function Get-ArgumentValue([string]$Name) {\n"
        "  $index = [Array]::IndexOf($Rest, $Name)\n"
        "  if ($index -lt 0 -or $index -ge ($Rest.Count - 1)) { throw \"missing $Name\" }\n"
        "  return $Rest[$index + 1]\n"
        "}\n"
        f"{manual_check}"
        "$path = Get-ArgumentValue '-ReportOutput'\n"
        "$map = Get-ArgumentValue '-Map'\n"
        "$zdmflags = [int](Get-ArgumentValue '-ZdmFlags')\n"
        "$deathmatch = @($Rest) -contains '-Deathmatch'\n"
        "[IO.Directory]::CreateDirectory((Split-Path -Parent $path)) | Out-Null\n"
        "$report = [ordered]@{\n"
        "  schema = 'zaereo.runtime-smoke/v2'; schema_version = 2; result = 'passed';\n"
        "  map = $map; game_mode = if ($deathmatch) { 'deathmatch' } else { 'single-player' }; zdmflags = $zdmflags;\n"
        "  game_directory = 'zaereo'; window_mode = 'windowed';\n"
        "  window_probe = [ordered]@{ method = 'win32-visible-top-level-window-enumeration'; process_id = 1234; style_hex = '0x14CF0000'; captioned = $true; popup = $false; left = 0; top = 0; width = 1280; height = 720 };\n"
        "  focus_diagnostic = [ordered]@{ stage = 'queue-activation'; foreground_process_id = 1234; target_foreground = $true };\n"
        "  non_windowed_visible_observed = $false; window_safety_abort = $false;\n"
        "  launch_protocol = 'two-stage-window-before-mod-map/v1'; command_delivery = 'engine-confirmed'; mod_map_command_injected_after_window_verification = $true;\n"
        "  process_exit_code_accepted = $true; timed_out = $false;\n"
        "  markers = [ordered]@{ session_begin = $true; windowed_mode_confirmed = $true; mod_map_command_injected_after_window_verification = $true; game_dll_loaded = $true; game_initialized = $true; map_spawned = $true; client_entered = $true; game_shutdown = $true; session_end = $true };\n"
        "  stderr_empty = $true; fatal_matches = @(); crash_dumps = @(); residual_process_ids = @(); publication_status = 'private-local-only'\n"
        "} | ConvertTo-Json -Depth 6\n"
        "[IO.File]::WriteAllText($path, $report, [Text.UTF8Encoding]::new($false))\n"
    )


class RuntimeMatrixTests(unittest.TestCase):
    def test_checked_in_scenarios_are_private_and_cover_v2_reruns(self) -> None:
        documents = {
            "legacy-smokes": json.loads(SCENARIOS.read_text(encoding="utf-8")),
            "deathmatch": json.loads(DM_SCENARIOS.read_text(encoding="utf-8")),
            "deathmatch-fixtures": json.loads(DM_FIXTURE_SCENARIOS.read_text(encoding="utf-8")),
        }
        for document in documents.values():
            self.assertEqual(document["schema"], "zaereo.runtime-matrix/v1")
            self.assertEqual(document["schema_version"], 1)
            self.assertTrue(all(scenario["requires_private_content"] for scenario in document["scenarios"]))

        scenarios = documents["legacy-smokes"]["scenarios"]
        self.assertEqual(
            [scenario["id"] for scenario in scenarios],
            [
                "zbase1-load-spawn",
                "zdef1-load-spawn",
                "zboss-load-spawn",
                "zdm6-load-spawn",
            ],
        )
        self.assertTrue(next(s for s in scenarios if s["id"] == "zdm6-load-spawn")["deathmatch"])

        deathmatch = documents["deathmatch"]["scenarios"]
        self.assertEqual(
            [(scenario["map"], scenario["zdmflags"]) for scenario in deathmatch],
            [("q2dm1", 0), ("q2dm1", 1), ("q2dm1", 2), ("q2dm1", 3), ("zdm1", 0)],
        )
        self.assertTrue(all(scenario["deathmatch"] and scenario["probe_deathmatch_items"] for scenario in deathmatch))

        fixtures = documents["deathmatch-fixtures"]["scenarios"]
        self.assertEqual(
            [scenario["map"] for scenario in fixtures],
            ["zaereo_fixture_dm_partial"] + [f"zaereo_fixture_dm_m{index}" for index in range(8)],
        )
        self.assertTrue(all(scenario["deathmatch"] and scenario["probe_deathmatch_items"] for scenario in fixtures))

    def test_scenario_schema_is_strict_and_accepts_checked_in_file(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        documents = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in (SCENARIOS, DM_SCENARIOS, DM_FIXTURE_SCENARIOS)
        ]
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["$id"], "https://zaereo.invalid/schemas/runtime-matrix/v1")
        self.assertEqual(schema["properties"]["scenarios"]["minItems"], 1)
        self.assertTrue(
            schema["properties"]["scenarios"]["items"]["properties"]["requires_private_content"]
            == {"const": True}
        )
        if jsonschema is None:
            self.skipTest("jsonschema is not installed")
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema)
        for document in documents:
            validator.validate(document)

    def test_result_schema_is_strict(self) -> None:
        schema = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["$id"], "https://zaereo.invalid/schemas/runtime-matrix-result/v1")
        self.assertEqual(schema["properties"]["publication_status"], {"const": "private-local-only"})
        self.assertEqual(schema["properties"]["manual_command_delivery"], {"type": "boolean"})
        scenario_properties = schema["properties"]["scenarios"]["items"]["properties"]
        self.assertIn("command_delivery", scenario_properties)
        self.assertIn("launch_protocol", scenario_properties)
        self.assertIn("focus_diagnostic", scenario_properties)
        if jsonschema is None:
            self.skipTest("jsonschema is not installed")
        jsonschema.Draft202012Validator.check_schema(schema)

    @unittest.skipUnless(POWERSHELL, "PowerShell is required")
    def test_powershell_parser_accepts_matrix_script(self) -> None:
        escaped = str(SCRIPT).replace("'", "''")
        command = (
            "$tokens=$null; $errors=$null; "
            f"[System.Management.Automation.Language.Parser]::ParseFile('{escaped}', "
            "[ref]$tokens, [ref]$errors) | Out-Null; "
            "if ($errors.Count) { $errors | ForEach-Object { Write-Error $_ }; exit 1 }"
        )
        result = subprocess.run(
            [POWERSHELL, "-NoProfile", "-Command", command],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(POWERSHELL, "PowerShell is required")
    def test_whatif_is_non_mutating_and_validates_the_scenario(self) -> None:
        with tempfile.TemporaryDirectory(prefix="zaereo-matrix-") as temporary:
            workspace = Path(temporary)
            tools = workspace / "tools"
            tools.mkdir()
            scenarios = tools / "scenarios.json"
            scenarios.write_text(json.dumps(scenario_document()), encoding="utf-8")
            runner = tools / "runner.ps1"
            runner.write_text("param([string[]]$Rest)\n", encoding="utf-8")

            result = subprocess.run(
                [
                    POWERSHELL,
                    "-NoProfile",
                    "-File",
                    str(SCRIPT),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-ScenarioFile",
                    str(scenarios),
                    "-RunnerPath",
                    str(runner),
                    "-ResultRoot",
                    "build/test-results",
                    "-WhatIf",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Runtime matrix plan", result.stdout)
            self.assertIn("fixture-load (zbase1)", result.stdout)
            self.assertFalse((workspace / "build").exists())
            self.assertFalse((workspace / ".install").exists())

    @unittest.skipUnless(POWERSHELL, "PowerShell is required")
    def test_matrix_emits_private_json_and_junit_only_for_passed_reports(self) -> None:
        with tempfile.TemporaryDirectory(prefix="zaereo-matrix-") as temporary:
            workspace = Path(temporary)
            tools = workspace / "tools"
            tools.mkdir()
            scenarios = tools / "scenarios.json"
            scenarios.write_text(json.dumps(scenario_document()), encoding="utf-8")
            runner = tools / "runner.ps1"
            runner.write_text(passing_runner_script(), encoding="utf-8")

            result = subprocess.run(
                [
                    POWERSHELL,
                    "-NoProfile",
                    "-File",
                    str(SCRIPT),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-ScenarioFile",
                    str(scenarios),
                    "-RunnerPath",
                    str(runner),
                    "-ResultRoot",
                    "build/test-results",
                    "-RunId",
                    "fixture-run",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result_root = workspace / "build" / "test-results" / "fixture-run"
            summary = json.loads((result_root / "runtime-matrix.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["result"], "passed")
            self.assertEqual(summary["passed"], 1)
            self.assertFalse(summary["manual_command_delivery"])
            self.assertEqual(summary["scenarios"][0]["report"], ".install/runtime-matrix/fixture-run/fixture-load.json")
            self.assertEqual(summary["scenarios"][0]["launch_protocol"], "two-stage-window-before-mod-map/v1")
            self.assertEqual(summary["scenarios"][0]["command_delivery"], "engine-confirmed")
            self.assertEqual(summary["scenarios"][0]["focus_diagnostic"]["stage"], "queue-activation")
            if jsonschema is None:
                self.skipTest("jsonschema is not installed")
            jsonschema.Draft202012Validator(
                json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))
            ).validate(summary)
            self.assertIn('tests="1" failures="0"', (result_root / "junit.xml").read_text(encoding="utf-8"))
            self.assertTrue((workspace / ".install" / "runtime-matrix" / "fixture-run" / "fixture-load.json").is_file())

    @unittest.skipUnless(POWERSHELL, "PowerShell is required")
    def test_manual_delivery_is_forwarded_and_recorded_without_relaxing_proof(self) -> None:
        with tempfile.TemporaryDirectory(prefix="zaereo-matrix-") as temporary:
            workspace = Path(temporary)
            tools = workspace / "tools"
            tools.mkdir()
            scenarios = tools / "scenarios.json"
            scenarios.write_text(json.dumps(scenario_document()), encoding="utf-8")
            runner = tools / "runner.ps1"
            runner.write_text(passing_runner_script(require_manual_delivery=True), encoding="utf-8")

            result = subprocess.run(
                [
                    POWERSHELL,
                    "-NoProfile",
                    "-File",
                    str(SCRIPT),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-ScenarioFile",
                    str(scenarios),
                    "-RunnerPath",
                    str(runner),
                    "-ResultRoot",
                    "build/test-results",
                    "-RunId",
                    "fixture-manual-run",
                    "-ManualCommandDelivery",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads(
                (workspace / "build" / "test-results" / "fixture-manual-run" / "runtime-matrix.json").read_text(encoding="utf-8")
            )
            self.assertTrue(summary["manual_command_delivery"])
            self.assertEqual(summary["scenarios"][0]["command_delivery"], "engine-confirmed")

    @unittest.skipUnless(POWERSHELL, "PowerShell is required")
    def test_matrix_rejects_passed_report_without_complete_v2_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="zaereo-matrix-") as temporary:
            workspace = Path(temporary)
            tools = workspace / "tools"
            tools.mkdir()
            scenarios = tools / "scenarios.json"
            scenarios.write_text(json.dumps(scenario_document()), encoding="utf-8")
            runner = tools / "runner.ps1"
            runner.write_text(
                "param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Rest)\n"
                "$index = [Array]::IndexOf($Rest, '-ReportOutput')\n"
                "$path = $Rest[$index + 1]\n"
                "[IO.Directory]::CreateDirectory((Split-Path -Parent $path)) | Out-Null\n"
                "[IO.File]::WriteAllText($path, '{\"schema\":\"zaereo.runtime-smoke/v2\",\"schema_version\":2,\"result\":\"passed\"}', [Text.UTF8Encoding]::new($false))\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    POWERSHELL,
                    "-NoProfile",
                    "-File",
                    str(SCRIPT),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-ScenarioFile",
                    str(scenarios),
                    "-RunnerPath",
                    str(runner),
                    "-ResultRoot",
                    "build/test-results",
                    "-RunId",
                    "fixture-invalid-pass",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            summary = json.loads(
                (workspace / "build" / "test-results" / "fixture-invalid-pass" / "runtime-matrix.json").read_text(encoding="utf-8")
            )
            self.assertEqual(summary["scenarios"][0]["result"], "invalid-report")
            self.assertIn("without required v2 evidence", summary["scenarios"][0]["failure"])

    @unittest.skipUnless(POWERSHELL, "PowerShell is required")
    def test_matrix_fails_closed_but_preserves_results_for_failed_reports(self) -> None:
        with tempfile.TemporaryDirectory(prefix="zaereo-matrix-") as temporary:
            workspace = Path(temporary)
            tools = workspace / "tools"
            tools.mkdir()
            scenarios = tools / "scenarios.json"
            scenarios.write_text(json.dumps(scenario_document()), encoding="utf-8")
            runner = tools / "runner.ps1"
            runner.write_text(
                "param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Rest)\n"
                "$index = [Array]::IndexOf($Rest, '-ReportOutput')\n"
                "$path = $Rest[$index + 1]\n"
                "[IO.Directory]::CreateDirectory((Split-Path -Parent $path)) | Out-Null\n"
                "$report = @{ schema = 'zaereo.runtime-smoke/v2'; schema_version = 2; result = 'failed' } | ConvertTo-Json\n"
                "[IO.File]::WriteAllText($path, $report, [Text.UTF8Encoding]::new($false))\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    POWERSHELL,
                    "-NoProfile",
                    "-File",
                    str(SCRIPT),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-ScenarioFile",
                    str(scenarios),
                    "-RunnerPath",
                    str(runner),
                    "-ResultRoot",
                    "build/test-results",
                    "-RunId",
                    "fixture-failed-run",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Runtime matrix failed (1/1)", result.stdout + result.stderr)
            result_root = workspace / "build" / "test-results" / "fixture-failed-run"
            summary = json.loads((result_root / "runtime-matrix.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["result"], "failed")
            self.assertEqual(summary["failed"], 1)
            self.assertEqual(summary["scenarios"][0]["result"], "failed")
            if jsonschema is None:
                self.skipTest("jsonschema is not installed")
            jsonschema.Draft202012Validator(
                json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))
            ).validate(summary)
            self.assertIn('tests="1" failures="1"', (result_root / "junit.xml").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

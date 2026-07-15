from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "run_game.ps1"
SCHEMA = ROOT / "docs" / "provenance" / "schemas" / "runtime-smoke.schema.json"
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


class RuntimeHarnessTests(unittest.TestCase):
    def test_script_has_no_machine_specific_path_and_brackets_current_session(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")

        self.assertNotRegex(text, r"(?i)[a-z]:\\(?:users|program files|_source)")
        self.assertNotIn("Invoke-Expression", text)
        self.assertIn('"zaereo_paths.ps1"', text)
        self.assertIn("Start-Process", text)
        self.assertNotIn("-WindowStyle Hidden", text)
        self.assertIn('"-window"', text)
        self.assertRegex(text, r'\$arguments\s*=\s*@\(\s*"-window"')
        self.assertIn('"-width", "1280"', text)
        self.assertIn('"-height", "720"', text)
        self.assertIn('"+set", "v_windowmode", "0"', text)
        self.assertIn("ZaeREoWindowProbe", text)
        self.assertIn("EnumWindows", text)
        self.assertIn("GetVisibleTopLevelWindows", text)
        self.assertIn("SendConsoleCommand", text)
        self.assertIn("non_windowed_visible_observed", text)
        self.assertIn("window_safety_abort", text)
        self.assertIn("two-stage-window-before-mod-map/v1", text)
        self.assertIn("mod_map_command_injected_after_window_verification", text)
        self.assertIn("3-second startup quiescence interval", text)
        self.assertIn("if ($windowSafetyAborted)", text)
        self.assertIn('"+set", "v_width", "1280"', text)
        self.assertIn('"+set", "v_height", "720"', text)
        self.assertNotIn('"+set", "game"', text)
        self.assertNotIn('"+map", $Map', text)
        self.assertIn('"set v_windowmode 0"', text)
        self.assertIn('"set game zaereo"', text)
        self.assertIn('"map $Map"', text)
        self.assertIn('"set deathmatch $(if ($Deathmatch)', text)
        self.assertIn('"set zdmflags $ZdmFlags"', text)
        self.assertIn("-ZdmFlags requires -Deathmatch", text)
        self.assertIn("-ProbeDeathmatchItems requires -Deathmatch", text)
        self.assertIn('"sv zaereo_dm_probe"', text)
        self.assertIn("zaero_entities_added", text)
        self.assertIn("dm_item_probe", text)
        self.assertIn("ZAEREO_DM_PROBE_ITEM", text)
        self.assertIn("WaitForExit", text)
        self.assertIn("Get-RereleaseProcesses", text)
        self.assertIn("Stop-Process -Id $current.Id -Force", text)
        self.assertIn("Refusing to launch while the selected Rerelease executable is already running", text)
        self.assertIn("ZAEREO_RUNTIME_BEGIN_", text)
        self.assertIn("ZAEREO_RUNTIME_END_", text)
        self.assertIn("$sessionLog", text)
        self.assertIn("Begin\\(\\) from", text)
        self.assertIn('schema = "zaereo.runtime-smoke/v2"', text)
        self.assertIn("managed_manifest_sha256", text)
        self.assertIn("process_exit_code_accepted", text)
        self.assertIn("crash_dumps", text)
        self.assertIn('publication_status = "private-local-only"', text)
        self.assertIn('Assert-StrictChildPath $installRoot $reportPath "runtime report"', text)

    @unittest.skipUnless(POWERSHELL, "PowerShell is required")
    def test_powershell_parser_accepts_script(self) -> None:
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
    def test_whatif_validates_a_managed_stage_without_launching(self) -> None:
        with tempfile.TemporaryDirectory(prefix="zaereo-runtime-") as temporary:
            workspace = Path(temporary)
            engine = workspace / "engine"
            user = workspace / "user"
            mod = user / "zaereo"
            (engine / "baseq2").mkdir(parents=True)
            mod.mkdir(parents=True)
            (engine / "quake2ex.exe").write_bytes(b"synthetic executable")
            (mod / "game_x64.dll").write_bytes(b"synthetic DLL")
            (mod / "pak0.pak").write_bytes(b"synthetic PAK")
            (mod / ".zaereo-managed-files.json").write_text(
                '{"schema_version":1,"product":"test","files":[]}',
                encoding="utf-8",
            )
            report = workspace / ".install" / "runtime-reports" / "zbase1.json"

            result = subprocess.run(
                [
                    POWERSHELL,
                    "-NoProfile",
                    "-File",
                    str(SCRIPT),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-EngineRoot",
                    str(engine),
                    "-UserRoot",
                    str(user),
                    "-Map",
                    "zbase1",
                    "-Deathmatch",
                    "-ZdmFlags",
                    "3",
                    "-ProbeDeathmatchItems",
                    "-ReportOutput",
                    str(report),
                    "-WhatIf",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Runtime smoke plan", result.stdout)
            self.assertIn("mode:    deathmatch", result.stdout)
            self.assertIn("zdmflags: 3", result.stdout)
            self.assertIn("DM item probe: True", result.stdout)
            self.assertFalse(report.exists())

            invalid = subprocess.run(
                [
                    POWERSHELL,
                    "-NoProfile",
                    "-File",
                    str(SCRIPT),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-EngineRoot",
                    str(engine),
                    "-UserRoot",
                    str(user),
                    "-Map",
                    "q2dm1",
                    "-ZdmFlags",
                    "1",
                    "-WhatIf",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn(
                "-ZdmFlags requires -Deathmatch",
                invalid.stdout + invalid.stderr,
            )

            invalid_probe = subprocess.run(
                [
                    POWERSHELL,
                    "-NoProfile",
                    "-File",
                    str(SCRIPT),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-Map",
                    "q2dm1",
                    "-ProbeDeathmatchItems",
                    "-WhatIf",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(invalid_probe.returncode, 0)
            self.assertIn(
                "-ProbeDeathmatchItems requires -Deathmatch",
                invalid_probe.stdout + invalid_probe.stderr,
            )

    def test_runtime_report_schema_is_strict_and_accepts_a_valid_report(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["$id"], "https://zaereo.invalid/schemas/runtime-smoke/v2")
        self.assertEqual(schema["properties"]["schema"]["const"], "zaereo.runtime-smoke/v2")
        self.assertEqual(
            schema["properties"]["publication_status"]["const"],
            "private-local-only",
        )
        self.assertEqual(schema["properties"]["zdmflags"]["maximum"], 3)
        self.assertEqual(
            schema["properties"]["game_mode"]["enum"],
            ["single-player", "deathmatch"],
        )
        probe_schema = schema["properties"]["dm_item_probe"]["oneOf"][1]
        self.assertEqual(probe_schema["properties"]["items"]["maxItems"], 8)

        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema is not installed")

        jsonschema.Draft202012Validator.check_schema(schema)
        report = {
            "schema": "zaereo.runtime-smoke/v2",
            "schema_version": 2,
            "result": "passed",
            "run_id": "a" * 32,
            "started_utc": "2026-07-14T12:00:00Z",
            "finished_utc": "2026-07-14T12:00:02Z",
            "map": "zbase1",
            "game_mode": "deathmatch",
            "zdmflags": 0,
            "zaero_entities_added": 8,
            "dm_item_probe": {
                "requested": True,
                "complete": True,
                "recorded_count": 1,
                "live_count": 1,
                "items": [
                    {
                        "set_index": 0,
                        "classname": "weapon_soniccannon",
                        "spawn_ordinal": 1,
                        "attempt": 1,
                        "entity_number": 99,
                        "start_origin": [0.0, 0.0, 24.0],
                        "placed_origin": [128.0, 0.0, 40.0],
                        "live_origin": [128.0, 0.0, -15.0],
                        "placement_radius_xy": 128.0,
                        "placement_height": 16.0,
                        "live": True,
                        "movetype_toss": True,
                        "solid_trigger": True,
                        "touch_item": True,
                        "ir_visible": True,
                        "grounded": True,
                    }
                ],
            },
            "game_directory": "zaereo",
            "window_mode": "windowed",
            "window_width": 1280,
            "window_height": 720,
            "window_probe": {
                "method": "win32-visible-top-level-window-enumeration",
                "process_id": 1234,
                "style_hex": "0x14CF0000",
                "captioned": True,
                "popup": False,
                "left": 100,
                "top": 100,
                "width": 1296,
                "height": 759,
            },
            "non_windowed_visible_observed": False,
            "window_safety_abort": False,
            "launch_protocol": "two-stage-window-before-mod-map/v1",
            "mod_map_command_injected_after_window_verification": True,
            "engine_executable": "quake2ex_steam.exe",
            "engine_sha256": "1" * 64,
            "game_dll_sha256": "2" * 64,
            "pak0_sha256": "3" * 64,
            "managed_manifest_sha256": "4" * 64,
            "process_exit_code": 1,
            "process_exit_code_accepted": True,
            "timed_out": False,
            "wait_frames": 200,
            "markers": {
                "session_begin": True,
                "windowed_mode_confirmed": True,
                "mod_map_command_injected_after_window_verification": True,
                "game_dll_loaded": True,
                "game_initialized": True,
                "map_spawned": True,
                "client_entered": True,
                "game_shutdown": True,
                "session_end": True,
            },
            "stderr_empty": True,
            "fatal_matches": [],
            "crash_dumps": [],
            "console_log": "stdout.txt",
            "publication_status": "private-local-only",
        }
        jsonschema.Draft202012Validator(schema).validate(report)

        false_pass = json.loads(json.dumps(report))
        false_pass["markers"]["windowed_mode_confirmed"] = False
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(false_pass)

        safety_aborted_pass = json.loads(json.dumps(report))
        safety_aborted_pass["window_safety_abort"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(safety_aborted_pass)

        missing_safety_evidence = json.loads(json.dumps(report))
        del missing_safety_evidence["window_safety_abort"]
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(missing_safety_evidence)

        impossible_count = json.loads(json.dumps(report))
        impossible_count["zaero_entities_added"] = 9
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(impossible_count)

        impossible_radius = json.loads(json.dumps(report))
        impossible_radius["dm_item_probe"]["items"][0]["placement_radius_xy"] = 127.0
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(impossible_radius)


if __name__ == "__main__":
    unittest.main()

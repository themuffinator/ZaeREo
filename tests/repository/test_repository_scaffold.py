from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]


class RepositoryScaffoldTests(unittest.TestCase):
    def test_editorconfig_covers_repository_languages(self) -> None:
        text = (ROOT / ".editorconfig").read_text(encoding="utf-8")
        self.assertIn("root = true", text)
        self.assertIn("charset = utf-8", text)
        self.assertIn("insert_final_newline = true", text)
        for extension in ("cpp", "py", "ps1", "json", "yml", "vcxproj", "md"):
            self.assertIn(extension, text)

    def test_dependabot_has_a_bounded_actions_schedule(self) -> None:
        text = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^version: 2$")
        self.assertIn('package-ecosystem: "github-actions"', text)
        self.assertIn('directory: "/"', text)
        self.assertIn('interval: "weekly"', text)
        self.assertRegex(text, r"(?m)^\s+open-pull-requests-limit: [1-9][0-9]*$")

    def test_shared_launch_configuration_uses_the_verified_windowed_wrapper(self) -> None:
        path = ROOT / ".vscode" / "launch.json"
        launch = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(launch["version"], "0.2.0")
        self.assertTrue(launch["configurations"])

        configuration = launch["configurations"][0]
        self.assertEqual(configuration["type"], "cppvsdbg")
        self.assertEqual(configuration["program"], "pwsh.exe")
        self.assertEqual(configuration["cwd"], "${workspaceFolder}")
        self.assertNotIn("preLaunchTask", configuration)
        self.assertEqual(
            configuration["args"],
            [
                "-NoLogo",
                "-NoProfile",
                "-File",
                "${workspaceFolder}\\tools\\run_game.ps1",
                "-EngineRoot",
                "${input:q2RereleaseEngineRoot}",
                "-UserRoot",
                "${input:q2RereleaseUserRoot}",
                "-Map",
                "${input:zaereoRuntimeMap}",
            ],
        )
        self.assertEqual(configuration["console"], "integratedTerminal")

        serialized = json.dumps(launch)
        self.assertIsNone(re.search(r"(?i)(?:[a-z]:\\\\|program files|steamapps)", serialized))
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("never start it fullscreen", agents)
        self.assertIn("`-window`", agents)
        self.assertIn("v_windowmode 0", agents)
        input_ids = {item["id"] for item in launch["inputs"]}
        self.assertEqual(
            input_ids,
            {
                "q2RereleaseEngineRoot",
                "q2RereleaseUserRoot",
                "zaereoRuntimeMap",
            },
        )

        tasks = json.loads((ROOT / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        runtime_tasks = [
            task
            for task in tasks["tasks"]
            if task["label"] == "ZaeREo: Run verified windowed runtime smoke"
        ]
        self.assertEqual(len(runtime_tasks), 1)
        self.assertEqual(runtime_tasks[0]["command"], "pwsh")
        self.assertIn("./tools/run_game.ps1", runtime_tasks[0]["args"])
        self.assertNotIn("-window", runtime_tasks[0]["args"])
        task_input_ids = {item["id"] for item in tasks["inputs"]}
        self.assertTrue(input_ids.issubset(task_input_ids))

        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("!.vscode/launch.json", ignore.splitlines())
        for pattern in (
            "*.dll",
            "*.exe",
            "SHA256SUMS-*.txt",
            "MANIFEST.json",
            "BUILD-METADATA.json",
            "SBOM.spdx.json",
            "LICENSE-MANIFEST.json",
        ):
            self.assertIn(pattern, ignore.splitlines())

    def test_upstream_record_matches_the_machine_readable_baseline(self) -> None:
        baseline_document = json.loads(
            (ROOT / "docs" / "provenance" / "baselines.json").read_text(
                encoding="utf-8"
            )
        )
        baseline = baseline_document["baselines"]["quake2_rerelease"]
        match = json.loads(
            (ROOT / "docs" / "provenance" / "upstream-match.json").read_text(
                encoding="utf-8"
            )
        )
        upstream = (ROOT / "docs" / "UPSTREAM.md").read_text(encoding="utf-8")
        normalized_upstream = " ".join(upstream.split())

        self.assertIn("hash-recorded supplied substrate", upstream)
        self.assertIn("exact official Git content match", normalized_upstream)
        self.assertEqual(baseline["origin_status"], "verified-exact-content-match")
        self.assertEqual(match["verification"]["match_status"], "verified-exact-content-match")
        self.assertEqual(
            baseline["official_git"]["commit"], match["selected_match"]["commit"]
        )
        self.assertEqual(
            baseline["official_git"]["subtree_tree_oid"],
            match["selected_match"]["subtree_tree_oid"],
        )
        self.assertEqual(match["baseline"]["tree_sha256"], baseline["tree_sha256"])
        self.assertIn(baseline["official_git"]["commit"], upstream)
        self.assertIn(baseline["official_git"]["subtree_tree_oid"], upstream)
        self.assertIn(baseline["tree_sha256"], upstream)
        self.assertIn(f"{baseline['file_count']} files", upstream)
        self.assertIn(f"{baseline['total_size']:,} bytes", upstream)
        self.assertIn(
            baseline["aggregate_algorithm"]
            .split("(", 1)[0]
            .strip()
            .casefold()
            .replace("-", ""),
            upstream.casefold().replace("-", ""),
        )


if __name__ == "__main__":
    unittest.main()

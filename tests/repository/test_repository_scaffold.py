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

    def test_shared_launch_configuration_contains_no_machine_path(self) -> None:
        path = ROOT / ".vscode" / "launch.json"
        launch = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(launch["version"], "0.2.0")
        self.assertTrue(launch["configurations"])

        configuration = launch["configurations"][0]
        self.assertEqual(configuration["type"], "cppvsdbg")
        self.assertEqual(configuration["program"], "${input:q2Executable}")
        self.assertEqual(configuration["cwd"], "${input:q2RereleaseEngineRoot}")
        self.assertNotIn("preLaunchTask", configuration)
        self.assertEqual(
            configuration["args"],
            [
                "+set", "game", "zaereo",
                "+set", "developer", "1",
                "+exec", "zaerostart.cfg",
            ],
        )

        serialized = json.dumps(launch)
        self.assertIsNone(re.search(r"(?i)(?:[a-z]:\\\\|program files|steamapps)", serialized))
        input_ids = {item["id"] for item in launch["inputs"]}
        self.assertEqual(input_ids, {"q2Executable", "q2RereleaseEngineRoot"})

        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("!.vscode/launch.json", ignore.splitlines())

    def test_upstream_record_matches_the_machine_readable_baseline(self) -> None:
        baseline_document = json.loads(
            (ROOT / "docs" / "provenance" / "baselines.json").read_text(
                encoding="utf-8"
            )
        )
        baseline = baseline_document["baselines"]["quake2_rerelease"]
        upstream = (ROOT / "docs" / "UPSTREAM.md").read_text(encoding="utf-8")
        normalized_upstream = " ".join(upstream.split())

        self.assertIn("hash-recorded supplied substrate", upstream)
        self.assertIn("not a pinned upstream commit", normalized_upstream)
        self.assertRegex(upstream, r"(?i)official commit \| \*\*unresolved\*\*")
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

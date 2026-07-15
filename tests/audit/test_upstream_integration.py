from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from audit_common import stable_json_text, tree_manifest  # noqa: E402
from audit_upstream_integration import (  # noqa: E402
    IntegrationAuditError,
    build_integration_report,
    integration_markdown,
)


class UpstreamIntegrationAuditTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> tuple[Path, Path, Path, Path]:
        baseline_root = root / "baseline"
        current_root = root / "current"
        repository_root = root / "repository"
        baseline_root.mkdir()
        current_root.mkdir()
        repository_root.mkdir()
        (repository_root / "evidence.md").write_text("evidence\n", encoding="utf-8")
        (baseline_root / "a.cpp").write_text("old\n", encoding="utf-8")
        baseline = tree_manifest(baseline_root)
        baseline.update(
            {
                "description": "fixture",
                "origin": "fixture",
                "official_git": {
                    "commit": "a" * 40,
                    "subtree": "rerelease",
                },
            }
        )
        baselines_path = root / "baselines.json"
        baselines_path.write_text(
            stable_json_text({"baselines": {"quake2_rerelease": baseline}}),
            encoding="utf-8",
        )
        (current_root / "a.cpp").write_text("new\n", encoding="utf-8")
        (current_root / "b.cpp").write_text("added\n", encoding="utf-8")
        policy = {
            "schema": "zaereo.upstream-integration-policy/v1",
            "policy_id": "fixture",
            "revision": 1,
            "baseline": {
                "key": "quake2_rerelease",
                "tree_sha256": baseline["tree_sha256"],
                "official_commit": "a" * 40,
                "official_subtree": "rerelease",
            },
            "categories": [
                {
                    "id": "fixture",
                    "description": "fixture classification",
                    "evidence": ["evidence.md"],
                    "modified": ["a.cpp"],
                    "added": ["b.cpp"],
                    "removed": [],
                }
            ],
        }
        policy_path = root / "policy.json"
        policy_path.write_text(stable_json_text(policy), encoding="utf-8")
        return current_root, baselines_path, policy_path, repository_root

    def test_checked_in_report_reproduces_exactly(self) -> None:
        report = build_integration_report(ROOT / "src")
        expected = json.loads(
            (ROOT / "docs" / "audits" / "upstream-integration.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(report, expected)
        self.assertEqual(integration_markdown(report), (ROOT / "docs" / "audits" / "upstream-integration.md").read_text(encoding="utf-8"))
        self.assertTrue(report["summary"]["policy_complete"])
        self.assertEqual(report["summary"]["modified"], 33)
        self.assertEqual(report["summary"]["added"], 34)
        self.assertEqual(report["summary"]["removed"], 1)

    def test_complete_fixture_classifies_every_difference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            current, baselines, policy, repository = self.make_fixture(Path(temporary))
            report = build_integration_report(
                current,
                baselines,
                policy,
                repository_root=repository,
            )
            self.assertTrue(report["summary"]["policy_complete"])
            self.assertEqual(report["summary"]["difference_count"], 2)

    def test_unclassified_and_stale_records_are_both_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            current, baselines, policy_path, repository = self.make_fixture(Path(temporary))
            (current / "unknown.cpp").write_text("unknown\n", encoding="utf-8")
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            policy["categories"][0]["removed"].append("never-there.cpp")
            policy_path.write_text(stable_json_text(policy), encoding="utf-8")
            report = build_integration_report(
                current,
                baselines,
                policy_path,
                repository_root=repository,
            )
            self.assertFalse(report["summary"]["policy_complete"])
            self.assertEqual(report["unclassified"], [{"path": "unknown.cpp", "status": "added"}])
            self.assertEqual(report["stale_policy"][0]["path"], "never-there.cpp")

    def test_wrong_baseline_and_duplicate_assignment_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            current, baselines, policy_path, repository = self.make_fixture(Path(temporary))
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            policy["baseline"]["tree_sha256"] = "0" * 64
            policy_path.write_text(stable_json_text(policy), encoding="utf-8")
            with self.assertRaisesRegex(IntegrationAuditError, "baseline differs"):
                build_integration_report(
                    current,
                    baselines,
                    policy_path,
                    repository_root=repository,
                )

            policy["baseline"]["tree_sha256"] = json.loads(
                baselines.read_text(encoding="utf-8")
            )["baselines"]["quake2_rerelease"]["tree_sha256"]
            policy["categories"].append(deepcopy(policy["categories"][0]))
            policy["categories"][1]["id"] = "duplicate-path-category"
            policy_path.write_text(stable_json_text(policy), encoding="utf-8")
            with self.assertRaisesRegex(IntegrationAuditError, "assigned twice"):
                build_integration_report(
                    current,
                    baselines,
                    policy_path,
                    repository_root=repository,
                )


if __name__ == "__main__":
    unittest.main()

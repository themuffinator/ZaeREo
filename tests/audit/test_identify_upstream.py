from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from audit_common import tree_manifest  # noqa: E402
from identify_upstream import UpstreamError, _load_baseline, identify_upstream  # noqa: E402


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return result.stdout.strip()


class IdentifyUpstreamTests(unittest.TestCase):
    def make_repository(self, root: Path) -> tuple[Path, dict, str, str]:
        repository = root / "official"
        source = repository / "rerelease"
        source.mkdir(parents=True)
        git(repository, "init", "-b", "main")
        git(repository, "config", "user.name", "ZaeREo test")
        git(repository, "config", "user.email", "test@example.invalid")
        (source / "a.txt").write_bytes(b"first\n")
        (source / "nested").mkdir()
        (source / "nested" / "b.bin").write_bytes(b"\x00\x01")
        git(repository, "add", "rerelease")
        git(repository, "commit", "-m", "matching tree")
        matching_commit = git(repository, "rev-parse", "HEAD")
        baseline = tree_manifest(source)

        (source / "a.txt").write_bytes(b"changed\n")
        git(repository, "add", "rerelease/a.txt")
        git(repository, "commit", "-m", "changed tree")
        main_commit = git(repository, "rev-parse", "HEAD")
        return repository, baseline, matching_commit, main_commit

    def test_finds_exact_historical_subtree_and_does_not_false_match_main(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository, baseline, matching_commit, main_commit = self.make_repository(Path(temporary))
            report = identify_upstream(
                repository,
                baseline,
                subtree="rerelease",
                preferred_ref="refs/heads/main",
                baseline_key="fixture",
            )
            self.assertEqual(report["selected_match"]["commit"], matching_commit)
            self.assertNotEqual(report["selected_match"]["commit"], main_commit)
            self.assertEqual(report["selected_match"]["selection_rule"], "first-topological-exact-match")
            self.assertEqual(report["scan"]["exact_commit_count"], 1)

    def test_prefers_main_when_main_is_the_exact_match(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository, _, _, main_commit = self.make_repository(Path(temporary))
            baseline = tree_manifest(repository / "rerelease")
            report = identify_upstream(
                repository,
                baseline,
                subtree="rerelease",
                preferred_ref="refs/heads/main",
                baseline_key="fixture",
            )
            self.assertEqual(report["selected_match"]["commit"], main_commit)
            self.assertEqual(report["selected_match"]["selection_rule"], "preferred-ref-exact-match")

    def test_baseline_loader_rejects_case_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "baseline.json"
            fixture = {
                "baselines": {
                    "fixture": {
                        "file_count": 2,
                        "total_size": 2,
                        "tree_sha256": "0" * 64,
                        "files": [
                            {"path": "A.txt", "size": 1, "sha256": "1" * 64},
                            {"path": "a.txt", "size": 1, "sha256": "2" * 64},
                        ],
                    }
                }
            }
            path.write_text(json.dumps(fixture), encoding="utf-8")
            with self.assertRaisesRegex(UpstreamError, "case-colliding"):
                _load_baseline(path, "fixture")


if __name__ == "__main__":
    unittest.main()

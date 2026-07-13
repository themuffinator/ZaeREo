from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))

from audit_repository import audit_paths, audit_repository  # noqa: E402
from create_evidence_snapshot import create_snapshot  # noqa: E402


class RepositoryCandidateAuditTests(unittest.TestCase):
    def test_safe_text_candidate_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("safe\n", encoding="utf-8")
            first = audit_paths(root, ["README.md"], head="abc")
            second = audit_paths(root, ["README.md"], head="abc")
            self.assertEqual(first, second)
            self.assertTrue(first["summary"]["ready_for_private_snapshot"])
            self.assertEqual(first["summary"]["candidate_file_count"], 1)

    def test_rejects_generated_binary_secret_and_hardcoded_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "dist").mkdir()
            (root / "tools").mkdir()
            (root / "dist" / "game.dll").write_bytes(b"MZ")
            (root / "tools" / "bad.ps1").write_text(
                'Set-Location "E:\\_SOURCE\\private"\n'
                'Write-Output "github_pat_' + ('a' * 24) + '"\n',
                encoding="utf-8",
            )
            report = audit_paths(root, ["dist/game.dll", "tools/bad.ps1"])
            codes = {item["code"] for item in report["violations"]}
            self.assertIn("generated-directory", codes)
            self.assertIn("forbidden-binary", codes)
            self.assertIn("secret-pattern", codes)
            self.assertIn("hardcoded-local-path", codes)
            self.assertFalse(report["summary"]["ready_for_private_snapshot"])

    def test_git_discovery_excludes_ignored_private_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / ".gitignore").write_text(".install/\n", encoding="utf-8")
            (root / "README.md").write_text("safe\n", encoding="utf-8")
            (root / ".install").mkdir()
            (root / ".install" / "pak0.pak").write_bytes(b"private")
            report = audit_repository(root)
            paths = {item["path"] for item in report["files"]}
            self.assertEqual(paths, {".gitignore", "README.md"})
            self.assertTrue(report["summary"]["ready_for_private_snapshot"])

    def test_private_snapshot_uses_temporary_index_and_exact_candidate_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "test@example.invalid"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "Repository Test"],
                check=True,
            )
            (root / ".gitignore").write_text("dist/\n", encoding="utf-8")
            (root / "seed.txt").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", ".gitignore", "seed.txt"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "seed"], check=True)
            (root / "new.txt").write_text("new\n", encoding="utf-8")
            (root / "dist").mkdir()
            (root / "dist" / "ignored.zip").write_bytes(b"ignored")

            real_index_before = subprocess.run(
                ["git", "-C", str(root), "diff", "--cached", "--name-only"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            report = create_snapshot(root, "refs/zaereo-private/test-snapshot")
            real_index_after = subprocess.run(
                ["git", "-C", str(root), "diff", "--cached", "--name-only"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout

            self.assertEqual(real_index_before, real_index_after)
            self.assertEqual(report["candidate_file_count"], 3)
            tree_paths = subprocess.run(
                ["git", "-C", str(root), "ls-tree", "-r", "--name-only", report["git_tree"]],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
            self.assertEqual(tree_paths, [".gitignore", "new.txt", "seed.txt"])
            self.assertEqual(
                subprocess.run(
                    ["git", "-C", str(root), "cat-file", "-t", report["ref"]],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip(),
                "tree",
            )


if __name__ == "__main__":
    unittest.main()

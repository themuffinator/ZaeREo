from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

try:
    import jsonschema
except ImportError:  # pragma: no cover - optional test dependency
    jsonschema = None


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "release_readiness.py"
SCHEMA = ROOT / "docs" / "provenance" / "schemas" / "release-readiness.schema.json"


class ReleaseReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.output_root = Path(tempfile.mkdtemp(prefix="readiness-test-", dir=ROOT / "dist"))
        self.output = self.output_root / "release-readiness.json"

    def tearDown(self) -> None:
        shutil.rmtree(self.output_root, ignore_errors=True)

    def invoke(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(TOOL), *arguments],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )

    def generate_local_full(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return self.invoke(
            "--mode",
            "local-full",
            "--channel",
            "private-local-filesystem",
            "--profile",
            "local-full-private",
            "--output",
            str(self.output),
            *arguments,
        )

    def test_generates_a_schema_valid_blocked_private_record(self) -> None:
        result = self.generate_local_full()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.output.is_file())
        record = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(record["schema"], "zaereo.release-readiness/v1")
        self.assertFalse(record["ready"])
        self.assertEqual(record["publication_status"], "private-local-only")
        self.assertFalse(record["publication_attempted"])
        self.assertEqual(record["mode"], "local-full")
        self.assertEqual(record["profile"], "local-full-private")
        self.assertEqual(record["policy"]["path"], "docs/provenance/distribution-policy.json")
        input_ids = {item["id"] for item in record["inputs"]}
        self.assertTrue(
            {
                "runtime-scenarios",
                "runtime-scenarios-dm",
                "runtime-scenarios-dm-fixtures",
            }.issubset(input_ids)
        )
        self.assertTrue(record["unmet_requirements"])
        self.assertIn("local-full-permanent-private", {item["id"] for item in record["non_waivable_rules"]})
        if jsonschema is not None:
            jsonschema.Draft202012Validator(
                json.loads(SCHEMA.read_text(encoding="utf-8"))
            ).validate(record)

        validation = self.invoke("--validate", str(self.output))
        self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
        self.assertIn("ready=false", validation.stdout)

    def test_require_ready_fails_after_preserving_blocked_evidence(self) -> None:
        result = self.generate_local_full("--require-ready")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertTrue(self.output.is_file())
        self.assertFalse(json.loads(self.output.read_text(encoding="utf-8"))["ready"])

    def test_rejects_noncanonical_profile_and_output_escape_without_writing(self) -> None:
        profile = self.invoke(
            "--mode",
            "local-full",
            "--channel",
            "private-local-filesystem",
            "--profile",
            "playable-stable",
            "--output",
            str(self.output),
        )
        self.assertEqual(profile.returncode, 2)
        self.assertIn("not allowed", profile.stderr)
        self.assertFalse(self.output.exists())

        outside = ROOT / "release-readiness-outside-dist.json"
        try:
            escape = self.invoke(
                "--mode",
                "local-full",
                "--channel",
                "private-local-filesystem",
                "--profile",
                "local-full-private",
                "--output",
                str(outside),
            )
            self.assertEqual(escape.returncode, 2)
            self.assertIn("must remain below", escape.stderr)
            self.assertFalse(outside.exists())
        finally:
            outside.unlink(missing_ok=True)

    def test_validator_rejects_a_hand_promoted_record(self) -> None:
        result = self.generate_local_full()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        record = json.loads(self.output.read_text(encoding="utf-8"))
        record["ready"] = True
        record["publication_status"] = "eligible"
        record["unmet_requirements"] = []
        for item in record["gates"]:
            if item["required"]:
                item["status"] = "passed"
        for item in record["non_waivable_rules"]:
            item["status"] = "passed"
        self.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

        validation = self.invoke("--validate", str(self.output))
        self.assertEqual(validation.returncode, 2)
        self.assertIn("conflicts with the fail-closed distribution policy", validation.stderr)

    def test_release_tooling_has_no_publication_escape_hatch(self) -> None:
        source = TOOL.read_text(encoding="utf-8").lower()
        self.assertNotIn("gh release", source)
        self.assertNotIn("github.com", source)
        self.assertNotIn("requests.", source)
        self.assertIn("no command-line override", source)


if __name__ == "__main__":
    unittest.main()

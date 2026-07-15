from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from audit_common import stable_json_text  # noqa: E402
from audit_traceability import (  # noqa: E402
    TraceabilityError,
    bsp_coverage_markdown,
    build_traceability_reports,
    source_coverage_markdown,
)


class TraceabilityAuditTests(unittest.TestCase):
    def test_checked_in_coverage_reproduces_and_has_no_uncovered_records(self) -> None:
        source, bsp = build_traceability_reports()
        expected_source = json.loads(
            (ROOT / "docs" / "audits" / "source-delta-coverage.json").read_text(encoding="utf-8")
        )
        expected_bsp = json.loads(
            (ROOT / "docs" / "audits" / "bsp-contract-coverage.json").read_text(encoding="utf-8")
        )
        self.assertEqual(source, expected_source)
        self.assertEqual(bsp, expected_bsp)
        self.assertEqual(
            source_coverage_markdown(source),
            (ROOT / "docs" / "audits" / "source-delta-coverage.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            bsp_coverage_markdown(bsp),
            (ROOT / "docs" / "audits" / "bsp-contract-coverage.md").read_text(encoding="utf-8"),
        )
        self.assertTrue(source["summary"]["complete"])
        self.assertTrue(bsp["summary"]["complete"])
        self.assertEqual(source["summary"]["path_record_count"], 102)
        self.assertGreater(source["summary"]["global_record_count"], 0)
        self.assertEqual(bsp["summary"]["classname_record_count"], 132)
        self.assertGreater(bsp["summary"]["spawnflag_value_record_count"], 0)

    def test_missing_per_classname_mapper_evidence_fails_closed(self) -> None:
        source_path = ROOT / "docs" / "audits" / "source-delta.json"
        baseline_bsp = json.loads(
            (ROOT / "docs" / "audits" / "bsp-entities.json").read_text(encoding="utf-8")
        )
        del baseline_bsp["global"]["classname_key_counts"]
        with tempfile.TemporaryDirectory() as temporary:
            broken_bsp = Path(temporary) / "bsp-entities.json"
            broken_bsp.write_text(stable_json_text(baseline_bsp), encoding="utf-8")
            with self.assertRaisesRegex(TraceabilityError, "per-classname key/value"):
                build_traceability_reports(source_path, broken_bsp)


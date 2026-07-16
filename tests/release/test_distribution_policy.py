from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
POLICY_PATH = ROOT / "docs" / "provenance" / "distribution-policy.json"
SCHEMA_PATH = (
    ROOT / "docs" / "provenance" / "schemas" / "distribution-policy.schema.json"
)
ASSET_SCHEMA_PATH = (
    ROOT / "docs" / "provenance" / "schemas" / "asset-policy.schema.json"
)

sys.path.insert(0, str(TOOLS))

from validate_distribution_policy import (  # noqa: E402
    PolicyError,
    check_schema,
    validate_policy_document,
    validate_policy_files,
    validate_schema_instance,
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class DistributionPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = _read_json(POLICY_PATH)
        cls.schema = _read_json(SCHEMA_PATH)
        cls.asset_schema = _read_json(ASSET_SCHEMA_PATH)

    def validate(self, policy: dict) -> None:
        validate_policy_document(
            policy,
            self.schema,
            repository_root=ROOT,
            now=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
        )

    def test_checked_in_policy_and_both_schemas_validate_offline(self) -> None:
        check_schema(self.schema, "distribution policy test schema")
        check_schema(self.asset_schema, "asset policy test schema")
        self.validate(self.policy)
        self.assertEqual(validate_policy_files(), self.policy)

    def test_asset_schema_accepts_fail_closed_overlay_shape(self) -> None:
        fixture = {
            "$schema": "schemas/asset-policy.schema.json",
            "schema": "zaereo.asset-policy/v1",
            "policy_id": "fail-closed-fixture",
            "revision": 1,
            "review": {
                "reviewed_at": "2026-07-13T00:00:00+01:00",
                "reviewer": "test engineering review",
                "authority": "engineering-inventory-review",
                "rights_clearance": False,
                "valid_until": None,
                "revisit_condition": "Replace only after path-level rights review.",
                "notes": "Schema fixture; not a shipping decision.",
            },
            "inventory": {
                "path": "docs/audits/assets.json",
                "schema_version": 1,
                "effective_runtime_path_count": 978,
            },
            "default_unmatched_status": {
                "license_status": "unknown",
                "shipping_status": "blocked",
            },
            "rules": [
                {
                    "id": "unknown-sounds",
                    "selector": {"category": "sound"},
                    "component_id": "zaero-runtime-media",
                    "license_status": "unknown",
                    "spdx_expression": None,
                    "shipping_status": "local-import-only",
                    "references": ["docs/provenance/ASSET_SOURCES.md"],
                    "reviewer": "test engineering review",
                    "expires_at": None,
                    "revisit_condition": "Record a holder grant for every covered path.",
                    "notes": "Unknown remains fail-closed.",
                }
            ],
            "notes": "Minimal offline schema fixture.",
        }
        validate_schema_instance(fixture, self.asset_schema, "asset policy fixture")

    def test_current_summaries_reflect_gpl_distribution_with_publishing_gated(self) -> None:
        # The GPL release of the inputs makes code and media distributable.
        self.assertTrue(self.policy["code_distribution_permitted"])
        self.assertTrue(self.policy["media_distribution_permitted"])
        self.assertTrue(self.policy["public_gameplay_tree_permitted"])
        # Publishing a release stays human-gated: no mode publishes on its own.
        self.assertFalse(self.policy["public_distribution_enabled"])
        public_modes = [mode for mode in self.policy["modes"] if mode["public_mode"]]
        self.assertTrue(public_modes)
        self.assertTrue(all(not mode["publication_permitted"] for mode in public_modes))
        self.assertTrue(all(mode["status"] == "blocked" for mode in public_modes))

    def test_tools_only_is_exact_and_history_clean_only(self) -> None:
        modes = {mode["id"]: mode for mode in self.policy["modes"]}
        channels = {channel["id"]: channel for channel in self.policy["channels"]}
        tools = modes["tools-only"]
        artifact_paths = [entry["artifact_path"] for entry in tools["file_allowlist"]]
        self.assertEqual(len(artifact_paths), len({path.casefold() for path in artifact_paths}))
        self.assertNotEqual(artifact_paths, [])
        self.assertTrue(
            all(entry["distribution_status"] == "permitted" for entry in tools["file_allowlist"])
        )
        self.assertEqual(tools["permitted_channel_ids"], [])
        self.assertTrue(
            all(
                channels[channel_id]["distribution_root"] == "history-clean-tools"
                for channel_id in tools["required_channel_ids"]
            )
        )
        self.assertEqual(tools["readiness_profiles"], ["tools-progress"])
        self.assertFalse(tools["stable_eligible"])

    def test_readiness_profiles_cannot_be_promoted_across_modes(self) -> None:
        policy = deepcopy(self.policy)
        tools = next(mode for mode in policy["modes"] if mode["id"] == "tools-only")
        tools["readiness_profiles"].append("playable-stable")
        with self.assertRaisesRegex(PolicyError, "non-canonical readiness profiles"):
            self.validate(policy)

    def test_local_full_is_permanently_private(self) -> None:
        modes = {mode["id"]: mode for mode in self.policy["modes"]}
        channels = {channel["id"]: channel for channel in self.policy["channels"]}
        local = modes["local-full"]
        self.assertFalse(local["public_mode"])
        self.assertFalse(local["publication_permitted"])
        self.assertTrue(local["permanent_private"])
        self.assertFalse(local["stable_eligible"])
        self.assertTrue(
            all(
                channels[channel_id]["audience"] == "private"
                for channel_id in local["permitted_channel_ids"]
            )
        )

    def test_derived_summary_cannot_be_overridden(self) -> None:
        # The headline booleans must equal the validated component summary; a
        # hand-edited value that disagrees (here, false while components permit
        # distribution) is rejected.
        policy = deepcopy(self.policy)
        policy["code_distribution_permitted"] = False
        with self.assertRaisesRegex(PolicyError, "validated summary"):
            self.validate(policy)

    def test_not_ready_mode_cannot_be_enabled_by_mode_flag(self) -> None:
        # Flipping a mode's publication flag cannot bypass readiness: the mode
        # still has unmet requirements and unresolved (not-yet-set-up) channels.
        policy = deepcopy(self.policy)
        tools = next(mode for mode in policy["modes"] if mode["id"] == "tools-only")
        tools["status"] = "eligible"
        tools["publication_permitted"] = True
        policy["public_distribution_enabled"] = True
        with self.assertRaisesRegex(PolicyError, "unmet requirements"):
            self.validate(policy)

    def test_unknown_channel_cannot_be_labeled_permitted(self) -> None:
        policy = deepcopy(self.policy)
        tools = next(mode for mode in policy["modes"] if mode["id"] == "tools-only")
        tools["permitted_channel_ids"].append("tools-release-assets")
        with self.assertRaisesRegex(PolicyError, "non-permitted channels as permitted"):
            self.validate(policy)

    def test_local_full_publication_flag_is_rejected(self) -> None:
        policy = deepcopy(self.policy)
        local = next(mode for mode in policy["modes"] if mode["id"] == "local-full")
        local["publication_permitted"] = True
        with self.assertRaises(PolicyError):
            self.validate(policy)

    def test_tools_allowlist_rejects_wildcards_and_case_collisions(self) -> None:
        policy = deepcopy(self.policy)
        tools = next(mode for mode in policy["modes"] if mode["id"] == "tools-only")
        tools["file_allowlist"][0]["artifact_path"] = "zaereo-tools/tools/*.py"
        with self.assertRaisesRegex(PolicyError, "artifact_path"):
            self.validate(policy)

        policy = deepcopy(self.policy)
        tools = next(mode for mode in policy["modes"] if mode["id"] == "tools-only")
        duplicate = deepcopy(tools["file_allowlist"][0])
        duplicate["artifact_path"] = duplicate["artifact_path"].upper()
        tools["file_allowlist"].append(duplicate)
        with self.assertRaisesRegex(PolicyError, "case-colliding artifact path"):
            self.validate(policy)

    def test_duplicate_and_unknown_cross_references_fail(self) -> None:
        policy = deepcopy(self.policy)
        policy["components"].append(deepcopy(policy["components"][0]))
        with self.assertRaisesRegex(PolicyError, "duplicate component id"):
            self.validate(policy)

        policy = deepcopy(self.policy)
        channel = next(
            c for c in policy["channels"] if c["id"] == "tools-public-git-tree"
        )
        channel["covered_component_ids"].append("missing-component")
        with self.assertRaisesRegex(PolicyError, "unknown id"):
            self.validate(policy)

    def test_cli_reports_gpl_distribution_and_no_enabled_public_mode(self) -> None:
        result = subprocess.run(
            [sys.executable, str(TOOLS / "validate_distribution_policy.py")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("code=true", result.stdout)
        self.assertIn("media=true", result.stdout)
        self.assertIn("public_modes=none", result.stdout)


if __name__ == "__main__":
    unittest.main()

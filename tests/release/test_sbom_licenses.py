from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
POLICY_PATH = ROOT / "docs" / "provenance" / "dependency-policy.json"
SPDX_SCHEMA = ROOT / "docs" / "provenance" / "schemas" / "spdx-schema-2.3.json"
sys.path.insert(0, str(TOOLS))

from audit_common import stable_json_text  # noqa: E402
from collect_licenses import (  # noqa: E402
    LicenseCollectionError,
    collect_license_bundle,
    load_dependency_policy,
)
from generate_sbom import (  # noqa: E402
    SbomError,
    build_sbom,
    validate_license_manifest,
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class SbomLicenseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy, cls.repository_root = load_dependency_policy(POLICY_PATH)

    def make_installed(
        self,
        root: Path,
        policy: dict,
        *,
        add_unknown: bool = False,
        omit_copyright: str | None = None,
        version_override: tuple[str, str] | None = None,
    ) -> None:
        paragraphs: list[str] = []
        for package in policy["packages"]:
            data = f"license evidence for {package['name']}\n".encode()
            package["copyright_sha256"] = sha256(data)
            path = root / package["copyright_path"]
            if package["name"] != omit_copyright:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            version = (
                version_override[1]
                if version_override and version_override[0] == package["name"]
                else package["version"]
            )
            paragraphs.append(
                "\n".join(
                    [
                        f"Package: {package['name']}",
                        f"Version: {version}",
                        f"Architecture: {package['architecture']}",
                        f"Abi: {sha256((package['name'] + package['architecture']).encode())}",
                        "Status: install ok installed",
                    ]
                )
            )
        if add_unknown:
            paragraphs.append(
                "\n".join(
                    [
                        "Package: surprise",
                        "Version: 1",
                        "Architecture: x64-windows",
                        f"Abi: {sha256(b'surprise')}",
                        "Status: install ok installed",
                    ]
                )
            )
        status = root / policy["vcpkg"]["status_file"]
        status.parent.mkdir(parents=True, exist_ok=True)
        status.write_text("\n\n".join(paragraphs) + "\n", encoding="utf-8")

    def test_checked_in_policy_pins_manifest_upstream_and_official_schema(self) -> None:
        self.assertEqual(self.policy["spdx"]["version"], "SPDX-2.3")
        self.assertEqual(self.policy["project"]["official_commit"], "8dc1fc9794c01ece06881e703851b768fb3994de")
        self.assertEqual(
            hashlib.sha256(SPDX_SCHEMA.read_bytes()).hexdigest(),
            self.policy["spdx"]["schema_sha256"],
        )
        direct = {package["name"] for package in self.policy["packages"] if package["direct"]}
        self.assertEqual(direct, {"fmt", "jsoncpp"})

    def test_two_license_bundles_and_sboms_are_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy = deepcopy(self.policy)
            installed = root / "installed"
            self.make_installed(installed, policy)
            outputs = []
            sboms = []
            for name in ("one", "two"):
                output = root / name
                manifest = collect_license_bundle(
                    policy,
                    self.repository_root,
                    installed,
                    output,
                    source_date_epoch=0,
                )
                sbom = build_sbom(
                    policy,
                    manifest,
                    document_name="Synthetic substrate SBOM",
                    document_namespace="https://zaereo.invalid/sbom/synthetic/0",
                )
                sbom_path = output / "SBOM.spdx.json"
                sbom_path.write_text(stable_json_text(sbom), encoding="utf-8", newline="\n")
                outputs.append((output / "LICENSE-MANIFEST.json").read_bytes())
                sboms.append(sbom_path.read_bytes())
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(sboms[0], sboms[1])
            for package in policy["packages"]:
                first = (root / "one" / "licenses" / package["license_filename"]).read_bytes()
                second = (root / "two" / "licenses" / package["license_filename"]).read_bytes()
                self.assertEqual(first, second)

    def test_unknown_package_missing_license_version_drift_and_hash_drift_fail(self) -> None:
        scenarios = (
            ("unknown", {"add_unknown": True}, "unknown"),
            ("missing", {"omit_copyright": "fmt"}, "missing or unsafe"),
            ("version", {"version_override": ("fmt", "999")}, "version mismatch"),
        )
        for name, options, expected in scenarios:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                policy = deepcopy(self.policy)
                installed = root / "installed"
                self.make_installed(installed, policy, **options)
                with self.assertRaisesRegex(LicenseCollectionError, expected):
                    collect_license_bundle(
                        policy,
                        self.repository_root,
                        installed,
                        root / "output",
                        source_date_epoch=0,
                    )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy = deepcopy(self.policy)
            installed = root / "installed"
            self.make_installed(installed, policy)
            policy["packages"][0]["copyright_sha256"] = "0" * 64
            with self.assertRaisesRegex(LicenseCollectionError, "copyright hash mismatch"):
                collect_license_bundle(
                    policy,
                    self.repository_root,
                    installed,
                    root / "output",
                    source_date_epoch=0,
                )

    def test_manifest_policy_scope_and_license_bytes_cannot_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy = deepcopy(self.policy)
            installed = root / "installed"
            self.make_installed(installed, policy)
            output = root / "output"
            collect_license_bundle(
                policy,
                self.repository_root,
                installed,
                output,
                source_date_epoch=0,
            )
            manifest_path = output / "LICENSE-MANIFEST.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["packages"][0]["role"] = "build-only"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(SbomError, "differs from policy"):
                validate_license_manifest(policy, manifest_path)

            manifest["packages"][0]["role"] = policy["packages"][0]["role"]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            license_path = output / manifest["packages"][0]["license_file"]["path"]
            license_path.write_bytes(b"tampered")
            with self.assertRaisesRegex(SbomError, "identity mismatch"):
                validate_license_manifest(policy, manifest_path)

    def test_generated_document_validates_against_pinned_official_spdx_schema(self) -> None:
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema is not installed; generator remains stdlib-only")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy = deepcopy(self.policy)
            installed = root / "installed"
            self.make_installed(installed, policy)
            manifest = collect_license_bundle(
                policy,
                self.repository_root,
                installed,
                root / "output",
                source_date_epoch=0,
            )
            sbom = build_sbom(
                policy,
                manifest,
                document_name="Synthetic substrate SBOM",
                document_namespace="https://zaereo.invalid/sbom/synthetic/0",
            )
            schema = json.loads(SPDX_SCHEMA.read_text(encoding="utf-8"))
            jsonschema.Draft7Validator.check_schema(schema)
            jsonschema.validate(sbom, schema)

    def test_cli_tools_run_without_site_packages_when_vcpkg_install_exists(self) -> None:
        status = ROOT / "vcpkg_installed" / self.policy["vcpkg"]["status_file"]
        if not status.is_file():
            self.skipTest("bootstrap has not restored the pinned vcpkg install")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "bundle"
            collect = subprocess.run(
                [
                    sys.executable,
                    "-S",
                    str(TOOLS / "collect_licenses.py"),
                    "--installed-root",
                    str(ROOT / "vcpkg_installed"),
                    "--output",
                    str(output),
                    "--source-date-epoch",
                    "0",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=60,
                check=False,
            )
            self.assertEqual(collect.returncode, 0, collect.stdout + collect.stderr)
            generate = subprocess.run(
                [
                    sys.executable,
                    "-S",
                    str(TOOLS / "generate_sbom.py"),
                    "--license-manifest",
                    str(output / "LICENSE-MANIFEST.json"),
                    "--output",
                    str(output / "SBOM.spdx.json"),
                    "--document-namespace",
                    "https://zaereo.invalid/sbom/integration/0",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=60,
                check=False,
            )
            self.assertEqual(generate.returncode, 0, generate.stdout + generate.stderr)


if __name__ == "__main__":
    unittest.main()

# Schema registry

This directory contains the immutable schemas used by repository policy and
generated evidence. A schema filename or identifier is versioned independently
from the document instance that uses it. Breaking changes require a new schema
identifier and migration test; silently changing the meaning of an existing
identifier is prohibited.

| Schema | Instance/status | Owner phase |
| --- | --- | --- |
| `asset-policy.schema.json` | Per-runtime-path shipping overlay for the GPL Zaero content; instantiate once the shipped asset set is finalized | Phase 0/9 |
| `distribution-policy.schema.json` | `../distribution-policy.json` | Phase 0/9 |
| `local-config.schema.json` | `.zaereo.local.json` (ignored; tracked example only) | Phase 1 |
| `dependency-policy.schema.json` | `../dependency-policy.json` | Phase 1/9 |
| `spdx-schema-2.3.json` | Generated `SBOM.spdx.json` | Phase 1/9 |
| `runtime-smoke.schema.json` (`https://zaereo.invalid/schemas/runtime-smoke/v2`) | Private `.install/runtime-reports/*.json` evidence. The current runner records the two-stage visible-window-before-mod/map protocol, full top-level-window enumeration, and a private focus-stage diagnostic. The diagnostic remains optional in this immutable v2 schema so older v2 evidence stays readable; current matrix acceptance requires it. Earlier v1 reports are historical only and cannot close this launch-safety gate. | Phase 1–9 |
| `runtime-matrix.schema.json` (`https://zaereo.invalid/schemas/runtime-matrix/v1`) | Reviewed private scenarios in `tools/runtime-scenarios.json` (legacy map smokes), `tools/runtime-scenarios-dm.json` (D-045 values 0–3/authored suppression), and `tools/runtime-scenarios-dm-fixtures.json` (derived fixture reruns). [The matrix runner](../../../tools/run_runtime_matrix.ps1) emits ignored per-run JSON/JUnit aggregation and fails closed on absent, malformed, or failed v2 smoke reports. | Phase 1–9 |
| `runtime-matrix-result.schema.json` (`https://zaereo.invalid/schemas/runtime-matrix-result/v1`) | Private `build/test-results/*/runtime-matrix.json` aggregation from the matrix runner. Each case retains the v2 launch protocol, command-delivery result, and focus-stage diagnostic; a matrix-level flag records when the human-only delivery fallback was used. | Phase 1–9 |
| `mapdb-merge.schema.json` (`https://zaereo.invalid/schemas/mapdb-merge/v1`) | Private `.install/` report from [the hash-pinned mapdb merger](../../../tools/merge_mapdb.py). | Phase 2/7 |
| `release-readiness.schema.json` (`https://zaereo.invalid/schemas/release-readiness/v1`) | Generated, ignored `dist/release-readiness.json` from [the fail-closed readiness evaluator](../../../tools/release_readiness.py). It fingerprints the current policy, baseline/audit/ledger inputs, source state, and selected mode/channel/profile; it is currently expected to be `ready: false` because the port has not yet earned its playable-stable readiness evidence, not for any rights reason. | Phase 0/9 |

`spdx-schema-2.3.json` is the unmodified SPDX 2.3 JSON Schema from official
`spdx/spdx-spec` tag `v2.3`, peeled commit
`aadf3b0b8dbbabdb4d880b0fc714255fea436ff7`. Its SHA-256 is
`239208b7ac287b3cf5d9a9af23f9d69863971102a5e1587a27a398b43490b89b`.
The exact Creative Commons Attribution 3.0 license text is retained at
`references/licenses/SPDX-spec-CC-BY-3.0.txt` and summarized in
`THIRD_PARTY_NOTICES.md`.

Planned schemas for import/install ownership and release manifests remain
roadmap gates and must be added here when implemented.

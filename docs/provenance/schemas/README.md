# Schema registry

This directory contains the immutable schemas used by repository policy and
generated evidence. A schema filename or identifier is versioned independently
from the document instance that uses it. Breaking changes require a new schema
identifier and migration test; silently changing the meaning of an existing
identifier is prohibited.

| Schema | Instance/status | Owner phase |
| --- | --- | --- |
| `asset-policy.schema.json` | Path-level overlay is deliberately not instantiated until rights review exists | Phase 0/9 |
| `distribution-policy.schema.json` | `../distribution-policy.json` | Phase 0/9 |
| `local-config.schema.json` | `.zaereo.local.json` (ignored; tracked example only) | Phase 1 |
| `dependency-policy.schema.json` | `../dependency-policy.json` | Phase 1/9 |
| `spdx-schema-2.3.json` | Generated `SBOM.spdx.json` | Phase 1/9 |
| `runtime-smoke.schema.json` (`https://zaereo.invalid/schemas/runtime-smoke/v2`) | Private `.install/runtime-reports/*.json` evidence. The current `zaereo.runtime-smoke/v2` requires the two-stage visible-window-before-mod/map protocol and full top-level-window enumeration; earlier v1 reports are historical only and cannot close this launch-safety gate. | Phase 1–9 |

`spdx-schema-2.3.json` is the unmodified SPDX 2.3 JSON Schema from official
`spdx/spdx-spec` tag `v2.3`, peeled commit
`aadf3b0b8dbbabdb4d880b0fc714255fea436ff7`. Its SHA-256 is
`239208b7ac287b3cf5d9a9af23f9d69863971102a5e1587a27a398b43490b89b`.
The exact Creative Commons Attribution 3.0 license text is retained at
`references/licenses/SPDX-spec-CC-BY-3.0.txt` and summarized in
`THIRD_PARTY_NOTICES.md`.

Planned schemas for import/install ownership, release manifests, and release
readiness remain roadmap gates and must be added here when implemented.

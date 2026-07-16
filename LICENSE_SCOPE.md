# License scope and distribution status

This document maps the licenses that apply to the components in ZaeREo. It is a
notice for convenience, not a substitute for the exact license text shipped with
each component.

ZaeREo as a whole is free software under the **GNU General Public License,
version 2** ([`LICENSE`](LICENSE)). Every foundational input — the Quake II
Rerelease game DLL and the original Zaero mission pack (source and assets) — was
released under the GPL, so the combined work is distributed under the GPL as
well. Distribution of code and media is permitted; the remaining gates on a
public build are engineering-readiness gates (is the port validated and tested),
not rights gates.

The machine-readable companion record is
[`docs/provenance/distribution-policy.json`](docs/provenance/distribution-policy.json).
It records:

- `code_distribution_permitted: true`;
- `media_distribution_permitted: true`; and
- publication enabled through the reviewed release modes, gated only by
  release-readiness evidence and human approval of a draft release.

Publishing a release is a deliberate, human-approved step: no automated workflow
ships code or media on its own. Records that are internally contradictory,
overbroad, or evidence-free are still rejected by the policy validator so that
attribution and corresponding-source obligations stay intact.

## Component scope

| Component | License | Distribution status |
| --- | --- | --- |
| Quake II Rerelease substrate | GNU GPL version 2. The supplied baseline exactly matches all 144 paths/blobs in official commit `8dc1fc9794c01ece06881e703851b768fb3994de` under `rerelease/`; see `docs/provenance/upstream-match.json`. | **Distributable under GPL-2.0.** Retain the upstream copyright and GPL notices on any imported file. |
| Combined ZaeREo gameplay source and DLL | GPL-2.0. The Rerelease substrate and Zaero-derived behavior are intermingled under `src/`; both inputs are GPL, so the combined work is GPL. | **Distributable under GPL-2.0.** A distributed DLL must be accompanied by its complete corresponding source (this repository) and notices. |
| Zaero-derived compatibility tests and audits | GPL-2.0 as project-authored work built on GPL inputs. | **Distributable.** These files are part of the corresponding source. |
| Acquisition and packaging tools | GPL-2.0 project-authored automation (`tools/`). | **Distributable.** They form part of the corresponding-source and build scripts the GPL requires alongside a released binary. |
| Zaero maps and media | GPL — released by Zaero's original team alongside the source. `docs/audits/assets.json` and importer manifests identify the exact bytes and precedence. | **Distributable under GPL.** The ported content is bundled into `asset-full` release packages; the original authors' credits and notices are preserved. |
| Runtime and editor definitions | GPL-2.0 project integration and generated definitions under `pack/` and `editor/`. | **Distributable.** Generated forms carry the license of the sources they are generated from. |
| fmt | MIT (with the project's optional compiled-object notice exception); `dependency-policy.json` pins fmt 11.2.0, its copyright SHA-256, and vcpkg ABI/SPDX evidence. | **Distributable under MIT.** The MIT notice is harvested into the release notice bundle and SBOM. |
| JsonCpp | Public-domain dedication where recognized, with MIT terms otherwise; `dependency-policy.json` pins JsonCpp 1.9.6 with copyright SHA-256 and vcpkg ABI/SPDX evidence. | **Distributable.** The applicable notice is harvested into the release notice bundle and SBOM. |
| MSVC compiler and static runtime | Microsoft toolchain, recorded in the SBOM as build evidence (compiler 19.44.35222, static runtime 14.44.35207). | **System-component exception.** Under GPL-2.0 §3 the compiler/runtime are normally-distributed major system components and need not be shipped as source; the SBOM records the exact versions used. |
| Repository documentation and automation | GPL-2.0 project-authored material. | **Distributable.** The root `LICENSE` applies to the project's own files. |

## Meaning of the root GPL text

[`LICENSE`](LICENSE) contains the GNU General Public License, version 2. It is
the license under which this project and its GPL-released inputs are
distributed. Keep the applicable per-file copyright headers from the original
authors intact — the GPL is a license to redistribute *with* those notices, not
a waiver of attribution.

If a release distributes a DLL, that exact release must also provide or durably
link complete corresponding source and build/install scripts for the same
binary, together with all applicable notices. This repository is that
corresponding source, which is why the GPL obligation is straightforward to meet
rather than a blocker.

## Release-mode consequences

- **asset-full** is the primary end-user mode: it bundles the ported Zaero
  content (`pak0.pak` plus required loose files) together with the DLL and
  notices, the same way the sibling REBLIVION port ships Oblivion. It is
  eligible once the port earns its release-readiness evidence.
- **importer-kit** ships the DLL and rebuilds the content pack from a user's
  existing Zaero installation. It exists as a convenience for users who prefer
  to supply their own copy, not because bundling is disallowed.
- **tools-only** ships only the project's automation and instructions. It is a
  narrow artifact, not a playable mod release.
- **local-full** is private engineering output assembled during development. It
  is kept out of release channels for hygiene (it is unvalidated developer
  scratch), not for any rights reason.

The project may publish `asset-full` and `importer-kit` builds once the
mode-specific readiness record and a maintainer's approval of a draft release
both authorize the exact operation. Distribution rights are settled; readiness
is the remaining bar.

See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and
[`docs/provenance/ASSET_SOURCES.md`](docs/provenance/ASSET_SOURCES.md) for the
recorded component and asset evidence.

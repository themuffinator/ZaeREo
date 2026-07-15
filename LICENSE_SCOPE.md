# License scope and current distribution status

This document explains the scope of license evidence currently recorded for
ZaeREo. It is a notice, not a copyright-holder permission, legal opinion, or
substitute for the exact license text shipped with a component.

The authoritative machine gate is
[`docs/provenance/distribution-policy.json`](docs/provenance/distribution-policy.json).
Its initial reviewed engineering baseline deliberately records:

- `code_distribution_permitted: false`;
- `media_distribution_permitted: false`;
- `public_gameplay_tree_permitted: false`; and
- no publication-permitted release mode.

Unknown, missing, contradictory, overbroad, expired, or evidence-free records
fail closed. Changing this prose cannot authorize a release.

## Component scope

| Component | Current evidence | Current public status |
| --- | --- | --- |
| Quake II Rerelease substrate | The supplied baseline contains GNU GPL version 2 notices and exactly matches all 144 paths/blobs in official commit `8dc1fc9794c01ece06881e703851b768fb3994de` under `rerelease/`; see `docs/provenance/upstream-match.json`. | **Upstream identity resolved; combined-work distribution still blocked.** The GPL evidence applies to code placed under it by its holders; it does not license unrelated Zaero additions or establish the outbound scope of the intermingled repository. |
| Combined ZaeREo gameplay source and DLL | Upstream substrate and Zaero-derived behavior are intermingled under `src/`. | **Unknown / no grant claimed.** No DLL, object, symbols, gameplay source, or corresponding-source bundle may be published. |
| Zaero-derived compatibility tests and audits | Project-authored material may encode detailed behavior or supplied-source facts. No file-by-file protectable-expression and outbound-license review is recorded. | **Unknown / no grant claimed.** These files remain part of the private gameplay tree. |
| Candidate acquisition tools | Three exact candidates are listed in the policy: `tools/import_legacy_assets.py`, `tools/make_pak.py`, and `tools/validate_runtime.py`. | **Unknown / not yet publishable.** Each file still needs independent-authorship and outbound-license approval, immutable hashes, and a separately audited history-clean tools root. |
| Zaero maps and media | `docs/audits/assets.json` and local importer manifests identify bytes and precedence. Identity and possession are not permission. | **Unknown / no grant claimed.** Original or extracted media is local-import-only and cannot enter project Git, CI, editor, or release channels. |
| Runtime and editor definitions | `pack/` and `editor/` contain project integration and generated definitions. Their derivation and authorship have not been reviewed file by file. | **Unknown / no grant claimed.** A generated form does not acquire a distribution grant merely by being generated. |
| fmt | `dependency-policy.json` pins fmt 11.2.0, MIT, its installed copyright SHA-256, vcpkg ABI evidence, and deterministic SPDX/license harvesting. | **Dependency evidence complete for the substrate candidate; release still blocked.** It must be tied to the exact mode-specific binary/manifest and the combined code/channel gates. |
| JsonCpp | `dependency-policy.json` pins JsonCpp 1.9.6, its MIT/public-domain alternatives, installed copyright SHA-256, vcpkg ABI evidence, and deterministic SPDX/license harvesting. | **Dependency evidence complete for the substrate candidate; release still blocked.** It must be tied to the exact mode-specific binary/manifest and the combined code/channel gates. |
| MSVC compiler and static runtime | The substrate SBOM records compiler 19.44.35222 and static runtime 14.44.35207 as engineering evidence. | **Unknown / NOASSERTION.** Outbound runtime scope and exact applicable Microsoft terms have not been reviewed; no public binary mode may rely on this record as clearance. |
| Repository documentation, automation, and remaining tests/tools | No blanket file-by-file authorship and outbound-license decision is recorded. | **Unknown.** The root `LICENSE` must not be treated as an automatic relicense of every file. |

## Meaning of the root GPL text

[`LICENSE`](LICENSE) contains the GNU General Public License, version 2. Its
presence preserves and communicates the observed upstream license, but it is not
evidence that every contributor or commercial rightsholder granted rights in
every repository file. In particular, it does not grant rights to original
Zaero source additions, maps, models, textures, sounds, cinematics, or other
media.

If a future code-cleared release distributes a DLL, that exact release must also
provide or durably link complete corresponding source and build/install scripts
for the same binary, together with all applicable notices. A corresponding-source
obligation cannot cure a missing grant for an included addition.

## Release-mode consequences

- **tools-only** is currently blocked. The policy lists an exact candidate file
  set for review, but every file and every history-clean repository, history,
  source-archive, Actions, cache, artifact, and release channel remains
  `unknown`. The gameplay repository can never serve as its source while the
  gameplay-code gate is open.
- **importer-kit** is blocked until the complete code/DLL and corresponding-source
  rights gate is permitted. It must contain no Zaero media and becomes playable
  only after a user completes a legitimate local import.
- **asset-full** is blocked until code and media are independently permitted for
  the exact files and channels. It must use a separately reviewed distributable
  media lineage, never a copied or renamed private import.
- **local-full** is private engineering output assembled from a user's legitimate
  installation. It is permanently non-publishable, even if later rights evidence
  permits a distinct asset-full release.

The project may continue private local engineering under these containment
rules. Do not push or tag the gameplay tree to a public remote, upload its source
or binary output to public CI, or publish any package until the machine policy
and the profile-specific readiness record both authorize the exact operation.

See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and
[`docs/provenance/ASSET_SOURCES.md`](docs/provenance/ASSET_SOURCES.md) for the
recorded component and asset evidence.

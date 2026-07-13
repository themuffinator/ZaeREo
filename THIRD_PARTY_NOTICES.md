# Third-party notices

This file records inputs and dependencies relevant to ZaeREo. It is not a grant
of rights for material that is not present in this repository, and it does not
replace the license text shipped with a component.

## Quake II Rerelease game DLL

- Project: Quake II Rerelease game DLL
- Upstream: https://github.com/id-Software/quake2-rerelease-dll
- License observed in the supplied baseline: GNU General Public License,
  version 2.0
- Current repository use: target implementation baseline imported under src
  with a pristine comparison snapshot; upstream commit/origin pinning remains
  unresolved

Any imported upstream files must retain their applicable copyright and GPL-2.0
notices. GPL coverage of this code does not grant rights to Zaero media or
source additions.

## {fmt}

- Project: {fmt}
- Role: statically linked build dependency declared by `vcpkg.json`
- License observed in the pinned vcpkg installation: MIT, with the project's
  optional compiled-object notice exception
- Copyright notice: Copyright (c) 2012–present, Victor Zverovich and {fmt}
  contributors

The release process must harvest the exact `share/fmt/copyright` file from the
pinned dependency installation into the release notice bundle and SBOM. This
summary does not replace that text.

## JsonCpp

- Project: JsonCpp
- Role: statically linked build dependency declared by `vcpkg.json`
- License observed in the pinned vcpkg installation: public-domain dedication
  where recognized, with MIT terms available/required in other jurisdictions
- Copyright notice for the MIT form: Copyright (c) 2007–2010 Baptiste
  Lepilleur and The JsonCpp Authors

The release process must harvest the exact `share/jsoncpp/copyright` file from
the pinned dependency installation into the release notice bundle and SBOM.
Dependency baseline changes require regenerated notices and license review.

## Legacy Quake II game source

- Project: Quake II game source
- Origin used for the audit: a locally supplied source tree
- Role: historical comparison only
- Redistribution status in this repository: no files imported by this scaffold

Record the precise upstream identity and applicable notices in the baseline
manifest before copying any source.

## Zaero source additions

- Work: original Zaero game-module source
- Origin used for the audit: a locally supplied source tree
- Role: behavioral evidence for the compatibility port
- Copyright holder/license: not established by the currently recorded evidence
- Redistribution status: not cleared; no permission is claimed

Do not publish or relicense Zaero-derived source until provenance and license
compatibility are documented. Clean-room facts, original implementations, and
source-derived code have different legal implications; the project owner should
obtain qualified review for the intended distribution.

## Zaero maps and media

- Work: original Zaero PAKs, BSPs, models, textures, images, sounds, sprites,
  cinematics, configuration, documentation, demos, saves, and screenshots
- Role: locally owned compatibility-test input
- Copyright holder/license: not established by the currently recorded evidence
- Redistribution status: not cleared
- Active media policy: local import only; users provide a legitimate local
  installation. Code and media publication gates are evaluated independently.

Original PAKs, loose media, legacy game DLLs, demos, saves, screenshots, and
installer artifacts are not distributable merely because their hashes are
known. See docs/provenance/ASSET_SOURCES.md for identification data and the
planned importer boundary.

While Zaero-derived code rights are unresolved, no DLL/source containing those
additions is publishable; the maximum possible public output is an independently
cleared tools-only artifact from a history-clean distribution root. A public
tag/release of the gameplay repository is not tools-only because its automatic
source archives expose the tagged tree. If code clears but media does not, an importer kit
may become eligible. `local-full` always denotes private user-imported output
and can never be published. A future rights-cleared media release must use a
distinct `asset-full` mode and reviewed distributable inputs.

The planned `docs/provenance/distribution-policy.json` records the exact
component/path license or no-grant status and permitted repository, source-
archive, CI/cache/artifact, editor, and release channels for each mode.
`asset-policy.json` remains the per-runtime-media overlay. Package and publisher
decisions must consume those records and a mode-specific `LICENSE_SCOPE.md`;
this notice file alone does not authorize distribution.

## Trademarks

Quake, Quake II, Zaero, and related names and marks are the property of their
respective owners. ZaeREo is an unofficial project and is not endorsed by id
Software, Bethesda Softworks, Nightdive Studios, or Zaero's original publisher
or rightsholders.

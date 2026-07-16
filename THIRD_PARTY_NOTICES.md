# Third-party notices

This file records the inputs and dependencies that make up ZaeREo and the
notices that must travel with them. ZaeREo is distributed under the GNU General
Public License, version 2; the notices below identify the copyright holders and
licenses of the components combined in that GPL distribution. It does not replace
the exact license text shipped with each component.

## Quake II Rerelease game DLL

- Project: Quake II Rerelease game DLL
- Upstream: https://github.com/id-Software/quake2-rerelease-dll
- License: GNU General Public License, version 2.0
- Pinned source identity: official commit
  `8dc1fc9794c01ece06881e703851b768fb3994de`, `rerelease/` subtree
  `7c3a380c5114dab4e7b7511a5c9c96390b72a1cd`, exactly matching the supplied
  per-file baseline
- Repository use: target implementation baseline imported under `src` with
  immutable per-file and official-match records

Imported upstream files retain their applicable copyright and GPL-2.0 notices.

## {fmt}

- Project: {fmt}
- Role: statically linked build dependency declared by `vcpkg.json`
- License observed in the pinned vcpkg installation: MIT, with the project's
  optional compiled-object notice exception
- Copyright notice: Copyright (c) 2012–present, Victor Zverovich and {fmt}
  contributors

The release process harvests the exact `share/fmt/copyright` file from the
pinned dependency installation into the release notice bundle and SBOM. This
summary does not replace that text.

## JsonCpp

- Project: JsonCpp
- Role: statically linked build dependency declared by `vcpkg.json`
- License observed in the pinned vcpkg installation: public-domain dedication
  where recognized, with MIT terms available/required in other jurisdictions
- Copyright notice for the MIT form: Copyright (c) 2007–2010 Baptiste
  Lepilleur and The JsonCpp Authors

The release process harvests the exact `share/jsoncpp/copyright` file from the
pinned dependency installation into the release notice bundle and SBOM.
Dependency baseline changes require regenerated notices and license review.

## SPDX 2.3 JSON Schema

- Project: SPDX Specification
- Upstream: https://github.com/spdx/spdx-spec
- Pinned tag/commit: `v2.3` / `aadf3b0b8dbbabdb4d880b0fc714255fea436ff7`
- Imported file: `schemas/spdx-schema.json`, stored as
  `docs/provenance/schemas/spdx-schema-2.3.json`
- SHA-256: `239208b7ac287b3cf5d9a9af23f9d69863971102a5e1587a27a398b43490b89b`
- License: Creative Commons Attribution 3.0 Unported; exact text retained at
  `references/licenses/SPDX-spec-CC-BY-3.0.txt`

The schema is retained unmodified to validate deterministic SBOM output. SPDX
is a registered trademark of the Linux Foundation; use here does not imply
endorsement.

## Legacy Quake II game source

- Project: Quake II game source
- Origin used for the audit: a locally supplied source tree
- License: GNU General Public License, version 2.0 (id Software's Quake II source
  release)
- Role: historical comparison only; no files are imported by this scaffold

Record the precise upstream identity and applicable notices in the baseline
manifest before copying any source.

## Zaero source additions

- Work: original Zaero game-module source
- Author: the original Zaero team (Team Evolve)
- License: GNU General Public License — released by the original team alongside
  the Zaero assets
- Role: the behavioral and source basis for this compatibility port
- Redistribution status: distributable under the GPL; preserve the original
  authors' copyright notices in ported files

Zaero-derived source is redistributed under the GPL together with its original
notices. Where the port re-implements behavior against the Rerelease API rather
than copying legacy code, the resulting project-authored code is likewise GPL.

## Zaero maps and media

- Work: original Zaero PAKs, BSPs, models, textures, images, sounds, sprites,
  cinematics, configuration, and documentation
- Author: the original Zaero team (Team Evolve)
- License: GNU General Public License — released alongside the Zaero source
- Role: the runtime content this port carries forward
- Redistribution status: distributable under the GPL; the ported content is
  bundled into `asset-full` release packages with the original credits and
  notices preserved

The ported Zaero content is redistributed under the GPL. See
docs/provenance/ASSET_SOURCES.md for the identification data and the importer
boundary used when rebuilding the pack from an existing installation. The
importer still excludes legacy `gamex86.dll`/`gamei386.so` binaries (they are
incompatible with the Rerelease engine, not a rights problem) and the
destructive original `default.cfg`.

Release packaging distinguishes two modes: `asset-full` bundles the ported
content directly, and `importer-kit` omits it so a user can rebuild the pack
from their own Zaero installation. Both are permitted; the choice is a packaging
and convenience decision. `local-full` denotes unvalidated developer scratch and
stays out of release channels for engineering hygiene.

The `docs/provenance/distribution-policy.json` record maps each component/path to
its license and the release channels it may travel through.
`asset-policy.json` is the per-runtime-media overlay. Package and publisher
tooling consume those records plus a mode-specific `LICENSE_SCOPE.md`; the human
approval of a draft release remains the final gate before anything is published.

## Trademarks

Quake, Quake II, Zaero, and related names and marks are the property of their
respective owners. ZaeREo is an unofficial project and is not endorsed by id
Software, Bethesda Softworks, Nightdive Studios, or Zaero's original team. The
GPL covers copyright in the released software and assets; it does not grant any
trademark rights, and none are claimed here.

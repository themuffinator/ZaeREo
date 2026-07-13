# Zaero asset sources and distribution status

- Record status: audited Phase 0 identity baseline; rights review remains open
- Audit date: 2026-07-13
- Maximum current public capability: **tools-only, subject to independent tool rights review**
- Zaero-derived code distribution permitted: **not established**
- Zaero media distribution permitted: **not established**
- Asset-bearing public release permitted: **no**

This record identifies the supplied legacy installation used for the planning
audit. It does not grant redistribution permission. The local paths below are
audit evidence from one developer machine, not build constants; committed tools
must resolve paths from arguments, environment variables, or ignored local
configuration.

## Evidence location

The audited installation was available at:

~~~text
E:\_SOURCE\_ASSETS\Zaero
~~~

Future contributors may keep a legitimate installation elsewhere. The importer
must identify inputs by hashes and structure, never by assuming this path.

## Original package layers

The effective package order is pak0.pak, then pak1.pak, then pak2.pak, with the
last package winning when a normalized runtime path is repeated.

The known retail `pak0.pak` contains non-zero, ignored bytes after the first NUL
in some fixed-width directory name fields. Quake II treats each field as a C
string. Audit/import code therefore enables this representation quirk only at
the legacy-source boundary while still rejecting an empty or unsafe visible
name, traversal, duplicate/case-colliding paths, invalid ranges, overlaps, and
hash mismatches. Newly generated PAKs always use canonical zero padding.

| Container | Bytes | Directory entries | SHA-256 | Status |
| --- | ---: | ---: | --- | --- |
| pak0.pak | 95,910,332 | 958 | 1de0161318cb946dbaad1ad6ac9abe375d3aa1da57f3571fdee3e5549cb0fafd | Identified locally; do not commit or redistribute |
| pak1.pak | 4,931 | 1 | 3806e4cc59564e5a081518adf04fc608d79159b1e31d073b6699f0a3a34b4973 | Identified locally; do not commit or redistribute |
| pak2.pak | 12,001,303 | 12 | e0b043599386f5b39701919f334de37d21011dd254630e17504dece497fec82e | Identified locally; do not commit or redistribute |

The three directories contain 971 entries before override resolution and 969
effective paths after layering. pak1 replaces default.cfg. pak2 adds six
deathmatch maps and replaces maps.lst. Those are the only repeated PAK paths
found by the planning audit.

The effective runtime view includes 20 BSPs: 14 campaign maps from pak0 and six
deathmatch maps from pak2. pak0 also contains elogo.cin and zlogo.cin.

## Required loose runtime files

The original installation leaves seven plasma-sprite files and two large
cinematics outside the PAKs. The original documentation describes the sprites
as intentionally loose. Keep this layout until packed behavior is tested in the
target Rerelease.

| Runtime path | Bytes | SHA-256 | Status |
| --- | ---: | --- | --- |
| sprites/plasma1.sp2 | 332 | f6d48de85014265c3e74b4d07bd7dc358c6ee29b16a3e63cbfcf176b4614bb2a | Required local input |
| sprites/plasma1_0.pcx | 8,679 | 5c5cf4ffe605527096dea1d99772856aa2c507f73e0acc1108fededc2f5b1f10 | Required local input |
| sprites/plasma1_1.pcx | 8,733 | 7d387962ca8a8354c2c31080576289ae5d9368f65abbf22d344658e517ed2845 | Required local input |
| sprites/plasma1_2.pcx | 8,679 | 5c5cf4ffe605527096dea1d99772856aa2c507f73e0acc1108fededc2f5b1f10 | Required local input; byte-identical to plasma1_0.pcx |
| sprites/plasma1_3.pcx | 8,630 | 514f9021fd5684a8d5d8e9c06f308e853b33a7e63988a864fc495008d03d9015 | Required local input |
| sprites/plasmashield.sp2 | 92 | bc534f26c80aacfd578db5e2979e51f58e83656f66c03e2b8a03a5c3a565ffd7 | Required local input |
| sprites/plasmashield_0.pcx | 5,505 | 493766008bac06a8b714325d45f1fec9ef231afff58b7e5e421a9b0773f05b12 | Required local input |
| video/intro.cin | 49,817,132 | 1ca8188f2f6a0c83445d069f8b57220347a262f71c86f2d4e331ccb3b98e2fce | Required local input |
| video/outro.cin | 16,606,854 | 313e06e29bf354e454353f0f11dddc63ff99645c8700ccfd42b56c5e6e0c0932 | Required local input |

## Content classification

Subject to provenance clearance, runtime dependencies include:

- 20 BSP maps and their effective textures, skies, models, skins, sprites,
  images, sounds, cinematics, and victory presentation;
- Zaero-specific item, weapon, monster, autocannon, camera, communications-dish,
  crate, IRED, seat, shrapnel, flare, shield, barrier, and explosion media;
- effective configuration data translated into non-destructive zaero.cfg,
  zaerostart.cfg, and a merged Rerelease map database entry; and
- original credits/notices where redistribution permits.

The canonical runtime import must exclude:

- legacy gamex86.dll and gamei386.so binaries;
- the destructive original default.cfg and loose autoexec;
- four legacy demos, four legacy save files, and sixteen screenshots;
- installer/uninstaller state, logs, and obsolete executable metadata; and
- source PAKs, compiler output, generated PAKs, release archives, or symbols.

Old demos and saves remain provenance evidence only. No playback or load
compatibility is promised.

## Rights and publication gate

The currently recorded installation does not contain evidence that establishes
permission for this project to redistribute Zaero source additions or media.
Known hashes prove identity, not permission. The GPL-2.0 terms of the Quake II
Rerelease DLL do not cover these assets.

The active public policy is therefore:

1. publish no original Zaero PAK, loose media, legacy binary, or extracted
   content;
2. accept no contributor upload of those files;
3. implement a local importer that requires a legitimate user installation;
4. validate the exact known containers and report unsupported variants safely;
5. assemble the effective runtime tree only on the user's machine; and
6. keep imported content under ignored `.install/`/stage roots and keep `dist/`
   output ignored; tracked `pack/` contains only reviewed redistributable project
   configuration contributions.

Code and media are independent fail-closed gates. While Zaero-derived code
rights are unresolved, no such source or DLL may be published and even an
importer kit is ineligible; only independently cleared tools/instructions may
form a tools-only artifact from a separately reviewed history-clean
repository/ref. A public gameplay-tree tag would expose gated code through
GitHub source archives and is therefore prohibited while that gate is open. If
code clears while media does not, an importer kit
may carry the DLL but must require local media import. An asset-bearing public
release remains blocked until the copyright holder,
specific permission/license, covered works, permitted channels, attribution,
modification terms, and sublicensing/hosting constraints are recorded and
reviewed. Update THIRD_PARTY_NOTICES.md and this file together if that evidence
changes.

The planned `docs/provenance/distribution-policy.json` is the authoritative
machine gate for components, repository history/source archives, Actions logs/
artifacts/caches, release assets, editor gamepacks, modes, and exact tools-only
file allowlists. This asset record and `asset-policy.json` identify media inputs
and per-runtime-path eligibility; neither authorizes a source or publication
channel. Missing/unknown policy fails closed, and readiness/package/publisher
tools must consume the JSON rather than scrape this prose.

`local-full` is permanently reserved for private output assembled from a user's
installation and can never be published, even if rights later change. A future
rights-cleared asset-bearing publication must be a distinct `asset-full` mode
built from a reviewed distributable-input manifest, not a renamed local import.

## Importer and manifest requirements

The importer must:

- take an explicit path, ZAERO_LEGACY_ROOT, or ignored local configuration;
- never download proprietary content;
- parse PAK directories defensively and reject traversal, invalid offsets,
  unreasonable sizes/counts, duplicate normalized paths, and case collisions;
- resolve last-package-wins precedence deterministically;
- preserve each effective path's source container, source path, hash, size, and
  case;
- exclude the non-runtime categories above through an allowlist;
- copy loose files only after hash validation;
- write only beneath a verified repository-local/stage destination;
- support dry-run and non-interactive modes; and
- produce a manifest whose staged tree validates exactly.

The checked-in identity inventory is `docs/audits/assets.json`. Each importer
run emits its own deterministic JSON manifest. The only reviewed shipping/
license policy overlay is the planned
`docs/provenance/asset-policy.json`, keyed by normalized exact path or narrowly
defined category; exact-path rules override categories and unmatched paths fail
closed. The merged release manifest carries at least:

~~~text
runtime_path, source_container, source_path, source_sha256, effective_sha256,
size, category, references, license_status, shipping_status, notes
~~~

A CSV may be generated solely as a review rendering. It is never a second
source of truth. Schema validation rejects duplicate, orphaned, overbroad,
expired, contradictory, or evidence-free policy entries.

Generated packages and archives are outputs, not source assets, and never enter
Git LFS.

## Records still required

This initial file does not close Phase 0. A generated
docs/provenance/baselines.json now records per-file and aggregate hashes for the
four supplied trees, but its origins still identify supplied local trees rather
than pinned upstream commits or archives. The following evidence must still be
generated or reviewed:

- baseline upstream/archive origins and review of the generated hash manifest;
- review of the 969 effective PAK paths plus nine loose paths in
  `docs/audits/assets.json`, and the canonical `asset-policy.json` overlay;
- the independently reviewed/versioned `distribution-policy.json` component,
  mode, per-file, and repository/source/CI/release-channel records;
- retained normalized asset-layer, reference-closure, case-collision, and
  importer-manifest validation reports;
- precise copyright/license or permission evidence for every source/media
  category; and
- a tested, policy-eligible tools-only/importer-kit package or a documented
  code/media clearance decision; `local-full` remains private in all cases.

Until those records exist and agree, no asset-distribution claim is valid.

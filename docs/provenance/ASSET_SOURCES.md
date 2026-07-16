# Zaero asset sources and distribution status

- Record status: audited identity baseline
- Audit date: 2026-07-13
- License of the Zaero content: **GNU General Public License** (source and
  assets released by the original Zaero team)
- Zaero-derived code distribution permitted: **yes, under the GPL**
- Zaero media distribution permitted: **yes, under the GPL**
- Asset-bearing public release permitted: **yes, once release-readiness evidence
  and human approval of a draft release exist**

This record identifies the Zaero content the port carries forward and the
importer boundary used to rebuild the content pack from an existing
installation. The local paths below are audit evidence from one developer
machine, not build constants; committed tools must resolve paths from arguments,
environment variables, or ignored local configuration.

## Evidence location

The audited installation was selected through:

~~~text
ZAERO_LEGACY_ROOT (or an explicit importer/audit argument)
~~~

Contributors may keep a Zaero installation anywhere. The importer identifies
inputs by hashes and structure, never by assuming this path.

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
| pak0.pak | 95,910,332 | 958 | 1de0161318cb946dbaad1ad6ac9abe375d3aa1da57f3571fdee3e5549cb0fafd | GPL Zaero content; importer source |
| pak1.pak | 4,931 | 1 | 3806e4cc59564e5a081518adf04fc608d79159b1e31d073b6699f0a3a34b4973 | GPL Zaero content; importer source |
| pak2.pak | 12,001,303 | 12 | e0b043599386f5b39701919f334de37d21011dd254630e17504dece497fec82e | GPL Zaero content; importer source |

The three directories contain 971 entries before override resolution and 969
effective paths after layering. pak1 replaces default.cfg. pak2 adds six
deathmatch maps and replaces maps.lst. Those are the only repeated PAK paths
found by the audit.

The effective runtime view includes 20 BSPs: 14 campaign maps from pak0 and six
deathmatch maps from pak2. pak0 also contains elogo.cin and zlogo.cin.
Under [D-011](../compatibility/decisions.md#d-011--ztomb1-target-for-absent-tomb1-bsp),
the importer preserves ztomb1's unreferenced changelevel string `tomb1` but
must not synthesize, alias, or copy a `maps/tomb1.bsp`; no such BSP is present
in the audited layers and the generated target graph proves the record inert.

## Required loose runtime files

The original installation leaves seven plasma-sprite files and two large
cinematics outside the PAKs. The original documentation describes the sprites
as intentionally loose. Keep this layout until packed behavior is tested in the
target Rerelease.

| Runtime path | Bytes | SHA-256 | Status |
| --- | ---: | --- | --- |
| sprites/plasma1.sp2 | 332 | f6d48de85014265c3e74b4d07bd7dc358c6ee29b16a3e63cbfcf176b4614bb2a | Required loose input |
| sprites/plasma1_0.pcx | 8,679 | 5c5cf4ffe605527096dea1d99772856aa2c507f73e0acc1108fededc2f5b1f10 | Required loose input |
| sprites/plasma1_1.pcx | 8,733 | 7d387962ca8a8354c2c31080576289ae5d9368f65abbf22d344658e517ed2845 | Required loose input |
| sprites/plasma1_2.pcx | 8,679 | 5c5cf4ffe605527096dea1d99772856aa2c507f73e0acc1108fededc2f5b1f10 | Required loose input; byte-identical to plasma1_0.pcx |
| sprites/plasma1_3.pcx | 8,630 | 514f9021fd5684a8d5d8e9c06f308e853b33a7e63988a864fc495008d03d9015 | Required loose input |
| sprites/plasmashield.sp2 | 92 | bc534f26c80aacfd578db5e2979e51f58e83656f66c03e2b8a03a5c3a565ffd7 | Required loose input |
| sprites/plasmashield_0.pcx | 5,505 | 493766008bac06a8b714325d45f1fec9ef231afff58b7e5e421a9b0773f05b12 | Required loose input |
| video/intro.cin | 49,817,132 | 1ca8188f2f6a0c83445d069f8b57220347a262f71c86f2d4e331ccb3b98e2fce | Required loose input |
| video/outro.cin | 16,606,854 | 313e06e29bf354e454353f0f11dddc63ff99645c8700ccfd42b56c5e6e0c0932 | Required loose input |

## Content classification

The runtime dependencies bundled by the port include:

- 20 BSP maps and their effective textures, skies, models, skins, sprites,
  images, sounds, cinematics, and victory presentation;
- generated local derivatives such as Rerelease glow maps, tracked with explicit
  generated-source provenance tied to the imported source path;
- Zaero-specific item, weapon, monster, autocannon, camera, communications-dish,
  crate, IRED, seat, shrapnel, flare, shield, barrier, and explosion media;
- effective configuration data translated into non-destructive zaero.cfg,
  zaerostart.cfg, and a merged Rerelease map database entry; and
- the original credits/notices, preserved as the GPL requires.

The canonical runtime import excludes, for compatibility and safety rather than
licensing reasons:

- legacy gamex86.dll and gamei386.so binaries (incompatible with the Rerelease
  engine);
- the destructive original default.cfg and loose autoexec (they would clobber
  Rerelease user configuration);
- legacy demos and save files (they do not load on the Rerelease engine);
- installer/uninstaller state, logs, and obsolete executable metadata; and
- source PAKs, compiler output, generated PAKs, release archives, or symbols
  (build/import artifacts, not runtime content).

Old demos and saves are kept as provenance evidence only. No playback or load
compatibility is promised.

### Soundtrack boundary

The audited Zaero PAKs and required loose files contain no `.ogg`, `.mp3`,
`.flac`, MIDI, or `music/` asset. Their BSP worldspawns instead author classic
numeric CD-track values. Under [D-010](../compatibility/decisions.md#d-010--music-values-111),
ZaeREo passes values 2–11 to the soundtrack already supplied by a Quake II
Rerelease installation and preserves value 1 as logged silence. The importer,
package stages, manifests, and release modes never copy Rerelease soundtrack
files into ZaeREo output — the Rerelease soundtrack is separate commercial
content owned by id Software / Nightdive, not part of the GPL-released Zaero
assets. A Rerelease installation is a runtime prerequisite for its own
soundtrack; ZaeREo redistributes only Zaero's GPL content.

## Rights and publication

The Zaero source and assets were released by their original team under the GNU
General Public License, and the Quake II Rerelease game DLL is GPL-2.0 software.
ZaeREo redistributes all of it under the GPL, preserving the original copyright
notices and credits and providing complete corresponding source (this
repository).

The active policy is therefore:

1. bundle the ported Zaero content into `asset-full` release packages with
   notices and credits preserved;
2. accept contributor content contributions under the GPL;
3. also provide an `importer-kit` mode that rebuilds the pack from a user's own
   installation, for users who prefer to supply their own copy;
4. validate the known containers and report unsupported variants safely;
5. assemble the effective runtime tree deterministically; and
6. keep large binary media under Git LFS or bundled release archives, and keep
   `dist/` build output ignored; tracked `pack/` carries the redistributable
   project content and configuration.

The only remaining gate on a public release is engineering readiness — is the
port validated, tested, and reproducible — plus a maintainer's approval of a
draft release. There is no separate rights gate to clear. The one asset the
project deliberately does not redistribute is the Rerelease soundtrack, which is
not Zaero content (see the soundtrack boundary above).

The `docs/provenance/distribution-policy.json` record is the machine-readable
companion for components, repository/source archives, Actions
logs/artifacts/caches, release assets, editor gamepacks, modes, and file
allowlists. This asset record and `asset-policy.json` identify media inputs and
per-runtime-path handling. Readiness/package/publisher tooling consumes the JSON
rather than scraping this prose.

`local-full` is developer-only output assembled during validation; it stays out
of release channels because it is unvalidated scratch, not for any rights
reason. A public asset-bearing release uses the `asset-full` mode built from the
reviewed distributable-input manifest.

## Importer and manifest requirements

The importer must:

- take an explicit path, ZAERO_LEGACY_ROOT, or ignored local configuration;
- parse PAK directories defensively and reject traversal, invalid offsets,
  unreasonable sizes/counts, duplicate normalized paths, and case collisions;
- resolve last-package-wins precedence deterministically;
- preserve each effective path's source container, source path, hash, size, and
  case;
- record generated local derivatives, including glow maps, with explicit
  generated-source provenance tied to the imported source path;
- exclude the non-runtime categories above through an allowlist;
- copy loose files only after hash validation;
- write only beneath a verified repository-local/stage destination;
- support dry-run and non-interactive modes; and
- produce a manifest whose staged tree validates exactly.

The checked-in identity inventory is `docs/audits/assets.json`. Each importer
run emits its own deterministic JSON manifest. The reviewed shipping policy
overlay is `docs/provenance/asset-policy.json`, keyed by normalized exact path
or narrowly defined category; exact-path rules override categories. The merged
release manifest carries at least:

~~~text
runtime_path, source_container, source_path, source_sha256, effective_sha256,
size, category, references, license_status, shipping_status, notes
~~~

A CSV may be generated solely as a review rendering. It is never a second
source of truth. Schema validation rejects duplicate, orphaned, overbroad,
contradictory, or evidence-free policy entries so attribution stays intact.

Generated packages and archives are build outputs, not source assets, and do not
enter Git LFS; the bundled runtime content does.

## Records maintained

The following identity and audit records back this baseline. A generated
`docs/provenance/baselines.json` records per-file and aggregate hashes for the
supplied trees. The Rerelease input has an exact official Git match in
`docs/provenance/upstream-match.json`. Remaining engineering records that keep
the audit trail complete:

- the generated hash manifest for the legacy/Zaero baseline trees;
- review of the 969 effective PAK paths plus nine loose paths in
  `docs/audits/assets.json`, and the canonical `asset-policy.json` overlay;
- the versioned `distribution-policy.json` component, mode, per-file, and
  repository/source/CI/release-channel records;
- retained normalized asset-layer, reference-closure, case-collision, and
  importer-manifest validation reports; and
- a tested, readiness-eligible `asset-full`/`importer-kit` package.

These are engineering-completeness records; the distribution rights themselves
are settled by the GPL release of the Zaero source and assets.

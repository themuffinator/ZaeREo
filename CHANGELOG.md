# Changelog

All notable user-visible and compatibility changes will be recorded here.
Version numbers follow Semantic Versioning once public compatibility promises
begin.

## [Unreleased]

### Added

- Evidence-based Zaero-to-Rerelease port roadmap.
- Contributor, security, provenance, compatibility, decision, issue-template,
  editor-definition, and Windows-first development scaffolding.
- Hash-recorded supplied Rerelease game-DLL substrate with verified
  Debug/Release builds and `GetGameAPI`/`GetCGameAPI` exports; official upstream
  commit/origin identity remains open.
- Hash-pinned source, asset, and BSP-entity audits covering all supplied source,
  20 maps, 969 effective PAK paths, and required loose content.
- Retail-content importer, strict runtime validator, deterministic PAK/ZIP
  tooling, managed developer installer, importer-kit/local-full packager, and a
  manual GitHub publisher prototype whose remote paths remain forbidden pending
  Phase-0 containment and machine-readable policy/readiness enforcement.
- Zaero compatibility spine: map classification, custom keys/spawn fields,
  JSON save registrations, movement types, stock-map behavior gates, world
  entities, item/ammo registry, Push, Flare Gun, and monster spawn accounting.
- Sonic Cannon charge/release behavior and ceiling/floor Autocannons with
  multipart rider state and retail-backed quirks.
- Sniper Rifle charge/zoom/trace/HUD lifecycle, player/map IRED deployment, and
  the selective EMP field/call-site matrix with a non-colliding saved BFG latch.
- Roadmap release hardening for independent code/media rights, tools-only,
  importer-kit, permanently private local-full, and distinct future asset-full
  artifacts; per-user installation; deterministic mapdb
  merging, private live testing, save-schema policy, editor gamepacks, and
  machine-readable release readiness.
- Completed source-gap classification for A2K immunity/countdown, low-trigger
  platforms, FALLFLOAT explosive barrels, door/train/path extensions, inbound
  boss inventory, runtime helpers, exact laser triggers, Visor/cameras,
  obituaries, projectile dodge, AI reaction, boss pain, and physics quirks.

### Known limitations

- The game DLL builds but is not yet a campaign-playable or supported release;
  no supplied map has completed live runtime/save verification.
- A2K, Plasma Shield, Visor, weapon-number/wheel completion, Handler, Hound,
  Sentien, ZBoss, campaign systems, co-op, deathmatch, and end-to-end live save/
  split-screen fixtures remain incomplete.
- Zaero-derived code and media redistribution remain independently unverified;
  no DLL/source/media publication is authorized by the current record.

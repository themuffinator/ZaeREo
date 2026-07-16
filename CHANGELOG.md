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
  tooling, managed developer installer, asset-full/importer-kit packager, and a
  manual GitHub publisher gated behind human approval of a draft release.
- Zaero compatibility spine: map classification, custom keys/spawn fields,
  JSON save registrations, movement types, stock-map behavior gates, world
  entities, item/ammo registry, Push, Flare Gun, and monster spawn accounting.
- Sonic Cannon charge/release behavior and ceiling/floor Autocannons with
  multipart rider state and retail-backed quirks.
- Sniper Rifle charge/zoom/trace/HUD lifecycle, player/map IRED deployment, and
  the selective EMP field/call-site matrix with a non-colliding saved BFG latch.
- Roadmap release hardening for GPL code and media distribution across the
  asset-full and importer-kit modes, with local-full kept as developer-only
  scratch; per-user installation; deterministic mapdb
  merging, live testing, save-schema policy, editor gamepacks, and
  machine-readable release readiness.
- Stable Windows release eligibility workflow hardening: dispatch input accepts
  only an exact annotated stable SemVer tag; its target, repository integrity,
  clean ancestry, policy, and `playable-stable` readiness record are verified
  before any dependency install or package build. A candidate remains
  runner-local and must match its source commit, manifest, and checksum; a build
  is published only after the `playable-stable` readiness record exists and a
  maintainer approves the draft release.
- Completed source-gap classification for A2K immunity/countdown, low-trigger
  platforms, FALLFLOAT explosive barrels, door/train/path extensions, inbound
  boss inventory, runtime helpers, exact laser triggers, Visor/cameras,
  obituaries, projectile dodge, AI reaction, boss pain, and physics quirks.
- D-010 worldspawn music adaptation: values 2–11 use the installed
  Rerelease soundtrack through its native numeric contract; zdm6's value 1 and
  invalid values select logged silence. ZaeREo imports and distributes no
  soundtrack media, preserves explicit Rerelease `music`, and does not change
  client volume or native-map selection.
- Generated activation-reference and destination closure for all 30 campaign
  changelevels. D-011 preserves ztomb1's absent `tomb1` record unchanged as the
  sole unreferenced/missing inert mapper artifact; no alias, BSP rewrite, or
  importer data patch is added.
- D-040 health pickup sound FIX: Zaero's 2/10/25/default count mapping is
  selected per pickup after explicit entity noise, preserving custom mapper
  behavior without mutating shared item metadata or changing native maps.
- Active Zaero Visor integration with typed elapsed duration, bounded camera
  cycling, mapper-authored tracking labels, 0.2-second static, 6.4-second yaw
  sway, client-local HUD/view state, native command/chat policy, exact-state
  restoration, generation-safe copy cleanup, damage/death/drop/disconnect
  cancellation, and JSON registrations. D-021 classifies the legacy
  link-order-dependent solid copy as a FIX: the real player stays solid and
  vulnerable while the visible copy is non-blocking.
- D-041 Zaero damage-reaction integration: exact non-monster Autocannon
  admission, `mteam` and four tank-class exclusions, retained
  `AI_SOUND_TARGET`, valid buddy targeting, and Q-046 self-target rejection are
  layered onto the native Tesla/medic/target-anger/cooldown/ignore-shot
  lifecycle instead of importing the legacy function wholesale.
- D-042 Hover fly-strafe integration: the exact Zaero `monster_hover` now uses
  its bounded radial projectile dodge, typed saved one-second deadline, and
  source-scaled 3D slide without changing stock Hover/Daedalus circle flight.
  Q-013 is a tested FIX that explicitly clears the expired/clipped state.
- D-043 stock-monster precache adaptation: a normalized identity-locked audit
  records all 22 helpers extracted across 19 Zaero stock files and proves only
  Infantry is reused across a source boundary. Handler now relies on the
  Rerelease-native `InfantryPrecache` plus its Zaero-owned Hound precache and
  cached sound indexes; the disabled, mutating 256-sound interceptor is not
  ported against Rerelease's 2,048-index capacity.
- D-015 Release-surface containment: an identity-locked policy/audit records
  the supplied Debug-only test modules and commands, never-enabled animated
  rocket, and compiled-out ZBoss grapple renderer. A fail-closed validator now
  rejects their modules, symbols, classnames, configs, project defines, DLL
  strings, or ZIP members while preserving native Rerelease grapple constants.
- D-044 FlyMove adaptation: an identity-locked audit isolates Zaero's one-line
  global exact-duplicate plane change and seven executable float32 goldens show
  its only legacy difference is a residual-driven dead-stop on an exact repeat.
  ZaeREo retains the unmodified Rerelease near-duplicate/overclip solver shared
  by server, player, and expansion movement instead of forking global physics.
- D-045 deathmatch item injection: `zdmflags` retains its public default and
  numeric values while clearer internal disable-bit names remove the bit-2
  inversion. A Zaero-owned module preserves the exact eight-item order,
  any-member suppression, wrapping successive starts, four 15-degree radial
  sweeps, Bounce/native item lifecycle, partial-success count, and stock-map
  mapper isolation. The normalized audit proves all 20 supplied maps already
  suppress injection and locks 230 authored starts. Private legacy-v1 one-stage
  `q2dm1` reports record counts 8, 8, disabled, disabled for `zdmflags` 0–3;
  a `zdm1` control records existing-item suppression. A `_DEBUG`-only structured
  probe additionally records all eight exact classnames, successive starts,
  first attempts, 128/16-unit offsets, final origins, and native live item
  state. A deterministic private fixture derived locally from `q2dm1`
  records alternating collision-brush failures retaining exactly four successes at
  historical set indices 0/2/4/6 and wrapped start ordinals 1/6/11/16. Eight
  additional private controls record that every one historical classname alone
  suppresses the entire pass. These reports predate the v2 window-before-mod/map
  protocol and must be rerun before they count as current runtime evidence.
  Pickup, save, dedicated, and multiplayer evidence remain.
- The bounded runtime wrapper now accepts deathmatch plus validated `zdmflags`
  0–3 and records mode and the observed legacy addition count in strict private
  evidence while retaining `-window` as the first argument and a mandatory
  native-window-style pass condition.
- The runtime wrapper now requires a continuous three-second no-process interval
  before launch and immediately terminates the exact executable on any visible
  popup/non-windowed observation. The report distinguishes this safety abort
  from an ordinary timeout while older schema-v1 reports remain valid.
- A private-fixture generator and path-scoped installer overlay provide
  deterministic historical collision-observation fixtures without tracking or
  publishing a derived BSP. Their legacy-v1 reports require D-046 reruns before
  current runtime use. Reinstalling normally removes the fixture and reproduces
  the ordinary 947-entry managed PAK byte for byte.
- D-015 policy revision 2 explicitly denies both structured DM-probe signatures
  from Release; the produced Release DLL passes the expanded 11-string scan.
- D-015 retains a historical legacy-v1 one-stage Release report: the audited
  Release DLL loaded, initialized, spawned `zbase1`, reached the native
  client-begin marker, and shut down in a captioned/non-popup windowed session
  with no recorded safety abort, timeout, fatal output, dump, or residual
  process. It supplied the mod/map before the v2 window verification and must
  be rerun before it can satisfy a current launch-safety or Release runtime
  gate. The harness accepts both native `entered the game` and Release
  `Begin() from` log forms.

### Known limitations

- The game DLL builds but is not yet a campaign-playable or supported release;
  no supplied map has completed live runtime/save verification.
- A2K, Plasma Shield, Visor, weapon-number/wheel completion, Handler, Hound,
  Sentien, ZBoss, campaign systems, co-op, remaining deathmatch behavior, and end-to-end live save/
  split-screen fixtures remain incomplete.
- No validated public release exists yet: the code and media are GPL and
  redistributable, but a stable release still waits on live map/save validation
  and maintainer approval of a draft release.

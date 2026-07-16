## Outcome

Describe the observable result and why it belongs in the current roadmap phase.
Do not describe planned or unverified behavior as complete.

## Evidence and classification

- Roadmap section:
- Feature/entity/map/quirk/decision row IDs:
- Disposition: PARITY / ADAPT / FIX / not gameplay-facing
- Legacy evidence:
- Rerelease integration point:

## Verification

List exact commands and results. For runtime work include map, skill, mode,
players, save lifecycle point, and 40 Hz behavior where applicable.

~~~text
command
result
~~~

## Compatibility checklist

- [ ] I preserved exact classnames, keys, flags, runtime path case, and package precedence where affected.
- [ ] New fields, callbacks, moves, identifiers, and entity references are save-registered and round-trip tested.
- [ ] Time-dependent behavior was verified at 40 Hz.
- [ ] Per-client state was checked for split-screen isolation where relevant.
- [ ] Death, disconnect, transition, free/reuse, and failed-spawn cleanup were considered.
- [ ] I updated every affected compatibility ledger and linked evidence.
- [ ] I preserved native Rerelease API, expansion, bot, and safety behavior.

## Repository and distribution checklist

- [ ] Focused tests and the available affected full gates pass.
- [ ] No generated build/stage/package or local configuration is included.
- [ ] No non-GPL game data (e.g. the Rerelease soundtrack or base files) or engine-incompatible legacy binaries are included.
- [ ] GPL notices and the original authors' credits are retained on any ported content.
- [ ] Unrelated dirty-worktree changes were preserved.

## Remaining limitations

List anything intentionally unverified, deferred, or blocked and the row that
tracks it.


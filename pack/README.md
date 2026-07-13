# Tracked runtime contribution

This directory contains only redistributable, source-controlled configuration.
Do not commit files imported from a commercial Zaero installation unless their
redistribution status has been resolved and recorded by the project.

## Verified legacy input

The importer recognizes the supplied Zaero 1.1 archive set by SHA-256:

- `pak0.pak`: `1de0161318cb946dbaad1ad6ac9abe375d3aa1da57f3571fdee3e5549cb0fafd`
- `pak1.pak`: `3806e4cc59564e5a081518adf04fc608d79159b1e31d073b6699f0a3a34b4973`
- `pak2.pak`: `e0b043599386f5b39701919f334de37d21011dd254630e17504dece497fec82e`

The deterministic precedence is `pak0.pak`, then `pak1.pak`, then `pak2.pak`,
then the seven explicitly named loose plasma-sprite files and the loose
`video/intro.cin` and `video/outro.cin`. Later layers replace earlier paths.
The importer rejects path traversal, duplicates, case-only collisions, unknown
retail hashes, and missing loose files.

Legacy native libraries, demos, saves, screenshots, `default.cfg`, and
`autoexec`/`autoexec.cfg` are excluded. In particular, the retail `default.cfg`
starts with `unbindall` and must never replace Rerelease user configuration.

Never import commercial content into this tracked directory. From the repository
root, validate the known input without writing:

```powershell
python tools/import_legacy_assets.py `
  --source "D:\Games\Zaero" `
  --output .install/imported/zaereo `
  --manifest .install/imported/zaereo-asset-manifest.json `
  --dry-run
```

Remove `--dry-run` to import into the ignored `.install/` tree. A differing
existing file is never overwritten unless `--overwrite` is explicit. Verify
imported bytes:

```powershell
python tools/validate_runtime.py `
  --root .install/imported/zaereo `
  --manifest .install/imported/zaereo-asset-manifest.json `
  --strict
```

The packager merges this tracked contribution with a separately validated
import stage according to the selected distribution mode. A config-only PAK
can be inspected without copying commercial media:

```powershell
python tools/make_pak.py pack .install/stage/zaereo/pak0.pak --exclude README.md
```

Do not validate that config-only PAK against the legacy import manifest; they
describe different inputs. The current release manifest treats a PAK as one
outer file, and the current `validate_runtime.py --pak` path does not compare
member names against staged loose files. Before publication, the roadmap
requires a generated cross-layer runtime manifest that expands PAK members and
rejects unexplained loose/PAK overrides; do not claim that check has passed yet.

`--allow-unknown-hashes` and `--allow-unknown-source-hashes` exist only for
synthetic tests and development of other known distributions. They are not
release switches.

## `mapdb.json` limitation

Quake II Rerelease does not provide a documented fragment-merge mechanism for
mod `mapdb.json` files. The checked-in file is therefore an honest Zaero-only
development scaffold: it declares the exact cinematic start chain, 14 campaign
maps, and six deathmatch maps, but it does not pretend to preserve every stock
episode in the New Game database.

Before a release claims stock-menu coexistence, local completion must start from
the `mapdb.json` belonging to the user's hash-supported Rerelease data build,
append the Zaero records without reordering upstream menu arrays, and test the
result in game. The combined database is locally generated and is not a public
package input unless the exact base bytes are separately cleared for
redistribution. Copying a stale database from another project would silently
discard future upstream entries. The console command `exec zaerostart.cfg`
remains independent of this menu limitation.

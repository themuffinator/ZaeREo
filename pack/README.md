# Tracked runtime contribution

This directory contains only redistributable, source-controlled runtime
definitions: configuration, map scaffolding, and Quake II Rerelease material
descriptors. Do not commit files imported from a commercial Zaero installation
unless their redistribution status has been resolved and recorded by the
project.

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

## Rerelease materials and glow maps

The checked-in `textures/**/*.mat` files are text-only Rerelease material
descriptors generated from verified Zaero texture names. They contain only
Rerelease material tokens such as `clank`, `glass`, or `splash`, and belong to
the project-owned `pak0.pak` contribution.

Regenerate them from a local import when the texture inventory changes:

```powershell
python tools/zaero_material_assets.py generate-mats `
  --source-root .install/imported/zaereo `
  --output-root pack
```

Glow maps are different. `_glow.png` files are derived from Zaero pixel data, so
they are generated only into the ignored import tree by `import_legacy_assets.py`
or `zaero_material_assets.py generate-glow`, recorded in the import manifest,
and remain import-owned private local output. Do not commit generated glow PNGs
under `pack/`.

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
import stage according to the selected distribution mode. A project-owned PAK
can be inspected without copying commercial media:

```powershell
python tools/make_pak.py pack .install/stage/zaereo/pak0.pak --exclude README.md
```

Do not validate that project-owned PAK against the legacy import manifest; they
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

`tools/merge_mapdb.py` provides the private mechanical merge. It reads either a
selected loose `mapdb.json` or the exact member from a selected Rerelease PAK,
requires that member's SHA-256, a reviewed data-build identifier, explicit
episode/map insertion indices, and a content root containing every referenced
Zaero BSP/cinematic; output and report paths must be beneath `.install`. It
preserves unknown base fields and upstream array order, atomically writes the
generated result, and proves inverse reconstruction when the Zaero records are
removed. Before a release claims stock-menu coexistence, an owner must still
select a supported data-build hash and menu position and test the result in
game. The combined database is locally generated and is not a public package
input unless the exact base bytes are separately cleared for redistribution.
Copying a stale database from another project would silently discard future
upstream entries. The console command `exec zaerostart.cfg` remains independent
of this menu limitation.

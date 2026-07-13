# Zaero editor definitions

`entities.json` is the canonical, reviewable schema for Zaero-specific map
entities. The checked-in FGD files under `common/`, `netradiant-custom/`, and
`trenchbroom/` are generated from it:

```powershell
python tools/generate_editor_defs.py
python tools/generate_editor_defs.py --check
```

The schema covers all 34 exact classnames exposed by the supplied Zaero source:
27 used by the retail maps and seven source-only compatibility surfaces. It does
not replace an editor's Quake II/Rerelease base definitions. Load `ZaeREo.fgd`
after the editor's normal Quake II FGD.

The historical `monster_sentien` spelling, property names, and spawnflag values
are compatibility ABI. Change them only with corresponding runtime, audit,
matrix, and map-fixture updates. Models referenced by the definitions are not
distributed by this directory; use the legal local asset importer described in
the root README.

The two editor-specific copies are deliberately identical today. Keeping
separate generated paths makes installation predictable and leaves room for
editor-specific wrappers without forking the entity contract.

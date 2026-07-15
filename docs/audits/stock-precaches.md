# Zaero stock-monster precache audit

This normalized audit classifies AI-015 and the related legacy sound-index
workaround. It is source/static evidence, not live audible or map-completion proof.

## Result

- Zaero adds **22** stock precache helpers across **19** source files.
- Only **1** helper has a cross-file consumer, at **1** call site: `SP_monster_infantry_precache` from Handler.
- The Rerelease baseline already exposes `InfantryPrecache` to both native
  Infantry and `SP_turret_driver`; ZaeREo reuses it for Handler precache and
  conversion, while Hound keeps its Zaero-owned precache.
- The other stock helper extractions are not port requirements by themselves.
  Other behavior changes in those files remain separately classified.

## Added stock helper call graph

| Owner | Helper | Local consumers | Cross-file consumers |
| --- | --- | --- | --- |
| m_berserk.c | `SP_monster_berserk_precache` | `SP_monster_berserk` | — |
| m_boss2.c | `SP_monster_boss2_precache` | `SP_monster_boss2` | — |
| m_boss31.c | `SP_monster_jorg_precache` | `SP_monster_jorg` | — |
| m_brain.c | `SP_monster_brain_precache` | `SP_monster_brain` | — |
| m_chick.c | `SP_monster_chick_precache` | `SP_monster_chick` | — |
| m_flipper.c | `SP_monster_flipper_precache` | `SP_monster_flipper` | — |
| m_float.c | `SP_monster_floater_precache` | `SP_monster_floater` | — |
| m_flyer.c | `SP_monster_flyer_precache` | `SP_monster_flyer` | — |
| m_gladiator.c | `SP_monster_gladiator_precache` | `SP_monster_gladiator` | — |
| m_gunner.c | `SP_monster_gunner_precache` | `SP_monster_gunner` | — |
| m_hover.c | `SP_monster_hover_precache` | `SP_monster_hover` | — |
| m_infantry.c | `SP_monster_infantry_precache` | `SP_monster_infantry` | `z_handler.c:SP_monster_handler_precache` |
| m_insane.c | `SP_misc_insane_precache` | `SP_misc_insane` | — |
| m_medic.c | `SP_monster_medic_precache` | `SP_monster_medic` | — |
| m_mutant.c | `SP_monster_mutant_precache` | `SP_monster_mutant` | — |
| m_parasite.c | `SP_monster_parasite_precache` | `SP_monster_parasite` | — |
| m_soldier.c | `SP_monster_soldier_light_precache` | `SP_monster_soldier_light` | — |
| m_soldier.c | `SP_monster_soldier_precache` | `SP_monster_soldier` | — |
| m_soldier.c | `SP_monster_soldier_ss_precache` | `SP_monster_soldier_ss` | — |
| m_soldier.c | `SP_monster_soldier_x_precache` | `SP_monster_soldier_light_precache`, `SP_monster_soldier_precache`, `SP_monster_soldier_ss_precache` | — |
| m_supertank.c | `SP_monster_supertank_precache` | `SP_monster_supertank` | — |
| m_tank.c | `SP_monster_tank_precache` | `SP_monster_tank` | — |

## Sound-index context

| Fact | Result |
| --- | --- |
| Legacy Zaero `MAX_SOUNDS` | 256 |
| Rerelease `MAX_SOUNDS` | 2048 |
| Rerelease legacy-compatibility value | 256 |
| Supplied project defines `CACHE_SOUND` | false |
| Workaround intercepts global sound indexing | true |
| Workaround mutates caller name buffers | true |
| Workaround rejects at the legacy limit | true |
| Workaround allocates a level list and copied names | true |

## D-043 disposition

Use the native Rerelease `InfantryPrecache` surface for Handler and retain
native stock spawn paths everywhere else. Use `cached_soundindex` assignments
for Handler, Hound, and Infantry resources. Do not port the disabled legacy
global interceptor or its 256-entry rejection behavior. Full all-map resource
reference and audible verification remains open.

This audit classifies only the added stock precache helper surfaces and their call graph. Other resource, AI, EMP, flash, cadence, and behavior changes in the same stock files require their own compatibility rows.

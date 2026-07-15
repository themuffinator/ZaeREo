# Zaero Visor trace-order audit

This normalized audit proves the source-level mechanism behind D-021.
It does not claim a live retail capture or live Rerelease verification.

## Identity

| Input | SHA-256 | Bytes |
| --- | --- | ---: |
| z_camera.c | 5a4b802772d4bf6d7b1f1b80e3df9bebe12f9001f96f544f7e10c237e712c5b8 | 2759 |
| p_client.c | f0e871b588fb4527bcafb42458bc810f4eef748c32f245646de760e9036db6a4 | 40165 |
| g_phys.c | 21a0e0374a925c9de1ac9e5143de80a64c2f197702b4ec8cbab1ecea45d5d056 | 25085 |
| server/sv_world.c | f423eaa292289205f0a265d4a75c2bdf0085b184ce056e410820f2bb54adbfa7 | 14297 |
| gamex86.dll | 9f530380d2202b03e252726478894a27f57ac7d5e54e97da106ecde199a2d786 | 461312 |

## Proof

| Fact | Result |
| --- | --- |
| copy_created_after_player | true |
| copy_is_solid_bbox | true |
| copy_takedamage_assignment_present | false |
| equal_fraction_replaces_winner | false |
| frozen_clientthink_relinks_player | false |
| initial_equal_hit_winner | real_player |
| post_pusher_equal_hit_winner | visorcopy |
| pusher_can_relink_frozen_player | true |
| real_player_hidden_not_desolidified | true |
| solid_links_append_at_tail | true |
| solid_trace_walk_is_oldest_first | true |
| trace_ownership_is_link_order_dependent | true |

Initial equal-hit order: real_player, VisorCopy.

After a mover relinks the frozen player: VisorCopy, real_player.

## D-021 disposition

Classify the port as FIX: preserve the hidden real player as solid and
damageable, but make the generation-owned presentation copy SOLID_NOT.
This removes link-order-dependent trace absorption without weakening the
player. Live hitscan, projectile, mover, save/load, and multiplayer
verification remain open.

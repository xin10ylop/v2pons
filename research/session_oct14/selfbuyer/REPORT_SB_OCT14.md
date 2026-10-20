# The V3 self-buyer lc:0a493d1a|13ead562, Oct 14 2026 ~10:00 UTC: the count gate passes; nearly half its tokens are sell-locked from the launch

**Verdict:** the watch's go signal is crossed: 15 launches in 6 h, all with the launcher's own 0.05 ETH buy (the gate asked for 4). The
full $5-probe gate of research/session_oct11/lines/REPORT_S.md also passes on the replay. But **11 of the 23 line launches in 24 h are
sell-locked**, and the lock is on from the block after the launch. On the 12 sellable pools rule (a) makes **+7.5% to +9.7% a trade (mean
+9.0%)**; the much larger means in the full replay come from locked pools, where a real sell reverts. Eight of the 12 sellable pools are
one 4-minute burst by one wallet (0xe30fa99d, 09:38-09:41 UTC). **The engine cannot trade this line today:** it has no self-buyer family
(fire on the mint, exit on the own buy), and FlipRelayV3 is not deployed (docs/RELAY_V3.md, HANDOFF 16.16).

Data: REPORT_S's scripts s01-s06 and s08, copied unchanged into this folder and rerun on the last 24 h (public RPC), plus `lockcheck.py`
(new): an eth_call of `token.transfer(pool, 0)` from an outside address on Dwellir's archive node (the research key) at the launch + 1,
the own buy - 1, the own buy, + 1, + 3, + 10, + 100 and now. Validated on the known locked token `0x7399605a` (RELAY_V3 section 2:
"verkoop vergrendeld") and on WETH (ok).

## The gate (REPORT_S), last 6 h unless noted
1. **At least 4 line launches:** 15 (7 wallets; 23 in 24 h). Pass.
2. **Own first buy 0.05 ETH in at least 80%, none missing, no 0.001 regime:** 15 of 15 (24 h: 22 at 0.05 and one at 0.10). Pass.
3. **Own buy at least 10 blocks after the mint and by +190:** mint at +6..+10; own buy at +22..+36, 16..28 blocks after the mint
   (2-3 s). Pass.
4. **No pull at or before the own buy + 3:** the earliest pull was 51 blocks after the own buy (11 of 15 pulled by +5000, all by
   the launch wallet). Pass.
5. **No outsider buy between the mint and the own buy:** 0. Pass, but untested: nobody has bought ahead of it.
6. **Rule (a) mean at least +5% at $5, win at least 0.9, 0 pulled:** all 15: mean +86.4%, median +9.7%, win 1.00, pulled 0. Pass on the
   replay, which does not know about the lock (below).

## The sell lock (lockcheck_24h.out)
- Locked: **11 of the 23** line launches in 24 h, and 3 of the last 15 (05:12, 07:29, 09:43).
- **On from the launch:** every locked token refuses the transfer at the launch + 1, before the mint and the own buy. So the engine's
  existing V3 sell check (the one p356 uses) would see the lock at the mint, before our buy, and skip the pool.
- Two templates: "verkoop vergrendeld" and "vente bloquée". Two "vente bloquée" tokens accept the transfer now; that does not matter
  for a sell at the own buy + 1.
- **Sellable pools: 12 of 23** (24 h) = 12 of 15 (6 h): 0xf48181ad, 0x752f831f x2, 0x7b2b9cdd, and 0xe30fa99d x8 (09:38-09:41).

## Rule (a) on the sellable pools only (s06's per-launch numbers)
- n 12: +7.5% (4 pools) and +9.7% (8 pools, the burst); mean +9.0% at $5.
- At $5: about +$0.45 a trade; at $15: about +$1.4.
- **12 a day** if the last 24 h repeat (8 of them one burst): about $5/day at $5, about $17/day at $15.

## Other behavior in the window
- An outside buyer (`0xe8b494`, SwapRouter02 04e45aaf, 0.0004 ETH) bought at the own buy + 2..+5 in each of the 8 burst pools.
- The EIP-7702 fleet (34fcd5be) bought 0.003-0.077 ETH from +117 to +400, as before.
- Pulls: 11 of 15 by the launch wallet, from +75 to +1823 (median +150).

## What a probe needs (REPORT_S "What the engine would need", unchanged, plus the lock)
- A V3 self-buyer family:
  - fire on the standalone mint (88316456, 356 B, to the V3 PositionManager), buy at the mint + 2;
  - take the position id from the mint's receipt;
  - sell at the own buy + 1 (the trigger: the launch wallet's exactInputSingle of at least 0.045 ETH), capped at the launch + 200;
  - refuse mirrored (WETH-as-token1) launches.
- The V3 sell check before the buy (the lock is visible at the mint).
- FlipRelayV3 deployed by the owner.
- The operator's reaction to a buy ahead of its own is still untested (Oct 9: it stopped buying after being sniped twice).

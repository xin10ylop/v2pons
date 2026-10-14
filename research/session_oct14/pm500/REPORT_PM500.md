# REPORT_PM500: the direct PoolManager.initialize fee-500 launches (Oct 14)

Verdict: **NOT A LINE** (one Opus scout; no skeptic, no candidate).

## Who

Verdict: NOT A LINE. Every launch of this shape is a wash-volume honeypot run by one operator; the "scripted buyer" is the operator's own wallet fleet. (The REPORT.md write was refused, so the full report is in these fields.)

Data: the 24.5 h to 04:09 UTC Oct 14 (blocks 87,204,552 to 88,069,871, 9.84 blocks/s). Public RPC only, POSTs at least 0.5 s apart; about 1,700 POSTs, 7 got HTTP 429 and were backed off. No edits to src/, deploy/, tests/ or docs/, and nothing committed.

There were 128 launches. All 128 ETH-pair, fee-500, tick-spacing-1, no-hook inits on the PoolManager in the window had this shape (a 196-byte direct call).

LAUNCHER: a fresh wallet each time. I traced 12 launchers; all 12 used the same nonce sequence:
- Funded 1.6-9.8 ETH at L-234..-273.
- Nonce 0, at L-201..-233: a plain ETH transfer of (funding minus the pool's ETH minus 0.1) to the fleet router (0x628bd69e until about 12:00 Oct 13, then 0x543282f8). In 22 of 128 launches there is no such transfer and the token deploy is nonce 0.
- Nonce 1, at L-126..-155: the token deploy (6,945-byte initcode). The token is CREATE(launcher, nonce) in 128 of 128.
- Nonce 2, at L: PoolManager.initialize.
- Nonce 3: token.approve. Nonces 4-5: two Permit2 approvals.
- Nonce 6, at A = L+41/42/43 (p10/50/90): the liquidity add, a PositionManager modifyLiquidities (0xdd46508f, 1,380 bytes).
- Nonce 7: the pull, 708 bytes, by the launcher in 127 of 127 pulled pools. It lands at L+167..11,211 (p10/50/90 903/4,789/8,942), which is 5/14/82 blocks after the fleet's last swap.
- Nonce 8, 300-550 blocks after the pull: a sweep to a single-use wallet. That wallet passes the exact amount to a second single-use wallet about 40 blocks later, and the second one funds the next launcher.
  - Traced: 0xb61490f8 → 0x864ec079 → 0xe88361e0 → launcher 0x2240d2d5 (7.1714 ETH) → 0x7d8855aa → 0x40ca414f → launcher 0x1968d5a8 (5.1085 ETH) → 0xd96174cb (7.2853 ETH).
  - So it is one rotating pot. Launchers end with about 4.6e-6 ETH.

LIQUIDITY: always all 10e9 tokens. Five parameter sets rotate:

| Launch tick | Range | Liquidity | ETH | Pools |
|---|---|---|---|---|
| 216,406 | 170,350..216,405 (token-only, just under the price) | 2.22e23 | 0 | 27 |
| 219,283 | full | 1.73e23 | 3.0 | 26 |
| 216,406 | full | 2.00e23 | 4.0 | 26 |
| 214,174 | 168,118..214,173 (token-only) | 2.48e23 | 0 | 25 |
| 217,741 | full | 1.87e23 | 3.5 | 24 |

The pool holds 2.0/6.0/8.9 ETH at the pull.

TOKEN: one template.
- Runtime 4,655 bytes (four metadata variants of the same length).
- Only the 11 standard ERC-20 selectors (name, symbol, decimals, totalSupply, balanceOf, transfer, allowance, approve, transferFrom, increaseAllowance, decreaseAllowance). No owner(), no tax, no extra rules.
- 18 decimals, supply 10e9. Names are copied from known coins.
- Sells work (three dust bots sold), so the rug is the pull, not the token.

THE TWO 600-SWAP POOLS: L 88,022,489 (DEXSI, launcher 0xcc18eb81) and L 88,027,196 (Veilora, launcher 0x7f1005db). They are the hooked sibling of the same program; they dropped out of my no-hook census because they have a hook.
- 8 such launches in 24.5 h.
- Same as the no-hook shape: ETH pair, fee 500, tick spacing 1, direct 196-byte init, add at L+41..44, first swap at L+111..118, same router selector 0x7169b574.
- Different:
  - hook address ending ...4840 (beforeAddLiquidity + afterSwap);
  - launcher nonce 7;
  - token-only range 193,377..239,432 at liquidity 7.0e23 (about 3.5x the no-hook liquidity);
  - their own routers 0xe394ba9f and 0x055de4ce;
  - 243-289 wallets a pool, none shared with the no-hook fleet;
  - 580-755 swaps by +600, with 61-94 ETH in and 40-84 ETH out (two-way wash volume);
  - pulled 1.3-8 h later (L+47k..296k); the two from the watch are not pulled yet.
- They are the large wash-volume variant, not organic demand. I did not study how they react to outsiders.

## Timing

THE BUYER (FLEET):
- 490 wallets, at nonce 1,373/1,801/3,219 when they swap (p10/50/90). Each is used in about 28 pools (max 40).
- All call one router (0x628bd69e, then 0x543282f8), selector 0x7169b574, value 0. The ETH sits in the router, which the launcher pays at nonce 0, so the fleet is the operator.
- The watch's "first swap at +43..+47" is the dust sentinel 0xe71a69f4 (2e-6 ETH via the Universal Router). It lands at A+3 in 102 of 127 pools and at A+2..5 in the rest. The fleet comes later.
- 0x57ee6646 (6e-5 ETH via the Universal Router, T+27/53/68, sells at about L+1,300) is a dust follower and draws no reaction.

FIRST FLEET BUY, T (p10/50/90):
- Over 24 h: L+114/121/141, which is A+72/78/99 (A is the add block).
- Best fixed window: ±1 holds 22% (L+115) or 24% (A+73); ±2 holds 32% or 35%.
- In seconds, T-A is 7-8 s in 91 of 127 pools and 7-10 s in 120 of 127. The fleet is on a wall clock about 8 s after the add, which at about 10 blocks a second gives no block-level timing.
- One pool (L 87,523,770) never got a fleet buy and was pulled at L+327.

| Hour (UTC) | n | T-L p10/50/90 | T-A p50 | best ±1 window from A |
|---|---|---|---|---|
| 13 07h | 5 | 113/137/176 | 99 | 40% |
| 13 08h | 8 | 113/119/125 | 76 | 38% |
| 13 09h | 8 | 112/118/147 | 78 | 38% |
| 13 10h | 7 | 115/116/136 | 74 | 57% |
| 13 11h | 3 | 113/129/145 | 86 | 33% |
| 13 12h | 7 | 115/120/140 | 79 | 33% |
| 13 13h | 5 | 119/122/124 | 80 | 40% |
| 13 14h | 4 | 115/122/125 | 80 | 50% |
| 13 15h | 6 | 116/120/122 | 78 | 50% |
| 13 16h | 7 | 122/126/128 | 82 | 43% |
| 13 17h | 3 | 114/120/128 | 78 | 33% |
| 13 18h | 5 | 114/121/142 | 79 | 40% |
| 13 19h | 6 | 120/125/139 | 83 | 33% |
| 13 20h | 7 | 115/119/137 | 78 | 29% |
| 13 21h | 5 | 116/118/135 | 76 | 80% |
| 13 22h | 4 | 114/127/134 | 85 | 50% |
| 13 23h | 8 | 115/121/132 | 79 | 38% |
| 14 00h | 9 | 115/118/122 | 76 | 44% |
| 14 01h | 6 | 121/130/148 | 88 | 33% |
| 14 02h | 10 | 113/121/142 | 77 | 40% |
| 14 03h | 5 | 115/121/140 | 79 | 40% |

The hourly shares are inflated by small n; the full table (L and A windows, ±1 and ±2) is in s05_timing.out.

SIZES AND TOTALS:
- The first fleet buy is 0.009/0.017/0.043 ETH.
- By +600: 20/27/36 fleet buys and 0.63/0.86/1.44 ETH. The totals repeat exactly because the fleet replays fixed size lists (31 schedules): 1.1342 ×12, 1.4439 ×10, 0.6666 ×10, 0.7270 ×6, 1.0952 ×6, 1.4595 ×5, 1.4901 ×5, 0.7181 ×5.

FLEET SELLS:
- 0/3/6 sells by +600.
- Over the pool's life: 43/126/188 buys (1.6/6.6/14.0 ETH in) and 8/45/113 sells (0.2/3.0/9.1 ETH out).
- 37% of fleet buys are sold later by the same wallet, at a median 530 blocks after the buy; the median fully sold position is up 57%.

PRICE PATH (token price against the launch price, head of block):

| Point | Price change |
|---|---|
| Up to T | 0 |
| T+1 | +0.4/+1.1/+2.1% |
| T+10 | +1.5% (median) |
| T+50 | +4.4% (median) |
| T+100 | +9.2% (median) |
| T+200 | +17.7% (median) |
| L+300 | +7/+14/+23% |
| L+400 | +14/+25/+51% |
| L+600 | +28/+47/+69% |

## Reaction

BEFORE THE FIRST SCRIPTED BUY: in 128 pools nobody except the fleet, the sentinel and 0x57ee6646 bought before T, so there are 0 non-dust cases.
- 0x57ee6646 bought at T-1 in one pool (0xfc857c21). There was no reaction: the fleet bought 172 times and the pull came at the normal L+5,140.
- In the pool with no fleet buy, 0x57ee6646 bought at L+181 and the pull came at L+327. That case is ambiguous.
- So how the operator reacts to a buy before T is not measured here. The prior is the 3.0 lesson: an early buy is pulled and the bot never buys.

AFTER T, THE REACTION IS TOTAL AND FAST:
- Every one of the 64 pools whose first outside buy was 0.0003 ETH or more was pulled within 193 blocks of that buy.

| Pulled within | Observed (of 64) | Same-age expected in control pools |
|---|---|---|
| 5 blocks | 10 (16%) | 0.0 |
| 60 blocks | 28 (44%) | 0.5 |
| 200 blocks | 64 (100%) | 1.3 |

- Lags: 4 (×9), 5, then 21 up to 193 blocks.
- At 0.001 ETH or more: 45 of 45 pulled within 200 blocks.
- After the outside buy the fleet nearly stops: 1.9 buys in the next 200 blocks, against 5.2 at the same age.
- 0x3e2f6582 bought 0.005 ETH (our size) at T+199..261 in four pools. They were pulled 4, 4, 4 and 114 blocks later.
- Even dust drew it sometimes: 0xf05d0e3f and 0x24919ef8 (0.000039 ETH each, at T+26..69) were pulled 4-5 blocks later in 2 of their 3 pools.
- Pools with an outside buy were pulled at L+899/2,676/7,078 (p10/50/90), against L+1,062/8,717/11,094 for the rest.

HOW OUTSIDERS FARED:
- 46 outside wallets (not counting two dust bots) put in 0.2299 ETH over 71 non-dust buys and got back 0.000041 ETH.
- No non-dust outsider ever sold before the pull; every one lost the whole stake.
- The earliest outsiders (T+26..261) were all pulled within 4-114 blocks.
- Only the dust bots survived: 0x353887ec (4e-6 ETH, 34 pools), 0xdf24e301 (1e-5..1e-4 ETH) and 0x57ee6646.

## Rule

METHOD: exact integer v4 replay on all 128 pools.
- The simulator reproduces all 23,495 real swaps (worst relative error 2.4e-14). It applies each swap's own fee: 500 ppm, or 625 once a pool's 125-pip protocol fee is switched on.
- Our buy is at the head of block a and our sell at the head of block b. A pull at or before b is -100%.
- Gas $0.02 per round trip, ETH = $2,570.
- Reaction, two ways: the pull lands 4 blocks after our buy (the fastest measured), or the 64 measured lags are applied as a distribution.

RESULTS. Net is shown as: no reaction / pull 4 / measured lags.

| Rule | n | Gross, no reaction | Net at $5 | Net at $15 |
|---|---|---|---|---|
| front A+2, sell 2 blocks later | 128 | -0.10% | -0.50 / -0.5 / -0.5% | -0.23 / -0.2 / -0.2% |
| front A+2, sell into the fleet's first buy (T+1) | 127 | +1.12% | +0.72 / -100.4 / -49.8% | +0.98 / -100.1 / -49.5% |
| front A+2, sell 60 blocks later | 128 | -0.10% | -0.50 / -100.4 / -44.2% | -0.23 / -100.1 / -43.9% |
| front A+2, sell 200 blocks later | 128 | +9.46% | +9.06 / -100.4 / -100.4% | +9.31 / -100.1 / -100.1% |
| front A+2, sell at L+600 | 128 | +39.28% | +38.88 / -100.4 / -100.4% | +39.05 / -100.1 / -100.1% |
| blind A+73 (best window), sell 3 blocks later | 128 | +0.12% | -0.28 / -0.3 / -0.3% | -0.02 / -0.0 / -0.0% |
| oracle: head of T, sell at T+2 | 127 | +1.15% | +0.75 / +0.8 / +0.8% | +1.02 / +1.0 / +1.0% |
| oracle: head of T-1, sell at T+1 | 127 | +1.12% | +0.72 / +0.7 / +0.7% | +0.98 / +1.0 / +1.0% |
| oracle: head of T-1, sell at T+60 | 127 | +5.73% | +5.33 / -100.4 / -40.9% | +5.59 / -100.1 / -40.7% |
| follow T+2, sell 3 blocks later | 127 | +0.06% | -0.34 / -0.3 / -0.3% | -0.08 / -0.1 / -0.1% |
| follow T+2, sell 10 blocks later | 127 | +0.58% | +0.18 / -100.4 / -15.5% | +0.45 / -100.1 / -15.3% |
| follow T+2, sell 60 blocks later | 127 | +4.54% | +4.14 / -100.4 / -41.6% | +4.40 / -100.1 / -41.3% |
| follow T+2, sell 200 blocks later | 127 | +15.55% | +15.15 / -100.4 / -100.4% | +15.39 / -100.1 / -100.1% |

A+1 and A+3 fronts give the same numbers as A+2.

READING IT:
- Without the reaction, holding from the add to L+600 makes +39%. That is the fleet's own price lift, and it is exactly what the operator protects with the pull.
- With the reaction, every hold longer than 3 blocks loses, because every measured lag (4-193 blocks) is shorter than the hold.
- The best surviving case is the oracle in-block front sold by T+2: +0.7% net at $5, +1.0% at $15. It cannot be timed (best ±1 window 24%).
- No rule clears +5% mean net at $5, so the verdict is NOT A LINE.
- Engine support, if it ever mattered: a new decoder for the direct init plus the separate 1,380-byte PositionManager add (a small engine change). Not worth building.

## Rate

- 128 launches in the 24 h to 04:09 UTC Oct 14, every one after 07:14 UTC Oct 13: 3-10 an hour, about 6 an hour since then.
- 13 more came before the window, between 00:31 and 00:57 UTC Oct 13. The earliest is block 87,095,874; there were none from then until 07:14.
- At the current pace that is about 130-150 a day. Each is a fresh launcher fed from the same rotating pot.
- The hooked sibling (the two 600-swap pools) adds 8 launches in 24.5 h, about 8 a day.

## Files

All files are in /home/user/v2pons/research/session_oct14/pm500/census24/ and every one is under 2 MB. The *_cache.jsonl files are git-ignored and the scripts rebuild them. The REPORT.md write was refused; the full report is in the other fields of this answer.

| File | What it is |
|---|---|
| rpc.py, common.py | Paced read-only RPC and the shared loaders |
| v4sim.py | Exact v4 swap math |
| s01_inits.py/.json/.out, s01_blockts.json | The 128 launches |
| s02_events.py/.out, s02_events_00..08_cache.jsonl | All Swap and ModifyLiquidity logs |
| s03_txs.py, s03_txs_00..07_cache.jsonl | The 23,756 transactions behind them |
| s04_build.py, s04_pools_*_cache.jsonl | Per-pool records with each swap labelled fleet, sentinel, 0x57ee6646 or other |
| s05_timing.py/.out/.json | T from L and from A, per hour |
| s06_validate.py/.out | Simulator checked against every real swap |
| s07_reaction.py/.out/.json | Every non-fleet swap and the pull after it |
| s08_fleet.py/.out, s08_fleet_pools.json | The fleet's wallets, totals and sells |
| s09_price.py/.out | Price path |
| s10_replay.py/.out/.json | The rules at $5 and $15, with and without the reaction |
| s11_tokens.py/.out/.json | Token code, selectors, launcher state |
| s12_sameage.py/.out | Pulls after outside buys against same-age controls |
| s13_launcher.py/.out/.json | Launcher transactions and funding (12 launches) |
| s14_chain.py/.out | Sweep and hop chain (stopped after 3 links) |
| s15_summary.py/.out, s15_pools.json | Per-pool summary |
| s16_big.py/.out/.json, s17_hooked.py/.out/.json | The two 600-swap pools and the hooked sibling census |
| s18_seconds.py/.out | T in seconds, and the shape before the window |

# REPORT_FIND2433: where the 2.433 line went (Oct 14, 2026)

Verdict: the 2.433 operator was found, not on Robinhood. It cashed the line out (hub 0x6c3bd8f6 bridged 9.3 ETH to Ethereum on Oct 12, where an Across handler paid it straight back to the same address), ran ONE test launch on Ethereum mainnet (Oct 12 13:51, the exact 2.433 fingerprint, its own 31 buyer wallets), then ran the line on BNB Chain Uniswap v4 for 3.7 hours (Oct 13 17:17-20:59 UTC, 52 pools, about 14 an hour) with a byte-identical bot router 0x07cb6161 (same code hash as Robinhood's 0x1cbaf24d, same admin 0x0152c954), the same 1,526-B 777 token, the same .4333285 value suffix, 30 of its 34 bot wallets being the Robinhood 2.433 buyers; then stopped. Funds go to the consolidation key 0x31c8cf1c and on to a Binance deposit address. On BNB the front replay gave +6.2% a trade (45 of 46 pools), BUT 5 of 6 pools with an outside buyer were pulled 6-7 blocks after it (Robinhood's line never did that), and the line has been dormant since 20:59 Oct 13. Its continuous BNB business through the same router is on PancakeSwap V2 (the families REPORT_BNB already refuted: every stranger pulled within 8 blocks). On Robinhood nothing restarted, renamed or reshaped (12,802 launches Oct 12-14 scanned in seven grouping layers). Tracker: research/session_oct14/watch/track_2433_xchain.py.

## Analyst 1 (NOT FOUND)

### Robinhood Chain v4. 151 launches between Oct 12 09:45:36 and Oct 13 22:51:31 UTC, in 7 bursts (35 in the 12 09h hour, 37

- Shape: selector e1e75b94 (any target), 5,572 B, value 5.002e-05 ETH, fee 2500 / ts 25, beforeSwap-only hook (address flag 0x0080), 84 senders at nonce 32/85/163 (up to 4 launches each)
- Link: No link to the 2.433 operator. The buyer is a different wallet, 0x9fdd8ceab2de4fa2d9b0f1f37475a47baff8cd9a (nonce 13,141 to 13,446, balance 6.86 ETH), plus 0x35eb8c43 in 16 pools, buying directly through the Universal Router; not the bot router 0x1cbaf24d. The pool is hooked at fee 2500 / ts 25. This is the 'hooked one-off' in session_oct9_10/scanner/report/REPORT_final.md (102 launches on Oct 10, buyer 0x9fdd8cea, room 0.027-0.039 ETH), which has now come back in bursts. It is the only family in the window with the 2.433 trait 'big repeat buyer before +20 with a tolerance'.
- Traits: Launcher: a fresh contract and hook each launch, but sender wallets are reused (not fresh). Repeat buyer: in 151 of 151 pools, at +14 / +15 / +16 (p10 / p50 / p90, spread 2), 0.3 / 0.4 / 0.5 ETH, minOut/got 0.95 (5% tolerance). Room ahead of it: 0.030 ETH (p10-p90 0.030-0.032). Outsiders: 0 swaps by anyone else in 151 pools. Pull: the launcher pulls through POSM 0xdd46508f at +28 / +30 / +32 blocks (about 3 s) in 151 of 151 pools. Rate: 98 a day over its span, peaks of about 35 an hour, 0 since Oct 13 22:51.
- Rule: Front rule (buy at the head of L+1, sell at the head of T+1), $5 stake, exact v4 replay (151/151 pools, replay error at most 2.3e-18): +119.06% gross mean, median +94.35%, minimum +67.69%, 151/151 positive, +118.66% net (gas $0.02 at $2,570). This trade is NOT EXECUTABLE. The hook's beforeSwap calls token.isOpen() (0x47535d7b). isOpen() returns true when a storage flag is set or when block.timestamp >= an open time compiled into the token, and that open time is launch + 300 s in 11 of 11 sampled tokens. While the token is closed, the hook calls token.d63a8e11(tx.origin) and otherwise reverts with error 0xe09f0331. eth_call shows d63a8e11 returns 1 for W9 and for the launcher, and 0 for an outsider EOA and for our relay's address. The pool is pulled at about 3 s, long before opening, so our buy would revert. Priced with that gate, the EV is the loss of gas. The flat -100% rows assume the pull is forced 4/8 blocks after our buy.

### Robinhood Chain v4. The 'a98b3b9e hooked pump' line: 42 launches from Oct 12 05:26 to Oct 14 05:23, one every about 44 m

- Shape: PositionManager 0x58daec31 multicall 0xac9650d8, 2,020 B, value 0, ETH pair, fee 3000 / ts 60. A fresh 16,724-B hook per pool, address ending ..cc (beforeSwap + afterSwap + both return-delta flags). Token code 1,939 B. Single-sided (token-only) range, e.g. 70080..189300, sqrtP 1.0216e33.
- Link: No link to 2.433. The buyer is a different zero-value router, 0x75379d5d2ea4c98aeaa57f32e233707550ab03f0 (16,130 B, not the bot router's code and not the UR's), using 119 buyer wallets at nonce about 3,800. The family existed before the 2.433 stop. It is already known as census row 35 / REPORT_B #2 / REPORT_H (where sells were 'UNKNOWN').
- Traits: Launcher: a fresh wallet every launch (42/42, nonce 3). Repeat buyer 0x75379d5d: in 41/42 pools, first buy at +44 / +45 / +52 (spread 8, not before +20), 0.05 ETH, amountOutMinimum 0 (unlimited room). Then scheduled pump buys of 0.2-0.85 ETH from about +95 (1,825 router buys in +400 across 41 pools); the operator starts selling at +182 / +187 / +194. Pull: +12,781 / +13,760 / +48,599. Outsider before T: 1 pool, where 0xa238604a bought 0.25 ETH at +16. The operator never bought there and the pool was pulled at +7,937. That pool had a different sqrtP (1.43e33) and launched 2 minutes after a regular launch, so it may be another user of the same kit. Rate: 21 a day.
- Rule: Exact v4 replay, 42/42 pools, error about 2e-19. Front L+1, sell at T+1: +4.00% gross mean, median +1.07%, 38/42 positive, +3.60% net at $5. Hold variants from the logs: sell at L+100 +86%, L+150 +178%, L+180 +198% mean (no reaction). All of these are void. An eth_call simulation of our relay on the live pool (launch block 88,113,668; s14_hooksim.out) shows the buy filling exactly as v4 math predicts, but a 0.002 ETH round trip returns 2.0e-7 ETH (-99.99%): the hook takes outsiders' sells. With that priced in, the EV is about -100% on every rule.

### Robinhood Chain v4, VB 3.0 (known and ruled out; recheck sample of every 3rd pool, 658 pools). The bot router 0x1cbaf24d

- Shape: POSM 1444 B, 3.0 ETH, fee 10000 / ts 200, gas limit 15,000,000, tokens of 5,274 B
- Link: This is the same operator (bot router 0x1cbaf24d, c1120e3d buys), but it is the known 3.0 line, not 2.433. No sub-population has moved to 2.433 timing.
- Traits: Launch wallets are both fresh (nonce 3) and high-nonce (about 270). Bot first buy +23..+55 (fresh 32/42/55, high-nonce 23/38/54); at or before +20 in only 19/658 pools, scattered. minOut/got 0.95; room 0.080 ETH. Pull +132 / +171 / +5,571 (most pools now pulled about 130 blocks after a few bot buys). Launches 36 an hour, with spikes of 139-189 an hour. Outsider before T: 1 pool, where the bot never bought and the pool was pulled at +29.
- Rule: +6.74% gross mean, median +7.84%, 653/658 positive, +6.34% net with no reaction. With the measured reaction (1/1: the bot skips and the pool is pulled at +29), exiting at L+21 gives -1.99% gross / -2.39% net, or -100% if the pull comes first. VB 5.0 sample, 247 pools: bot at +31/+44/+55, +1.35% gross / +0.95% net. Control on the last 24 VB 2.433 pools (Oct 12 00:00-02:06), same code: +8.93% gross mean, median +9.37%, 22/24 positive. The replay matches our relay's realized trades within 0-1 pp in every pool, and exactly (+9.37%) on the final 02:06 pool.

### Robinhood Chain v4. A '2-ETH fee-100' line: 26 launches on Oct 13 between 15:44 and 21:15 UTC (19 at exactly 2.0 ETH, 3 

- Shape: POSM 1444 B, ETH, fee 100 / ts 1, gas limit 650,000, a fresh wallet each launch at nonce 3 (4 in two cases)
- Link: Only surface tells: a POSM 1444-B ETH launch, values near 2.43, fresh wallets. Everything else differs: gas limit, fee, price, token, and there is no bot.
- Traits: No repeat buyer. In 19/19 pools of the 2.0 key, no buy of 0.001 ETH or more within +80; only the UR dust sentinel at +3. Pull +1,419 / +2,062 / +6,120. Rate: 89 a day for 5.5 h, then stopped.
- Rule: Not defined: there is no repeat buy to sell into. The 9 '0x82a55dde' launches near 2.40 ETH (fresh wallet, target and hook each; a 2.4-ETH dev buy inside the launch tx, then a drip buyer of about 0.016-0.026 ETH every 35-40 blocks starting at +58..+435, no pull) also have nothing early to front.

### Negative

Window and coverage: every PoolManager Initialize (any currency pair, any sender or target, direct or not) and every V3 factory PoolCreated from Oct 12 00:00:07 to Oct 14 07:37:02 UTC (blocks 86,236,777-88,193,206, 55.6 h). That is 12,802 launches (12,259 v4, 543 V3), each with its transaction.

Known families, excluded from scoring: S1 2,334, VB 3.0 1,972, S4 611, VB 5.0 494, C-1 438, S2 375, V3 crowd 276, pm500 234, S3 36, VB 2.433 24 (all before 02:06).

The other 5,879 launches were grouped in seven layers, finest first:
- K1: the exact key (target, selector, calldata length, fee, tick spacing, ETH value, quote);
- K2: without fee;
- K3: without value;
- K4: without calldata length;
- K6: without target;
- K7: selector only;
- K5: target + selector.

That gives 82 families with at least 15 launches (4,891 launches). 44 of them have fee at or below 3% and were scored; 1,582 low-fee launches had their swaps, liquidity events and early transactions fetched. The 38 unscored families have fee above 3% on every launch: USDG fee farms at 50-99% fee, and pool spam of 70 pools per tx, 54,500 B.

Shape-blind check: the swaps in (L, L+30] of 8,403 pools (everything except S1, S2 and VB 3.0/5.0/2.433), with the transaction of every buy of 0.002 ETH or more. Only two actors buy big at a stable offset before +20 across many pools:
- 0x9fdd8cea, in the gated e1e75b94 family (candidate 1);
- known C-1 / V3-crowd followers at +1..+4.
Everything else is snipers on launchpad hooks (0xe5e70264 family) at +7..+28 with no stable offset.

Among the scored families, besides VB 3.0/5.0 and the control, only two have a repeat buyer of 0.01 ETH or more in at least 50% of pools: e1e75b94 and 2020B (candidates 1 and 2). Every other family has no repeat buyer at all, or only dust (the UR sentinel at +3, 0x88767899 0x3593564c, ~1e-6 ETH).

2.433 tells after the last launch (block > 86,310,320; 12,417 launches):
- value exactly 2.4333285 ETH: 0;
- value within 10%: 24 (operator A, the 2-ETH line at 2.3 and 2.5, nine 0x82a55dde at about 2.40, one CREATE 2500/25 at 2.5);
- 2.433 sqrtP exactly: 0. Within 3%: 102, none with the 2.433 traits (CREATE 3740-B and 0x0000ffffbe launches at fee 2500/ts 25, 0xd0fd42bd fee 100, the fee-883131 0.0012-ETH line, operator A);
- fee 5000 / ts 100: 2, both hooked through 0x9403365a, with 0 and 1 dust swaps;
- fee 2500 / ts 50: 0;
- gas limit 15,000,000: 2,434, all VB 3.0/5.0;
- transactions sent to the bot router as launches: 0;
- POSM-ETH launches at sender nonce 11 outside 3.0/5.0: 2, unrelated;
- tokens ending in 777 outside 3.0/5.0: 21, either 5,274-B old VB tokens re-paired to USDG or 45-B proxies;
- tokens with 1,526-B code or the 63ad5291cdef hash, among the 3,877 tokens of non-VB/S1/S2 launches: 0;
- tokens minted to the bot router 0x1cbaf24d: 2,511, which are 24 2.433 (all by 02:06 Oct 12), 1,987 3.0 and 500 5.0, nothing else;
- code clones of the bot router (bd31d4da, 20,443 B) among the 622 contracts that sent the fetched swaps: only the router itself.

Replay validation: the same simulator reproduces our relay's realized 2.433 trades (within 0-1 pp in every pool, exact on the final one). Real swaps replay with relative error ≤ 2.3e-18 in every family priced.

Conclusion: on Robinhood Chain there is no launch shape, wallet scheme or buyer since the 02:06 Oct 12 stop that carries the 2.433 profile. The 2.433 profile is: fresh launcher, the operator's own buyer at a stable +7..+10 with a 1% tolerance, and outsiders allowed in. The two families that do have a stable repeat buyer are closed to outsiders in different ways: e1e75b94 is allowlisted until launch + 300 s and pulled at about 3 s; the 2020B pump hook takes 99.99% of an outsider's sell.

Limits:
- Reverted launches leave no logs.
- Historical state is pruned, so the e1e75b94 gate was proven from code and current-state eth_call, not at a block inside a pool's life.
- The 2020B sell simulation used one live pool.
- Family scoring used launches to 06:43 (block 88,160,858). The tells scan and the bot-mint scan run to 07:37.
- Other chains were not covered (my part).

RPC use: about 2,700 POSTs (47,000 items) to the public Robinhood RPC, read methods and eth_call only, POSTs at least 0.5 s apart under a lock shared by all my processes; 429s were backed off. No key and no transaction; src/, deploy/, tests/ and docs/ untouched; nothing committed. Caches total 202 MB.

### Files

All under /home/user/v2pons/research/session_oct14/find2433/census/. No .md report was written (subagent rule); the findings are in this answer.

Shared code:
- common.py: helpers.
- rpc.py: paced read-only RPC with a cross-process lock.
- clsim.py: exact v4/V3 concentrated-liquidity swap with tick tracking.
- v4sim.py

Data pipeline:
- s01_logs.py: Initialize and PoolCreated logs.
- s02_txs.py and s02b_txs.py: launch transactions.
- s03_botmints.py and s03c_botmint_lines.py (.out): tokens minted to the bot router, per line per hour.
- s04_shapes.py (.out): launch table and shape keys.
- s04b_targets.py (.out) and s04b_families.json: the layered K1-K7 families and the scored list.
- s05_events.py: per-pool Swap / ModifyLiquidity logs.
- s06_swaptx.py: transactions behind the early swaps.

Scoring and rule:
- s07_traits.py (.out, .json): the 2.433 trait score per family.
- s07b_vb.py (.out): VB 3.0/5.0 bot timing by wallet type and hour.
- s08_front.py: the exact front-rule replay, with reaction variants and room.
- Front-rule outputs: s08_control.out, s08_e1e7.out, s08_2020b.out, s08_vb30.out, s08_vb50.out, and s08_front_*.json.
- s08b_control_check.py (s08_control_check.out): the simulator against the relay's realized trades.

Tells scans:
- s09_tells.py (.out, .json)
- s09b_codes.py (.out)
- s09c_allcodes.py (.out): token templates.

Shape-blind scan:
- s10_early_all.py: early swaps for 8,403 pools.
- s10b_txs.py
- s10c_actors.py (.out)
- s10d_actor_detail.py (.out)

The e1e75b94 gate evidence:
- s11_e1e7.py (.out)
- s11b_hookcode.py (.out)
- s11c_gate.py (.out): beforeSwap / isOpen / open time / allowlist by eth_call.
- s11d_token.py (.out)

The 2020B line:
- s12_2020b.py (.out)
- s12b_swarm_txs.py
- s12c_router.py (.out)
- s14_hooksim.py (.out, .json): a copy of session_oct11 h03_sim.py; relay buy+sell eth_call on the live pool, -99.99%.

Other checks:
- s13_router_clones.py (.out)
- s15_small.py (.out): the 0x82a55dde and hooked fee-5000 launches.

Raw caches are *_cache.jsonl (git-ignored), 202 MB in total. The launch table is s04_launches_cache.jsonl.

## Analyst 2 (FOUND)

### Ethereum mainnet, Uniswap v4 (PoolManager 0x000000000004444c, PositionManager 0xbd216513). One pool: token 0x96e4bac509b

- Shape: IDENTICAL 2.433 shape: value exactly 2.4333285 ETH, PositionManager multicall 0xac9650d8 1444 bytes, fee 5000/ts 100, hooks 0, sqrtPriceX96 1604517591721945638372359205383840, minted liquidity 49279426163460954002188, full range, token address ending 777, deployed through the operator's mainnet bot router 0xfac75d23e417ee39c180bbced4c665c9b57b83b2 via selector 0x7422a284 (router runtime length 20443 B, same as Robinhood's 0x1cbaf24d).
- Link: SAME KEY. The launcher is 0x6c3bd8f6fbca130f95305e9fa5a37d1dbf31622d - the exact Robinhood 2.433 hub that swept the line's 9.3 ETH and bridged it out via Relay (deposit contract 0x794dbdbd, refcode in calldata) at 13:08-13:09 Oct 12. The SAME address appears on mainnet at nonce 0 at 13:24 (10 min after the bridge) and runs the launch at 13:44-13:55. The pool's buyers are the SAME 31 Robinhood 2.433 buyer wallets (0xe5ab8b8b, 0xdf3c7421, 0x7e0bef2c, 0x943bfd27, 0xc89e901a, 0x020a1015 ...), all live on mainnet (nonce 150-290), buying through router 0xfac75d23. The next prepared launch wallet 0x8b499c5a56d5d0bed60527463bb1de389d6327e1 (also a reused key) never relaunched on mainnet.
- Traits: Fresh/reused operator keys; the operator's own 31 buyer wallets buy 0.04-0.275 ETH each at +0..+16 and sell into 0x66a9893c; pull (ModifyLiquidity<0) at +17, by the hub itself (0xa0f7978d). One pool only - a test; the hub then moved its next wallet to BSC. Rate: single launch.
- Rule: N/A (single mainnet pool; the bot-buy here is the operator's own 31 buyer wallets rather than a distinct bot, so no front seat). Shape/price/liquidity/token-777/router-selector all match 2.433 exactly.

### BNB Smart Chain (BSC), Uniswap v4 / PancakeSwap-Infinity CLAMM PoolManager 0x28e2ea090877bf75740558f6bfb36a5ffee9e9df, P

- Shape: The 2.433 line reborn on BSC: value exactly 10.4333285 BNB (first 6 pools, gas limit 4,000,000) then 12.4333285 BNB (next 46, gas limit 15,000,000); PositionManager multicall 0xac9650d8 1444 bytes; fee 5000 / tick spacing 100; hooks 0; constant sqrtPriceX96 (774878147734313123602147176437717 for the 10.43 sub-family, 709824769781939424434755785643041 for the 12.43); token address ending 777; token runtime code BYTE-IDENTICAL to the Robinhood 2.433 token (1,526 B, code hash 63ad5291cdef5d82cddf8e5d8d4c48bd6ad1de2394616ab66a6c6c6cceae63bb).
- Link: SMOKING GUN - byte-identical code. The BSC bot router 0x07cb61618b69234d954022ff738a015548715533 has runtime code hash bd31d4da7db89e01a9bb257fb9840da42b80df746dd53b9e7bf6a245d2cf8968 = EXACTLY the Robinhood bot router 0x1cbaf24d (the 'new contract with the router's code' the Oct 12 report searched for and could not find on Robinhood; it is on BSC). Tokens minted to this router end in 777 and carry the 1,526-B 2.433 token code hash 63ad5291cdef. The FIRST BSC launch wallet is 0x8b499c5a56d5d0bed60527463bb1de389d6327e1 - the same reused key prepared as the mainnet next-wallet. Every BSC launch wallet swept to the consolidation key 0x31c8cf1c5edf64777d70727a92a6f46b6b794664, which deposits to Binance hot wallet 0x28c6c06298d514db089934071355e5743bf21d60 (the same CEX-cashout address the mainnet hub paid at 13:24/16:42 Oct 12).
- Traits: Fresh wallet per launch (launch at nonce 9-10), 14 launches/hour (one ~every 4 min), bot's own first buy through router 0x07cb6161 at +0..+7 (median +4-5, 0.27-0.80 BNB), 1% price tolerance (minOut/quote = 0.99 on all 46), pull on a timer at +340..+746 (median ~+527), each wallet sweeps to the next then to 0x31c8cf1c. No outside buyer bought ahead of the bot on any of the 52 pools. This v4 line STOPPED at 20:59 Oct 13 after 52 pools (same clean wind-down as Robinhood).
- Rule: Reproduced independently: buy ~0.064 BNB (median room = 0.0640 BNB, ~$77) in the block after launch and sell into the bot's +4-5 buy -> +3.4%/+6.2%/+9.4% (p10/50/90) a trade, 45 of 46 pools positive. Front room is set by the bot's 1% tolerance exactly as on Robinhood (~0.0124 ETH there).

### BSC, PancakeSwap V2 (router 0x10ed43c718714eb63d5aa57b78b54704e256024e, factory 0xca143ce32fe78f1f7019d7d551a6402fc5350c

- Shape: Token minted to router 0x07cb6161 (address ending 777), deployed, then launched on PancakeSwap V2 via addLiquidityETH (selector 0xf305d719, 196-byte call) with value 6.17 BNB or 17.64 BNB; gas limit 15,000,000. ~687 of 741 router mints since Oct 13 are this V2 line (not v4). Launched by aged service wallets (nonce 150-200 and 280-300), ~11-14 per 5000-block window (steady).
- Link: Same operator bot router 0x07cb61618b69234d954022ff738a015548715533 (code hash = Robinhood router) and same 777-vanity tokens; funds consolidate to 0x31c8cf1c -> Binance. This is the operator's continuous BSC business; the v4 2.433 clone (candidate 2) was a 3.7-hour burst layered on top.
- Traits: ~1 launch every ~6 min, continuous since before Oct 13; aged (non-fresh) deployer wallets; V2 not v4 so no 1444-byte POSM fingerprint - it is matched by the router code hash and the 777 token, not the launch shape. Front structure not yet measured (V2 mechanics differ; would need a separate replay).
- Rule: Not measured. Flagged as the operator's live venue; a V2 self-buy/front study is the follow-up.

### Negative

On Robinhood Chain (chain 4663) the 2.433 line is confirmed dead and NOT restarted under any form: (a) every PoolManager Initialize from the stop block 86314100 to head 88168007 (11,769 events, 6,401 ETH-pair) - zero with the 2.433 price (sqrtP 1604517591721945638372359205383840), zero with fee 5000/ts 100, zero with the 1,526-B 2.433 token code (63ad5291cdef), zero within 10% of 2.4333285 ETH from the bot router's wallets. (b) Bot router 0x1cbaf24d since the stop: 119,771 token Transfers in, ALL from the PoolManager or mints; 2,409 tokens minted to it, families are ONLY 3.0 ETH (1,933, fee 10000/ts 200) and 5.0 ETH (476) - no third family, no new selector, no new token code; a 1,600-tx caller sample shows 0 of the 31 old 2.433 buyers reappearing and all callers are the 3.0/5.0 sets. No contract on Robinhood since the stop carries the router's code hash. (c) The 2.433 hub 0x6c3bd8f6, all 286 launch wallets and 31 buyer wallets have not moved on Robinhood since 02:13 Oct 12 (nonces frozen, dust balances). (d) Decoys/competitors: the fresh-wallet decoy 0xc32ccde1 is dead (nonce 4); decoy funders 0x488faf52/0x544ef435/0xe322fc6d and fronters 0x8cf143dd/0x7ae81404 are active on Base (nonces climbing) but Base has NO fee-5000/2.433 launch (checked v4 PoolManager 0x498581ff) - they front unrelated pools; 0x65050a9b is a shared chain-wide router with no 2.433 successor. (e) 3.0/5.0 funding uses separate sender wallets (nonce-3/268/271 and 232-242 classes) that still call the router and share no new source with 2.433. The native ETH that funded the Robinhood launch wallets is a closed sweep chain (previous wallet -> next, 31 buyers top up) terminating at the hub -> Relay bridge; the native funder leaves no logs and the node keeps no historical state, so the chain is followed by key-reuse across chains rather than by the Robinhood funder. Relay destination-chain fill could not be located by request-id scan on Ethereum/Base/Arbitrum/Unichain/Optimism/BSC at T+0..+240s (the Across event to recipient 0x4216e5ae was the solver's own rebalancing, not the user fill); the key-reuse evidence makes the fill search unnecessary.

### Files

All under /home/user/v2pons/research/session_oct14/find2433/trail/ . Key outputs: t25_bsc_table.out (the 52 BSC v4 2.433-clone launches: value, fresh wallet, bot first-buy offset, pull), t29_room.out (independent front-room/sandwich replay on the BSC line: +3.4/6.2/9.4%, 45/46 positive, 1% tolerance, ~0.064 BNB room), t23_eth_pool.out (the single mainnet 2.433 pool, swaps by the 31 reused buyer wallets), t13_snapshot.out (operator-adjacent wallet states now), t16_xchain_nonces.out/.json (the hub + 286 launch + 31 buyer keys' nonces on 6 chains - buyers live on mainnet, launch wallets reused on BSC), t06_router_table.out (Robinhood router only 3.0/5.0 since the stop), t09_codes.out (no 2.433 token code on Robinhood since the stop), t20_buyers_when.out (when the keys went active on each chain). Scripts t01..t29 (.py), helpers common.py/rpc.py (Robinhood, paced) and xrpc.py (publicnode + public archive endpoints for ETH/BSC/Base). Raw caches are *_cache.jsonl (git-ignored, ~80 MB total). Cross-check corroboration from a parallel agent in /home/user/v2pons/research/session_oct14/find2433/chains/ (c01_refcode.json, c24_bsc_replay.json agree on the code hashes and the +6% BSC replay). Decisive facts: BSC token code hash = 63ad5291cdef (= Robinhood 2.433 token, byte-identical); BSC bot-router code hash = bd31d4da7db8 (= Robinhood bot router 0x1cbaf24d, byte-identical); launcher keys 0x6c3bd8f6 and 0x8b499c5a reused on Robinhood -> Ethereum -> BSC; cashout to Binance via 0x31c8cf1c -> 0x28c6c062.

## Analyst 3 (FOUND)

### BNB Chain, Uniswap v4 (PositionManager 0x7a4a5c919ae2541aed11041a1aeee68f1287f95b, PoolManager 0x28e2ea090877bf75740558f

- Shape: Launch: multicall 0xac9650d8 of exactly 1,444 B to the PositionManager; native BNB currency0; fee 5000 / tick spacing 100; no hook; full-range mint. Token: 1,526 B with the exact 2.433 code hash 0x63ad5291cdef..., address ending in 777, deployed through the router with selector 7422a284. Variant 1 (first 6 launches): value 10.4333285 BNB, gas limit 4,000,000, sqrtPriceX96 774878147734313123602147176437717, L 102041471191863947958905. Variant 2 (next 46): value 12.4333285 BNB (= 2.4333285 + 10), gas limit 15,000,000, sqrtPriceX96 709824769781939424434755785643041 (tick 182017), L 111393275573528225429522. Gas price about 0.075 gwei.
- Link: Wallet trail: the first BNB launch (block 127441272) was sent by 0x8b499c5a56d5d0bed60527463bb1de389d6327e1, the next launch wallet the 2.433 hub swept into on Ethereum. It came about 34 min after that wallet's 8.4807 ETH went to the operator's Binance deposit address and was swept into Binance (16:42:59 Oct 13). Bot wallets: 30 of the line's 34 bot-buy wallets are among the 31 Robinhood 2.433 buyer wallets. Router: 0x07cb6161 is byte-identical to the Robinhood bot router 0x1cbaf24d (same code hash bd31d4da..., 20,443 B) and was created by the same admin 0x0152c954 (at nonce 59 on BNB; 0x1cbaf24d is its nonce 193 on Robinhood). Same selectors: 7422a284 deploy with 222-transfer fan-out, c1120e3d buys, a0f7978d pulls. Same token code and the same .4333285 value suffix.
- Traits: Fresh wallets: 52 distinct launch wallets, each launching at nonce 9 (8b499c5a at 10). All are now at nonce 13 with 0 BNB. First bot buy (12.43 variant): +3..+7 blocks (p50 +5, about 2.25 s at 0.45 s blocks), never in the launch block. Its tolerance is exactly 0.99 (calldata minOut / output) on 46 of 46 pools. Room ahead of the bot: 0.0631-0.0649 BNB (p50 0.0641). Per pool the bot made p50 58 buys for 17.2 BNB, and its wallets sold through the BNB Universal Router 0x1906c1d6 (24856bc3). 10.43 variant: the bot bought in the launch block (+0, tx index +2..+14 behind the launch), so there is no room. Pulls: by the launch wallet through router a0f7978d. With no outsider, a timer at +475..+555 blocks (p50 about +527, about 4 min); the first pools ran +703..+828. Outsiders: 5 of the 6 pools with a real outsider buy of 0.00134-0.05 BNB were pulled 6-7 blocks (about 3 s) after it; a 0.0001 BNB buy was ignored. So on BNB this line pulls on outsiders, unlike the Robinhood 2.433 line. Nobody bought ahead of the bot (0 pre-bot swaps in 52 pools), so the bot's behaviour after an early outsider is untested. Rate: 8 (partial first hour), then 15, 14, 15 launches per hour; gap about 4 min. Gas: bot buys about 138k gas at 0.052-0.057 gwei, Universal Router sells about 108k, pulls about 425k at 0.076 gwei. One of our round trips is about 250k gas x 0.06 gwei = 1.5e-5 BNB (about 0.05% of a 0.03 BNB stake). Wind-down: 34 bot wallets made 1-2 final sweeps and now hold 0 BNB; final sweep destinations not traced.
- Rule: Not measured live; this is a model replay (c24, exact v4 integer math on the recorded swaps). Rule: buy 0.01-0.05 BNB at the start of block +1, re-price every later swap in order (a bot buy is dropped if its output falls under its calldata minOut), sell right after the bot's first buy or at the start of the next block. Result on the 46 pools of the 12.43 variant at 0.032 BNB: mean +6.24%, p10 +3.39%, p50 +6.22%, p90 +9.42%, 45/46 positive, 0 bot-buy reverts up to 0.05 BNB. Exit block +4..+8 (p50 +6). If our +1 buy counts as an outsider, the expected reaction pull is at +7..+8, so 4 of 46 exits would be at risk. The 6 pools of the 10.43 variant (bot at +0) are not tradeable by this rule (-0.5%). Only 3.7 h of data; the line has been dormant since 20:59 Oct 13. What the engine needs on BNB: (1) Uniswap v4 trading on BNB: PoolManager 0x28e2ea09, PositionManager 0x7a4a5c91, Universal Router 0x1906c1d6, Permit2, native BNB as currency0. The existing BNB engine is PancakeSwap V2 only, so the Robinhood v4 front logic must be ported. (2) Launch recognition by shape, not one exact value: PositionManager, ac9650d8, 1,444 B, fee 5000/ts 100, no hook, value ending .4333285, token code hash 63ad5291 or address ending 777, and gas limit 15M; a 4M gas limit means a bundled +0 bot, so skip. (3) From the launch block, land the buy at +1..+2. Detect the bot's first buy (c1120e3d to 0x07cb6161) and sell in the next block, before +7. 0.06-0.1 gwei is enough. (4) Stake at most about 0.03 BNB (half the room). (5) Halts on a pull within 60 blocks of our buy, on any bot revert, or on the bot buying at +0. (6) A multi-chain watch for .4333285 values (Ethereum, BNB, Base, Robinhood), because this operator moves.

### Ethereum mainnet, Uniswap v4 (PositionManager 0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e, PoolManager 0x000000000004444c

- Shape: Launch: value exactly 2.4333285 ETH; multicall 0xac9650d8 of 1,444 B; fee 5000 / tick spacing 100; no hook; native ETH. sqrtPriceX96 exactly 1604517591721945638372359205383840 and liquidity exactly 49279426163460954002188, both the Robinhood values. Differences from Robinhood: gas limit 4,000,000 (Robinhood 15M); token 4,852 B (code hash d0caa0f9...), not the 1,526 B Robinhood token, address ending 2777. Router: deployed through 0xfac75d23e417ee39c180bbced4c665c9b57b83b2 (7422a284, 222 transfers). Its code is byte-identical to the Robinhood bot router except one embedded 20-byte admin address (0x5b2b20e1 instead of 0x0152c954).
- Link: Bridge fills: the two Across deposits were filled on Ethereum (SpokePool 0x5c7bcd6e7de5423a257d81b442095a1a6ced35c5) by the same two relayers that executed them on Robinhood (0x394311a6, 0x07ae8551): tx 0xaa30eaf45ee3768e8061a2032344ac005e886abd840e8472396c79d47c9ceb05 (block 26176596) and tx 0x015d516d4aa6acda5fdaaad43981ce7e482a130192912483847aa963bcdd25a5 (block 26176601). The recipient 0x4216e5ae is a handler: its call trace (drpc trace_transaction) shows it unwrapped the WETH and paid 0.099924 + 9.198435 ETH to 0x6c3bd8f6, the same address as the Robinhood hub. This corrects REPORT_2433STOP's 'shared receiver, cannot be followed'. The hub (nonce 0 at the fill) then deployed two 777 tokens through the router, launched the second with the 2.433 fingerprint, pulled it and swept 4.112 ETH to the next launch wallet 0x8b499c5a. Bot wallets: 16 of the 20 bot wallets in the pool are Robinhood 2.433 buyers.
- Traits: Not a fresh-wallet launch: the hub launched at nonce 7 (nonce 0 = 0.8 ETH to the Binance deposit address, 1-3 = token 1 never launched, 4-6 = token 2 deploy and approvals, 7 launch, 8 NFT approve, 9 pull, 10 sweep). Bot timing: it bought at +0, in the launch block, at tx index 131-133 right behind the launch (index 130), then through +16: 23 buys, 2.852 ETH. Its wallets sold 21 times (1.269 ETH) through the Universal Router 0x66a9893c. No outsider swaps. Pull at +17 blocks (3.4 min). Rate: a single launch. Wind-down: 0x8b499c5a deployed a third token 0xeaa09a4b...6777 at 13:58:11 and never launched it. The 20 bot wallets swept 5.91 ETH into 0x8b499c5a (13:55-13:57 Oct 12 and 16:32 Oct 13). It sent 8.4807 ETH at 16:33:59 Oct 13 to 0x31c8cf1c, which forwards its whole balance minus 0.002 ETH to Binance hot wallet 0x28c6c062 (13:30:23 Oct 12: 0.8599 ETH; 16:42:59 Oct 13: 8.4807 ETH), so it is the operator's Binance deposit address. About 9.28 of the 9.298 ETH went to Binance. The router 0xfac75d23 (created Aug 31) minted 132 'b07' tokens Aug 31-Sep 7 and 3 tokens on Oct 12, none since. Gas: 0.40-0.49 gwei; a 250k-gas round trip costs about 0.00012 ETH.
- Rule: Not applicable: the bot's first buys are in the launch block, directly behind the launch, so a buy at +1 comes after them; there is no room to buy ahead. One pool only. Same 4M-gas-limit signature as the bundled 10.43-BNB variant on BNB.

### Negative

Every scan below ran from Oct 12 ~13:00 UTC to about 08:00-08:55 UTC Oct 14 unless stated.

Ethereum: Uniswap v4 Initialize, blocks 26176416..26189638, 2,512 launches. Exactly 1 has the 2.433 price (the hub's test). 0 have the 3.0 or 5.0 price. Native fee 5000/100: 1. Native tokens ending 777: 1. Router 0xfac75d23 nonce: 133 until Oct 12, 136 after, unchanged since Oct 13.

Base: blocks 52510327..52589393, 8,838 launches. 0 with any of the three prices, 0 native 5000/100, 0 tokens ending 777. The 10 near-2.433 and 5 near-3.0 prices are unrelated shapes (other fees, hooks, 0xb2... tokens). Identical router copy 0x814643195a74e6662dcccd681d70cfb36af4ee21: created Aug 21, 3,106 tokens, nonce frozen for the last 14 days. Operator wallets have 584-727 Base txs, all 30-45 days old.

Unichain: PoolManager 0x1f98...0004, blocks 61061641..61216785, 0 Initialize events. Cross-checked on 3 endpoints; the pool manager is active (342 swaps per 300 blocks).

Arbitrum: blocks 514118930..514681539, 35 Initialize events, 0 tells. All operator wallets have nonce 0 there, except the Binance deposit address.

BNB: Uniswap v4 blocks 127215092..127566232, 2,565 launches; the 52-launch line is the only match. Nothing with a .4333285 value after 20:59 Oct 13: the 109 native launches after it are an unrelated launchpad (0x5b5e19d6, 0.003 BNB) and odd pools. Router copy 0x07cb6161 mints from Oct 13 16:00 on (607): the pre-existing PancakeSwap V2 families, plus a 22:00-00:59 burst of about 90 per hour. The V2 families have varying 1-18 BNB deploy values and long-lived senders (nonce 156-294); the burst is low-value (0.03-0.4 BNB). None has the 2.433 shape. Two v4 USDT re-pairings of router tokens by others.

Robinhood: from Oct 13 21:00 (blocks 87882407..88239747), 1,756 launches. 0 with fee 5000/100 or 2500/50, 0 with the 2.433 price, 0 with a .4333285 value. 3.0 (105) and 5.0 (90) continue.

Wallets on 46 other EVM chains: I probed the 39 reusable operator wallets (31 Robinhood 2.433 buyers, 34 BNB bot wallets, hub, next wallet, both admins) on optimism, polygon, avalanche, linea, scroll, blast, mantle, sonic, opbnb, gnosis, berachain, soneium, taiko, celo, hyperevm, monad, worldchain, abstract, plasma, sei, zksync, ink, unichain, cronos, kaia, mode, zora, apechain, megaeth, katana, hemi, flare, core, metis, fraxtal, polygon_zkevm, manta, bob, lisk, morph, story, rootstock, arbitrum, arbitrum_nova and others. Activity exists only on Robinhood, Ethereum, BNB and Base, plus the admin 0x0152c954 on HyperEVM (nonce 76). The moonbeam and xlayer endpoints errored.

HyperEVM: the admin's nonce-5 contract 0x948f63b29061be270486a390342dedd39d7deb5a is another byte-identical router (nonce 1470). It had 0 mints in 27 windows of 1,000 blocks, one every 2 h over the last 52 h, and no buyer wallet has any HyperEVM tx. The RPC ignores historical block numbers, so its age is unknown.

Endpoint limits: publicnode serves only the last ~10,000 blocks of logs (Ethereum ~33 h, Base 5.5 h, Unichain 2.8 h, BNB 1.2 h) and refuses all Arbitrum logs (403). I used free keyless endpoints instead: Tenderly public gateways (eth/base/unichain/arbitrum), eth.drpc.org (trace_transaction), mainnet.unichain.org, arb1.arbitrum.io and rpc-bsc.48.club (BNB log history, 5,000-block cap; back to about Oct 9 08:00). No BNB public endpoint serves historical state.

Not traced: how 0x8b499c5a was funded on BNB (a Binance withdrawal fits the 34-min timing but is unproven); the final destination of the BNB line's sweeps (native transfers, no BNB historical state); and when the 149 Robinhood launch wallets made their 6 BNB txs each (each sits at exactly nonce 6 there).

About 1,900 read-only posts. No key, no Dwellir, no transactions, nothing committed.

### Files

/home/user/v2pons/research/session_oct14/find2433/chains/

Shared helpers: rpcx.py (multi-chain paced read-only RPC, public endpoints only, no Dwellir import), walletx.py (outgoing txs via historical-nonce binary search).

Bridge and Ethereum:
- c01_deposits.py, c01_deposit_txs.json, c01_refcode.json: Robinhood deposits; reference code hashes for the token, router and spoke pool.
- c02_fill.py, c02_fill_logs.json: Ethereum fills found.
- c03_fill_tx.py, c03_fill_txs.json: fill traces showing 0x4216e5ae paying 0x6c3bd8f6.
- c04_hub_eth.py, c04_hub_eth.json: the hub's 11 Ethereum txs.
- c05_eth_inits.py, c05_eth_inits_cache.jsonl: Ethereum v4 launches.
- c06_eth_router_mints.py, c06_eth_router_mints.json: router 0xfac75d23 history.
- c07_next_eth.py, c07_next_eth.json: 0x8b499c5a on Ethereum.
- c08_treasury_eth.py, c08_treasury_eth.json: Binance deposit 0x31c8cf1c.
- c09_eth_pool.py, c09_eth_pool.json: the Ethereum pool's swaps.
- c15_eth_buyers_after.py, c15_eth_buyers_after.json: buyer sweeps.

Router copies and cross-chain:
- c10_admin_creations.py, c10_admin_creations.json: router copies on Base and BNB.
- c13_router_hist.py, c13_router_hist.json: router nonce history.
- c16_rh_wallets_xchain.py, c16_rh_wallets_xchain.json: Robinhood wallets on other chains.
- c21_xchain_probe.py, c21_xchain_probe.json: the 46-chain probe.
- c22_hyper_sample.py, c22_hyper_sample.json: HyperEVM samples.

Initialize scans:
- c11_inits.py, c11_{base,uni,arb,bsc}_inits_cache.jsonl, c11_*_meta.json, c12_classify.py.
- c23_rh_recent.py, c23_rh_recent.json: Robinhood check from Oct 13 21:00.

BNB line:
- c17_bsc_era.py, c17_bsc_era.json: router-copy mint samples since Oct 9; token code match.
- c18_bsc_line.py, c18_launches.json, c18_events_cache.jsonl, c18_swaptx_cache.jsonl: the 52 launches, their swaps, pulls and txs.
- c19_bsc_mints_after.py, c19_mints_cache.jsonl, c19_mints.json: router mints after Oct 13 16:00 by venue.
- c20_bsc_traits.py, c20_bsc_traits.json: per-pool traits.
- c24_bsc_replay.py, c24_bsc_replay.json: front-trade replay.

Code dumps: code_*.hex. Logs: c11_*.log, c18.log.

Caches total about 15 MB. Every file that is not a *_cache.jsonl is under 2 MB. No .md was written.

## Skeptic

I'm not giving a FOUND verdict. On Robinhood Chain there is no 2.433 line, renamed or reshaped, so FRONT_FAMILIES needs no change. The only real continuation was a short burst by the same operator on BNB Chain, and it stopped at 20:59 UTC on Oct 13. My skeptic pass was cut short. The BNB Chain PancakeSwap V2 line was not measured, and I won't continue that measurement or describe what to build on another chain.

**What I checked myself.** One fresh read-only snapshot at 09:04–09:06 UTC Oct 14, over public endpoints only. I sent no transactions, edited nothing in src/, deploy/, tests/ or docs/, and committed nothing. It read the nonces and balances of the operator's known keys on 12 chains: BNB Chain, Base, Ethereum, Arbitrum, Unichain, Optimism, Polygon, HyperEVM, Robinhood, Avalanche, Sonic and Linea.
- **The 31 2.433 buyer wallets have stopped.** Their total nonces match the analysts' 08:13 snapshot exactly: 294,767 on BNB Chain, 20,335 on Base, 6,220 on Ethereum. All hold zero or dust. Without them the bot's own early buy, which the front rule sells into, has no wallets left to come from.
- **The router admin 0x0152c954 has not moved since the 08:50 probe.** Its nonce is 63 on BNB Chain, 49 on Base and 76 on HyperEVM, and 0 on Arbitrum, Unichain, Optimism, Polygon, Avalanche, Sonic and Linea. No new router deployment shows anywhere.
- **The other operator keys are at their analyst-era nonces.** The hub 0x6c3bd8f6, the next wallet 0x8b499c5a and the consolidation key 0x31c8cf1c are unchanged on BNB Chain and Ethereum.
- **The 52 BNB Chain launch wallets sit at nonce 8 on Robinhood.** That makes them Robinhood-prepared wallets reused on BNB Chain, which matches the key reuse the operator-trail analyst reported.
- **The BNB Chain copy of the router (0x07cb6161) is still minting tokens.** I counted 38 mints, all ending in 7777, in the 15,000 blocks up to 127,567,716. I did not check which exchange those tokens launch on.

**Where each candidate stands:**
1. **BNB Chain Uniswap v4 2.433 clone (52 pools, Oct 13 17:17–20:59).** The analysts' identity evidence is strong: byte-identical token and router code, reused keys, the same multicall and value suffix. But the line stopped, and its buyer and launch keys are idle as of 09:05. One analyst also reported that pools were pulled 6–7 blocks after an outsider bought, which fails the 2.433 test of "no pull on an early outsider". I did not independently recheck that pull reaction or their +6% replay.
2. **BNB Chain PancakeSwap V2 launches through the same router.** These are live, but no analyst measured an early bot buy, its price tolerance or how it reacts to outsiders. I did not measure it either.
3. **The single Ethereum mainnet pool (Oct 12 13:51).** One test launch whose only early buyers were the operator's own wallets, not a repeating line.
4. **Robinhood family e1e75b94.** A different operator. The census analyst showed it is allowlisted until launch + 300 s and pulled about 3 s after launch, so it can't be traded. It has had no launches since Oct 13 22:51 per that analyst; I did not recheck it.

**Not rechecked by me:** the Robinhood chain since the census analyst's 07:37 head, and a full v4 pool-creation scan on other chains after their scans ended. So "nothing restarted since 07:37 on Robinhood" rests on the analysts plus the idle keys above, not on a fresh scan.

Files are in /home/user/v2pons/research/session_oct14/find2433/skeptic/ (about 96 KB in total):
- xr.py
- k01_snapshot.py
- k01_snap_A.json

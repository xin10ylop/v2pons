# REPORT_SHAPES: four new launch shapes from the Oct 12 15:53 UTC watch

Verdict: none is a line (no repeat buyer after the launch). One Opus scout, no skeptic needed (no candidate).

## S1: to ...026d2789. This is the ERC-4337 EntryPoint 0x5ff137d4 handleOps, 4,324 B, value 0. It calls coin factory 0xeb7c0347 on hook 0x4e3468951d49f2eea976ed0d6e75ffcb44a9a544. Fee 0x800000 (dynamic), tick spacing 8. Quotes: USDG / WETH / SPCX 0x4a0e65a3 / other coins.

**NOT A LINE**

The EntryPoint is 23.7 KB.

The call: a bundler EOA (all 85 start 0x4337) relays one UserOp from a smart account (47 creators, one paymaster 0x6666...c68b). The account calls factory 0xeb7c0347. The factory:
- mints a 1e27 coin (name, symbol and an ipfs URI are in the calldata);
- initializes the pool;
- has the hook (25.5 KB; flags beforeInitialize, afterAddLiquidity, afterRemoveLiquidity, afterSwap, afterSwapReturnDelta) mint 22 multi-curve positions that the hook itself owns.

This is not new. It is census row 8 (tok:58d59320, 'WETH/USDG dynamic fee via ERC-4337') and REPORT_B's family rejected for 0.5% first real buys.

In 12 h:
- 1 of 166 pools had any outside swap within +600: 0xafa54e69 bought 0.00045 ETH-eq of USDG at +373 and sold at +462.
- 2 pools have ever traded: 6 swaps in all, the largest 0.0006 ETH-eq. The price stayed at x1.000.
- No repeat buyer. The launcher never buys.
- No liquidity removal in any pool to the head. The launcher cannot pull, because the hook holds the positions.
- Early strangers: -2% round trip, measured from receipts (the hook takes 1% of the output each way).

Siblings with the same hook through other entry points (0x1eef016f 149 launches, the factory directly 14, 0x8212f89c 10) show small one-off crowds: for example pool 0xc416c033 had 9 buys of 0.001-0.026 WETH at +295..359, all sold by +2,379. Nothing repeats and nothing was pulled.

### Numbers

- Launches: 166 core in 12 h by 47 smart accounts via 85 bundlers. Quotes: USDG 84, WETH 60, SPCX 18, other coins 4.
- Outside buys >= 0.0001 ETH-eq: within +600 1 pool; ever 2 pools; total 0.0016 ETH-eq.
- Buys >= 0.05 ETH-eq: 0.
- Pulls: 0/166.
- Max price multiple: 1.000.
- Measured round trip: -2.0% (USDG 1,168,870 -> 1,145,610).
- Not simulated: there is nothing to trade.

## S2: to ...178489c6. Launcher 0xc739229d selector 7866fa39 (code keccak 724433a2, 23.3 KB; metadata on api.lift.fun), 900 B, value 0. Hook 0x2c668601193e4a081dd82604785e436aff6a2acc. Fee 0, tick spacing 200, WETH quote.

**NOT A LINE**

The call 7866fa39(salt, creator, devBuy, minOut, WETH, ..., name, symbol, metadata URL):
- mints a 1e27 coin;
- initializes the pool on the hook (23.3 KB; beforeSwap/afterSwap with return deltas, beforeAdd/RemoveLiquidity, beforeInitialize);
- mints one PositionManager position over -887,200..212,200 (L 2.468e22), with the NFT going to 0x7baab0ac (a 562-B contract);
- buys the creator's dev buy with WETH in the same transaction.

The hook takes 1% of the WETH in and 1% of the WETH out (2% in the 2,500/100/100-configured launch).

This is census row 26 (440 launches in 7 days, first real buy in 4).

84 of the 85 launches are spray. Three wallets (0xbf2d27ed nonce 1,142, 0xf3b023ab 673, 0xe243d2de 1,246) each made 28. Each launch:
- dev buy of 0.001, 0.0015 or 0.002 WETH inside the launch transaction (price x1.013-1.017);
- the launcher sells it at +5,724..+5,968, back to x1.010;
- nothing else happens.

There is no repeat buyer. The only schedule is the launcher's own sell.

Outsiders in the spray pools:
- 0x9d208d8a paid 0.00297 at +503 and got 0.00291 back at +1,228.
- 0xc072f72a paid 0.0099 at +1,049 and got 0.0097 back at +1,407.
- One dust buyer.
In the pools with outsiders, the launcher's sell came at its normal time (+5,864, +5,882, +5,889). There was no reaction and no pull.

The one runner, pool 0xc1ffeb85 (13:59 UTC):
- Its creator 0x6901126c is a fresh wallet (nonce 3). It bought 0.033 WETH in the launch, with the 2% fee configuration.
- The stranger 0xbffebe78 bought 0.039 at +3 (x1.26); then 0x493e2bf9 bought 0.138 at +488.
- 69 outside wallets traded and 67 buys were >= 0.05 ETH. The peak was x102, and it is x81 at the head.
- Early strangers hold large paper gains (valued at the marginal price, so overstated). Realized P&L is mostly negative because they still hold.

This is a single lottery ticket, not a line.

### Numbers

- Launches: 85 in 12 h, 4 wallets (28/28/28/1).
- Outside buys within +600: 2, both in the runner. Over the lifetime, outside buys in 4 pools.
- Buys >= 0.05 ETH: 67, all in the runner.
- Pulls: 0/85.

Rule: buy 0.002 ETH at +1/+2, then sell (single-range v4 math, the hook's fees, gross of gas):

| Sell at | Mean | Median | Winners |
|---|---|---|---|
| +60 | -1.87% | -1.99% | 1/85 |
| +600 | -1.29% | -1.99% | 1/85 (+56%) |
| +3000 | +3.60% | -1.99% | 1/85 (+473%, the runner) |

- Without the runner, every cell is -1.99%.
- A buy at +3 is -2.01% / -1.50% / +2.84%.
- Spray launcher sell offsets: +5,724..+5,968.

## S3: to ...fa61a056. Launcher 0xeebb258267e730c8c937500cb9890323fa61a056, selector a25a9a3d (code ea85919a, 23.6 KB), 804/836/868/900 B. Value 0.000100683 ETH (a launch fee). ETH pair, fee 1%, tick spacing 200, no hook.

**NOT A LINE**

This shape is new today. The first launch was at 11:34 UTC, by one fresh wallet 0x836f5370 (nonce 39).

The call a25a9a3d(name, symbol, metadata on cronos.hypercarsbrokers.xyz, website, x.com, image):
- mints a 1e27 coin;
- sends 20% to 0xd1cc6c4c;
- adds 80% as single-sided ETH-pair liquidity over 87,200..207,200 (start tick 207,199), owned by the launcher contract.

In all 36 pools the only swap ever is the dust sentinel 0xe71a69f4 (2e-6 ETH at +2..10, via the Universal Router). Nothing else happened from launch to the head (1.7-4.5 h per pool): no buyer, no seller (not even the 20% holder), no liquidity removal.

No repeat buyer. Nothing to front or follow.

### Numbers

- Launches: 36 in 12 h (all after 11:34 UTC), 1 wallet.
- Outside swaps: 0, within +600 or ever.
- Pulls: 0/36.
- Price: x1.000 throughout.
- Rule (buy +1..+3 at 0.002, sell +60/+600/+3000): -1.99% in all 36 (the 1% LP fee each way).

## S4: to ...af0ff9d8 / ...025c7d37. Launcher contracts 0xeb89d7d369f10a22fc8849eae606c2a1af0ff9d8 (code 5a25e605, 19.0 KB) and 0xeec51433d57e89b03ec73afe3404daf2025c7d37 (3f5e1dda), selector 7fde822e, 740/772/804/836 B, value 0. ETH pair, fee 1%, tick spacing 200, no hook.

**NOT A LINE**

The call 7fde822e(dev 0x94dddbb5, 2,500 bps, dev, 1.7 ETH, name, symbol, image on imortal.buzz, x.com, website):
- mints 25% of a 1e27 coin to the dev wallet;
- mints 75% to the contract, which adds single-sided ETH liquidity over 132,800..201,800, owned by the contract.

One wallet, 0x06cb3a68 (nonce 2,709), deploys a fresh launcher contract every ~20 launches.

This is the known 7fde822e launchpad family: census rows 29/31/38 and REPORT_B's '7fde822e launchpads 1,461, 0.3% real buys'.

In all 26 pools the only swap is the sentinel's 2e-6 ETH at +3/+4. Nothing else happened to the head, and nothing was removed.

The 37 other 7fde822e launches in the same 12 h (contracts 0x96956a00, 0x8a9959fb, 0xa1c9c202, 0x2d0ee806) are identical: 0 outside swaps and 0 pulls.

No repeat buyer.

### Numbers

- Launches: 26 to these two targets in 12 h (pool ages 0.15-2.2 h), plus 37 siblings.
- Outside swaps: 0 of 63.
- Pulls: 0 of 63.
- Price: x1.000.
- Rule: -1.99% in all 26 at every buy/sell offset.

## Files

The REPORT.md write was refused (subagent rule); the report text is in the candidates above. Everything is in /home/user/v2pons/research/session_oct12/shapes/launch4/.

Scripts, each with an .out printout of the same name:
- common.py, rpc.py: a copy of c1/rpc.py with its log in cache/.
- s01_launches.py: every Initialize in 12 h, the shape table and s01_launches.json.
- s02_anatomy.py: the target and hook code, calldata words and sample receipts.
- s03_events.py: grouped Swap and ModifyLiquidity logs to +600, later ModifyLiquidity to the head, and the event transactions.
- s04_build.py: s04_pools.json (1.9 MB).
- s05_lifetime.py: every swap to the head.
- s06_activity.py: s06_pools.json (0.5 MB, now under 2 MB). The parent's .gitignore still lists it from when it was 2.07 MB.
- s07_fees.py: the hooks' take, from receipts.
- s08_cases.py: per-pool listings, 6 pools per shape.
- s09_rule.py: the buy +1..3, sell +60/600/3000 replay.
- s10_siblings.py: the same selectors or hooks through other targets.
- s11_strangers.py: strangers' P&L.
- s12_wallets.out: launcher nonces and balances.
- s13_spotcheck.py: single-pool queries match the grouped ones in 6 of 6.

Raw caches are in cache/*_cache.jsonl, ignored by research/**/cache/.

RPC load: 473 POSTs (4,769 items), at least 0.5 s apart, about 45 HTTP 429 back-offs. No transaction and no key; src/, deploy/, tests/ and docs/ were not touched. I did not commit anything; the parent session's commit fadf609 picked up the early files.

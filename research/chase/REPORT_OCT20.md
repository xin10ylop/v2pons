# The 2.433 operator, Oct 15 21:30 to Oct 20 11:35 UTC: where it is, what it does, what the engine needs

Scanned from public RPCs with `research/chase/scan.py` (every Uniswap v4 pool paired with the native coin, grouped by the launch
transaction's target contract, the hook and the tick spacing), `deep.py` (every swap and liquidity event in the first five minutes
of a launcher's pools, with the wallet behind each swap) and `price_deep.py` (the paper return of the two trade shapes). The box's
log was not reachable from here, so this is the chain's report, not the engine's. The operator's fingerprint, from report 24.54:
a fresh wallet per launch (nonce 0), a pool with ETH as currency0, tick spacing 200, a sub-1% fee, 1-5 ETH of liquidity, a
scripted buying fleet starting a few seconds after the launch, the liquidity pulled minutes later.

## 1. Where the operator is

| chain | native-paired v4 pools in the window | the operator | verdict |
|---|---|---|---|
| **Robinhood Chain** | 10,185 | **launcher `0x3194e32622c5d860a0572c74edda99dcfd8fc827` (the original one, same launch selector `0x2fcb9108`): 527 pools from Oct 16 04:51 UTC, 165 in the last 24 h (about 7/h, bursty: 22/h at 15:00 UTC Oct 19, nothing 19:00-23:00 Oct 19 and 01:00-06:00 Oct 20), latest at 11:33 UTC Oct 20.** No hook, tick 200, every deployer a nonce-0 wallet, 111 recurring buying wallets. | **back since Oct 16, live now** |
| Base | 5,127 | see section 4 | |
| BNB Chain | 1,260 | no group with fresh-wallet deployers and pulls within minutes; the big groups are direct PositionManager launches by funded wallets (739 pools at a fixed 10.53 BNB, 1 of 25 pulled) | not here since Oct 15 |
| Ethereum | 591 | no group at scale; the only pull-in-4-minutes group (5 pools, 1.5-2.5 ETH, one wallet, hook `0xba01b983…`) has zero swaps: an LP test, not the operator | not here |

Robinhood, Base, BNB and Ethereum were scanned in full. Arbitrum, Unichain and Optimism were checked only for the Robinhood
fleet's wallets (none present); the operator uses fresh wallets per chain, so that check proves nothing, and those chains are not scanned.

## 2. The Robinhood line now (527 pools, Oct 16-20)

- **Fees**: 0.05% to 6%, mode 0.45%; 136 of 527 at exactly 1% (10000 ppm), one at 3%. The engine's `FEE_MAX_PPM=9999` skips the 1% pools.
- **Liquidity**: median 1.87 ETH, p10 1.30, p90 2.25; the last 20 pools 2.25 ETH median (2.13-2.39). The "2.433 line" is 2.1-2.4 again.
- **The fleet**: the first real-size buy lands 26 blocks (2.6 s) after the launch (p10/p90 23/56). Median 54 buys and 2.23 ETH bought per pool
  (as much as the liquidity), 20 buying wallets per pool, 111 recurring wallets in the five days, 25,887 of 26,450 swaps through the
  router `0x8876789976decbfcbbbe364623c63652db8c0904` (a public router; not a fingerprint).
- **The pull**: inside 5 minutes on 419 of 527 pools, median 137 s after the launch (p10 10.6 s, p90 248 s), never before the fleet's first buy.
- **Nobody else is trading it**: 19 of 527 pools saw a buyer outside the fleet (wallet on one pool only, nonce above 5 or not via the fleet's router).

**The two trade shapes, priced from the chain (paper, both legs pay the pool fee, a pull at or before the exit counts -100%):**

| shape | 0.02 ETH stake | 0.0012 ETH stake |
|---|---|---|
| the flip the repo trades (buy 2 blocks after the fleet's first buy, sell 7 blocks later) | **-3.9% mean, 14.5% win**, 13 pulled | -1.8% (gas excluded) / -2.5% (with $0.02 gas), 16% win |
| the early seat the Base engine traded (buy at launch+2, sell at launch+100 = 10 s) | +15.6% mean, +21.5% median, 92% win, 38 pulled (7%) | +17.9% mean |
| early seat sold 20 blocks after the fleet's first buy | +6.2% mean, 95% win, 18 pulled | +8.2% |

The flip is dead: the fleet's first buys no longer move the price enough to cover two fees of 0.4-1% and our own impact; the engine
would lose on Robinhood as configured. Both numbers were reproduced by an independent script (`scratchpad/verify/backtest.py`, 3 pools
checked event by event against the chain).

**The early seat's paper return is not real money on Robinhood.** Of the 19 pools where an outsider bought, 12 were pulled 5-7 blocks
(0.5-0.7 s) after that buy, 6 pools confirmed on the chain event by event. The 7 that survived longer were dust buys (0.00001-0.001 ETH);
**every outside buy of 0.002 ETH ($5) or more, 9 of 9, was followed by the pull within 3-7 blocks** (0.0025, 0.0022, 0.0022, 0.099,
0.005, 0.02, 0.006, 0.02, 0.02 ETH). Outsider pools are pulled at a median of 200 blocks after the launch against 1,800 for the rest,
so this is a reaction to the buy, as in report 24.54, and faster than any sell the engine can land (its sell goes out at buy+5). With a
0.02 ETH stake the expected return is about -60%: the seat is the trap again. The only outsider who got out bought 0.0001 ETH.

Robinhood therefore has the operator but no trade for us until its reaction changes: neither the flip (negative) nor the seat (pulled).

## 3. BNB Chain and Ethereum

The operator's Oct 13 BNB pools and its Ethereum test were before this window; in the window neither chain has a launcher group with
the fingerprint. BNB's PositionManager-direct launches (739 pools, fixed 10.53 BNB liquidity, 8/h, stopped Oct 19 18:27 UTC) are a
launchpad's migrations, not a pump-and-pull. Ethereum's five hooked pools with the 4-minute pull had no swaps at all.

## 4. Base

(filled from the Base scan below)

## 5. The errors behind us and what the engine lacks for a relaunch

The repository (5 commits) is the Robinhood flip only. The Base engine, the second launch call, the honeypot launcher and the hook
code-size guard live on the box and were never committed; whatever runs next should start from a committed engine.

Errors fixed in the history: the first live first-buy crashed the engine (the dry run with no relay built transactions against an empty
address; fixed in f8796f5, fire() failures are alarms now), and relay_deploy's buy check printed "differs" on a 1e-20 gap (b6b0268).
Errors from the Base run, none of them in the repo: the engine sat idle 81 minutes when the operator changed its launch call
(the engine matches only the launcher address, `LAUNCHERS`, src/flip_engine.py:36 and :455, not the selector, so a new call on a new
contract is invisible until added by hand); the honeypot (a launcher added without a sell simulation; the hook that only lets the fleet
sell is not detectable from the launch receipt, the engine only checks `hooks == 0`, :232); and the guard that followed skipped every pool.

What the engine lacks (file:line in src/flip_engine.py):

1. **Chain config.** `CHAIN_ID=4663` is a constant (:35), the feed decoder is Nitro-only (:143-154, :432-443), gas is legacy `gasPrice` (:253, :258),
   every timing is in 100 ms blocks (`HOLD_BLOCKS`, `TRIGGER_MAX_BLOCKS`, `SELL_FALLBACK_S`, :42-44). Base needs a per-chain map, a Flashblocks
   or mempool source, type-2 transactions with a priority fee, and timings in seconds.
2. **Launcher recognition by (contract, selector, hook, tick spacing, liquidity band)**, not by address alone, with new groups logged as
   `unverified` until step 3 passes. `scan.py` already groups this way; it is not wired into the engine.
3. **The exit test before any trade on a new group**: an `eth_call` round trip (buy, then sell, through the relay with a state override, as
   `deploy/relay_sim.py` does by hand) on the group's latest live pool; refuse the group if the sell reverts or returns under a floor. This is
   the check that would have caught the honeypot. The hook code-size guard is a weaker proxy for it; a hook with code should be refused unless
   the exit test passes on it.
4. **The entry rule of the Base trade**: buy off the launch receipt (the liquidity add), stake 0.02 ETH, sell when the fleet's buys are seen
   behind us (a swap counter per pool from the feed or Swap logs), not on the fleet's first buy (:457-465) with a fixed hold.
5. **Defaults that misfire today**: `FEE_MAX_PPM=9999` (:41) skips the 1% pools; `MIN_TRIGGER_ETH=0.0002` with first-match semantics (:461-466)
   fires on any tx carrying the token address, outsider or not; the 4 s receipt wait (:225) can arm a pool after the fleet's first buy has
   passed, so the engine fires on the second buy as if it were the first; `MIN_LIQUIDITY=1e21` is a raw v4 L figure, check it against today's
   pools from the `armed` lines; `ETH_USD=2570` is static and sets the daily stop.

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

The operator's Base launchers from Oct 14-15 are on the box, not in the repo, so Base was read by fingerprint. Every v4 pool paired
with ETH (5,127), with WETH as currency0 (2,267) or as currency1 (940) since Oct 15 21:30 UTC was grouped; the liquidity and the pull
were read for all 5,127 ETH-paired pools. Result: **the operator's v4 line on Base is gone.** The groups with real ETH liquidity and
fast pulls are one line only: direct PositionManager launches at tick spacing 1, fee 0, a fixed 1.2 ETH per pool (2,215 pools, 20/h,
2,237 funded deployer wallets, 581 pulled a median 4 blocks = 8 s after launch); its buyers and its reaction are being read (pending).
Everything else is launchpads (Clanker, Zora, 4337 launches) with no pulls, or two token mills: a family of 30 rotating launcher
contracts (a new one every 15 pools, 404 pools, 2 persistent deployers, Oct 15 22:11 to Oct 20 02:00 UTC) and a single-wallet launcher
(426 pools) that both initialize token-only pools with no ETH side; their only swap is a probe bot's dust buy; nobody buys them.
Those mills are not attributable to the operator and have nothing in them to trade.

**The live Base lead is Uniswap V2.** A pair created at 12:07 UTC today by a fresh wallet (nonce 2) with 15 ETH of liquidity drew a
probe's dust buy in the creation block and then 0.08-0.12 ETH buys from wallets with nonces 1,800-2,900 within a minute. Whether that
is a pump-and-pull with a fleet and a pull, and how many such pairs there are, is being read from every WETH pair created on the V2
factory in the window (773 pairs; pending).

A correction on wallets: the wallet `0xe71a69f434a719cd5afa411568b69716aab3b84a`, which looked like a shared fleet wallet across
chains, is a probe bot: it buys exactly 0.000002 ETH on every new pool (468 of the operator's 527 Robinhood pools at launch+3 blocks,
about 800 pools a day on Base across v4, V2 and v3, 250k transactions on BNB in the past, idle there since before Oct 12). It is not
the operator's, and the operator's detector ignores it. Four more dust-only wallets do the same on Robinhood.

## 4b. Inside the operator's Robinhood line (527 pools, read swap by swap)

- **The fleet**: 98 recurring wallets with median buys of 0.03 ETH (menu 0.03 / 0.05 / 0.07 / 0.08 / 0.09, up to 0.26), about 40 of
  them new this week; buys from 2 s after launch, sells from 5-8 s, both interleaved until the pull; the price plateaus at about 3x
  the launch price from 50 s. Per pool the fleet buys 2.85 ETH and sells 1.45 ETH back; the deployer's pull (its nonce-1 transaction
  to the PositionManager) recovers the rest: a closed loop. Half the buy ETH is in by 33 s.
- **The pull**: bimodal. 40% of pools with no outsider at all are pulled inside 30 s by the program's own end; the rest at 210-250 s.
- **The detector**: a wallet whitelist plus a size rule. Every outside buy of 0.002 ETH or more was followed by the pull 3-7 blocks
  later (33 of 33; median 5 blocks = 0.5 s), 89% of buys of 0.0005-0.002 ETH, 74% of 0.0002-0.0005 ETH, independent of fee tier,
  router, hour and phase (a 0.099 ETH buy at launch+18, before any fleet buy, was pulled at +23). Dust under 0.0001 ETH triggered it
  0 of 69 times on Oct 20 (36-39% on Oct 16: the threshold is a setting and moves). No outsider ever sold before the pull.
- **A second shape**: pools at 2-3% fee with no fleet, where 12-30 of the operator's own fresh wallets buy one menu size each and never
  sell, as bait; the snipers who followed them lost everything (pull 48 blocks after the last sniper buy).
- **Seats priced** (paper, fees both legs, our impact, gas, real pulls): the pre-first-buy seat (buy +22, sell one block after the
  fleet's first buy) is +3 to +4% only if the operator did not react, and -57% once his 5-block reaction is modelled; a fixed exit
  inside his reaction window (+24..+26) is 0 to +1%; the shortest flip (+2 and +3 blocks after the first fleet buy) is -1 to -2%;
  an LP seat (adding 5-10% of his liquidity) is -11 to -13% even with no reaction, and the token purchase to build it would itself
  be pulled.
- **The sub-threshold seat is dead too.** A buy under his size rule (0.0001-0.00015 ETH at launch+22, held into the 3x pump) prices
  at +74% to +168% on paper, but an independent refutation showed the trigger is a **per-pool counter of net outside buying**, exact at
  0.0002 ETH (highest net position never pulled: 0.000195; smallest pulled: 0.000200), pull 5 blocks after the crossing, pre-fleet buys
  included: 33 pools crossed it through several dust wallets and 25 were pulled 5-7 blocks after the crossing buy. The probe bots'
  routine 0.00005-0.00017 ETH buys push 397 of 514 pools over the line once our 0.00015 sits in the counter: 404 of 514 seats pulled,
  mean -43% / -13% at +300 / +500 blocks, expected value -$0.05 a pool. Only a stake at or under 0.00003 ETH survives (+80% mean, about
  +$0.06 a pool, one gas round trip), and wallets cannot be multiplied because they share the counter. **No seat at any size.**
- **His economics** (all 527 pools, every swap attributed): seed 1.79 ETH in and fleet buys 2.85 in, fleet sells 1.45 and the pull 3.19
  out: 4.638 against 4.639 ETH, a closed loop to the fourth decimal. Profit is exactly what outsiders leave: 1.063 ETH (about $2,700)
  in 4.27 days, 0.55 of it taken within 10 blocks of the buy; gas about $0.77 a pool (launch 1.0M gas, pull 159k, 115 transactions a pool
  at 0.02 gwei); net about +0.0018 ETH a pool, $500-770 a day. Another 2.7 ETH came from 57 fresh menu-size wallets on four 2-3%-fee
  pools that look like his own bait (one of them deployed a pool and bought its own token); if they were victims, the take triples.
  The fleet's 1,465 ETH of buys and 744 ETH of sells (about $1.8M a day of self-trade) are out of all proportion to the trapped ETH, so
  a volume or activity incentive on Robinhood Chain or its DEX is the plausible second purpose; the chain data cannot verify it.

## 4c. The money trail on Robinhood (traced live through eight launches)

- **Two floats, fully recycled, nothing parked.** Line A: about 7.29 ETH and a roster of 42 fleet wallets; line B: about 6.79 ETH and
  29-31 wallets (disjoint rosters, launches interleaved, two launches 6 s apart). Each cycle: a fresh collector wallet receives the
  deployer's sweep (its nonce-2 transaction, 100-310 blocks after the pull, about 5.5 ETH) and every roster wallet's remainder in the
  same 20-block burst (about 1.7 ETH), forwards all of it 21-28 blocks later to a fresh distributor, which funds the next deployer
  (1.2-2.6 ETH) 8 blocks later and then the roster in a fixed order two blocks apart (0.11-0.16 ETH each). Every hop is a one-shot
  wallet that forwards everything minus a gas reserve of 0.0000132 ETH. The deployer's nonce-3 transaction is a dust sweep.
- **No bridge, no exchange, no inflow but victims.** No wallet in the loop ever touched the Orbit bridge or an exchange-like address.
  The float was seeded on Oct 15 21:30 UTC from the previous generation's sweeps (an older launcher) and grew from 5.84 to 7.29 ETH
  in 4.6 days: +0.32 ETH a day.
- **Economics per pool**: 1.9 ETH added (the launcher skims exactly 0.1% of the launch value), the fleet buys 2.2-2.6 ETH and sells
  0.8-1.3 ETH, the pull removes 3.2 ETH; net per pool equals exactly what outsiders paid in: 0.000 ETH on 391 of 419 pulled pools,
  +0.089 ETH mean on the 28 that had an outsider. Per day at 175 launches: about 1.0 ETH from outsiders, 0.4 ETH launcher fee, 0.2-0.35
  ETH gas, net about +0.3 to +0.5 ETH on roughly 14 ETH of float and about 500 ETH of self-traded volume.
- **Why he reacts the way he does**: the outsider's ETH is the whole profit, so the program takes it the moment it lands (the pull
  3-7 blocks after any buy at or above its size rule). The 0.5 s reaction is not defensive; it is the business.
- Old-generation fleet wallets (234-253 pools each, nonces 3,800-5,900) were retired on Oct 15 and sit empty; the current roster
  wallets hold 0.008-0.118 ETH between cycles; the launcher's 0.1% fee recipient could not be resolved without traces.

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

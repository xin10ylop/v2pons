# The chase, Oct 15 21:30 to Oct 20 13:30 UTC: where every operator is, what each line pays, what we do now

Read from public RPCs with `research/chase/report.sh` (every Uniswap v4 pool paired with ETH, WETH or WBNB on Robinhood, Base, BNB and
Ethereum, grouped by launch contract, hook and tick spacing; every V2 pair on the factories the pump-and-pull lines use), deep pulls of
every swap and liquidity event with the wallet behind each, and exact paper replays with the engines' own rules. Independent agents
re-derived every money figure and tried to refute every seat. The box's logs were not reachable; the owner's `results.py` screen of
13:07 UTC Oct 20 is folded in.

## 1. The answer in one table

| line | chain, venue | state now | our engine | seat |
|---|---|---|---|---|
| **the 2.433 line** (the volume bot's 2.4333285 ETH family: flip-engine's `v2.433`, +$1,515 over 1,267 trades) | Robinhood v4 | **dead since Oct 12 02:06 UTC** (last launch; tapered from 132 to 20 per 2.8 h on its last day) | flip-engine, release 0.9, idle, service stopped, relay empty | none: the family does not launch |
| the volume bot's 3.0 and 5.0 ETH families | Robinhood v4 | live, about 650 pools a day, through the same contract the engine watches (`0x1cbaf24d53`) | refused by the engine's sub-1% fee gate (they are 1%) | none: the pull follows any outside swap in 5-21 blocks, before its own fleet buys; the front rule replays at -2% to -5% |
| **a third operator's V2 line** (1, 30, 40, 50 ETH pairs, 236 a day; not operator A, not the volume bot) | Robinhood V2 | live, since before Oct 8 | none | the big tiers pull 13-60 s after any foreign buy of 0.00015 ETH; **the 1 ETH tier is the one untested seat** (+94% paper at a 3-minute hold, 70% win) |
| operator A (launcher `0x3194e326`, flip-engine's `follow`) | Robinhood v4 | back since Oct 16 04:51, about 175 a day | idle (the flip prices -4%) | none: a per-pool counter of outside buying, exact at 0.0002 ETH, pull 5 blocks later; the dust seat is -$0.05 a pool |
| the tick-spacing-1 direct line, the dust traps, the fee traps, the launchpads | Robinhood v4 | live or dead, see section 4 | none | none |
| the 2.433 operator's v4 line (base-0.2's +$588) | Base v4 | **gone since the honeypot of Oct 15**; no pool of its shape since | flip-base, idle by design, relay 0.045 ETH | none |
| **the Base V2 line** (a different crew, same playbook; 749 fresh-wallet pairs in 4.6 days) | Base V2 | live, 24 h a day, about 5-7 pairs an hour | none yet: **being built** (section 6) | **the 1.4-2.2 ETH tier**: +29% mean, 96% win on paper, 4% pulled; the 1.2 and 13.8-17.8 ETH tiers react and are off-limits |
| the Base 1.2 ETH tick-1 line, the token mills | Base v4 | live | none | none: a sniper trap and empty pools |
| BNB Chain, Ethereum | v4 and V2 | nothing of any operator in the window | flip-bnb disabled | none |

Three operators were found on Robinhood, one crew on Base, and none of the three has a seat our engines can take as they are. The one
thing worth money that the data supports is the Base V2 tolerant tier, under a staged live test; the one cheap experiment is the
Robinhood V2 1 ETH tier.

## 2. Operator A on Robinhood (launcher `0x3194e32622c5d860a0572c74edda99dcfd8fc827`)

- **Back since Oct 16 04:51 UTC**, 527 pools by Oct 20 11:14, 165 in the last 24 h (bursty, up to 22 an hour), latest at 11:33 UTC; no hook,
  tick 200, fees 0.05-6% (136 at exactly 1%), 1.3-2.4 ETH per pool (the last 20 at 2.25), a fresh nonce-0 deployer per pool.
- **The fleet**: 98 recurring wallets with 0.03-0.09 ETH buys through router `0x8876…`, about 40 of them new this week; buys from 2 s after
  the launch (first real buy at 26 blocks), sells from 5-8 s, the price plateaus at 3x from 50 s; per pool the fleet buys 2.85 ETH and
  sells 1.45 back; the deployer's pull recovers the rest. Bimodal pulls: 40% of untouched pools inside 30 s, the rest at 210-250 s.
- **The detector**: a wallet whitelist plus **a per-pool counter of net outside buying, exact at 0.0002 ETH** (highest net position never
  pulled 0.000195, smallest pulled 0.000200), pull 5 blocks after the crossing; pre-fleet buys count; 33 pools were crossed by several dust
  wallets and 25 pulled 5-7 blocks after the crossing buy; 100% of outside buys of 0.002 ETH or more pulled (33 of 33); probe dust of
  0.000002 ETH never. No outsider ever sold before the pull on the main line.
- **A second shape**: 2-3%-fee pools with no fleet where 12-30 of its own fresh wallets buy one menu size each as bait; snipers who followed
  lost everything.
- **Money**: two floats of 7.29 and 6.79 ETH, each recycled every pool through a fresh collector and a fresh distributor (every hop a
  one-shot wallet forwarding everything minus 0.0000132 ETH), the roster of 42 or 31 fleet wallets refunded 0.11-0.16 ETH each per cycle,
  nothing parked, no bridge or exchange ever touched; profit is exactly what outsiders leave: 1.06 ETH ($2,700) in 4.27 days, net about
  $500-770 a day after gas ($0.77 a pool); the launcher skims 0.1%. The $1.8M a day of self-trade is out of proportion to that, so a
  volume or activity incentive is the plausible second purpose. The 0.5 s reaction is the business: the outsider's ETH is the only income.
- **Seats, all dead** (paper, fees both legs, our impact, the reaction modelled): the flip -3.9%; the pre-first-buy seat +3-4% with no
  reaction and -57% with it; a fixed exit inside the reaction window 0 to +1%; the LP seat -11%; the dust seat under the threshold
  +74-168% on paper but -$0.05 a pool once the counter and the probe bots' routine buys are modelled; only a stake under 0.00003 ETH
  survives, worth one gas round trip, not multipliable because every wallet shares the counter.

## 3. The volume bot (the 2.433 line) on Robinhood

- **The 2.4333285 ETH family stopped on Oct 12 at 02:06 UTC** (the last launch; 132 launches per 2.8 h the previous afternoon, 33 and 31
  that evening, 20 in its last stretch). Nothing of that fingerprint since.
- **Its 3.0 and 5.0 ETH families are live** at about 650 pools a day: exactly 3.000 ETH (1,006 pools from fresh nonce-3 wallets and 810
  from a recycled family at nonce 290-304) and exactly 5.000 ETH (969), fee 1%, tick 200, full range, the same 5,274-byte token template,
  launched through the PositionManager's multicall and pulled through the bot's own contract `0x1cbaf24d53` (the engine's
  `FRONT_BOT_ROUTERS`), which also carries the fleets' 0.10-0.15 ETH buys (fleets of 51, 60 and 105 wallets, no overlap). Each slot sweeps
  7-10 ETH to the next launch wallet 48 blocks after every pull and relaunches 126-157 blocks later. 100% pulled: a 9.5-minute timer when
  nothing touches the pool, **5-21 blocks (median 13) after any outside swap down to 0.00001 ETH**. About 9,000 ETH of wash buys over five
  days, a closed loop. The front rule replayed exactly on 300 of these pools (fire at launch, land +1, sell into the bot's first buy,
  take-profit 1%, hold 18, the bot's minOut revert model): -2% to -5% at every stake, because the bot's real buys come 24-46 blocks after
  the launch and its reaction comes first. Oct 10's verdict on v3.0 (+3%, rejected) and v5.0 (pulls on outsiders) holds.
- **The V2 line on factory `0x8bceaa40` is a third, separate operator** (zero shared wallets with operator A at every layer, a different router `0x89e5db8b`, different token templates, persistent funder wallets instead of one-shot hops, running since before Oct 8 and unaffected by the others' pauses): 236 fresh-wallet (nonce 2) pairs a day at exactly 1.00, 30.09, 40.59 and 50.09 ETH; 17 core
  wallets buy until the pool holds 30% more ETH than the mint (price 1.7x), the pull returns mint plus buys (net -0.003 ETH a pool);
  99.96% of the first hour's 9-14 ETH of buys is its own money. The 40.59 and 50.09 tiers pull 134-603 blocks after any foreign buy of
  0.00015 ETH or more (19 of 20); the 30.09 tier tolerates up to 0.004 ETH (a seat worth 0.0016 ETH a pool). **The 1.00 ETH tier**: a
  9.6-minute timer with a third of pools aborted early, price 1.5x at 1 minute and 3.6x at 5 minutes, paper +94% mean at a 3-minute hold
  (70% win, 30% pulled, stake-insensitive up to 0.5 ETH), and no foreign buy above dust has ever landed on it: its reaction is unknown. A
  $20 live test settles it (0.005 ETH at +300 blocks on one fresh pair, three trials; a pull inside the next 700 blocks has a 20% base rate).
- **Its money**: one funder wallet per tier sends exactly tier + 0.01 ETH to each creator and 9.5-18 ETH through a disperse contract to a
  10-wallet bait fleet; the creator pulls at nonce 4 and sweeps everything back to the funder at nonce 7; in-flow equals out-flow
  (135 against 136 ETH on the 50 ETH funder), no bridge or exchange, about 70 ETH of working capital per tier in flight. The buyers are
  its own fleets: 100% of the buy ETH on the big tiers, and most of the 1 ETH tier's buyers are fresh wallets the hub drops 0.04-0.22
  ETH into (at most 10-20 ETH a day could be genuine). About 2,100 ETH a day of self-bought volume and 10,000 ETH a day of liquidity
  churned through the router for nothing: a volume farm.

## 4. The other Robinhood lines

- **The tick-spacing-1 direct line** (720 pools at 0.05% fee launched straight on the PoolManager, 3-4 ETH, pulled at 27 s median): a
  closed-loop wash machine recycling the same ETH 6.7 times an hour through about 490 gas-only fleet wallets; 35 of 150 pools ever saw an
  outsider, who never sold; the pull is event-driven. No seat.
- **The bonding-curve graduation launchpad** (hook `0xe5e7…e044`, 4.2 ETH of permanent full-range liquidity per pool, real crowds of up
  to 135 ETH in five minutes): a flat 2.5-5% hook tax each way, no time cliff, the first 30 blocks dominated by curve holders dumping.
  Both seats lose on median. Informational only (which curve graduates).
- The 89% and 96% fee traps, the dust wash line (pools holding 0.004 ETH), the 1.00xx%-fee bid walls, the scam-token factories, the
  one-off launchers: nothing to trade.
- Six probe bots dust-buy every new pool on the chain (0.000002-0.0001 ETH at +3 blocks); `0xe71a69f4…` does it on Base and Robinhood
  alike (800 a day on Base, 110k transactions on Robinhood). They are not any operator's wallets and the operators' detectors ignore them.

## 5. Base

- **The 2.433 operator's v4 line is gone.** Every v4 pool paired with ETH (5,127), WETH as currency0 (2,267) or currency1 (940) since Oct 15
  21:30 was read; the only ETH-funded fast-pull group is a PositionManager tick-1 line (2,215 pools at a fixed 1.2 ETH, fee 0, a quarter
  pulled 8 s after launch, 0-1 blocks after the first outside buy of about 0.02 ETH: a sniper trap), plus launchpads and two token mills
  (empty token-only pools; 404 of them from 30 rotating launcher contracts). Nothing of his shape.
- **The V2 line** (factory `0x8909Dc15`): 749 fresh-wallet pairs in 4.6 days, 24 h a day, 1.8x busier at 01-07 UTC. A persistent hub funds
  a fresh wallet with exactly tier plus gas; it deploys the token at nonce 0 (3,553 bytes, no owner, no tax), approves at nonce 1, and at
  nonce 2 calls the router's `addLiquidityETH` with the tier (1.2, 1.4, 1.5, 1.9-2.2, 2.5, 13.79, 15.0, 17.79 ETH); a fleet of about 143
  wallets buys from +2 blocks (first real buy at +8/+11/+54 blocks); the creator pulls on a schedule per tier (1.2: +393; 1.4-2.2: +540,
  never under +198; 15: +1,131 blocks) a median 9 blocks after the fleet's last buy; the pool plus the fleet's buys sweep back to the hub,
  which funds the next creator 8-15 blocks later. **A different crew from the Robinhood operator**: persistent hubs since Sep 22 with
  thousands of nonces, no intermediate hops, no shared wallet, a different token template; the same playbook and the same detector.
- **The reaction**: on the 1.2, 13.79, 15.0 and 17.79 tiers every non-fleet buy, dust included, is followed by the pull 2-8 blocks later
  (18 of 22 dust buys, 20 of 20 above 0.0005 ETH); the 15 ETH tier is negative even with no reaction (the fleet lifts the price 2.5% in 2
  minutes). **The tolerant tier, 1.4-2.2 ETH**: about 40 outsider buys of 0.0005-0.04 ETH drew no reaction (31 of them from two bots on
  Oct 20 that may be whitelisted; one 0.0008 ETH buy on Oct 16 was pulled 2 blocks later); the fleet buys 0.58-0.65 ETH, 30-40% of the pool,
  over 5-10 minutes; price +13% at +60 blocks, +24% at +120, +34% at +180. The rule "buy at creation+1, hard exit at +180 blocks, take
  +25% early" prices **+28.8% mean, +34.3% median, 96% win, 9 of 219 pulled over all days, +59% and 100% win on Oct 20's 16 pairs**, at 0.02-0.1
  ETH (above 0.2 ETH we are the pump). The tier is intermittent (none on Oct 18-19) and its size moves (1.9, then 2.1-2.2, then 1.5-1.6,
  now 1.4-1.5): zero-trade days are accepted rather than widening the band.
- **The exit test passed**: a simulated buy and sell through the router (`deploy/base_v2_sim.py`) on the seven latest 15 ETH pairs, six
  of them between mint and pull, returns 99.4% of the stake, the two 0.3% fees exactly; the same through the new relay
  (`deploy/base_v2_relay_sim.py`) on the open pair. The 2.5 ETH tier (now stopped) used a 1,366-byte token that freezes a holder on demand:
  a pre-buy exit test cannot catch that, so only the 3,553-byte template is admitted.

## 6. The engines, and what is being built

- **flip-engine (Robinhood, release 0.9, the one that made the money)**: idle because its family stopped on Oct 12; the service is stopped,
  the relay holds 0 ETH and the wallet 0.0001 ETH (your screen of 13:07 UTC). No setting makes it earn on today's lines (the 1% families
  lose, the V2 line is another venue). Leave it; nothing to fix.
- **flip-base (base-0.2, +$588)**: idle by design since the honeypot; its line never came back. Leave it.
- **The Base V2 engine (`src/base_v2_engine.py`, in progress on this branch)**: designed in `docs/BASE_V2.md`; reuses base-0.2's transport
  (the Flashblocks stream, the confirmed websocket with its poller, the sender, the signer, the halts, the positions) and trades the
  tolerant tier only: creation recognised from the pending `addLiquidityETH` (router, selector `0xf305d719`, value in the band, sender
  nonce 2, the token equal to the sender's nonce-0 CREATE address) or the confirmed PairCreated plus Mint; the guard chain before every buy
  (the exit test on the very pair, the 3,553-byte template, 99% of the supply in the pool, the tier gate); the buy through `FlipRelayV2`
  at creation+1 with minOut 97% of the constant-product output; three exits (hard +180 blocks sent at +176, +25% early take, instant sell on
  any buy whose recipient is not the fleet roster, the probe or the creator); a Burn before our sell is -100% and halts the tier; up to 3
  positions; daily stop -0.15 ETH. Already in the tree: the relay (`contracts/FlipRelayV2.sol`, 2,994 bytes), the exit test, the relay
  simulator, the fixture of a real pair (`tests/data/base_v2_pair.json`).
- **The staged live test** (in `docs/BASE_V2.md` section 9): stage 0 a 24 h dry run; stage 1 a 0.001 ETH reaction probe on up to 5 pairs of
  the tolerant tier (stop the tier if 1 of the first 3 draws a pull inside 10 blocks); stage 2 0.02 ETH on 10 pairs; stage 3 0.05 then 0.1
  ETH. Never the 1.2, 13.79, 15.0 or 17.79 tiers at any stake.

## 7. Open

- The volume bot's V2 money trail and its identity link to the v4 families (agents pending).
- Whether the two Oct-20 bots on the tolerant tier are whitelisted rather than tolerated: stage 1 of the live test exists for this.
- The Robinhood V2 1 ETH tier's reaction: a $20 live test.
- The Flashblocks latency from the box, and whether a 0.02-0.05 gwei tip lands our buy in the creation block: stage 0.
- The Denim hardfork (200 ms native blocks) will remove the Flashblocks subscriptions; the feed layer must stay swappable.

## 8. Reproducing this

`bash research/chase/report.sh "2026-10-20 00:00"` reruns every scan and pricing for a window; `research/chase/front_replay.py` replays the
front rule on a deep sample; `deploy/base_v2_sim.py --all 6000` runs the exit test on every recent fresh-wallet pair on Base.

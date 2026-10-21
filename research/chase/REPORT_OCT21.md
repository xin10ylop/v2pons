# Oct 21: the Base V2 live test, and Robinhood re-scanned (Oct 20 08:17 to Oct 21 08:17 UTC)

## Base V2 (the tolerant 1.4-1.5 ETH tier): the seat is closed

- The box's dry run and a chain replay agree: 23 dry trades (Oct 20 22:10 to Oct 21 01:00), all take-profit, +27.6% mean; the day's 79
  tolerant pairs replayed from the chain, 79 of 79, +27.6%; within 0.1 point on the 9 pairs both covered.
- Live, 0.002 ETH at N+1, two trades: the fleet never came to the first pair (only our buy and our hard sell in 272 blocks, -1.1%), while
  every neighbouring pair had it from +5; the second pair was pulled at +6 (a sniper bought at +3), our sell behind the Burn: -100%.
  **Total cost of the test: 0.002032 ETH ($5.22)**, relay emptied back to the wallet (0.057215 ETH).
- On the day's chain every outsider's buy before the pull was followed by the pull within 10 blocks (8 of 8); 16 of 77 pulls came 2-3
  blocks after an outsider's buy. A dry run cannot see a reaction to our own buy. docs/BASE_V2.md section 9a.

## Robinhood, every line (scan.py / analyze.py on the v4 PoolManager, v2scan.py on the V2 factory)

| line | last 24 h | the seat |
|---|---|---|
| operator A, v4 launcher `0x3194e326` | 137 pools, ~2.1 ETH, pull median 218 s; none since 05:00 UTC Oct 21 | dead (Oct 20: a per-pool counter at 0.0002 ETH, pull 5 blocks later) |
| the volume bot's 3.0 / 5.0 ETH v4 families (PositionManager multicall) | 498 and 205 launches | dead (pull 5-21 blocks after any outside swap) |
| the 2.433 ETH family | **none** (0 PositionManager launches at 2.40-2.46 ETH of 2,113) | the line that paid +$1,515 is still gone |
| tick-spacing-1 direct line (`0x8366a39c`) | 164 pools, 3-4 ETH, pull median 70 s | none (Oct 20) |
| launchpad hook `0xe5e7…`, fee and dust traps | 8 launchpad pools; the rest empty | none |
| **the third operator's V2 line, factory `0x8bceaa40`** (router `0x89e5db8b`, WETH `0x0bd7d308…`) | 277 fresh-wallet pairs: 1.0 ETH 93, 50.09 ETH 88, 40.59 ETH 80, 30.09 ETH 16 | see below |

- **The 1.0 ETH tier, the one seat Oct 20 left untested, reacts to dust**: two Universal Router wallets (`0x9c411612`, `0x07b0054b`) buying
  0.00004 ETH at +312 blocks were followed by the pull a median 89 blocks (9 s) later, 32 of 38 within 200 blocks; the 6 pairs no foreign
  wallet touched were pulled on the timer (+5,770 blocks, 9.6 min); the probe `0xe71a69f4` (at +4) is ignored. A 0.005 ETH test buy at
  +300 would be pulled about 9 s later. Not run. The tier has launched nothing since about 00:40 UTC Oct 21.
- 40.59 and 50.09: fleets of 0.4-0.7 ETH buys every ~380 blocks; the Oct 20 reaction (134-603 blocks after a foreign buy of 0.00015 ETH or
  more) stands. 30.09: six bait wallets buy on every pair; Oct 20 measured a tolerance up to 0.004 ETH (a seat worth about 0.0016 ETH a pool).
- `report.sh` passed a wrong WETH (`0xf41eacad73d5…`) to the Robinhood V2 scan; fixed to the router's `WETH()`, `0x0bd7d308…f41eacad73`.

Every live line on both chains now pulls on an outside buy (or, on Base, its fleet skips the pair); the one that paid, the 2.433 family,
has not launched since Oct 12 on Robinhood or since the Oct 15 honeypot on Base.

## Robinhood V2, the 30.09 ETH tier re-checked (3 days, 80 pairs, research/chase/v2tier_scan.py, horizon 2 h)

- 31, 33 and 16 launches in the three days (the last 24 h slower, gaps up to 9 h). Ten bait wallets buy round-robin every ~25 s, 0.003-0.2
  ETH each, and never sell; the price is x1.15 at 10 min, x1.32 at 20, x1.41 at 25, x1.50 at 30, x1.68 just before the pull. Pulls: 78 of 80
  within 2 h, median 40 min (p10 26 min); one early pull with no outside buy (12.7 min). Pool fee 0.3%; a router swap costs 0.0000027 ETH.
- **The detector is a per-buy size threshold between 0.0041 and 0.0062 ETH**: 36 outside buys up to 0.0041 ETH were ignored (one of 0.004
  ETH at +6 blocks; two wallets' 0.0041 + 0.0037 on one pair, 0.0078 together, ignored too); every single buy of 0.006 ETH or more was
  followed by the pull 190-198 blocks (19-20 s) later (4 of 4).
- The seat (0.004 ETH at N+1, sold at a fixed time, or 1 s after a foreign buy of >= 0.005 ETH; -100% if pulled first): at 20 min +26.7%
  mean, 78 of 80 won; **at 25 min +32.9%, 77 of 80, +0.00132 ETH a pair**; at 30 min +39.5%, 76 of 80. About $50-110 a day at 16-33 pairs,
  one wallet; untested live.
- **Ten days (Oct 11 09:00 to Oct 21 08:40 UTC, 257 pairs, research/chase/t30_daily.py): every UTC day positive.** The seat at 0.004 ETH,
  25-minute exit: +0.2984 ETH ($767, $70 a day), per day $20 (Oct 17, 14 pairs) to $117 (Oct 19, 33 pairs); 13-39 pairs a day. 20-minute
  exit +0.2360 ETH, 30-minute +0.3485 ETH. Of the 26 pulls inside 25 minutes, 9 came 19-20 s after a foreign buy of 0.006-0.041 ETH (the seat
  sells first) and about 17 had no visible trigger (random early aborts, 7 of them on Oct 12, the seat's -100%, counted). Foreign buys left
  alone reached 0.0060 ETH on some days; two buys of 0.0030 and 0.0039 ETH (Oct 12, Oct 14) were followed by a pull 1.5-3 minutes later, not
  the 19 s reaction: 0.003 ETH is the cautious stake.

## The 2.433 operator found again: BNB Chain, Oct 15-19 (research/chase/bsc2433_scan.py, bsc2433_price.py)

- `track_2433_xchain.py` (its 31 bot-buyer wallets and keys): +44,851 transactions on BNB and +14,812 on Base since Oct 14. By day, Base
  only Oct 14-15 (the base-0.2 stretch); BNB +18,361 / +16,131 / +1,252 / +2,636 / +5,682 a day Oct 15-20, then nothing. On Oct 19 18:21-18:33
  UTC the buyers made their last trades and swept their BNB to `0x23055b43851c387cce0d659d388a8ed22ebe8e5a` (an EOA it also used on
  Robinhood), which still holds 26.65 BNB. No transaction from these wallets on 25 other EVM chains (Arbitrum, Optimism, Unichain, Avalanche,
  Linea, Sonic, Ink, Soneium, World Chain, Blast, Mode, Zora, Celo, Gnosis, opBNB, Mantle, Scroll, Berachain, Abstract, Monad, Sei, Plasma,
  Katana; Polygon and HyperEVM unreadable). It is idle, its money parked on BNB.
- **Its BNB line**: 750 pools Oct 15 11:30 - Oct 20 (every Uniswap v4 pool on BNB with fee 5000, tick spacing 100, no hook, native/token
  in the window), all launched with exactly 10.5333 BNB (about $6,300, the 2.433 ETH pool's dollar size) through the PositionManager
  `0x7a4a5c91`, pulled at a median 813 blocks (6.1 min). The Oct 20 report saw these "fixed 10.5 BNB launches" and set them aside.
  Its fleet (the 31 + about 10 more wallets) buys 0.3-0.65 BNB each through the Universal Router from a median +15 blocks (7 s).
- **The front seat is closed** (150 pools, senders read): when anyone else buys at or before the fleet's first buy, the pool is pulled at a
  median +19 blocks, 8 s (68 of 74); when the fleet buys first, 74 of 76 run their normal course (pull at +877). After the fleet's first buy,
  outside buys of 0.0005-0.001 BNB were mostly left alone (5 of 6), and 0.015 and 0.025 BNB buys were pulled 6-7 blocks later (2 of 2). The
  late seat's paper +12.3% (in after the fleet's first buy, out after its third) assumes no reaction to our buy; at any stake worth trading
  the data says there is one.

## The watch (from Oct 21 15:13 UTC)

`research/chase/watch2433.py --hours 1` checks, every hour, the operator's 31 bot buyers, its 10 further BNB fleet wallets and 7 keys on
BNB, Base and Ethereum (nonces now against an hour ago), on Robinhood (against the Oct 21 baseline) and on 23 more chains (against
their Oct 21 nonces); the 26.65 BNB in its sweep wallet; and new fee-5000 / tick-100 / no-hook native pools on BNB (flagged at 10.4-10.7
BNB) and Base (flagged at 1.3-4.5 ETH). Stateless, read-only, public endpoints, exit 10 when anything moved. Checked over 48 hours it
flags the Oct 19 BNB run (buyers +2,564, fleet +1,387, the sweep wallet's 26.65 BNB arriving). A scheduled task ("Watch the 2.433
operator", hourly at :13) runs it in a fresh cloud session and sends a push notification only when it moved.

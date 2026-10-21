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

# 2.433 and Robinhood/Base re-searched, Nov 10-11 (Nov 12)

**Asked:** is 2.433 back; search Robinhood and Base for another line like it that we can actually trade (not like C-1).

## 2.433

Not back. Every Robinhood block from Nov 7 to Nov 12 02:37 UTC checked for its launch price (`sqrtPriceX96` 1604517591721945638372359205383840):
zero launches. Daily samples show the last launches on about Oct 11. Its operator is alive: the decoy-buy router `0x65050a9b…` made 51,164
swaps in 4.5 days, and the same operator's **3.0 ETH family** (PositionManager multicall 1,444 B, 3.0 ETH, fee 1%, tick spacing 200) is still
launching. That family was tested and closed: it pulls 6-20 blocks after any outside buy (REPORT_STRUCT, `slot30_rh.out`). The volume bot's
own router `0x1cbaf24d…` made no swaps.

## Base: a block-time bug fixed

Base moved from 2-second to 0.2-second blocks in early November. `hlib.block_at` assumed 2 s for Base, so the first "Nov 10" census covered
2.4 hours of Nov 11 (114 pools). Fixed (Base uses the same binary search as every chain). Base windows set in blocks are now 10x shorter
in real time; the Nov 10-11 buyer search used `WIN=3000` (10 minutes).

## The search, Nov 10-11

| chain | pools | buyers in 15+ pools | output |
|---|---|---|---|
| Robinhood | 4,720 | 956 | `buyerlab_rh_nov1011.out` |
| Base | 3,078 | 109 | `buyerlab_base_nov1011.out` |

**Base: nothing new.** The "blind" buyers are contracts called by 9-21 wallets with no fixed timing (sniper or trading-bot routers). The
only scheduled line is the known 2,180 B timer line (0.2 ETH at ~28 s, 142 pools a day): no outsider went first in these two days; in the
7 earlier cases the big buy never came or the launcher pulled.

**Robinhood: operator A's crowd is back, and it is defended.** The whole "blind" list was one line: operator A on its original launcher
`0x3194e326` (`0x2fcb9108`, 644 B; token code `fe89ad0f15d8`), 308 pools over the two days.

- **The token is clean**: a plain 1,770-byte ERC-20 (name, symbol, decimals, supply, balance, transfer, approve, allowance, tokenURI), no
  external calls, no owner or team list, no gas-price / coinbase / time checks, no burn. No C-1 backdoor, no BNB/ETH-style sell block.
- **The crowd is real money**: ~38 buys and ~1.75 ETH into each pool between +24 and +423 blocks; fees 0.05-0.3%; clean pools are pulled
  at a median of +2,028 blocks (~3.4 minutes).
- **But it pulls on a true outsider** (`opAreact.py`). Crowd = any wallet buying in 3+ of the line's pools (74 wallets); a true outsider =
  a wallet in only 1-2 of them. In the 12 pools a true outsider bought (as little as 0.0012 ETH), the launcher pulled a median **12 blocks
  (~1.2 s)** later: 6 of 12 within 10 blocks, 9 of 12 within 50. **0 of 12 outsiders got out**, and the crowd's buying stopped (median 0
  ETH after the outsider). This is C-1's defence, by pull instead of burn.

**Why the buyer search called it blind.** `buyerlab.py` counted a wallet as crew only in 10%+ of a line's pools. Operator A's crowd rotates
across 70+ wallets, many in under 10% of its pools, so crowd wallets were counted as "outsiders who went first", and the crowd looked as if it
bought regardless. Fixed: crew is now any wallet that buys in 3+ of the line's pools.

## Where this leaves it

Nothing tradeable on Robinhood or Base for Nov 10-11. Every line with a real crowd or scheduled buyer pulls, stops or blocks when a true
outsider buys first; the 2.433 family remains the only one that did not, and it has not launched since about Oct 11.

## Tools

- `opAtiming.py LINE_JSON` — a crowd line pool by pool: the wave (start, end, buys, ETH), the pull, the gap, the fee.
- `opAreact.py LINE_JSON` — the reaction test with crowd = recurring wallets (3+ pools) and outsiders = one-off wallets.
- `lineprobe.py` no longer crashes on an unresolved sample transaction.

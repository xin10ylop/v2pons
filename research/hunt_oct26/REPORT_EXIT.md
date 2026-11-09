# The exit test: does a line let its outsiders out? (Nov 9)

**Asked:** search well for another line of the 2.433's caliber, one we could actually trade — not C-1, not a honeypot.

**The one property that decides it.** Every scheduled-buyer line looks the same on paper (a bot buys each pool at a fixed delay; front it,
sell into its buy, +50% to +300% on paper). What separated the 2.433 seat from every line found since is not the entry — it is the **exit**:
a real outsider, not the operator's own fleet, could buy and then sell back at a profit. Every line found since blocks that, in one of three
ways: it pulls the pool on an outside buy, it stops buying, or the token refuses the outsider's sell (a honeypot). So the search is not for a
scheduled buyer — those are common — it is for a scheduled buyer **whose outsiders demonstrably round-trip at a profit on-chain.**

**The test (`roundtrip.py`).** For a line (every pool of one launch template), read every swap with the real wallet behind it. The operator's
fleet = any wallet buying in 10%+ of the line's pools; it is never an outsider. For every *other* wallet that buys, track its token balance
across its own buys and sells:

- **round trip** — it sold 80%+ of what it bought before the pool's liquidity pull → return = native out / native in − 1.
- **cut off** — the pool was pulled and it never got 80%+ out → −100%.

A tradeable (2.433-type) line: most outsiders round-trip, median return positive, few cut off. A defended line: the opposite. This is the same
exit idea the engine already uses on Base (`BASE_PROMPT.md`), measured here from real wallets at scale instead of one simulated sell.

## Recent scheduled-buyer lines — all fail the exit test

| line | outsiders bought | completed a round trip | cut off by a pull | verdict |
|---|---|---|---|---|
| **ETH 1,852 B** (the +230%-on-paper line) | 11 | **0 (0%)** | 4+ (rest blocked, no pull) | honeypot — `minievm.py` showed the token's controller blocks the sell 1–2 blocks after a buy |
| **Base 2,180 B** (the 0.501 ETH timer, +97% on paper) | 10 | **0 (0%)** | 10 (100%) | the launcher pulls the pool on the outside buy |
| **BNB 4,050 B** (+313% on paper) | — | — | — | team-list token; outsider sells revert `Hush()` unless sent at gas price 0 (decoded in `REPORT_FOURCHAINS.md`). Its per-pool rotating shells defeat the 10%-crew heuristic, so `roundtrip.py` can't score it; the exit is settled separately. |

Every line with a big paper number is big *because* the exit is closed — the paper gain is what an outsider would make if they could sell,
and they can't.

## 2.433 positive control

To trust "nothing recent qualifies," the same test must flag 2.433 as tradeable on its own history. Running `roundtrip.py` on the 2.433 line
(RH POSM multicall, 1,444 B) over its live period (Oct 10). _[result pending — the run is in progress; this section fills in when it lands.]_

## Tools

- `roundtrip.py CHAIN DAY[,DAY...] TO SELECTOR LEN [TOKEN_LEN] [WIN]` — the exit test on one launch line, from on-chain round trips.
- `exitlab.py DUMP.json` — the same, over every line in a `buyerlab` DUMP at once (ranks lines by scheduled-buyer strength × outsider exit).
- `buyerlab.py` DUMP now also emits a per-swap `swaps` list (block, native, token, EOA) so `exitlab` can match round trips.

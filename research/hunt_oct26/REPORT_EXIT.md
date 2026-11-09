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

## 2.433 positive control — and a correction to the test

Running the same round-trip test on the 2.433 line over its peak (Oct 10, `rt2433.py`, 1,596 pools found by launch price):

```
fleet wallets (buy in 10%+ of pools): 5; pulled pools: 1467/1596
outsiders that bought: 3823
completed a round trip (sold before the pull): 1380 (36%)
cut off by a pull before selling: 1635 (43%)
round-trip return: median -2.6%, mean -5.3%, won 619/1380
```

**The crude test rejects 2.433 too.** Measured as "can any outsider who buys get back out at a profit," 2.433 looks no better than the
defended lines: 1,467 of its 1,596 pools were pulled, and the average outsider lost. So this metric is **wrong for the question** — it was
never true that a random buy-and-hold on a 2.433 pool was safe.

**What 2.433 actually was.** The seat was never buy-and-hold. It was a *timed front*: buy at launch + 2, **ahead of a specific scheduled
buyer**, and sell into that buyer's buy a few blocks later — out long before the pull at ~block +600. The edge was three things together:

1. a scheduled buyer of real size that reliably arrives (someone to sell into),
2. the sell at that moment **executes** — a plain v4 token, no transfer block, and
3. the pull comes *after* the scheduled buy, not before.

The 3,823 "outsiders" above are mostly not running that trade — they buy at random offsets and hold into the rug. The timed front, which
`buyerlab`'s front-paper models (in at max(launch+2, buy−5), out at the buy), was positive on 2.433; that is the number that mattered.

**So the right discriminator is whether the timed front's sell executes** — not general outsider survival. On that sharper test the recent
lines still fail, each for a definite reason:

| line | does the scheduled buy arrive when fronted? | does the sell execute at that moment? |
|---|---|---|
| 2.433 (Oct) | yes | **yes** — tradeable |
| ETH 1,852 B | yes | **no** — token blocks the sell 1–2 blocks after a buy |
| Base 2,180 B | **no** — the 0.2 buy doesn't come, launcher pulls | n/a |
| BNB 4,050 B | yes | **no** — sell reverts unless gas price 0 |
| RH crowds (5,274 B etc.) | **no** — they stop buying when fronted | n/a |

The conclusion is unchanged — no current line supports the 2.433 trade — but the reason is sharper than "outsiders can't round-trip": in
every recent line either the scheduled buyer refuses to arrive once an outsider is ahead of it, or the sell into it cannot be made.

**Caveat on `roundtrip.py`:** its all-outsiders round-trip rate is a weak screen (it rejects 2.433). Use it only to *exclude* honeypots and
pull-on-front lines (0% round-trip is decisive); a line that passes still needs the front-paper edge and a sell-at-exit check before it means
anything.

## Tools

- `roundtrip.py CHAIN DAY[,DAY...] TO SELECTOR LEN [TOKEN_LEN] [WIN]` — the exit test on one launch line, from on-chain round trips.
- `exitlab.py DUMP.json` — the same, over every line in a `buyerlab` DUMP at once (ranks lines by scheduled-buyer strength × outsider exit).
- `buyerlab.py` DUMP now also emits a per-swap `swaps` list (block, native, token, EOA) so `exitlab` can match round trips.

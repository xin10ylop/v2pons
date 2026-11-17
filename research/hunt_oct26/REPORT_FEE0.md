# The fee-0 line (Robinhood Chain), Nov 17

A launch line where buying behind the crowd and selling into its pump has paid since Oct 12, with nothing seen that blocks or punishes an
outside buyer. The engine for it is `src/fee0_engine.py` (RUNBOOK 4o). It is dry until the owner turns it live.

## The line

- **Pool:** a Uniswap v4 ETH/token pool with fee 0, tick spacing 60, no hook, and one fixed launch price
  (sqrtP 2505036234966386302045715536678303).
- **Launch:** a call `d27d1e00` to a launcher contract with code keccak `0xf554b29b…dceb4`. Each launcher is deployed fresh by its
  own wallet a few transactions before the launch. Over 3 days that was 24 wallets for 27 launches, mostly new (median nonce 11), and
  all 27 contracts had the same code: one operator rotating throwaway wallets (`opfee0.out`). The launch puts in about 5.2 ETH now
  (12-32 ETH in October), and all of it buys the token in the launch transaction itself.
- **The crowd:** 809 wallets buying through the Universal Router, 662 of them in 3 or more of the 27 pools. None of them appear in the
  2.433 operator's 3.0/5.0 ETH lines or in operator A's lines. It is not those fleets.
- **Its life:** the first crowd buy of 0.02 ETH or more lands at launch + 100-2160 blocks (median about 300-420). The price rises,
  then the crowd sells out. The launch wallet sells back 0-8.9 ETH within 6000 blocks.
- **No pulls:** no liquidity was pulled in any of the 968 launches since Oct 12 (`famhistory`). A round trip through the relay costs
  0.00% (fee 0), and every buy and sell carries the token's address (`fee0shape.py`).
- **Volume:** 0-69 launches a day (968 in 36 days). It comes in bursts: Nov 9-17 had 15, 22, 3, 8, 0, 1, 2, 21 and 3 (75 in 8 days),
  with gaps of up to 53 hours between launches. A quiet half day is normal and does not mean the line has stopped.

## The trade and its exit

Buy behind the first crowd buy of 0.02 ETH or more, then sell at +8%, at -5%, after 2000 blocks, or on a pull. All numbers below are
at 0.02 ETH a trade, net of gas, with our buy landing 2 blocks late and our sell 3 blocks late (`exitrules.py`, `exitlag.py`).

| window | trades | +8% / cap 2000 (no stop) | **+8% / -5% stop** | +8% / -10% stop |
|---|---|---|---|---|
| Oct 19-26 | 216 | -1.8% mean, 174 won | **+4.2%**, 140 won | +3.1% |
| Nov 14-17 | 25 | +4.6%, 21 won | **+4.6%**, 17 won | +5.8% |

**What the stop fixes:** without it, October's losers were mostly slow bleeds. The crowd cashed out over 1000-1900 blocks and the
take-profit never came. In 26 of the 32 losers the single worst sell made only 2-4% of the fall, and the launch wallet made only 6 of
the 32 (`dumpwho_oct19_26.out`). Nothing visible before the buy (launch size, trigger size or timing, early buyers) separates winners
from losers. The fix is the exit, not a filter.

**Latency** (stop -5%; the figures are blocks late for our buy / our sell):

| | 2 / 3 | 5 / 5 | 10 / 10 | 20 / 20 | 50 / 20 |
|---|---|---|---|---|---|
| Oct 19-26 | +4.2% | +5.0% | +5.9% | +1.0% | -3.0% |
| Nov 14-17 | +4.6% | +5.4% | +4.1% | +8.8% | +5.1% |

Up to about 10 blocks (1 s) late is fine. At 20 the October edge is nearly gone, so polling the RPC's logs works if the poll loop stays
fast.

## The engine

`src/fee0_engine.py`, run as the `flip-fee0` service with its own wallet and relay:

- **Reading the chain:** it polls the PoolManager's Initialize, Swap and ModifyLiquidity logs, one RPC round trip per poll. Prices come
  from each Swap event, so the crowd's sells are included.
- **Checks before any buy:** the launch transaction's target must carry the launcher code, and an eth_call round trip of the stake
  through the relay (state overrides: `contracts/RoundTripHarness.json`) must lose under 2%. This check repeats every 300 blocks, and a
  buy needs one younger than 600 blocks.
- **Limits:** one position at a time, 40 trades a day, a $10 daily stop. The engine halts itself if a sell fails twice or returns under
  half of what the price said. A position left by a stop or a crash is sold at the next live start.
- **Checked against the research:** the replay mode, over Nov 14-17 with landing 3 blocks late, booked +4.5% on 25 trades (17 won).
  The research replay gave +4.6% (17 won). With one position at a time and landing 6 blocks late: +4.4%.
- **Tests:** `tests/test_fee0_engine.py` (14 cases: arming, triggers, the three exits, the checks, live round trip, halts, recovery).

## Live dry run, Nov 17 (public RPC, 09:06-12:40 UTC)

Four launches, four paper trades at 0.002 ETH: +11.6%, -4.9%, +10.3%, -6.1% (mean +2.7%). The engine saw each trigger 1-4 blocks
late. The first trade, recomputed from the chain's own swap logs, matches the engine exactly. The -6.1% one hit +11.1%, but a 0.5 ETH
sell landed 7 blocks after the signal and before the paper sell (modeled at 8 blocks). A sell inside 6 blocks would have kept +11.1%.

**Verdict:** the line is real and safe to trade, but small. At $50 a trade it is worth about $10-20 a day (about 8 trades a day at
+3-4%). The owner judged that not worth running. Not deployed.

## Size (Nov 17, `earlyentry.py`)

Same entry and exit (+8% / -5% / cap 2000), our buy's own price impact included on the way in and out:

| stake | Oct 19-26 (206 trades) | Nov 13-17 (29 trades) |
|---|---|---|
| 0.1 ETH | +3.9%, 0.11 ETH/day | +5.9%, 0.04 ETH/day |
| 0.3 ETH | +3.8%, 0.33 ETH/day | +5.0%, 0.11 ETH/day |
| 1 ETH | +3.0%, 0.90 ETH/day | +3.8%, 0.28 ETH/day |

The backtest holds the crowd fixed, so a size is only credible while our buy keeps the price inside the range the crowd trades in by
itself. Our buy lifts the price by ((x + S) / x)^2, with x the pool's virtual ETH reserve at our entry: median 16 ETH in October, 5.9 now.

| | Oct: 0.5 ETH | Oct: 1 ETH | Nov: 0.3 ETH | Nov: 1 ETH |
|---|---|---|---|---|
| price lift | +6% | +13% | +10% | +37% |
| pools where the crowd went that high alone | 89% | 71% | 90% | 38% |
| crowd buying done at or above it (median) | 31% | 9% | 18% | 0% |

So the credible stake is about 5% of x: about 0.3 ETH now, and about 0.5-0.8 ETH at October's launch size. That is about 0.1 ETH a day
now and about 0.5 ETH a day in an October-like week. Buying ahead of the crowd (launch + 3 to + 100 blocks) loses about 1% a trade: the
crowd buys and sells about equally (gross buys 15-37 ETH per pool in 2000 blocks, net flow -1 to -3 ETH).

## Risks

- **The operator can change the line** (fee, launcher, price) at any time. The engine then simply stops arming.
- **The crowd can stop.** Then there are no triggers, and so no trades.
- **A slow week like Oct 19-26** without the stop lost money. The stop is what made it positive; a week of sharp crashes inside 3
  blocks would beat it.
- **Size:** about 5% of the pool's virtual ETH reserve (about 0.3 ETH now). A buyer that size has never traded this crowd, so how
  it reacts is unknown until live trades show it.

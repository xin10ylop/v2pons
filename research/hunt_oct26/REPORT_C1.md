# C-1, Robinhood: the ride, re-tested for going live (Nov 2)

**Asked:** find a line we can enter, search deeper; then "prepare going live".

**Answer:** operator **C-1** (Oct 11 name, `docs/HANDOFF.md` 16.x) is live, bigger than in October, and following its router paid on
paper every day of the last week: **+12.1% a trade on 811 pools, 4 pulled** (enter behind the router's first buy, sell when its router
has been quiet for 20 blocks). It is not the 2.433 operator. The engine already trades it as a "wave family"; it needed one new exit
(`quiet_blocks`, added with tests) and an updated config (no price pin). The plan below goes dry, then a $5 probe, then up.

## 1. How it was found: what the earlier sweeps could not see

Every earlier search started from **pools pulled within 2 h** and skipped pools launched with **0 native** (`nat_in > 0` in tape.py and
roundtrips.py). C-1 launches token-only, so it was invisible to all of them. `allfront.py` (new) reads every pool created on Robinhood
and Base, Oct 27 - Nov 2 (32,069 on Robinhood), and asks who bought in the first 30 s, sold later, and what bigger buy they sold into
(`allfront_rh_summary.out`). On Robinhood almost all of that money sold into **private routers**, each an operator's own contract that
holds ETH and funds a wallet crowd (`0xd6d35b56` holds 79 ETH; the public Universal Router holds 0):

| crowd operator | launch | its routers | pools pumped in 7 days | the ride (K2, quiet 20) |
|---|---|---|---|---|
| **C-1** | v4 PositionManager multicall `ac9650d8`, 2,276 B, 0 ETH | `0xd6d35b56` | 811 | **+12.1% a trade, 4 pulled, 7/7 days** |
| "v4-2020" | the same call, 2,020 B | `0x75379d5d`, `0xcbd412a8` (one code) | 71 | +132% a trade, 0 pulled, but 71 pools and uneven days |
| V3 crowd (Oct's v3crowd) | V3 PositionManager, 836 B | `0x7feb3ecb`, `0xaf9d6fa0`, `0xfc7241d4`, `0x80e49ed1` | 335 | +10.2% a trade, 4 pulled; outsiders' real buys pulled within 100 blocks 18% (4% base): more reactive than C-1 |

`0x204faca1` (a router that calls the PoolManager itself, `routerlab_rh_0x204faca1.out`) is a public-style router of 21,063 wallets, not
a crowd: following it loses about 9% a trade.

On Base the money was a launchpad (hook `0xbdf93814`, 1,891 pools): the creator's own bundled buy in the creation block, and for a
sniper a lottery: +174 ETH on paper at 0.1 a pool, **-4.6% a trade without its best 20 of 306 trades** (`snipelab_base_bdf9.out`). Not a line.

## 2. C-1 now (`c1lab.py`, `c1lab_rh.out`)

- **1,009 launches** with its fingerprint in 7 days; its router bought in **811** (about 116 a day), first buy a median **+140 blocks**
  after the launch (p10 +43, p90 +292), **93 buys and 12.5 ETH a pool** (31,806 ETH in the week: wash, funded in a loop, HANDOFF 16.x).
  855 of the 1,009 pools were pulled within 2 h, but a median **3,192 blocks after the router's first buy** (only 1.7% within 100).
- **The ride**, on the recorded reserves of every pool, our own buy kept in the pool until we sell, each pool's real swap fee:

| exit (entry: the router's first-buy block + 2, as the engine lands) | per trade | won | pulled | 0.01 ETH a trade, week | 0.1 ETH, week |
|---|---|---|---|---|---|
| **quiet 20**: sell when the router has not bought for 20 blocks (cap 100) | **+12.1%** | 636 / 811 | **4** | +0.98 ETH | +9.8 ETH |
| hold 100 blocks | +12.0% | 701 / 811 | 16 | +0.97 | +9.7 |
| hold 50 blocks | +6.2% | 587 / 811 | 0 | +0.50 | +5.0 |

  Every day positive (Oct 27 - Nov 2: +0.19, +0.19, +0.24, +0.09, +0.13, +0.11, +0.03 ETH at 0.01; Nov 2 is a part day). Landing a block
  earlier or later changes it by under a point. By fee tier: +9.4% (fee 0.01%), +15.0% (0.0125%).
- **Reaction to outsiders.** Real outside buys (0.001+): pulled within 100 blocks 5% against 2% for pools of the same age. In OUR slot
  (1-5 blocks after the router's first buy): **10 buys by 4 wallets, 3 pulled within 100 blocks**. Two of those were one wallet
  (`0xb410c684`, 0.012 ETH at router + 1, twice): in both pools the router **stopped buying** (last buys at + 43 and + 8), then the pull came
  32 and 49 blocks later; the quiet-20 exit was out first both times (+ 64 and + 29, against pulls at + 75 and + 57). When C-1 reacts it stops
  its router first, which is exactly what the exit watches. The disciplined outsider `0xfc246d79` (0.03-0.05 ETH at router + 3, 5 pools)
  got out of all 5. The sample is small; the probe exists to measure it on us.

## 3. Live check, Nov 2 17:00-19:00 UTC

- 19 launches in the last hour; the router bought 85 ETH in 10 of the 11 classic launches in two hours.
- **The trigger decodes exactly as configured in October:** router `0xd6d35b56`, selector `e6cb474f`, 484-byte value-0 calls; in **404
  of 404** buys word 7 = 0, word 2 = the ETH, word 8 = the token; its sells carry a non-zero word 7.
- **The launch shape moved:** the 2,276-byte call now also launches WETH pools at fee 1% and hooked WETH pools at fee 0.01% (other
  launchers on the same template): **C-1's router buys only in the classic shape** (fee 100, tick spacing 1, native ETH, no hook), which
  the engine's own decoder reads (same pool id as the chain) and accepts; the others it refuses ("not an ETH pair without a hook"). The
  classic launches' price and liquidity now vary, so the October pin would skip most of them: **`"pin": false`**.

## 4. Not the 2.433 operator

Router code 10% similar to `0x1cbaf24d` (7 of 107 constants shared, the ERC20 ones); tokens of 3,854 / 4,844 bytes without the 2.433
developer's selector `3c130d90`; its own money loop (hub `0xbae53801`, multisend `0xf341c935`); no allowlist. Nothing links the two.

## 5. The engine (`src/flip_engine.py`, tests 20f2)

- New family key **`quiet_blocks`** (a v4 wave family only, under `hold_blocks`): once our buy is in, the sell goes when the feed shows
  `quiet_blocks` blocks with no buy through the operator's router since its last (the trigger counts; a router buy behind ours restarts
  the count; its sells do not). `hold_blocks` stays the cap. Logged as `sell_why` "quiet: ...". All 2,700 lines of tests pass.
- `take_profit` is a fraction (9 = +900% = off), as October's c1 had it: keep 9.
- The stake cap `FRONT_STAKE_CAP_ETH` is 0.012 ETH (sized for the 2.433 bot's room). Enough for the probe and the first step; going above
  it is a code change for later.

## 6. Going live: the gates (RUNBOOK 4n)

1. **Dry, 24 h and at least 100 triggers** (`dry_run` true): recognised C-1 launches with a router buy 90% or more of the chain's count for
   the same hours; dry mean +6% or better (half the paper); dry exits after the pull 3% or fewer.
2. **Live probe at 0.002 ETH ($5), 50 trades**, its own halt file `HALTED.front.c1`, `nonbot_halt` 0 (C-1's flat trades are normal):
   mean +4% or better, pulled before our sell 5% or fewer, and **no sign of a reaction to us**: our pools pulled within 100 blocks of our buy
   no more than twice the 1.7% base. Any pull before our sell in the first 10 trades: stop and look.
3. **Then 0.006, then 0.012 ETH** (the cap), a step a day while the live mean holds.

Risks: the 2.433 operator closed its gap after being fronted for days, so C-1 may react once it sees one wallet in every pool; the
in-slot evidence is 10 outside buys; the October live probe's result is not recorded in the repo.

## Files

New: `allfront.py`, `c1lab.py` (with FP= and ROUTERS= for any crowd operator), `routerlab.py` (for routers that call the PoolManager
themselves), `snipelab.py`. Outputs: `allfront_rh_*.out`, `allfront_base_*.out`, `allfront_rh_summary.out`, `c1lab_rh.out`,
`crowd_v4_2020.out`, `crowd_v3_836.out`, `snipelab_base_bdf9.out`.

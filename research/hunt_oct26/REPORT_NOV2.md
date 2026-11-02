# Is anyone back? Robinhood, Base and Solana, Oct 27 - Nov 2

**Asked (Nov 2):** is the operator back, maybe under different wallets, and has a similar line appeared on Robinhood or Base?

**Answer: no.** The 2.433 operator is not back on Robinhood or Base under any wallet: not its token, not its bot contract, not its
launch shape. A new line did appear on Robinhood (an 11 ETH hooked line from the same developer's token family), but its hook taxes sells
and there is no bot buy to sell into, so it is not a seat. Base has no new line at all. The Solana 29giReft funder has been idle since
Oct 26. A pool-level Solana search could not run from here (below).

## What was read

| chain | window | pulled pools (0.5+ native) | how |
|---|---|---|---|
| Robinhood | Oct 27 00:00 - Nov 2 11:17 UTC | 6,310 | `census.py` / `roundtrips.py` / `front.py` per day (`run_days.py`, `run_front.py`), `verdicts.py` |
| Base | the same | 3,173 | the same |

Three independent tests for the operator under other wallets:

1. **Its token** (`bytecode.py`, `bytecode_deep_rh.out`, `bytecode_deep_base.out`): every pulled pool's token against the 2.433 token's
   code (1,526 B, byte-identical everywhere it ran). **0 exact matches on either chain.** The family matches (the developer's selector
   `3c130d90`) are known lines: operator A's 1,770 B tokens (51 pools), the tick-spacing-1 line's 2,857 B (3), Base's fee-0 volume bot's
   1,627 B (24 pool groups), and one new 7,196 B template (below).
2. **Its bot contract** (`earlybuyers.py`, new; `earlybuyers_rh.out`, `earlybuyers_base.out`): every transaction that swapped in a pulled
   pool within 40 blocks (Robinhood) / 10 blocks (Base) of its launch, by the contract it called, matched against the 2.433 bot's code
   (Robinhood `0x1cbaf24d`, Base `0x987d5db8`) and its buy/pull selectors (`c1120e3d`, `27f7e6ee`, `a0f7978d`).
   - Robinhood: 17,380 early transactions. `0x1cbaf24d` bought early in 1,268 pools, **all of them the volume bot's 3 / 5 ETH fee-1% shape**
     (1,034 + 234): the router still carries that line, nothing in a 2.43-style shape. No other contract carries its code or selectors.
   - Base: 9,238 early transactions; **no contract with its code or selectors**.
3. **Its launch fingerprints** (`research/chase/watch2433.py`): no fee-5000 / tick-100 pools on Base or BNB, its wallets unmoved on
   Robinhood, Base and Ethereum for 48 h, its keys silent on 23 more chains (Oct 31). On BNB it still runs its closed line
   (`REPORT_OCT23_SWEEP.md`, Oct 28 update) and its parked BNB was bridged out on Oct 24.

## New lines since Oct 26

`verdicts_rh_nov2.out`, `verdicts_base_nov2.out` (all days since Aug; lines active since Oct 26 below).

**Robinhood**

| line | pools | verdict | note |
|---|---|---|---|
| v4 fee 3000 ts 60 via PositionManager | 157 (Aug 16 - Oct 27) | CLOSED | the fleet skipped 58 of 65 pools someone bought ahead of |
| v4 fee 75 ts 1 | 72 (Aug 13 - Oct 30) | CLOSED | fleet skipped 11 of 18 fronted pools |
| v4 fee 500 ts 10 | 13 (Oct 30) | CLOSED | 5 real outside buys rugged |
| v4 fee 1 ts 1, 4 ETH | 16 (Oct 31) | untested | a 470-wallet fleet, fresh nonce-5/6 launchers, router `0x33675123`: the tick-spacing-1 trap's machinery (488 wallets, 4 ETH) on a new fee tier |
| **11 ETH hooked, 7,196 B token** | 6 (Oct 27 - Nov 1) | not a seat | below |
| operator A, fee 2000 | 20 (Oct 29 - Nov 1) | CLOSED | 400 outside buys sold, 8 rugged, but its fleet skipped all 8 fronted pools (the old "follow" situation) |

**The 11 ETH hooked line.** Fee 10000 / ts 200 (Oct 27, 29) and fee 100 / ts 1 (Nov 1), 11.0 ETH each, a fresh launcher (nonce 5-7) per
pool, a per-pool 2,022 B hook whose address flags are beforeSwap, afterSwap and both swap return-deltas (it can rewrite any swap's
amounts). Lives 2-81 min. A ring of about 48 recurring wallets (1,600-3,600 transactions each) buys 0.07-0.12 ETH every ~400 blocks
(~40 s) through the Universal Router and sells back later at a loss of 2-75% (e.g. 0.0854 ETH in, 0.0215 out 16 blocks later): the
hook's sell tax. Across the six pools the non-launch wallets put in 0.17-8.6 ETH and took out 30-60% of it. The first fleet buy lands
anywhere from +66 to +614 blocks. No fixed bot buy to sell into, and a sell-taxing hook: the "never trade a pool whose exit test
fails" rule applies. Not a seat.

**Base:** no new line. Every line active since Oct 26 is documented: the 0.5013 ETH timer line (TRAP, 1,035 pools), the V2 crew's tiers
1.2 / 1.5 / 1.6 / 15 ETH (CLOSED / TRAP / untested), the 1.2 ETH fee-0 volume trap (TRAP).

## Solana

- The **29giReft** funder (`29giReftu9BmqqQhLzHUSzVyNmg8ifJNFeBMWjPPmZ4h`): last transaction **Oct 26 14:57 UTC**, **55.6 SOL** parked.
  Its two fleet wallets and its last launcher are emptied to 0.001 SOL, untouched since Oct 26. Its last three cycles (SOL to the launcher
  vs back): Oct 21 11 -> 16.71 (+5.71), Oct 22 21 -> 22.84 (+1.84), Oct 26 11 -> 10.79 (-0.21, an 11-minute pool nobody bought).
- **Not done: the search for the same pattern under new wallets.** It needs every Raydium creation of the period (987 CPMM in 9 days)
  parsed, and this environment has no `HELIUS_API_KEY`. The public endpoints refuse it: api.mainnet-beta throttles `getTransaction`
  (429), publicnode answers in bursts and then refuses (403) for minutes at a time. `research/solana/solsize.py` (new) is the
  low-cost version (one lookup per creation, profiles only for 5-30 SOL pools, waits out refusals); with a Helius key it runs as is,
  and `census.py` / `linescan.py` / `funderwatch.py` do the full search.

## Files

New: `earlybuyers.py`, `research/solana/solsize.py`. Outputs: `earlybuyers_rh.out`, `earlybuyers_base.out`, `bytecode_deep_rh.out`,
`bytecode_deep_base.out`, `verdicts_rh_nov2.out`, `verdicts_base_nov2.out`. The day files (`out/rh_YYYYMMDD_00.json` etc.) stay in
`out/` (gitignored).

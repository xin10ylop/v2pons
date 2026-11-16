# A live lead: operator A's 1,380 B line, by liquidity tier (Nov 16)

**Asked:** anything back, not exactly 2.433 but similar, that we can make money with.

## 2.433

Still not back: no launches with its signature from Nov 7 to Nov 15 12:40 UTC; its router has not traded. Its operator's 3.0 ETH trap
family is the only one still running.

## The screen (`linescan.py`)

Every line in a `buyerlab` dump, Robinhood and Base, Nov 10-11 and Nov 14-15 (~17,400 pools), screened for what makes money: with crowd =
any wallet buying in 3+ pools and outsiders = one-off wallets, how often a pool is pulled within 5 s of an outsider's buy, how much crowd
money still comes in after it, and whether outsiders got out. Burn/blacklist lines pass the pull test but show 0% exit, so exit decides.

- C-1 (`5fcfacb98bd0`) and the V3 crowd (`19e3e2a65bec` on V3) do not pull, but 0% of outsiders got out (C-1 burns; the V3 crowd stopped on
  our live buy).
- The 1,764 B token (`19e3e2a65bec` on v4) makes an external call and carries the ETH 1,852 B honeypot's error set: treated as a honeypot.
- The 5,274 B line (12 ETH crowd, fee 1%) pulls within 5 s on every outsider.
- Base: nothing with an outsider-first pool and a crowd to sell into.

## The lead: PositionManager `modifyLiquidities`, 1,380 B, 4,655 B tokens

Operator A's other scheme (several crowds taking turns), 232 pools over the four days (~58 a day):

- **The token is clean**: a standard OpenZeppelin ERC-20 (with increase/decreaseAllowance), no external calls, no gas-price / coinbase /
  time checks, no owner functions. Plain v4 pools, no hook, fee 0 (1-2 millionths).
- **The crowd brings net money**: per pool in the first 10 minutes, ~7.8 ETH of crowd buys against ~3.0 ETH of crowd sells.
- **Outsiders got out, at a profit, on-chain** (`full1380_nov.out`, the 8 pools with a one-off outsider followed for 4 hours): the four
  who bought before the crowd made +25%, +153%, +323% and +814%; three late buyers made −29% to +5%. None of the 8 pools was pulled within
  2 hours (one at ~3.5 h).

**The operator launches at fixed liquidity tiers, and the tier decides the pull** (`wave1380_tiers.out`):

| starting liquidity | pools | clean pools pulled within 2 h | outsider pools pulled | paper: in at launch + 5, out at +300 / +600 blocks (0.05 ETH) |
|---|---|---|---|---|
| **2.2 ETH** | 3 | 0 of 1 | 0 of 2 | +48% / **+255%**, won 3/3, 0 pulled |
| 3.0 ETH | 27 | 27 of 27 (median ~14 min) | — | +12% / +43%, won 24/27, 3 pulled |
| **3.3 ETH** | 7 | 0 of 4 | 0 of 3 | **+564%** / +477%, won 7/7, 0 pulled |
| 4.4 ETH | 51 | 49 of 50 (median ~4 min) | 0 of 1 | +1% / +34%, won 41/51, 10 pulled |
| 5.6 ETH | 132 | 132 of 132 (median ~9.5 min) | — | +2% / +19%, won 118/132, 14 pulled |
| 12.2 ETH | 6 | 3 of 4 | 0 of 2 | +13% / +59%, won 6/6 |

- **Keep tiers (2.2, 3.3 ETH)**: never pulled, with or without an outsider; most profitable outsiders were here. This looks like selection
  (snipers pick the tiers that live), not a reaction. The tier is visible at launch (the pool's starting liquidity), so a trade can choose it.
- **Rug tiers (3.0, 4.4, 5.6 ETH)**: pulled almost always; nearly no outsider ever bought early, so how they react to one is **unknown**.

## What is not known yet

- How the operator reacts to a buy at launch + 5. The earliest real outsider here bought at +147. On its other launcher (`0x3194e326`)
  operator A pulls ~1 s after an outsider.
- The keep-tier sample is small: 10 pools in four days (~2.5 a day).
- Paper is not live: C-1 and the V3 crowd also looked good on paper and turned on our own buys.

## Tools

- `wave1380.py DUMPS DAYS` — the early-in trade replayed on the recorded swaps with our trade in the pool.
- `react1380.py DUMPS DAYS` — the line's reaction to one-off outsiders.
- `full1380.py` — the outsider pools followed for 4 hours: every outsider's trades and return, and the pulls.
- `linescan.py DUMP SEC_PER_BLOCK` — every line screened for the outsider's way out.

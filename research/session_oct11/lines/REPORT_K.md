# K: the bonding-curve launchpad 0x7ed598bc (Robinhood Chain), Oct 11 2026

This is read-only research. The data came from the public RPC only: about 600 sequential POSTs, with the 429 answers backed off. The census
cache was read offline. Window: creates from block 79,984,897 (Oct 4 13:52 UTC) to head 86,027,283. Replays need a full 3,000-block window
after each create, so they use the 17,919 ETH-quoted curves created up to head - 3,100 (7.17 days). Code is in `code/` and outputs are in
`out/`. `data/` holds the raw logs: `trades.jsonl` has 1.11 M curve events and `packed.pkl` is the packed copy. USD figures use $2,570/ETH.

## 1. What the venue is

- **Factory** `0x7ed598bc…` (24,177 bytes) is owned by `0x263ed295…`, which also owns the launch router `0xe33e9e47…`.
  - Each create deploys a fresh token (3,248 bytes, 1e9 supply minted to the curve) and a fresh curve contract (10,229 bytes; it is not a clone).
  - The create fee is 0.0005 ETH, paid to the collector `0x31ea5b45…`.
  - The create event is `TokenLaunched(token, curve, creator, quote, 0, threshold)`, topic 0x8d4aad49 (the name matched by keccak).
  - Since the census start there were 21,177 creates: 17,927 quoted in ETH, 893 in USDG and 2,357 in other tokens.
  - Entry points of the 200 most recent creates: the router's `f85f8e41` (create plus a creator buy) 151, factory `a72101af` 27, factory `f35abbcf` 15.
  - No front-end name appears on chain. The metadata is IPFS plus the projects' own sites.
- **Curve math:** x·y = k, with x = 1.68 ETH virtual + real ETH and y0 = 1e9 tokens.
  - The fee is 1% of the ETH side, on buys and on sells.
  - On top comes a **per-curve creator fee**, the Buy/Sell 4th word, constant within a curve on all 14,890 curves with 2+ trades. Rates: 200 bps 5,038 curves, 0 bps 2,864, 100 bps 1,890, 300 bps 1,414, … up to 1,000 bps.
  - The model reproduces 720,835 curve trades exactly (median error 0; 0.35% off by more than 1e-9). eth_call buys at the head match it to the wei.
  - Curve calls: `buy(uint256 ethIn, uint256 minOut, address to)` is `0x59a87bc1`, payable, about 100k gas. `sell(uint256 tokens, uint256 minOut, address to)` is `0xd04c6983`, about 76k gas.
  - Gas is about 0.0000036 ETH for a round trip.
- **Anti-snipe surcharge** (event 0x3bc39a55). Measured on 789 exact block timestamps:
  - same second as the create: 88-96% (4 buys);
  - second 1: 6.18% (132 buys);
  - second 2: 0.19% (171 buys);
  - second 3 and later: 0.
  - **Wallets named in the create tx (event 0xe4b7e48f, the creator's allowlist) are exempt.** In blocks 1-10, 8,524 listed buys paid nothing, 1 paid; 8,013 unlisted buys all paid.
- **Selling:** a holder can sell at any time. There is no lock and no window, and transfers are free (eth_call). The sell needs `approve(curve)`: without an allowance it reverts with ERC20InsufficientAllowance.
- **Graduation** happens when real ETH reaches 4.2 ETH, i.e. 714.3 M tokens sold.
  - Mostly in the same tx as the filling buy (blocks from full to migration: p50 0, p90 47).
  - 4.2 ETH and 204.08 M tokens go into a v4 ETH pool: fee 0, tick spacing 200, hook `0xe5e70264`, one full-range position, no adds or pulls in 3,000 blocks (143 of 144). 81.63 M tokens are burned.
  - The price is continuous: 2.058e-8 ETH per token on both sides.
  - The hook takes 1% plus the same creator fee on every swap's output.
- **Graduation count:** 120 of 17,919 ETH curves graduated (0.67%, about 17 a day).
  - Time from create to graduation (blocks): p10 40, p25 634, p50 5,023, p75 72,986, p90 686,344 (4 s to 19.6 h).
  - The census's "918 graduated" counted third-party pools: 156 tokens created in the window graduated.
  - Price after migration, as price / p0 (median, mean): +1 block 1.060, 1.52; +10 blocks 1.029, 1.48; +300 blocks 0.990, 1.50; +3,000 blocks 0.900, 1.56.

## 2. Flow

All 17,919 curves, first 3,000 blocks:

- Buys: median 3, mean 12.3. Buy ETH: median 0.047, mean 0.389. Wallets: median 3.
- 73% of creators buy in the create tx (median 0.031 ETH); 3.2% buy later; 32% sell.
- 36% of creates list wallets besides the creator; 39% are sniped.
- Graduated: 53 within the window, 120 ever.

The 200 most recent (Oct 11):

- 142 had trades. 2,551 buys (86.6 ETH) and 1,818 sells.
- 1,160 buyer EOAs: 248 in at least 2 curves, 64 in at least 5, none in 20 or more.
- The creators' EOAs made 159 buys (12.9 ETH). 1 curve graduated.

## 3. Replays

Exact curve math with our trade inserted; others' trades re-applied; fees, creator fee, surcharge and gas included; a drain is the realised loss.

| line | n | mean | median | win | worst | $/day |
|---|---|---|---|---|---|---|
| (a) snipe at +1/+2 blocks (surcharge) | 17,900 | -96% | -96% | 0 | | |
| (a) at ≥3 s (40 blocks), hold 300, all | 17,896 | -3.6% | -6.0% | 15% | -89% | -1,333 |
| (a) same, creator fee ≤1% | 5,021 | -0.6% | -2.3% | 22% | -89% | -62 |
| (a) same + ≥0.2 ETH crowd by 40 blocks | 220 | -1.0% | -6.0% | 31% | -70% | -5 |
| (b) curve crosses 3.9 ETH, buy +2, sell v4 at migration +2 | 81 | -0.6% | +5.4% | 73% | -92% | -1 |
| (b) crosses 3.5 ETH | 182 | -12.3% | -2.8% | 45% | -90% | -46 |
| (c) v4 buy at migration +1, hold 10 | 120 | -8.4% | -7.5% | 21% | -94% | -21 |
| (d) the top creators' curves, follow at 40 / hold 300 | 17-155 each | -10.3% to +6.0% | | | | |
| (d) copy the top-5 direct bots (picked on Oct 4-7), buy +1, hold ≤300, tested on Oct 8-11 | 1,095 | +2.5% | -2.5% | 43% | -90% | +116 at 0.0058; +39 at 0.002 |

Notes on the table:

- All rows are at 0.0058 ETH. The 0.002 ETH stake gives the same returns.
- (b): 49 of the 130 curves that crossed 3.9 ETH graduated before our +2 entry.
- (d) copy line, by day: +3.4%, +4.1%, 0.0%, +0.8%. With the buy at +2 blocks it is negative on Oct 10 and 11.
- The largest direct trader `0x9689992f` made +60.6 ETH on 486 ETH (marked to market) over 1,764 curves. Copying it loses (-1.7% to -6.3%).

## 4. Risks and what trading here would need

**Risks:**

- the surcharge (a buy in the create's second loses about 90%);
- allowlisted creator wallets that buy free and dump;
- creator fees of up to 10% each way;
- 99.3% of curves never graduate;
- after migration, the median price fades to 0.90 by +3,000 blocks;
- many bots (136 wallets with 20 or more buys inside 40 blocks).

**What the engine would need:**

- a decoder for creates (router `f85f8e41` and factory `a72101af`/`f35abbcf`). The curve address only appears in the receipt logs; deriving it was not checked.
- entry timing from block timestamps;
- the creator fee and the allowlist, read from the create;
- direct `buy` and `approve` + `sell` from our wallet;
- for after graduation, a v4 swap through the hook's PoolKey.

That is roughly 1-2 days of work. Nothing is worth building now: the only positive line (d-copy) is tail-driven (median -2.5%) and fading. If anything, run it as a 48 h forward test from the chain.

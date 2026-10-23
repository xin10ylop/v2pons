# Behavioural sweep: every pump-and-pull line on 28 chains (Oct 23)

Asked, after the 2.433 re-trace came up empty: am I searching the right way — a line like 2.433 can't be a one-time thing, there must be others.

The earlier search was too narrow (Uniswap v4 only, fixed launch amounts only). This one searches by **behaviour**: `rugcensus.py` finds every native-paired pool, on any venue (Uniswap v4, any V2 fork, any V3 fork), created and then emptied by its own liquidity within 2 hours, on 28 chains, then groups the pulls into lines by shape and launch size and by the launcher/router they went through. It has no fingerprint built in. Proof it works: on Robinhood and Base it re-finds every line we already knew without being told their shape.

## Result: no new line that accepts a real outside buy

| chain | pools created / 24 h | pulled < 2 h | lines found |
|---|---|---|---|
| BNB | 9,975 | 1,503 | PancakeSwap V2 operators (6.17 / 17.6 / 58 BNB); all react to dust |
| Base | 4,630 | 1,091 | the three we knew: V2 operator tiers, the 0.5013 ETH timer line, the 1.20 ETH volume bot |
| Ethereum | 362 (24 h), 2,810 (7 d) | 75 / 694 | the 0.4-0.6 ETH V2 line (new); tolerates only ~0.002 ETH dust |
| Robinhood | 5,798 | 1,785 | the volume bot (3/5 ETH), the V2 operator (1/40/50 ETH), operator A |
| Polygon, Ink | 29 / 17 | 3 / 1 | one-off rugs, no line |
| Arbitrum, Optimism, Avalanche, Sei, Monad | 1-68 | 0 | new pools, none pulled in 2 h |
| Linea, Sonic, Unichain, Blast, Zora, Berachain, Abstract, Plasma, Mantle, Katana, Scroll, Mode, Celo, Soneium, World Chain | 0 | 0 | the chain creates ~no native pools (RPCs checked directly) |
| HyperEVM | — | — | RPC rate-limited; the operator's router there has never launched |

Every line found has the same front-seat detector: an outside buy of any real size is followed by the pull within a few seconds. The amount, venue and chain differ; the reaction does not.

### Ethereum mainnet, 0.4-0.6 ETH on Uniswap V2 (the one the narrow search missed)

- ~345 pools in 7 days (~50/day), each from a fresh wallet through the standard V2 router `0x7a250d56`. Sizes 0.4, 0.5, 0.6 ETH.
- A 21-wallet fleet buys ~0.015 ETH every 2-3 blocks (~0.33 ETH total, price to ~2.7x), then the pull at a median ~17 min.
- Outsiders (21 cases, 7-day 0.5 ETH set): dust ≤0.002 ETH mostly ignored; every buy ≥0.004 ETH after the fleet's first buy was pulled on within 1-3 blocks (8 of 8); a buy before the fleet's first is pulled on in 2 blocks.
- A seat is capped at ~0.002 ETH (~$5). Paper ceiling ~$150-250/day gross over ~50 pools, well below that after misses. One 0.0166 ETH buy at +2 was tolerated — a single case, unproven.
- Gas now 0.15 gwei (~$0.06/swap), so the line is tradable cheaply; it is just small.

### BNB, the 6.17 BNB PancakeSwap V2 line

- 274 pools/24 h, ~$4,000 each, fleet of 100+ wallets. Every outside buy in the sample was dust (0.0001-0.0005 BNB) and the pull came 8-16 blocks (4-7 s) after it. No real buy tolerated.
- The v4 pulls through the 2.433 operator's old BNB PositionManager `0x7a4a5c91` are tiny 0.003 BNB pools from others sharing that contract, not the operator's 10.5 BNB line restarting. The watch stays quiet.

## Standing conclusion

Across all 28 chains, nothing has been shown to accept a real-sized outside buy the way the 2.433 operator did on Base when our engine earned. The only exception is the Solana 29giReft line (REPORT_SOLANA.md): its pools let outside buys of 0.01-0.8 SOL ride without a fast pull. It is thin (~9 pools/week) and its Oct 22 pool shrank the fleet's buys. Every number here is paper until one small live test; the cheapest honest test is Solana at 0.1 SOL (~$10).

## Tools

- `rugcensus.py HOURS OUT [CHAIN...]`: the behavioural census above.
- `rugline.py RUGS CHAIN SHAPE SIZE OUT [N]`: one line's pools, fleet vs outsiders, and how soon the pull follows an outside buy.

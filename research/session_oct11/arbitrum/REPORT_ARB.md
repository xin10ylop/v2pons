# Arbitrum One: the discovery method's first step (the scout), Oct 11 19:13-19:30 UTC

Verdict: not a target now. Token-launch activity on Arbitrum One's Uniswap venues is close to zero (about 15 quote-paired v4 launches a
day, 6 of 104 ever bought in 7 days; V3 about 4 a day; V2 about 1; Sushi and Camelot negligible or dormant), so the census and the grid
(the workflow's later phases) did not run: there is nothing to group. The one busy v4 launcher (474 launches in 7 days) creates
token/token pairs at a 90% fee with no swaps: not frontable.

What was established (scout_result.json; scripts in scout/):
- Endpoints: arb1.arbitrum.io/rpc is the only public endpoint fit for a census (>= 5 req/s, 50-item batches, address-filtered eth_getLogs
  over very large ranges, chunk Swap queries at <= 50k blocks); publicnode needs a token for historical logs (10k-block cap); drpc 10k cap
  and batch <= 3; llamarpc, 1rpc, ankr unusable. Head 513,904,384 at 19:12 UTC, 3.65 blocks/s; ETH/USD 2,532.85 from Chainlink on-chain.
- The sequencer feed wss://arb1-feed.arbitrum.io/feed answers (handshake 0.45 s, deflate) with the same Nitro broadcast protocol our reader
  speaks (kind-3 batches, l2Msg base64): the engine would read it as is (FEED_URL, FEED_COMPRESSION=deflate), on Arbitrum's published terms.
- Uniswap v4 on Arbitrum: PoolManager 0x360e68faccca8ca495c1b759fd9eee466db9fb32, PositionManager 0xd88f38f930b7952f2db2432cb002e7abbf3dd869,
  UniversalRouter 0xa51afafe..., StateView 0x76fd297e...; the PositionManager and PoolManager bytecode is the same template as Robinhood's
  (identical PUSH32-masked hash and opcode skeleton; only the baked-in addresses differ), so `decode_launch` would work unchanged. All v4
  PositionManager launches there carry msg.value 0 (WETH, not native ETH): a value-keyed family cannot occur; the volume bot's signatures
  (its 1,444-byte native-ETH launch, its router selector c1120e3d, code at 0x1cbaf24d) were not seen.

| venue | launches 24 h | 7 days | census | notes |
|---|---|---|---|---|
| Uniswap v4 (PoolManager 0x360e68) | 11 | 104 | no | Counts are quote-paired launches (exactly one side ETH/WETH/USDC/USDC.e/USDT): 104/7d (~15/day), 11 in last 24h (ETH 1, USDT 5, USDC 4, USDC.e 1). Of  |
| v4 90%-fee token/token batch launcher | 0 | 474 | no | This is the bulk of v4 Initialize volume (~68/day) but it is NOT frontable: token/token pairs (no quote asset to buy with), 90% fee, and the first 6 p |
| Uniswap V3 (factory 0x1F98431c) | 1 | 26 | no | ~4/day. Standard Uniswap V3 factory, init-code-hash path reusable from scanner2/analysis/C. Too low to census. |
| Uniswap V2 (factory 0xf1D7CC64) | 0 | 7 | no | ~1/day. Negligible. |
| SushiSwap V2 (factory 0xc35dAdB6) | 1 | 11 | no | ~1.5/day. Negligible. |
| SushiSwap V3 (factory 0x1af415a1) | 0 | 2 | no | Negligible. |
| Camelot V2 (factory 0x6EcCab42) | 0 | 0 | no | Live historically but dormant for new-pair creation in this window. |
| Camelot V3 / Algebra (factory 0x1a3c9B1d) | 0 | 0 | no | No pool creations observed at this factory; Camelot V3 may route creation through another deployer, but new-pool activity is in any case far below the |

Conclusion: Arbitrum One's launch activity has moved off its Uniswap venues; the method found nothing to work on. The port would be cheap
(the feed and the decoders carry over) but there is no line to port it for. Next: the other-chains survey (research/session_oct11/chains/).

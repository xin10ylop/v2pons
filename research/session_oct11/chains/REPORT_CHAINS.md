# Other EVM chains for the launch census (survey hand-back, Oct 11 ~19:40 UTC; scripts/ and out/ here, out/final_table.txt first)

Only Base and BNB have real launch flow. Every other chain with a public pre-confirmation stream had 0-14 new pools a day that drew almost no
trades. No chain combines what Robinhood Chain had: first-come sequencer ordering, a stream we may read on its operator's terms, and launch
flow with operator bots that leave room.

| chain | ordering | pre-confirmation stream, terms | launches/day by venue | recurring first buyer | wallets in the first 3 blocks (traded launches) | block | gas/swap |
|---|---|---|---|---|---|---|---|
| Base | priority fee within each 200 ms flashblock | wss://mainnet.flashblocks.base.org/ws; the FAQ says it is "reserved for infrastructure-to-node data syncing... Applications should not connect"; deprecation planned (Denim) | v4 10,394 (Zora hook 4,161, hook 0x87a4 1,859, Doppler 591, no hook 329, Clanker 202); V2 532; V3 106; Slipstream-type 85; Aerodrome 13; an unknown V2 factory 1,044 (0 of 20 traded) | EOA 0x8fde9156 via the Universal Router first in 11/20 traded Doppler launches (median offset 1.5 blocks); three EOAs each in 13/20 hookless v4 launches; contract 0x6131b5fa in 3/9 Clanker launches | Doppler median 1, others 0, max 3 | 2.0 s | $0.0023 |
| BNB | public mempool plus builders (BEP-322) | none | four.meme ~3,330; PancakeSwap V2 ~6,000; Uniswap v4 ~315-394; Pancake Infinity ~197; Pancake V3 ~99; Uniswap V3 ~20 (from 1.22 h) | contract 0xb300000b in 8/16 traded four.meme launches | median 0 | 0.45 s | $0.0058 |
| Unichain | TEE builder, priority fee, revert protection | wss://mainnet-flashblocks.unichain.org/ws, 200 ms, no terms stated | v4: 2 | none | 0 | 1.0 s | $0.0002 |
| OP Mainnet | priority-fee auction | wss://op-mainnet-fb-ws-pub.optimism.io/ws, 250 ms, "strictly rate-limited" | v4: 14 (0 traded) | none | - | 2.0 s | <$0.0001 |
| Ink | not documented | subblocks wss://subblocks.inkonchain.com/ws ~200 ms, no terms | v4: 517 (485 hookless from one deployer, 2 traded within 1 h) | none | max 3 | 1.0 s | $0.0008 |
| World Chain | priority fee + PBH | flashblocks, no public endpoint documented | 0 in 6 h | | | 2.0 s | $0.0002 |
| Soneium / Mode | OP default | none documented | 2 / 0 | | | 2.0 s | ~$0 |
| MegaETH | single sequencer, policy not documented | eth_subscribe miniBlocks on wss://mainnet.megaeth.com/ws ~10 ms; 5 connections/IP, 5 msg/s | 0 (despite ~218 swaps/h) | | | 1.0 s | $0.0004 |
| Monad | leader orders by priority fee | monadNewHeads at the Proposed stage | Uniswap v4 ~24 (1 h); nad.fun 0 | | | 0.3 s | 0.015 MON |
| ApeChain / Xai / Reya (Orbit) | first-come (Nitro default) | the standard Nitro feed exists but URLs only in node configs / provider dashboards; no terms | 0 / 0 / 0 | | | 1.0 / 1.84 / 0.5 s | |

Unreachable from here: Degen, Sanko, Proof of Play Apex, RARI, Superposition. No stream, not sampled: Polygon, Avalanche, Sonic, Berachain,
HyperEVM. Arbitrum One has replaced Timeboost with priority-fee ordering (125 ms rounds in 250 ms blocks) and sells a paid "Fast Feed".
Gas excludes the L2 L1-data fee; BNB per-day figures are extrapolated from 1.22 h; the websocket streams were documented, not connected to.

What this means for us: Base has the flow but its stream's terms exclude applications and its ordering is a priority-fee auction already
contested by a sniper at offset 1-2; BNB has the largest launch volume but no pre-confirmation stream (a census there would be about
follow-type lines after a visible scheduled buy, e.g. the four.meme bot contract 0xb300000b, not about a race); Ink is the structural analog
but has ~2 traded launches a day. Robinhood Chain remains the only place where our race edge exists today; the method's next real
expansion would be a follow-type census on BNB (a mempool listener on four.meme's TokenManager2 and PancakeSwap, with a paid/archive RPC).

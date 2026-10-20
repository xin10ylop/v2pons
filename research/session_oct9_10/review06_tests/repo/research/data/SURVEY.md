# The four conditions, chain by chain and launchpad by launchpad (Oct 8, 2026)

The Pons seat exists because four things hold together on Robinhood Chain (report 21.3, 24.20, 24.50):

1. **FCFS with no priority fee.** The sequencer orders by arrival and no tip buys a place, so a box beside it can be first for free.
2. **A launch tax keyed to discrete time.** Pons charges 99% in the creation's clock second, 6.18% in the next, 0.19% in the one
   after, then nothing. The seat sits at a known boundary.
3. **An exact curve.** A constant-product curve on virtual reserves, so a trade is priced to the wei from chain state.
4. **A pre-tick crowd visible on the feed.** The bots' early shots are sequenced, revert cheaply and show on the public feed, so the
   number of fleets lining up before the boundary is countable. That count is the demand the seat sells into.

## How this was surveyed

- Two web surveys: chains (ordering, feeds, reverts) and launchpads (time-keyed taxes, curves).
- On-chain checks of the decisive claims, by this session:
  - `src/analysis/chain_ordering_check.py` (output `chain_ordering.txt`)
  - `src/analysis/doppler_first_trades.py` (output `doppler_first_trades.txt`)
  - the v4 family test (`slowrug_test.txt`, report 24.54)

"Unconfirmed" means the surveys found no primary source and nothing here measured it.

## Chains: conditions 1 and 4

| chain | ordering (condition 1) | public pre-final feed, reverts visible (condition 4) | verdict |
|---|---|---|---|
| **Robinhood Chain** | **FCFS; tips offered but never charged, order random in tip.** Measured Oct 8: 50% of 1,951 transactions offer a tip; 48% of adjacent pairs in descending tip order; 0 of 41 receipts charged above base fee. ArbOS 61 lets the owner turn on tip collection; it ships off. | Yes. `wss://feed.mainnet.chain.robinhood.com`, one message per ~100 ms block, reverts included. Compliance-voided transactions also show status 0. Paid faster relays exist (BlockRazor, Dwellir). | **1 yes, 4 yes** |
| Arbitrum One | **Priority-fee ordering since Sep 24, 2026** (PGA in 125 ms rounds; Timeboost retired; paid "Fast Feed"). Measured: Sep 10, 48% descending pairs, 0 of 43 receipts above base fee. Oct 7, 79% descending, 32 of 50 above base fee. | Feed per block; reverts included | 1 no |
| Other Orbit chains (ApeChain, Sanko, Plume…) | FCFS by default; no Orbit chain found running Timeboost or tip ordering | A Nitro feed exists; public URLs unconfirmed per chain | 1 likely yes, 4 partial; no time-tax launchpad found on any |
| MegaETH | Executes on arrival; RPC says tips "not needed"; the ordering rule is undocumented | 10 ms mini-block stream (public WebSocket capped at 5 msg/s); `block.timestamp` whole seconds per ~1 s EVM block; reverts undocumented | 1 possible, 4 partial; no time-tax launchpad found |
| ZKsync Era, Abstract | Priority fee "not utilized" (arrival order implied, undocumented) | No pre-block feed, no public mempool | 1 partial, 4 no |
| Base, OP Mainnet, Unichain, Ink, Soneium, World, Zora, Mode, Blast, Mantle, Celo, Katana | Priority fee (Unichain: TEE-enforced inside 200 ms Flashblocks) | Flashblocks streams on Base and Unichain; reverts included on Base | 1 no |
| Solana | Priority fees plus Jito/BAM tips and bundles; 300 ms slots | Shreds to node operators; ShredStream permissioned | 1 no |
| BNB Chain | Builders (48 Club, BlockRazor), bundles, private RPCs; 0.45 s blocks | Public mempool; bundles hide reverts | 1 no |
| Monad, Sonic, Berachain, Avalanche, Polygon, Sei, Linea, Starknet, Sui, Aptos, HyperEVM | Tip or gas-price priority | Mostly none | 1 no |
| TON, Tron, Scroll, Taiko, X Layer, Plasma | Unconfirmed or conflicting (Tron sorts by cost; X Layer sources conflict; Taiko has whitelisted preconfirmers) | Unconfirmed | not established |

## Launchpads: conditions 2 and 3, on the chains where condition 1 holds or might hold

| launchpad | chain | launch tax keyed to time | curve | crowd at the boundary (condition 4) | verdict |
|---|---|---|---|---|---|
| **Pons V2** | Robinhood | **99%, then 6.18%, then 0.19%, then 0, per whole second** (factory: 9900 bps, 3 s), buys only; up to 32 creator-named wallets exempt | constant product, virtual reserves | yes: the fleets the engine counts | **all four: the existing trade** |
| Clanker v4 (MevDescendingFees) | Robinhood (also Monad) | Swaps revert in the deployment second. Then a parabolic fee per whole second, 66.7% to 4.2% over 15 s. It is an LP fee, so **sells pay it too**. There is no cliff: the first seat after the lock pays 66.7%. | Uniswap v4 positions | none seen (4 launches sampled); **13 launches in 7 days** | 2 and 3 yes; no supply, no crowd |
| Bankr / LONG (Doppler hook, Rehype) | Robinhood (Bankr also Base) | Linear 80% to 1.69% over 10 s on whole seconds, both directions. Each step is about 7.8 points, so the boundary at second 10 is a step from 9.5% to 1.69%. | Doppler multicurve on v4 | **none: 1,135 Doppler-hook launches a day, 4% (8 of 200) have any swap in their first minute** (measured Oct 8) | 2 and 3 yes; no crowd |
| the v4 operator family (launcher 0x3194e326) | Robinhood | none; a scripted pump and a liquidity pull that answers outside buys within 0.5-1.5 s | v4, no hook | its own wash wallets | a trap (report 24.54) |
| Flap.sh, Bags, pools.trade, Klik, Long.xyz | Robinhood | none found (fixed rates, clearing auctions, flat fees) | exact | – | 2 no |
| Clanker v4 MevTimeDelay / MevBlockDelay | Arbitrum (1 s lock), Unichain (2-block lock) | a lock, no tax tiers | v4 | – | chain fails 1 |
| Zora coins | Base | 99% to 1% linear over 10 s, per second, both directions | Doppler multicurve | – | chain fails 1 |
| Virtuals launchpad v5 | Base (Robinhood and Monad deploy scripts exist; no live router found) | `floor(99·(D−t)/D)`%: 60 s, 10 min or 98 min; start can be scheduled | constant product | – | chain fails 1; watch for a Robinhood router |
| Clanker SniperAuctionV2 | Base, BSC | 5 auction rounds priced on `tx.gasprice`, then a per-second decay | v4 | – | keyed to priority fee by design |
| Meteora DBC fee scheduler, Jupiter Studio, Heaven | Solana | step schedules by slot or second (DBC: linear or exponential, 99% cap) | constant-product segments | – | chain fails 1 |
| four.meme X Mode | BSC | 100% in block 0, then falling per block (schedule unconfirmed) | bonding curve | – | chain fails 1 |
| pump.fun / PumpSwap, Raydium LaunchLab / Bonk.fun, Flaunch | Solana, Base | none (pump.fun fees tier by market cap) | exact | – | 2 no |
| nad.fun, LiquidLaunch, HypurrFun, Arena, SunPump, Sui and TON pads, Abstract, ApeChain, MegaETH, Sonic, Berachain pads | – | nothing primary found | – | – | unconfirmed |

## Verdict

- **All four conditions hold together in one place: Pons on Robinhood Chain.** That is the seat already traded.
- **Two other Robinhood launchpads have a time-keyed tax on an exact curve** (Clanker v4, Bankr/Doppler). Neither has a crowd to sell into: Clanker makes about two launches a day, and only 4% of Doppler launches trade in their first minute. Both also tax sells, and neither has a cliff.
- **Every other chain with a time-keyed launch tax orders by priority fee.** That covers Base (Zora, Virtuals, Clanker), Solana (Meteora DBC, Jupiter Studio, Heaven), BSC (four.meme) and Monad (Clanker). The seat is bought there, not raced.
- **Arbitrum One left the FCFS set on Sep 24.**

What to watch:

- **A tip-ordering switch on Robinhood Chain** (ArbOS 61; `getCollectTips`). It would end the free race on Pons too.
- **A Virtuals v5 router going live on Robinhood.** It has a scheduled per-second tax on a constant-product curve.
- **A time-tax launchpad on a FCFS Orbit chain or on MegaETH**, if its ordering is confirmed.

## Sources

Chain survey:

- Robinhood Chain: docs.robinhood.com/chain/connecting, /chain/differences-from-ethereum; latency.glassnode.com; github.com/chainstacklabs/robinhood-chain-sequencer-feed; blockrazor.io/blog/robinhood-sequencer-feed-benchmark
- Arbitrum: docs.arbitrum.io/how-arbitrum-works/sequencer; forum.arbitrum.foundation (the PGA and Fast Feed AIPs); cryptobriefing.com/arbitrum-priority-gas-auctions-replace-timeboost; blog.arbitrum.io/arbos-elara
- Base, Unichain, OP: docs.base.org/base-chain/network-information/transaction-ordering; docs.base.org/base-chain/flashblocks/websocket-reference; developers.uniswap.org/docs/unichain/technical-information/flashblocks; docs.optimism.io/op-stack/features/flashblocks
- ZKsync, Abstract: docs.zksync.io/zk-stack/concepts/transaction-lifecycle; docs.abs.xyz
- MegaETH: docs.megaeth.com/mini-block
- Monad: monad.xyz/blog/300ms-block-times
- BNB Chain: bnbchain.org (the Fermi hard fork)
- Solana: solanacompass.com (300 ms slots)
- Starknet: community.starknet.io (0.14.0 notes)

Launchpad survey:

- Pons: docs.bitquery.io/docs/blockchain/robinhood/pons-api
- Clanker: github.com/clanker-devco/v4-contracts (`ClankerMevDescendingFees.sol`, `ClankerSniperAuctionV2.sol`)
- Doppler: github.com/whetstoneresearch/doppler (`RehypeDopplerHookInitializer.sol`, `deployments/4663.md`); bankr-support.support.site/article/launching-a-token
- Zora: github.com/ourzora/zora-protocol (`ZoraV4CoinHook.sol`)
- Virtuals: github.com/Virtual-Protocol/protocol-contracts (`FRouterV3.sol`)
- Meteora: docs.meteora.ag/core-products/dbc/fees/fee-scheduler
- Jupiter: docs.jup.ag/user-docs/launch/studio
- Heaven: docs.heaven.xyz
- four.meme: cryptopolitan.com/four-meme-tools-to-slow-bot-activity
- Flap: docs.flap.sh
- Bags: docs.bags.fm/robinhood/overview

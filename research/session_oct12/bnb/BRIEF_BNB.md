# Brief: find lines on BNB Chain (the Robinhood method, adapted to a public-mempool chain)

## Rules for every agent
- Read-only on the repository /home/user/v2pons. Never look for keys or secrets. Never send a transaction. Write only under your own directory
  below /tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/bnb/. Network: read-only JSON-RPC and websocket
  subscriptions (eth_subscribe newPendingTransactions / logs / newHeads; eth_getLogs, eth_getTransactionByHash, eth_getBlockByNumber,
  eth_getCode, eth_call) to public BNB Chain endpoints, within their published limits (one request in flight per endpoint, back off on 429
  or "limit exceeded"); the scout reports which endpoints work and for what. Public documentation via WebFetch/WebSearch where available.
  Report only numbers you computed; every number must come from a script and output left in your directory.

## What we know and what we are looking for
On Robinhood Chain (an Arbitrum Orbit rollup with first-come sequencer ordering and a public ordered-transaction stream) our engine made
+$1,400 in three days by fronting a "volume bot": an operator launching hundreds of Uniswap v4 pools a day from fresh wallets with a constant
launch shape (same contract, selector, calldata length, fixed msg.value), whose own bot bought each pool 7-10 blocks later with a 0.99 minOut
(so ~0.0124 ETH of room ahead of it); we landed a small buy one block after the launch and sold into the bot's buy at +9%, before its pull.
The three conditions: (1) a scheduled self-buy by the operator with slack; (2) a gap we can enter in, with the launch visible to us before the
operator's buy executes; (3) a pull that comes after our exit. Operators defend (quick pulls on strangers, decoys filling the room, fee changes),
so lines last days, not months: the method must find them fast and the engine must probe at $5 with per-line halts.
The method (the owner's): gather every launch over a window; group by launch shape (target contract, selector, calldata length, fee/tick
spacing where they exist, quote, msg.value rounded) and by token code skeleton; for every family with >= 20 launches and recent activity, price
a grid of entry rules (buy at launch + K blocks, exits by fixed hold, take-profit, or "sell into the next buy >= X") with an exact replay, one
trade per launch, a pull = -100%; fit on the first days, validate on the last ones and in 6-hour slices; then explain why the winners work
(who moves the price: the launch wallet, a fixed router/contract, a crowd of reused wallets, strangers; the operator's buy offset, size and
minOut; the reaction to strangers; token sellability) and check executability. Robinhood findings to reuse: the census code at
/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census/code/ (schema in its README.md), the grid with
concentrated liquidity at .../scanner2/analysis/G/ (gsim2.py), the V2 reserve rebuild at .../scanner2/analysis/C/, the bonding-curve study
at .../scanner2/analysis/K/ (REPORT.md: how a launchpad curve was modelled exactly and where an anti-snipe surcharge killed the snipe).

## BNB Chain specifics (the survey of Oct 11, research/session_oct11/chains/REPORT_CHAINS.md)
Ordering: a public mempool plus block builders (BEP-322: builders such as bloXroute, 48Club/Puissant, BlockRazor, NodeReal take private
bundles; priority fee decides within a builder's block). Block time ~0.45-0.75 s. Gas ~$0.006 a swap. Launch flow: four.meme (a bonding-curve
launchpad; its TokenManager2 contract: find the address and ABI in its docs or from the chain) ~3,300 creates/day; PancakeSwap V2 ~6,000 pairs
a day; Uniswap v4 ~315-394/day; PancakeSwap Infinity ~197/day; PancakeSwap V3 ~99/day. A recurring contract 0xb300000b... bought in 8 of 16
traded four.meme launches sampled. 18 of the 20 latest four.meme launches had only the creator's buy. Endpoints: bsc-rpc.publicnode.com keeps
only ~10k blocks of logs with an address filter (and has websockets); bsc-dataseed "limit exceeded"; blockrazor 25-block cap; drpc free tier
10k-block cap; others to test (blastapi public, llamarpc, 1rpc, zan, chainstack free, bloXroute's public RPC). An archive/paid RPC may be
needed for a 7-day census: if none is free, build the deepest window the endpoints allow and add a forward recorder (eth_subscribe on the
factories' creation events and the pools' swaps) for the hours the study runs.

## The questions that decide everything on this chain
A. Visibility and the gap: are the operator bots' buys (four.meme's 0xb300000b and any self-buying launcher found) visible in the public
   mempool before inclusion, and how many blocks after the create do they land? (A live test: subscribe to pending transactions for 20-30
   minutes, record first-seen time and the inclusion block, match to creates and to the bot contracts; count how many of the bots' included
   transactions were ever seen pending: the invisible ones went through private builder bundles.) Without a visible gap there is no front,
   only follow-type lines.
B. Priority competition: for traded launches, how many distinct wallets buy in the first 1-3 blocks after the create, and at what priority fee;
   is the first external buyer a recurring sniper (the Base sniper pattern) and what does its presence do to a hypothetical entry at +1.
C. The curves and pairs: four.meme's exact buy/sell math and fees, any anti-snipe rule (compare the Robinhood launchpad: 88-96% surcharge in
   the create's second), graduation and migration to PancakeSwap, whether tokens can be sold back at any time; PancakeSwap V2 pairs' launch
   shapes (routers, launchpads, self-buying launchers), pull timing, taxes/blacklists in token code.
D. The grid on every family, the reaction to strangers, executability: a BNB engine would send from our wallet through the launchpad or
   PancakeSwap router (no relay yet), bid a priority fee, and read the mempool instead of a sequencer feed; say what each candidate line needs.

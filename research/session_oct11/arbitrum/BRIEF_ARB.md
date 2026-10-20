# Brief: find front-like lines on Arbitrum One (the Robinhood Chain method, applied to a new chain)

## Rules for every agent
- Read-only on the repository /home/user/v2pons. Never look for keys or secrets. Never send a transaction. Write only under your own
  directory below /tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/ (create it). Network: read-only
  JSON-RPC to public Arbitrum One endpoints only (try https://arb1.arbitrum.io/rpc, https://arbitrum-one.publicnode.com,
  https://arbitrum.llamarpc.com, https://1rpc.io/arb; respect rate limits: one request in flight, back off on 429/-32005, batch where the
  node allows; the scout reports which endpoints work and their limits, use its findings). Report only numbers you computed; every number in
  your report must come from a script and output file left in your directory.

## What we know (Robinhood Chain, Oct 8-11 2026; docs/HANDOFF.md sections 6, 16.13-16.17; research/session_oct11/lines/)
The engine fronts a "volume bot": an operator launching hundreds of Uniswap v4 pools a day from fresh wallets through the PositionManager
multicall (initializePool + modifyLiquidities, exactly 1,444 bytes of calldata, a fixed msg.value per line: 2.4333285, 3.0, 5.0 ETH), whose
own bot buys each pool 7-10 blocks after launch (0.05-0.2 ETH through its router 0x1cbaf24d53fe930fce8eff149fa797d2611da149, selector
c1120e3d, minOut = 0.99 x its launch-state quote), then cycles buys and sells for volume and pulls the liquidity later (its pulls a0f7978d).
We see every transaction the instant the sequencer orders it (the Arbitrum-style sequencer feed), fire at the end of the launch block, land a
0.002-0.0097 ETH buy one block later, and sell into the bot's own buy: +9% a trade, 1,180 live trades, 87% up. The bot's minOut leaves a
"room" of ~0.0124 ETH ahead of its buy shared with its own decoy buys. The operator defends: pulls 3 blocks after a fronter's sell; on its 3.0
line it pulls ~9 blocks after any stranger's buy (a trap); on Oct 11 it doubled the fee, throttled launches and filled the room with decoys.
Other operators found and rejected here: C-1 (a buyer bot through router 0xd6d35b56 at +73..+205 after launch, follow-type, the edge is its
own buying and faded), C-2 (hooked honeypot), operator A (a crowd that pulled on us), a V3 crowd line (+5%/trade, thin), a V3 self-buyer
(0.05 ETH own buy at +22..+35, replay $678/day, then it cut its buy), V2 fleets with stale minOuts. Token templates of the volume bot: code
skeleton hashes aff2095f... (2.433 line) and 037449b1... (3.0/5.0) (the census's `skel` = keccak of the opcode sequence with PUSH operands
dropped and metadata stripped); C-1's cb79985d...; the launcher PositionManager code hash c873e135... on Robinhood (the same v4
PositionManager bytecode may exist on Arbitrum under another address).

## The discovery method (the owner's, verbatim in spirit)
1. Gather every pool launched against the chain's quote assets over a window (here 7 days): Uniswap v4 (Initialize events on the PoolManager),
   Uniswap V3 (PoolCreated on the factory), Uniswap V2 and the chain's big V2/V3 forks (Camelot, SushiSwap) if they carry launch activity.
2. Group by launch shape, not wallet: launch target (or created contract), selector, calldata length, fee, tick spacing, hooks, quote, msg.value
   rounded to 7 decimals; also by the token's code skeleton. A bot changes wallets every time but not easily its launch shape.
3. For every family with >= 20 launches in the window and activity in the last 48 h, price the rule grid with an exact replay (v4/V3: Swap
   events' sqrtPriceX96 and liquidity, concentrated ranges handled; V2: reserves from Mint/Swap/Burn): entry at launch + K for K in
   {1,2,3,4,6,8,10,12,16,20,30,40,60,80,100,150,200} (our buy lands at the head of L + K; K >= 1), exits by fixed hold {3..200}, take-profit
   {1..50}% with the hold as deadline, and "sell into the next buy >= X ETH" for X in {0.01,0.03,0.05,0.1}; one trade per launch, q = 0.0058 ETH
   (also 0.002), a pull/burn at or before the sell = -100%, gas per the chain; choose rules on days 1-5, validate on days 6-7 and require
   every 6-hour slice with >= 3 trades positive; rank by validated $/day.
4. For what scores: why does it work (who moves the price after launch: the launch wallet, a fixed router, a crowd of reused wallets,
   strangers; its buy's offset distribution, size, minOut and the room it leaves), does the operator react to strangers (pulls after an
   outsider buy vs baseline), can the token be sold (code: taxes/blacklists; outsiders' sells), does it last (per-day stability, the last 24 h).
5. Executability on our stack: the launch recognisable from calldata alone; our buy landing 1-2 blocks after the launch block (Arbitrum One
   blocks ~250 ms, first-come sequencer ordering, the public sequencer feed wss://arb1-feed.arbitrum.io/feed); gas cost per round trip on
   Arbitrum (~$0.05-0.3); the pool depth vs our stake.

## Arbitrum One facts to verify first (the scout)
Uniswap v4 PoolManager and PositionManager addresses on Arbitrum One (the Uniswap deployments list; verify by eth_getCode and the Initialize
event signature Initialize(bytes32,address,address,uint24,int24,address,uint160,int24) topic 0x... as in src/flip_engine.py); Uniswap V3
factory 0x1F98431c8aD98523631AE4a59f267346ea31F984; Uniswap V2 factory on Arbitrum 0xf1D7CC64Fb4452F05c498126312eBE29f30Fbcf9; Camelot
and SushiSwap factories; WETH 0x82aF49447D8a07e3bd95BD0d56f35241523fBab1; USDC 0xaf88d065e77c8cC2239327C5EDb3A432268e5831; USDT
0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9. Working public RPC endpoints and their limits (requests/s, eth_getLogs block range and result
caps, batch size). The chain's block rate and the window's block numbers. ETH price for $ figures (use 2,570 unless the scout finds better).

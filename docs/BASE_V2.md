# BASE_V2.md: the V2 line on Base (design, Oct 20, 2026)

A second operator runs a pump-and-pull line on Base through Uniswap V2: a fresh wallet a launch, a scripted fleet of about 143 wallets,
a liquidity pull on a per-tier schedule, and a detector that pulls 2-8 blocks after an outsider's buy on most tiers but not on the
1.4-2.2 ETH tier. It was measured Oct 15-20 (749 pairs; the full spec is the `fingerprint_for_an_engine` result in the Oct 20 workflow
journal; `tests/data/base_v2_pair.json` is one real 15 ETH pair's whole event stream). This file is the design of `src/base_v2_engine.py`,
a new engine beside `src/base_engine.py` (docs/BASE.md, whose feeds, transport and conventions it keeps): the line, the trade, the feeds,
every setting and log line, the halts, the box, the staged live test. `tests/test_base_v2_engine.py` and `deploy/base_v2_*` hold the
engine to it.

## 1. The chain and the line's contracts

| what | value |
|---|---|
| Chain | Base mainnet, chain id 8453, 2.000 s blocks, base fee about 0.005 gwei, type-2 transactions, ordered by priority fee inside each 200 ms Flashblock (a later Flashblock never gets ahead of an earlier one), an L1 data fee on top of the gas (`l1Fee`) |
| Uniswap V2 factory | `0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6` (`PairCreated(token0, token1, pair, n)`; WETH is token0 on 553 of 749 pairs, token1 on 196) |
| Uniswap V2 router02 | `0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24`: `addLiquidityETH` `f305d719`, `removeLiquidityETH` `02751cec`, `swapExactETHForTokens` `7ff36ab5`, `swapExactETHForTokensSupportingFeeOnTransferTokens` `b6f9de95`, `swapExactTokensForETH` `18cbafe5`, `swapExactTokensForETHSupportingFeeOnTransferTokens` `791ac947` |
| WETH | `0x4200000000000000000000000000000000000006` |
| The pair's events | `Mint`, `Burn`, `Swap(sender, amount0In, amount1In, amount0Out, amount1Out, to)`, `Sync(reserve0, reserve1)` (topics in the fixture's `topics`) |
| Constant product | out = in x 997 x R_out / (R_in x 1000 + in x 997); a round trip with nobody behind us is -0.6% (two 0.3% fees plus our own impact) |
| Flashblocks | `wss://mainnet.flashblocks.base.org/ws`: brotli JSON every 200 ms, `index` 0 with the header (`base`), every message with `diff.transactions` (raw signed transactions); `base_engine`'s `flash_session`, `on_flash`, `decode_tx` consume it unchanged. A transaction is seen up to 1.8 s before its block is final |
| Confirmed feed | `wss://base-rpc.publicnode.com` (`eth_subscribe newHeads` + `logs`), `eth_getLogs` polling on `https://base-rpc.publicnode.com` as the fallback |
| Sends | `https://mainnet-sequencer.base.org` and `https://mainnet.base.org` at once, User-Agent `Mozilla/5.0 Chrome/128` |
| Archive reads, `eth_call` with state overrides | `https://open-platform.nodereal.io/<key>/base` (single requests, never a batch; only its host is ever logged); `https://mainnet.base.org` also takes state overrides and the Flashblocks `pending` tag |
| Our wallet / key / relay | `BASE_V2_WALLET` and `BASE_V2_KEY_FILE` (may be the Base engine's `/etc/flip/base.key`, mode 600, never printed, never in the repository) and `BASE_V2_RELAY`, a `FlipRelayV2` (`contracts/FlipRelayV2.sol`: owner-only `buy(token, stake, minOut, deadline)` `1622dbe4` and `sell(token, minOut, deadline)` `6a272462` through the router, `withdraw`, `sweep`; the sell approves inside the call and sells everything the relay holds, so no amount and no approval transaction stand between our buy and our exit; immutables `owner`, `router`, `weth`) |
| The exit test | `contracts/V2RoundTrip.sol` placed by a state override at `0xa2..a2` with twice the stake, `roundTrip(router, weth, token, stake, true)` by `eth_call`, exactly as `deploy/base_v2_sim.py` does: it returns the tokens bought, the ETH the sell returned and the constant-product quote for that sell. Nothing is ever sent |

## 2. The line, measured (Oct 15 21:48 to Oct 20 11:29 UTC, 742 of 749 fresh-wallet pairs)

- **The creator**: a persistent hub funds a fresh wallet with exactly tier + gas (2.202 ETH for a 2.1-2.2 pool, 1.602 for 1.54, 15.02 for
  15.0, 13.8 for 13.79, 17.8 for 17.79) 11-36 blocks before the creation. Nonce 0: the token by plain CREATE from the EOA, no launcher
  (token address == `keccak(rlp([creator, 0]))[12:]`, 18 of 18 sampled; runtime 3,553 bytes, decimals 18, totalSupply 5.6e27, no
  `owner()`, 0% buy and sell tax, the code hash differs only with the name compiled in). Nonce 1: `approve(router, max)` 2-3 blocks
  before. Nonce 2, **the creation, block N**: `router.addLiquidityETH` (`f305d719`), msg.value == the ETH side of the Mint exactly
  (742 of 742), type-2, priority = maxFee = 0.006 gwei on the 15.0 tier, 0.0072 on 13.79/17.79, priority 0.001 and maxFee 0.006-0.008
  on 1.2-2.2, gas limit 2.79 M or 3.35 M, 2.72 M used; the receipt carries `PairCreated` on the factory, then the pair's `Transfer`,
  `Sync`, `Mint`. The Mint holds 100% of the supply on the 1.2-2.2 tiers, about 82% on 13.79/15/17.79.
- **The tiers** (the Mint's ETH): 1.2, 1.4, 1.5, 1.9-2.2 (2.17, 2.14, 1.59, 1.56, 1.52...), 2.5 (a different token, 0.01% of the supply in
  the pool, no Burn, a supply dump at +1,201/1,341/1,721 blocks; stopped Oct 18), 13.79 (Oct 15-16 only), 15.0, 17.79. By day: Oct 16 184
  pairs, Oct 17 274, Oct 18 124, Oct 19 87, Oct 20 62 by 11:29; 6.8 an hour, 1.8x busier 01-07 UTC; gaps p10 60 s, median 358 s; a median
  of 3 pairs of the line live at a creation. **The 1.4-2.2 tier ran Oct 16 (55), Oct 17 (148), not at all Oct 18-19, and Oct 20 (16 at
  1.4/1.5).**
- **After the creation**: nonce 3 `approve(LP -> router)` at +2/+3; nonce 4 a 0.00009 ETH self-buy at +5/+6 on the 2.x tiers (324 of 742);
  the pull `removeLiquidityETH` (`02751cec`, to = the creator, 627 of 627 pulls, nonce 4 or 6): a `Burn` on the pair; then the token
  remainder sold and one transfer sweeping everything to the hub 14 blocks later.
- **The probe** `0xe71a69f434a719cd5afa411568b69716aab3b84a` buys 0.000003 ETH (legacy, 0.012 gwei, `b6f9de95`) **inside the creation
  block** on 414 of 742 pairs, 8-63 indexes after the creation, and never triggers anything.
- **The fleet**: about 143 wallets, nonces 950-9,000, type-2 buys with a 0.001 gwei tip and 0.011 gwei maxFee straight to the router
  (`7ff36ab5`, `b6f9de95`), about 119k gas each; a 0.000019 ETH dust buy at +2 on 53% of pairs, real buys (>= 0.005 ETH) from +8/+11/+54
  (p10/50/90); **nothing of the fleet in the creation block, 0 of 742**. On the 1.4-2.2 tier it buys 0.58-0.65 ETH (30-40% of the pool)
  over the first 5-10 minutes and the price is +13% at +60, +24% at +120, +34% at +180, +47% at +300 (medians); it barely sells.
- **The pull schedule** (blocks after N, p10/50/90): 1.2: 365/393/410 (min 51 and 210 on Oct 19-20); 1.4-2.2: 404/540/796 over the window,
  on Oct 20 198/217/304 x5/404 x3/443/479, **min +198**; 15.0: 408/1,131/1,306; 17.79: 167/1,126/1,271; 13.79: 14/1,059/1,245. The pull
  comes a median 9 blocks after the fleet's last buy, so a "fleet stopped buying" rule signals nothing.
- **The reaction**: on the 1.2, 13.79, 15.0 and 17.79 tiers every non-fleet buy, dust included, is followed by the pull 2-8 blocks later
  (0.00001-0.0002 ETH: 18 of 22; 0.0002-0.0005: 13 of 17; >= 0.0005: 20 of 20; e.g. the fixture: an outsider's 0.000753 ETH at +419, the
  Burn at +424); a seat there prices -60% to -100%. On the 1.4-2.2 tier about 40 outsider buys of 0.0005-0.04 ETH drew no reaction (31 of
  them from two bots, nonces about 60k and 109k, on all 16 Oct-20 pairs, pulled on schedule at 198-479) and one 0.0008 ETH buy on Oct 16
  was pulled 2 blocks later.
- **The paper seat** (buy 0.1 ETH at N+1, 0.3% a leg, our impact, a pull = -100%): the 1.4-2.2 tier with a hard exit at +180: +28.8% mean,
  +34.3% median, 96% win, 9 of 219 pulled over all days; Oct 20: +59%, 100% win, 0 of 16 pulled. At +120: +20%; at +300: +41.7% but 11
  pulled. 0.02 ETH is 1-1.4% of the pool; each doubling of the stake costs about a point; above 0.2 ETH we are the pump.

## 3. The trade (the tolerant tier only)

1. **The creation seen**. Pending (Flashblocks): a raw transaction to `BASE_V2_ROUTER` with selector `BASE_V2_CREATE_SELECTOR`, value in a
   known tier; the sender is recovered, its nonce must be `BASE_V2_CREATOR_NONCE` and `keccak(rlp([sender, 0]))[12:]` must equal the
   calldata's token; the Mint's reserves are then known before the block seals (a fresh pair takes `amountTokenDesired` and msg.value
   whole). Confirmed (the logs feed): a `PairCreated` on the factory with WETH on either side; the creation transaction and its receipt
   are read (`eth_getTransactionByHash`, `eth_getTransactionReceipt`) for the same shape and the `Mint`. Either way the line is logged as
   `creation` with its class: `tradable` (value inside `BASE_V2_TIER_BAND` and not in `BASE_V2_TIER_EXCLUDE`), `watched` (any other value),
   and a shape mismatch is `skip` with the reason. Every pair of the line, tradable or watched, is followed (its logs subscribed) until its
   Burn or `BASE_V2_WATCH_BLOCKS`: their `outsider_buy` and `pull` lines are the data the tiers are re-qualified from.
2. **Arm** (tradable only): the pair's state is its reserves, folded from its own events in (block, logIndex) order (`Sync` exact after
   every swap, the `Mint`, a `Burn`), the launch price r_eth / r_tok, token0/token1 from `PairCreated`; at the arm one `eth_getLogs` of
   the pair at block N catches the creation block's own swaps (the probe's; anyone else's is an outsider before our fire, which skips the
   pair). Nothing else is read on the trade path.
3. **The guard**, before every buy, in under 1 s, in the dry run too. During the pending window (the token exists 6-19 blocks before N):
   `eth_getCode(token)` size in `BASE_V2_TOKEN_CODE_SIZES`; `totalSupply()` so that the Mint's token side is >= `BASE_V2_MIN_SUPPLY_IN_POOL`
   of it. Once N is sealed: the exit test, `V2RoundTrip.roundTrip` by `eth_call` at the explicit block N with the state override, the
   stake we intend, sent to `BASE_V2_ARCHIVE_URL` and `BASE_V2_READ_ALT_URL` at once (an endpoint without block N yet answers an error
   and is asked again every 100 ms; the first verdict counts). **Refused unless the tokens bought equal the constant-product expectation
   from the reserves (a buy tax) and the ETH back is >= `BASE_V2_EXIT_MIN` of the quote (a sell tax); a reverted sell is a honeypot.**
   The verdict is one `guard` line. The fire is refused on any failure, and nothing retries a failed guard.
4. **Fire**. The buy is aimed at N+1 (the paper seat; the fleet's dust comes at +2, its real buys at +8). It is refused once the confirmed
   head is at or past N + `BASE_V2_LAND_MAX`, when a pull was seen, on an outsider buy before ours, when `BASE_V2_MAX_POSITIONS` are open,
   when halted or stopped (the day, or the tier for the day), at `BASE_V2_MAX_PER_DAY`, or when the relay holds less than the stake plus
   `BASE_V2_RELAY_MARGIN_ETH` beyond the open positions' stakes. With `BASE_V2_BACKRUN=1` the buy goes in the creation block itself: the
   guard then runs at the `pending` tag on `BASE_V2_PENDING_URL` as soon as the creation is seen pending, and the buy is sent at once with a
   priority above the creation's 0.006 gwei; off by default until stage 0 has measured the delay. The buy:
   `FlipRelayV2.buy(token, stake, minOut, deadline)` with stake = min(`BASE_V2_STAKE_ETH`, `BASE_V2_STAKE_CAP_ETH`, `BASE_V2_SHARE_CAP` x
   r_eth), minOut = the constant-product output on the Mint's reserves x (1 - `BASE_V2_BUY_SLIP`) (the probe's dust moves the price
   0.0004%, inside the slip), deadline now + `BASE_V2_BUY_DEADLINE_S`; type-2, chain 8453, priority `BASE_V2_PRIO_GWEI`, maxFee = 2 x the
   head's base fee + the priority, at most `BASE_V2_MAX_FEE_GWEI`, gas `BASE_V2_BUY_GAS`, at the wallet's next nonce, sent to every
   `BASE_V2_SEND_URLS` at once. One `fire` (or `would_fire`) line, with `ready_ms`, the delay from the creation's first sight to the
   signed transaction.
5. **Sell**: `FlipRelayV2.sell(token, minOut, deadline)` at the next nonce, on the first of:
   - **an outsider's buy** (`exit: outsider`, minOut 0, at once): pending, a transaction whose raw bytes carry our token with value > 0 whose
     sender is not in the roster, not `BASE_V2_PROBE`, not the creator, not our wallet; confirmed, a `Swap` on our pair with ETH in
     (amountIn on the WETH side) >= `BASE_V2_OUTSIDER_MIN_ETH` whose `to` is none of those and not the relay (an aggregator's buy shows the
     aggregator as `to`: an outsider). The sell aims at the block behind the buy.
   - **the take**: the reserves after a `Sync` value the position at >= launch x (1 + `BASE_V2_TAKE_PROFIT`) (`exit: take_profit`, minOut =
     the output x (1 - `BASE_V2_SELL_SLIP`)); or the fleet's first sell on our pair (`exit: fleet_sell`, the same minOut).
   - **the hard block**: sent when the head reaches N + `BASE_V2_SELL_SEND_BLOCK` (`exit: hard`, minOut 0, deadline `BASE_V2_SELL_DEADLINE_S`),
     sent again at the same nonce with twice the priority when unseen (no Flashblock, no receipt) by N + `BASE_V2_SELL_RESEND_BLOCK`, and
     from the wall clock at the creation block's timestamp + `BASE_V2_SELL_FALLBACK_S` when no head has come. A position is never held past
     N + `BASE_V2_HARD_BLOCK`.
   - **a pull** (`exit: pulled`): a `Burn` on our pair, or the creator's pending `BASE_V2_PULL_SELECTOR` call to the router carrying our
     token, before our sell: -100%; a sell at minOut 0 still goes once (a partial pull would strand the tokens), and section 7 decides the halt.
   A sell that reverted or was refused on a pair not pulled is sent again at the next nonce with minOut 0, twice at most, then the line
   halts (`sold none`); a buy that filled with no tokens halts the same way. `exit` values: `outsider`, `take_profit`, `fleet_sell`,
   `hard`, `pulled`, `buy_reverted` (a buy that reverted or never mined).
6. **Settle** from the receipts: ETH in (the stake), the tokens (the token's `Transfer` to the relay), ETH out (the relay's balance
   change, which the sell's `Swap` confirms), the gas of both (gasUsed x effectiveGasPrice + `l1Fee`), the return, the pull's block
   against our sell's, the first outsider's block, the fleet's ETH behind us: one `trade_done`. A buy without a receipt is polled on while
   its transaction was seen in a Flashblock or its Transfer logged; failing that, the relay's token balance decides (tokens there: a sell at
   minOut 0, `via: balance`).
7. **Dry run** (`BASE_V2_DRY_RUN=1`, the default): everything but sign and send, the guard included. A dry buy is priced on the reserves at
   the end of block N+1 as recorded, our own impact applied, follows every `Sync` and sells by the same rules at the recorded reserves:
   `would_fire` and `trade_done` with `dry: true`, `ready_ms` measured as live.

Up to `BASE_V2_MAX_POSITIONS` positions at once, one per pair, one wallet, one nonce counter: every transaction is signed at its send
at the wallet's pending nonce (re-read after a send error or "nonce too low"), and a buy's deadline makes it mine and revert at worst, so
one position's sell never waits on another's buy. Open positions are written to `base_v2_positions.json` beside the log and taken back
at a start (sold at once).

## 4. The feeds

- **Confirmed (required)**: one websocket to `BASE_V2_WS_URL` with `eth_subscribe newHeads` (the clock: number, timestamp, base fee), one
  `logs {address: factory}` (the factory emits only `PairCreated`; WETH is checked client-side) and one `logs {address: pair, topics:
  [[Mint, Burn, Swap, Sync]]}` per followed pair, unsubscribed at its Burn or `BASE_V2_WATCH_BLOCKS`. Silent for `BASE_V2_WS_SILENT_S`, the
  engine polls `eth_getBlockByNumber("latest")` and `eth_getLogs` (the factory, then the followed pairs) one block behind the head over
  `BASE_V2_RPC_URL` for every block it missed (the start reads 12 blocks back, so a restart mid-launch still arms) and reconnects.
- **Flashblocks (optional, on by default; `BASE_V2_FLASH_URL=0` turns it off)**: as `base_engine` (types 0x00/0x01/0x02/0x04 decoded, 0x7e
  skipped, senders recovered only for the router calls that match). It advances three things: the creation (seen up to 1.8 s before N
  seals, which is when the code and supply checks run), an outsider's or the creator's pull transaction (the sell goes before the block
  seals), and our own transactions' inclusion. Everything it does the confirmed feed does a little later: an outage costs speed, never
  correctness, except the N+1 landing, which `ready_ms` in `flow` shows.
- **Sends**: `BASE_V2_SEND_URLS`, every one at once over warm connections with the browser User-Agent; the first "ok" or "already known"
  counts. The sequencer refuses `eth_chainId`: it passes the start's check by answering a malformed raw transaction with -32602.
- **Reads**: `BASE_V2_RPC_URL` (receipts, transactions, `eth_getLogs`, balances, nonces), `BASE_V2_READ_ALT_URL` once when it fails;
  `eth_getCode`, `totalSupply()` and the exit test on `BASE_V2_ARCHIVE_URL` (single requests only) and `BASE_V2_READ_ALT_URL`.
- **The roster**: `BASE_V2_ROSTER_FILE`, JSON `{"built": <utc>, "wallets": [...]}`, written daily by `deploy/base_v2_roster.py` from the
  chain: every wallet that bought on >= 3 of the line's pairs in the last 3 days with the fleet's shape (type-2, 0.001 gwei tip, `7ff36ab5`
  or `b6f9de95` straight to the router, nonce under 20,000; the two Oct-20 bots at 60k/109k fall out). The engine reads it at the start and
  again when its mtime changes, never adds to it, and refuses a live start without it. The probe is `BASE_V2_PROBE`, not the roster.
- **Files beside the log**: `HALTED.base_v2` (read at the start and before every fire), `base_v2_positions.json`, and the `fcntl` lock on
  `BASE_V2_KEY_FILE` while live: with the Base engine's key file, a live start while that engine is live is refused (two signers on one
  nonce), and `deploy/base_ops.py` sees the lock as before.

## 5. Settings (`/etc/flip/base_v2.env`; the default in parentheses, then the bound a wrong value is refused at: the start stops naming it)

Feeds and keys: `BASE_V2_DRY_RUN` (1; 0 or 1), `BASE_V2_LOG_PATH` (/var/log/flip/base_v2.jsonl), `BASE_V2_WS_URL` (wss://base-rpc.publicnode.com;
ws/wss), `BASE_V2_RPC_URL` (https://base-rpc.publicnode.com; http/https), `BASE_V2_READ_ALT_URL` (https://mainnet.base.org; 0 = none),
`BASE_V2_SEND_URLS` (https://mainnet-sequencer.base.org,https://mainnet.base.org; comma-separated, not empty), `BASE_V2_FLASH_URL`
(wss://mainnet.flashblocks.base.org/ws; 0 = off), `BASE_V2_ARCHIVE_URL` (https://open-platform.nodereal.io/64a9df0874fb4a93b9d0a3849de012d3/base;
http/https, logged as its host), `BASE_V2_PENDING_URL` (https://mainnet.base.org; the `pending` tag, used only with the back-run),
`BASE_V2_WALLET` ("" ; 40 hex), `BASE_V2_KEY_FILE` (/etc/flip/base.key), `BASE_V2_RELAY` (""; 40 hex), `BASE_V2_FACTORY`
(0x8909dc15e40173ff4699343b6eb8132c65e18ec6), `BASE_V2_ROUTER` (0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24), `BASE_V2_WETH`
(0x4200000000000000000000000000000000000006), `BASE_V2_HALT_FILE` (HALTED.base_v2 beside the log), `BASE_V2_ROSTER_FILE`
(/etc/flip/base_v2_roster.json), `BASE_V2_WS_SILENT_S` (10; 1..600).

The fingerprint: `BASE_V2_CREATE_SELECTOR` (f305d719; 8 hex), `BASE_V2_PULL_SELECTOR` (02751cec; 8 hex), `BASE_V2_CREATOR_NONCE` (2; 0..100),
`BASE_V2_TOKEN_CODE_SIZES` (3553; comma list of bytes, 0 = any), `BASE_V2_MIN_SUPPLY_IN_POOL` (0.99; 0..1), `BASE_V2_TIER_BAND` (1.3,2.3; two
ETH values lo,hi with 0 < lo <= hi <= 1000), `BASE_V2_TIER_EXCLUDE` (1.2; comma list of ETH values, a creation whose value rounds to one at
0.001 ETH is never traded; may be empty), `BASE_V2_PROBE` (0xe71a69f434a719cd5afa411568b69716aab3b84a; comma list of 40 hex, may be empty),
`BASE_V2_OUTSIDER_MIN_ETH` (0; 0..1: a confirmed buy under it is not an outsider; 0 = any buy, dust included), `BASE_V2_WATCH_BLOCKS`
(1400; 200..5000), `BASE_V2_LAND_MAX` (1; 0..10: the fire is refused once the confirmed head is at N + this), `BASE_V2_BACKRUN` (0; 0 or 1),
`BASE_V2_EXIT_MIN` (0.98; 0.5..1: the exit test's ETH back over its quote).

The trade: `BASE_V2_STAKE_ETH` (0.02; 0.000001..10), `BASE_V2_STAKE_CAP_ETH` (0.02; 0.000001..10; the owner raises it in steps), `BASE_V2_SHARE_CAP`
(0.05; 0.001..0.5 of the ETH reserve), `BASE_V2_BUY_SLIP` (0.03; 0.0001..0.5), `BASE_V2_BUY_DEADLINE_S` (6; 2..600), `BASE_V2_HARD_BLOCK` (180;
1..200: the earliest scheduled pull seen on the tier is +198), `BASE_V2_SELL_SEND_BLOCK` (176), `BASE_V2_SELL_RESEND_BLOCK` (178) (refused unless
SELL_SEND_BLOCK < SELL_RESEND_BLOCK <= HARD_BLOCK), `BASE_V2_SELL_FALLBACK_S` (370; 10..3600), `BASE_V2_TAKE_PROFIT` (0.25; 0.01..100),
`BASE_V2_SELL_SLIP` (0.05; 0..0.99), `BASE_V2_SELL_DEADLINE_S` (6; 2..600), `BASE_V2_MAX_POSITIONS` (3; 1..10), `BASE_V2_MAX_PER_DAY` (20;
0..100000), `BASE_V2_DAILY_STOP_ETH` (0.15; 0..1000), `BASE_V2_SCHEDULE_MIN` (220; HARD_BLOCK+1..5000: a Burn on a pair of the tier earlier
than this ends the tier for the day), `BASE_V2_PULL_SHARE` (0.30; 0.01..1: a sell taking this share of the ETH reserve on a pair of the tier
ends the tier for the day), `BASE_V2_REACT_BLOCKS` (10; 1..100: a Burn within this many blocks after a buy is a reaction), `BASE_V2_LOSS_STREAK_HALT`
(2; 0..100, 0 = off: live losses in a row that halt), `BASE_V2_LATE_HALT` (2; 0..100, 0 = off: live buys mined past N + LAND_MAX that halt),
`BASE_V2_ETH_USD` (2570; 1..1e6, for the dollar figure only), `BASE_V2_PRIO_GWEI` (0.03; 0..100: above the creation's 0.006 and the fleet's
0.001; a round trip of about 250k gas plus two L1 fees is about 0.03% of a 0.02 ETH stake), `BASE_V2_MAX_FEE_GWEI` (0.5; 0.000001..1000, refused
under PRIO), `BASE_V2_BUY_GAS` (250000; 50000..5000000), `BASE_V2_SELL_GAS` (250000; 50000..5000000), `BASE_V2_RELAY_MARGIN_ETH` (0.0005; 0..10).

Every number is read as `base_engine`'s `_setting` / `_exact` do (an exact integer of its unit, never through a float); a live start needs the
wallet, the key file and its lock, the relay (its `owner()` the wallet, `router()` and `weth()` the settings), the roster file, `eth_chainId`
8453 on every endpoint, and the guard's self-test (the exit test on the newest pair of the line, `deploy/base_v2_sim.py`'s pick) answering
`SELLABLE` on `BASE_V2_ARCHIVE_URL`.

## 6. Log lines (`/var/log/flip/base_v2.jsonl`, one JSON a line, every one with `ev` and `t`; no key, no URL beyond its host)

- `start`: release, dry, head, wallet, relay, roster_n, roster_built, positions (taken back), settings (every one, URLs as hosts).
- `flow` (every 60 s): head, head_ts, lag_s, lag_max_s, ws, flash, head_src, logs_to, flash_block, flash_msgs_min, flash_total,
  flash_reconnects, flash_bad, dups, reorgs, filled, creations, tradable, watched, followed, positions (open pairs), trades_today,
  pnl_today_eth, trades_done, halted, stopped, tiers_ended, relay_eth, wallet_eth, roster_n, ready_ms_last, guard_ms_last.
- `creation`: block, tx, creator, nonce, token, pair, weth_is0, value_eth, tier, cls (tradable | watched), r_eth_wei, r_tok, supply_share,
  tx_type, prio_gwei, max_fee_gwei, gas, via (flash | logs), seen_ms (from the block's timestamp).
- `arm`: pair, token, block, tier, r_eth_wei, r_tok, followed (pairs of the line live).
- `skip`: pair, token, block, tier, why (one of: `value outside the band`, `excluded tier`, `creator nonce`, `create address`, `selector`,
  `not the router`, `code size`, `supply share`, `guard`, `late`, `outsider before our fire`, `pulled before our fire`, `positions`,
  `halted`, `stopped`, `tier ended`, `day cap`, `relay balance`), and the measured value (value_eth, nonce, code_size, supply_share, head...).
- `guard`: pair, token, block, stake_wei, tokens, expect_tokens, eth_back_wei, quote_wei, ratio, code_size, supply_share, verdict
  (ok | buy_tax | taxed | honeypot | unreadable), ms, src (host).
- `fire` / `would_fire`: pair, token, tier, creation, head, aim (the block aimed at), stake_wei, min_out, expect_tokens, nonce, prio_gwei,
  max_fee_gwei, via (flash | logs), ready_ms, positions.
- `buy_sent` / `sell_sent`: pair, hash, nonce, block_seen, reason (buy: `fire`; sell: the `exit` value), min_out, via (first | resend | retry |
  balance), deadline, prio_gwei.
- `outsider_buy`: pair, tier, block (or `pending: true` with the Flashblock), tx, sender, to, value_eth, via (flash | logs), ours (a position
  open), action (sell | skip | none).
- `pull`: pair, tier, block (or pending), tx, eth_out_wei, since_creation, since_last_buy, since_outsider (null with none), reaction
  (a buy within REACT_BLOCKS before it), before (fire | sell | after), ours.
- `trade_done`: pair, token, tier, creation, buy_block, buy_index, sell_block, eth_in_wei, tokens, eth_out_wei, gas_wei, l1_fee_wei, ret, usd,
  exit, pulled_at, outsider_at, fleet_first_buy, fleet_eth, peak_ret, loss_streak, dry, live, trades_today, pnl_today_eth.
- `halt`: reason, tier, pair, dry, file.
- `stop`: what (day | tier | process), day, tier, reason, pnl_today_eth, trades_today, positions (open at a process end).
- `alarm`: what, and the key's fields; at most one a key every 10 min.

## 7. The halts and the stop rules

- **Halt** (`HALTED.base_v2` written, holds across restarts until the owner removes it; no new buy, open positions still sold): a Burn on
  a pair of ours before our sell, or within `BASE_V2_REACT_BLOCKS` after our buy even when our sell landed first, **when no outsider bought
  before it** (we were the trigger: the tier reacts); `BASE_V2_LOSS_STREAK_HALT` live losses in a row; `BASE_V2_LATE_HALT` live buys mined
  past N + `BASE_V2_LAND_MAX`; `sold none` twice or a buy that filled with no tokens (the path is broken). The dry run halts in memory.
- **The tier ended for the day** (`stop`, what: tier; cleared at 00:00 UTC, never by the engine before): a Burn earlier than
  `BASE_V2_SCHEDULE_MIN` on any pair of the tier, a Burn within `BASE_V2_REACT_BLOCKS` after any buy on any pair of the tier (a reaction on
  someone else's buy), or a sell taking >= `BASE_V2_PULL_SHARE` of the ETH reserve on any pair of the tier (the dump pattern).
- **The day stopped** (`stop`, what: day): the live net P&L at -`BASE_V2_DAILY_STOP_ETH`, or `BASE_V2_MAX_PER_DAY` buys; both restored from
  the log's own lines of the day at a restart, as the Base engine does.
- **Never**: the 1.2, 13.79, 15.0, 17.79 tiers at any stake; a tier re-qualified by the engine itself (the owner does it from the chain
  and the `outsider_buy` / `pull` lines, and widens `BASE_V2_TIER_BAND` by hand); a band widened to fill a day with no 1.4-2.2 pairs: a
  zero-trade day is a result.

## 8. The box

| path | what |
|---|---|
| `src/base_v2_engine.py` | the engine (this design); `python3 src/base_v2_engine.py` runs it from the env |
| `tests/test_base_v2_engine.py`, `tests/data/base_v2_pair.json` | the engine against the real 15 ETH pair of 12:07 UTC Oct 20 (block 52,854,344: the probe at +0, the dust at +2, the fleet from +15, an outsider at +419, the Burn at +424), the chain, both websockets and the guard stubbed; the tolerant-tier cases replay the same stream at a 2.0 ETH value |
| `contracts/FlipRelayV2.sol`, `.json` | the relay; `deploy/base_v2_relay_deploy.py` deploys it (`constructor(router, weth)`) and writes `BASE_V2_RELAY=` |
| `contracts/V2RoundTrip.sol`, `deploy/base_v2_sim.py` | the exit test by hand: `SELLABLE` / `TAXED` / `HONEYPOT` on any pair at any block |
| `deploy/base_v2_relay_sim.py` | the relay's own round trip on a live pair, and the owner check |
| `deploy/base_v2_roster.py` | the fleet roster from the chain, daily (a cron entry the setup installs); written in place, since the unit binds the file into the engine's namespace |
| `deploy/base_v2_results.py` | the owner's screen from the log: feeds, positions, trades, tiers, skips, halts, alarms |
| `deploy/base_v2_wallet.py`, `deploy/base_v2_ops.py` | base_wallet.py's helpers pointed at the V2 files (`address`, `withdraw`); the money: status, deposit, withdraw, sweep, payout through the relay, refused while the engine is live |
| `deploy/base_v2_setup.sh`, `deploy/flip-base-v2.service` | the box: the env template (every setting of section 5), the hardened unit, logrotate, the roster cron, a dry start |
| `docs/RUNBOOK.md` 4m | every box step, numbered, with expected output |

## 9. The staged live test (each stage's settings in the env; a stage ends by the owner's hand, never by the engine)

- **Stage 0, the dry run, until three correct decisions** (`BASE_V2_DRY_RUN=1`; the owner's choice, Oct 20: not a full day). Pass: the
  first three creations of the tolerant tier armed within 1 s of their block (`seen_ms`), the tier right, every guard under 1 s (`guard`
  ms), each `would_fire` with `ready_ms` under 1,500 (the N+1 landing) and a dry `trade_done` priced from the recorded swaps; the watched
  tiers refused with the right `why`; the probe logged as `outsider_buy`, the fleet never. A tolerant-tier creation comes every 20-60
  minutes when the tier is running (none at all on some days: wait, do not widen the band).
- **Stage 1, $5 live on 5 pairs** (`BASE_V2_DRY_RUN=0`, `BASE_V2_STAKE_ETH=0.002`, `BASE_V2_STAKE_CAP_ETH=0.002`, `BASE_V2_MAX_POSITIONS=1`,
  `BASE_V2_MAX_PER_DAY=5`, the full rule otherwise: hard +180, take-profit +25%, the instant sell on an outsider buy). The reaction
  question is answered here: stop at once if a Burn lands inside 10 blocks of our buy on any of the first 3 (section 7's halt does it;
  the stake is the whole loss). Go on when 3 of the first 5 are positive and no pull came inside 10 blocks of any buy.
- **Stage 2, 0.02 ETH on 10 pairs**, the same rule (`BASE_V2_STAKE_ETH=0.02`, `BASE_V2_STAKE_CAP_ETH=0.02`, `BASE_V2_MAX_PER_DAY=10`). Pass:
  7 of 10 positive and the mean >= +10% net. Stop (automatic): a Burn before our exit on a pair with no outsider buy, two losses in a row
  (`BASE_V2_LOSS_STREAK_HALT`), our buy mined later than N+1 twice (`BASE_V2_LATE_HALT`).
- **Stage 3, 0.05 then 0.1 ETH, 20 pairs each**, `BASE_V2_TIER_BAND=1.95,2.3` preferred (0.1 ETH is 5% of a 2.0 pool, the share cap's
  edge), `BASE_V2_MAX_POSITIONS=3`, `BASE_V2_DAILY_STOP_ETH=0.15`, the stage-2 stops; the tier's pulls moving under +220 end it for the
  day by section 7.

## 10. What was not measured

Whether the two Oct-20 bots are whitelisted rather than tolerated (the tolerant-tier evidence is about 40 outsider events, 31 of them
theirs; stage 1 exists for this); the reaction to buys of 0.2 ETH or more (nothing that size was seen); the Flashblocks latency from
the box, and whether a 0.02-0.05 gwei type-2 buy lands in N+1 (or N) from there (the probe shows it is done, not that we can); the tier mix
on a given day (none of the tolerant tier launched Oct 18-19; the mint size moves, 1.9 -> 2.1-2.2 -> 1.5-1.6 -> 1.4/1.5: the band is a
setting, not a law); the 1.2 tier's reactive label rests on 2 events; fleet attribution past the first 25 swaps of a pair uses the Swap's
`to`, so a bot buying through a contract appears as the contract; every return is paper (a pull = -100%, no partial fills, no failed
sells); the Denim hardfork (200 ms native blocks, no Flashblocks) has no date, so the feed layer stays swappable.

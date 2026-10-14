# BASE.md: the 2.433 line's front on Base (design, Oct 14, 2026)

The operator that ran the 2.433 ETH line on Robinhood Chain (HANDOFF sections 3.2, 16.13: the front made about +14% a trade, 400 trades a
day) left Robinhood on Oct 12, tested once on Ethereum, ran 52 pools on BNB Chain on Oct 13 (REPORT_FIND2433.md) and set up on Base on Oct
14 (REPORT_BASE2433.md: three test launches 09:32-09:42 UTC, a real launch at 10:30). This file is the design of the Base engine,
`src/base_engine.py`: what the line does on Base, the trade, the feeds, every setting and log line, and the deployment. The code's docstring
and `tests/test_base_engine.py` hold the engine to it; `deploy/base_*` and RUNBOOK 4l put it on the box.

## 1. The chain

| what | value |
|---|---|
| Chain | Base mainnet, chain id 8453, OP Stack, 2 s blocks, EIP-1559 (base fee about 0.005 gwei on Oct 14), transactions ordered by priority fee within each 200 ms Flashblock, an L1 data fee charged on top of the gas (receipt field `l1Fee`) |
| Public RPC (reads) | `https://mainnet.base.org`, `https://base-rpc.publicnode.com` (logs for the last ~10,000 blocks only); old blocks and `eth_call` with state overrides: `https://base.gateway.tenderly.co` |
| Websocket (newHeads, logs) | `wss://base-rpc.publicnode.com` (measured Oct 14 11:08 UTC: a new head 40-80 ms after its block timestamp; `eth_subscribe logs` on the PoolManager streams every event of a block as it is sealed) |
| Flashblocks (pending blocks) | `wss://mainnet.flashblocks.base.org/ws`: brotli-compressed JSON, about 11 messages a block (`index` 0..10, one every 200 ms); `index` 0 carries `base` (the header: `block_number`, `timestamp`, `base_fee_per_gas`, ...), every message carries `diff.transactions` (the raw signed transactions added in that 200 ms, hex) and `metadata.block_number`. No receipts, no logs. The block's timestamp is its sealing time: `index` 0 arrives 2.0 s before it, so a transaction is seen up to 1.8 s before the block that holds it is final |
| Sequencer (sends) | `https://mainnet-sequencer.base.org` (eth_sendRawTransaction only); `https://mainnet.base.org` as the second send |
| Uniswap v4 PoolManager | `0x498581ff718922c3f8e6a244956af099b2652b2b` |
| Universal Router | `0x6ff5693b99212da76ad316178a184ab56d299b43` (`execute` `24856bc3`: the bot's wallets sell through it) |
| Permit2 | `0x000000000022d473030f116ddee9f6b43ac78ba3` |
| The bot's buy contract | `0x987d5db84d105c1f49391af409cc34c6050fb1d0` (22,816 B, code hash `008737874a66…`): its buys are calls with selector `27f7e6ee` (356 B, value = the ETH) whose calldata carries the Universal Router, the PoolManager, the pool key (0, token, 5000, 100, hook), the amount, a constant, its minOut and a deadline; it also holds the Robinhood router's `c1120e3d` and `a0f7978d` |
| Our wallet / relay / key | `BASE_WALLET` (made by `deploy/base_wallet.py`; its key in `/etc/flip/base.key`, mode 600, never in the repository or a chat) and `BASE_RELAY`, a FlipRelay (`contracts/FlipRelay.sol`, unchanged: it takes the PoolManager at deployment and its PoolKey carries the hook) deployed on Base by `deploy/base_relay_deploy.py` |

## 2. The line on Base (measured on the 09:42 UTC test pool, launch block L = 52,590,807; b02/b04/b07/b08 in research/session_oct14/base2433)

- **L+0, the launch**: a fresh launch wallet (nonce about 10, funded minutes earlier by the buyer wallets) calls a launcher contract created
  for this launch (11,031 B, code hash prefix `225f9af97d88`) with selector `c3e0ff3d`, 260 B, value 0, gas limit about 1.98 M. The call
  emits the PoolManager's `Initialize`: currency0 = 0 (ETH), currency1 = the token (1,526 B, code hash
  `63ad5291cdef5d82cddf8e5d8d4c48bd6ad1de2394616ab66a6c6c6cceae63bb`, the Robinhood 2.433 token byte for byte, address ending `777`),
  fee 5000, tick spacing 100, hooks = a contract created for this launch (9,002 B) whose address flags are `0x80` = **beforeSwap**
  (REPORT_BASE2433 said afterSwap; the flag bit 7 is beforeSwap and the hook's bytecode holds the beforeSwap selector `575e24b4`),
  sqrtPriceX96 about 1.7e33. The pool has no liquidity yet.
- **L+1**: the launch wallet funds the buyer wallets through the bot contract (`4977dff6`, 1,732 B, 6.13 ETH on the 09:42 pool).
- **L+2**: `approve(token -> hook)`.
- **L+3, the liquidity**: the launch wallet calls the hook with selector `2346bb56` (228 B), value = the pool's ETH (2.133 ETH on the
  09:42 pool, 0.133 on the 09:32 one): two `ModifyLiquidity` events with a positive delta, full range (-887200..887200). From here the
  pool can be traded.
- **L+4, L+5**: approvals (Permit2, Universal Router).
- **L+8, the bot's first buy**: a buyer wallet -> the bot contract, `27f7e6ee`, 0.15 ETH; then buys of 0.1-0.27 ETH at +10, +12, +13, +15,
  +17, +21, +23, +25, +27, +28 and sells through the Universal Router from +12. Priority fee 0.0011 gwei, gas limit 500k.
- **L+30, the pull**: the launch wallet -> hook, `f2f230a8` (132 B): a negative `ModifyLiquidity`. The 09:32 pool (no buys) was pulled at +18.
- **The exit test (b07, eth_call at past blocks with our FlipRelay's code placed by state override)**: an outsider's buy followed by its
  sell goes through at every block from +3 to +29 and returns -1.00% (the two 0.5% fees: the hook takes nothing); a sell alone from a later
  block works (+13% at +8, after the bot's first buy). No outsider has traded in these pools, so **the operator's reaction to an
  outsider is unknown** (on BNB it pulled 6-7 blocks, about 3 s, after an outsider's buy; on Robinhood it never did).

**Measured on all five launches (the 11:30 UTC update of REPORT_BASE2433.md; b09, b10, b12):** the sequence above is fixed (the add at +3,
once at +2; 2.133329 ETH and liquidity 46141758126452008872416 in every real pool; the two 0.1333 ETH pools were tests with no buys); the
bot's first buy is at **+8 in all three real pools** (5 blocks after the add), 0.15-0.20 ETH, and **its tolerance is 5%** (calldata minOut /
tokens received = 0.9500 on all 90 bot buys decoded; Robinhood's and BNB's lines ran at 0.99); the pull is a **timer of about 4.1 minutes**
(+126, +128); the **Swap event's `sender` is the Universal Router for every swap, the bot's included** (its contract routes through it), so
the bot's buy is told apart only by its transaction (to the bot contract, selector `27f7e6ee`, the token in the calldata), which Flashblocks
shows pending; the fleet is **35 wallets** (the 31 plus `0x5f0190f1`, `0xa2deb9f0`, `0xaab209e7`, `0xf7b323ba`, all funded by the launch
wallet's +1 call); **no outsider has traded in any pool**, so the reaction to one is unknown.

## 3. The trade

The front, as on Robinhood (HANDOFF 3.2), timed off the liquidity add instead of the launch:

1. **Arm** on the launch: an `Initialize` with currency0 = 0, fee `BASE_FEE`, tick spacing `BASE_TICK_SPACING`, a hook whose low 14 address
   bits are `BASE_HOOK_FLAGS`; the launch transaction's selector `BASE_LAUNCH_SELECTOR` and calldata length `BASE_LAUNCH_CALLDATA_LEN`
   (read from the Flashblock's raw transaction if it was seen there, else `eth_getTransactionByHash`); the token's runtime code hash in
   `BASE_TOKEN_CODEHASHES` (`eth_getCode` at the arm); the launcher's code hash prefix `BASE_LAUNCHER_CODEHASH_PREFIX` when set. A
   mismatch logs `launch` with `skip` and the reason and arms nothing. The armed pool keeps its key (with the hook), sqrtPriceX96 and tick.
   The pool's state after that is folded from its own events in (block, logIndex) order: each Swap's recorded sqrtPriceX96 and liquidity
   (exact), each ModifyLiquidity's delta on the active range; `v4math` prices only our own buy and sell (its `buy_out_int` runs up to 6e-22
   relative LOW against the PoolManager, the safe side for a minOut; the confirmed add's ETH is computed from its liquidity at the pool's
   price, 2.1333285 ETH on the real pools, so no RPC read sits on the trade path).
2. **Fire** on the liquidity: the first `ModifyLiquidity` with a positive delta on the armed pool (expected at L+3; an arm with no add by
   L+`BASE_ADD_MAX_BLOCKS` expires). The pool's state is the Initialize price and the liquidity of the adds covering the current tick;
   every `Swap` on the pool before our fire moves it (`v4math`). The add's transaction value must be at least `BASE_MIN_POOL_ETH` (the
   0.133 ETH test pool is skipped). With the Flashblocks feed the add is recognised earlier, as a pending transaction to the armed pool's
   hook with selector `BASE_ADD_SELECTOR` and value >= `BASE_MIN_POOL_ETH`, and the fire goes then (the pending add's liquidity is not in any log yet: the
   minOut uses the liquidity a full-range position of the add's ETH value makes at the launch price, which `BASE_BUY_SLIP` covers; the
   confirmed `ModifyLiquidity` then fixes the state). The fire is refused when the head is past the add's block +
   `BASE_FIRE_MAX`, when a pull was seen, when a position is open, when halted or stopped, when the day's count is at
   `BASE_MAX_PER_DAY`, or when the relay holds less than the stake plus a margin. The buy: `FlipRelay.buy(key, stake, minOut, deadline)`
   with the stake min(`BASE_STAKE_ETH`, `BASE_STAKE_CAP_ETH`), minOut = the exact v4 output x (1 - `BASE_BUY_SLIP`), deadline now +
   `BASE_BUY_DEADLINE_S`, at the wallet's nonce, a type-2 transaction (chain 8453, `maxPriorityFeePerGas` `BASE_PRIO_GWEI`, `maxFeePerGas`
   = 2 x the head's base fee + the priority, at most `BASE_MAX_FEE_GWEI`, gas `BASE_BUY_GAS`), sent to every `BASE_SEND_URLS` at once.
3. **Sell**: `FlipRelay.sell(key, minOut, deadline)` at the next nonce (the relay sells everything it holds: no amount, no approval), on
   the first of:
   - **the bot's buy seen pending** (Flashblocks): a transaction to a `BASE_BOT_ROUTERS` address whose calldata carries the pool's token,
     after our buy was sent; the sell goes at once, aiming at the same block behind it;
   - **the bot's buy confirmed**: a `Swap` on the pool, after our buy's block, whose `sender` is in `BASE_BOT_SENDERS` (b10 says which
     address the Swap event names for the bot's buys), at any size (`exit: bot`);
   - **a paying buy behind ours**: any confirmed `Swap` buying (amount0 < 0) after ours whose price values our tokens at the stake x
     (1 + `BASE_TAKE_PROFIT`) plus the round trip's gas (`exit: take_profit`);
   - **the deadline**: the head (or a Flashblock) at our buy's block + `BASE_HOLD_BLOCKS` (`exit: deadline`, minOut 0).
   The sell's minOut is the ETH out at the tracked price x (1 - `BASE_SELL_SLIP`), 0 at the deadline. The `exit` values: `bot` (the bot's
   buy, pending or confirmed), `take_profit`, `deadline`, `pulled`, `buy_reverted`.
4. **The pull watch**: a `ModifyLiquidity` with a negative delta on our pool, or a pending `BASE_PULL_SELECTOR` call to its hook, marks it
   pulled: before our fire, the pool is skipped (`skip: pulled before our fire`); after our buy and at or before our sell's block, the trade
   is -100% (`exit: pulled`) and **the line halts** (`HALTED.base`); a pull within `BASE_NEAR_MISS_BLOCKS` after our buy halts too even when
   our sell landed first (the reaction is too fast to keep trading). A sell that reverted on a pool that was not pulled halts (`sold none`:
   the sell path is broken). `BASE_NONBOT_HALT` live trades in a row under `BASE_NONBOT_MIN_RET` halt (the decoy rule of HANDOFF 16.13).
   The owner's own `HALTED.base` holds across restarts; a halt stops new buys and still sells what is open.
5. **Settle** from the receipts: ETH in (the buy's value), the tokens (the Swap of our buy, or the token's Transfer to the relay), ETH out
   (the Swap of our sell), the gas of both (gasUsed x effectiveGasPrice + `l1Fee`), the return and the dollars (`BASE_ETH_USD`), the pull's
   block against our sell's: one `trade_done` line. `BASE_DAILY_STOP_USD` of losses stops new buys for the UTC day.
6. **Dry run** (`BASE_DRY_RUN=1`, the default): everything but sign and send. A dry buy is priced at the state of the block after the fire
   (behind that block's recorded swaps), follows every real swap, sells by the same rules at the chain's recorded price: `would_fire` and
   `trade_done` with `dry: true`. The dry run is how the line is watched before any money (RUNBOOK 4l).

One position at a time. Open positions are written to `base_positions.json` beside the log and taken back at a start (sold at once).

## 4. The feeds

- **Confirmed (required)**: one websocket to `BASE_WS_URL` with `eth_subscribe newHeads` (the clock: block number, timestamp, base fee) and
  `eth_subscribe logs {address: PoolManager, topics: [[Initialize, ModifyLiquidity, Swap]]}`. Every event of a sealed block arrives within
  about 100 ms. When the websocket is down or silent for `BASE_WS_SILENT_S`, the engine polls `eth_blockNumber` and `eth_getLogs` over
  `BASE_RPC_URL` for the blocks it missed (never skipping a block), and reconnects.
- **Flashblocks (optional, on by default; `BASE_FLASH_URL=0` turns it off)**: the pending-block stream. Each raw transaction is decoded
  (types 0x02, 0x00, 0x01, 0x04; 0x7e deposits skipped) for `to`, `value`, `data`, nonce; the sender is recovered only for the few that
  matter (the armed pool's hook, a bot router, our own wallet). It advances two actions: the fire (the add seen pending) and the sell (the
  bot's buy seen pending), and confirms our own transactions' inclusion early. Everything it does is also done by the confirmed feed a
  little later, so a Flashblocks outage costs speed, never correctness. The `flow` line reports both feeds' state.
- **Sends**: `BASE_SEND_URLS`, every one at once over warm connections, with a browser User-Agent (the sequencer's Cloudflare refuses
  Python's own, error 1010); the first "ok" or "already known" counts; "nonce too low" re-reads the nonce and signs once more. The
  sequencer refuses `eth_chainId` ("rpc method is not allowed"): a send-only endpoint passes the start's check by answering a malformed raw
  transaction with -32602 instead.
- **Reads**: `BASE_RPC_URL` (receipts, `eth_getCode`, `eth_getTransactionByHash`, `eth_getLogs` for the catch-up, the relay's balance),
  `BASE_READ_ALT_URL` once when it fails. `BASE_RPC_URL` defaults to publicnode because `mainnet.base.org` answers `eth_getLogs` with HTTP
  429 (measured Oct 14); `mainnet.base.org` is the alternate.
- **Files beside the log**: `HALTED.base` (read at the start and before every fire, so the owner's own file holds without a restart),
  `base_positions.json` (`{"positions": {...}}`, written on every change), and the engine holds an `fcntl` lock on `BASE_KEY_FILE` while
  live (what `deploy/base_wallet.py` and `deploy/base_ops.py` test before they sign).

## 5. Settings (`/etc/flip/base.env`; the code default in parentheses)

Feeds and keys: `BASE_DRY_RUN` (1), `BASE_LOG_PATH` (/var/log/flip/base.jsonl), `BASE_WS_URL` (wss://base-rpc.publicnode.com), `BASE_RPC_URL`
(https://base-rpc.publicnode.com), `BASE_READ_ALT_URL` (https://mainnet.base.org), `BASE_SEND_URLS` (comma-separated:
https://mainnet-sequencer.base.org,https://mainnet.base.org), `BASE_FLASH_URL` (wss://mainnet.flashblocks.base.org/ws; 0 = off), `BASE_WALLET` (""), `BASE_KEY_FILE`
(/etc/flip/base.key), `BASE_RELAY` (""), `BASE_POOL_MANAGER` (0x498581ff718922c3f8e6a244956af099b2652b2b), `BASE_HALT_FILE` (HALTED.base
beside the log), `BASE_WS_SILENT_S` (10).

The line's fingerprint: `BASE_LAUNCH_SELECTOR` (c3e0ff3d), `BASE_LAUNCH_CALLDATA_LEN` (260; 0 = any), `BASE_LAUNCHER_CODEHASH_PREFIX`
(225f9af97d88; "" = any), `BASE_TOKEN_CODEHASHES` (0x63ad5291cdef5d82cddf8e5d8d4c48bd6ad1de2394616ab66a6c6c6cceae63bb), `BASE_FEE` (5000),
`BASE_TICK_SPACING` (100), `BASE_HOOK_FLAGS` (0x80; -1 = any hook, 0 = no hook), `BASE_ADD_SELECTOR` (2346bb56), `BASE_PULL_SELECTOR`
(f2f230a8), `BASE_BOT_ROUTERS` (0x987d5db84d105c1f49391af409cc34c6050fb1d0), `BASE_BOT_SENDERS` ("" = off: b10 measured that the Swap
event's `sender` is the Universal Router for every swap, the bot's and anyone else's, so a sender rule cannot name the bot; the bot's buy
is recognised pending by its transaction, and a confirmed buy behind ours sells by the take-profit rule), `BASE_MIN_POOL_ETH` (1.0),
`BASE_ADD_MAX_BLOCKS` (10).

The trade: `BASE_STAKE_ETH` (0.002), `BASE_STAKE_CAP_ETH` (half the smallest room b11 measured; 0.005 until then), `BASE_BUY_SLIP` (0.03),
`BASE_BUY_DEADLINE_S` (20), `BASE_FIRE_MAX` (2 blocks after the add), `BASE_HOLD_BLOCKS` (6), `BASE_TAKE_PROFIT` (0.01), `BASE_SELL_SLIP`
(0.05), `BASE_SELL_DEADLINE_S` (30), `BASE_NEAR_MISS_BLOCKS` (3), `BASE_NONBOT_HALT` (5), `BASE_NONBOT_MIN_RET` (0.02), `BASE_MAX_PER_DAY`
(400), `BASE_DAILY_STOP_USD` (10), `BASE_ETH_USD` (2570), `BASE_PRIO_GWEI` (0.01: the bot pays 0.0011; a round trip of about 320k gas at
0.015 gwei plus two L1 data fees is about 0.2% of a 0.002 ETH stake; 0.05 would be 0.9%), `BASE_MAX_FEE_GWEI` (0.5), `BASE_BUY_GAS` (400000),
`BASE_SELL_GAS` (400000), `BASE_RELAY_MARGIN_ETH` (0.0005).

Every number is checked at the start (a wrong one stops the start naming it, as bnb_engine's `_setting`); a live start needs the wallet, the
key file, the relay (its `owner()` must be the wallet, its `pm()` the PoolManager) and `eth_chainId` 8453 on every endpoint.

## 6. Log lines (`/var/log/flip/base.jsonl`, one JSON per line, `ev`, `t`)

`start` (release, settings without secrets, dry, head), `flow` (every 60 s: head, lag_s, lag_max_s, ws, flash (booleans), head_src,
logs_to, flash_block, flash_msgs_min (the last minute's messages, about 330 when healthy), flash_total, flash_reconnects, flash_bad, dups,
reorgs, filled, launches, armed, trades, trades_done, halted, stopped, position, relay_eth), `launch` (block, pool, token, hook, fee, ts, launcher, selector, calldata_len, token_code, armed or skip + reason), `add` (pool,
block, eth, liquidity, pending or confirmed), `fire` / `would_fire` (pool, add_block, head, stake_wei, min_out, nonce, via: flash|logs),
`buy_sent`, `sell_sent` (hash, nonce, block_seen, reason), `bot_buy` (pool, block or pending, value, via), `pull` (pool, block, before:
fire|sell|after), `trade_done` (pool, token, buy_block, sell_block, eth_in_wei, tokens, eth_out_wei, gas_wei, l1_fee_wei, ret, usd, exit,
pulled_at, nonbot_streak, dry, live), `halt` (reason), `stop` (day, losses), `alarm` (what, at most one a key every 10 min), `skip`.

## 7. Files

| path | what |
|---|---|
| `src/base_engine.py` | the engine (this design); `python3 src/base_engine.py` runs it from the env |
| `tests/test_base_engine.py`, `tests/data/base_launch.json` | the engine against the 09:42 test pool's real events and transactions, the chain and both websockets stubbed |
| `research/session_oct14/base2433/b13_fixture.py` | builds the fixture from Base (Tenderly) |
| `deploy/base_wallet.py` | the Base wallet: `/etc/flip/base.key` (600) and `BASE_WALLET=` in `/etc/flip/base.env`; never prints the key |
| `deploy/base_relay_deploy.py`, `deploy/base_relay_sim.py` | deploy FlipRelay on Base and check it (code, owner, pm, a simulated buy); simulate a round trip on a live or past pool with the hook in the key |
| `deploy/base_ops.py` | `status`, `deposit`, `withdraw`, `sweep`, `payout` on Base |
| `deploy/base_results.py` | the results screen from the Base log |
| `deploy/base_setup.sh`, `deploy/flip-base.service` | the box: the env template, the hardened unit (as flip-bnb's), logrotate, a dry start |
| `docs/RUNBOOK.md` 4l | every box step, numbered, with expected output |

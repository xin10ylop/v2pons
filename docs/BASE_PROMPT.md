# Prompt for a new session on the Base engine

Paste everything below the line as the first message of a new Claude Code session on this repository. It is self-contained.

---

You are taking over a live trading engine on the Base chain. The repository is `v2pons`; the box runs branch
`claude/brave-gauss-55iyg8` (last commit 25fca04, release `base-0.2`). The owner runs the engine on their own AWS box and will
tell you what to adjust. This message gives you everything you need to understand the engine, change it safely, and get the
change onto the box. The repository is large: read only the files named here, and only the parts of them the task needs.

**Start by asking the owner to paste the report** (`sudo python3 ~/v2pons/deploy/base_results.py`). The state below is from
Oct 15 21:32 UTC; days may have passed.

## What the engine does

An operator (called "the 2.433 line" in the docs) runs a pump-and-pull pattern on Base with Uniswap v4. For each token it:
launches a pool through a per-launch launcher contract (block L), adds liquidity 3 blocks later (2.133 or 4.133 ETH on Oct 14,
1.533 ETH since 19:42 UTC Oct 14, native ETH paired), lets its own bot buy from about L+7 or L+8 (contract
`0x987d5db84d105c1f49391af409cc34c6050fb1d0`, selector `27f7e6ee`, 5% slippage tolerance) while its fleet of about 30 wallets
sells through the Universal Router, then removes the liquidity on a timer at about L+190 to L+225 (on Oct 14 L+126 to L+165),
sometimes much earlier (L+10 to L+40).

The engine buys a stake right after the liquidity add, through the owner's own relay contract, and sells into the bot's first
buy so the sale lands in the same block behind it. If the operator pulls the liquidity between our buy and our sale, the stake
is lost; the halts below make sure that happens at most once.

The trade, per launch:

1. **Arm** on the launch's fingerprint: native ETH as currency0, fee 5000, tick spacing 100, hook address flags 0x80 (checked on
   the PoolManager's `Initialize`), then the launch transaction's selector and calldata length, the token's runtime code hash,
   the launcher's code hash prefix and the hook's code size (8,951 B; the honeypot hook is 8,957 B).
2. **Fire** on the liquidity add, seen pending on the Flashblocks stream or confirmed in the PoolManager's `ModifyLiquidity`
   log, when the pool holds at least `BASE_MIN_POOL_ETH`. The buy is aimed at the add's block + `BASE_FIRE_DELAY_BLOCKS` (3).
3. **Buy** through `FlipRelay.buy(PoolKey, amountIn, minOut, deadline)` (selector `5ed06f60`), minOut the exact v4 output less
   `BASE_BUY_SLIP`.
4. **Sell** through `FlipRelay.sell(PoolKey, minOut, deadline)` (selector `137f1fdd`): on the bot's buy seen pending, else on the
   first paying buy behind ours (`BASE_TAKE_PROFIT`), else at our buy + `BASE_HOLD_BLOCKS` (6).
5. **Halt** (the file `/var/log/flip/HALTED.base`, which survives restarts) on: a pull before our sale; a pull within
   `BASE_NEAR_MISS_BLOCKS` of our buy; a pull within `BASE_NEAR_MISS_SELL_BLOCKS` of our sale; `BASE_NONBOT_HALT` weak trades in a
   row; the daily stop `BASE_DAILY_STOP_USD`. A halt stops new buys; an open position is still sold.

## The chase, and where the money came from

The operator's line is named for the 2.433 ETH it put in each pool on Robinhood Chain. Our first engine (`src/flip_engine.py`)
traded in front of it there. The operator left Robinhood on Oct 12, tested once on Ethereum, ran 52 pools on BNB Chain on Oct 13
and moved to Base on Oct 14, where `src/base_engine.py` follows it. On Base:

| when (UTC) | the operator's launch | the engine | trades | result |
|---|---|---|---|---|
| Oct 14 13:32 to 19:42 | call `c3e0ff3d` (260 B), launcher code `225f9af97d88`, pools 2.133 / 4.133 ETH | live, stake 0.02 ETH from 14:56 | 28 | +$49 |
| Oct 14 19:42 to 21:03 | new call `99dfa5c4` (868-1348 B), launcher code `53959585f666`, pools 1.533 ETH | idle: the fingerprint did not match | 0 | 0 |
| Oct 14 21:03 to Oct 15 08:22 | the same | adapted (release base-0.2), the best stretch | 58 | +$591 |
| Oct 15 07:16 onward | launcher code `aee87105d146`, hook 8,957 B: **a honeypot**, only its own wallets can sell | the prefix was added at 08:22 without the exit test; the first trade could not sell | 1 | -$51 |
| Oct 15 08:42 onward | the honeypot, still at 21:32 | idle on purpose: skips it (`launcher code 0xaee87105d146`) | 0 | 0 |
| **total** | | | **87** | **+$588** |

The honeypot's hook (`beforeSwap`, selector `575e24b4`) reverts with "meta error" on any sell whose sender is not one of the
wallets listed in the launch calldata. The PoolManager wraps it as `WrappedError` (`0x90bfb865`). Its token code, add, bot and
pull are identical to the sellable line, so chain measurement alone does not reveal it. Only a simulated sell does. The owner
took $500 (0.195 ETH) out to their own address on Oct 15.

## The chain

Base mainnet, chain id 8453. Uniswap v4 PoolManager `0x498581ff718922c3f8e6a244956af099b2652b2b`, Universal Router
`0x6ff5693b99212da76ad316178a184ab56d299b43`. Reads go to `https://base-rpc.publicnode.com` (mainnet.base.org answers
`eth_getLogs` with HTTP 429; publicnode serves logs and receipts only for recent blocks and answers older ones with "Archive
requests require a personal token"; from your session call it with curl, Python's urllib gets HTTP 403). Sends go to
`https://mainnet-sequencer.base.org` and `https://mainnet.base.org` at once. For older state and simulations, Tenderly's public
gateway `https://base.gateway.tenderly.co` works. You can read the chain from your session; you cannot reach the box.

## Files you need

| file | what it is |
|---|---|
| `docs/BASE.md` | The design. Section 2 is the operator's measured fingerprint, 3 the trade, 4 the feeds, 5 every setting with its default, 6 every log line. Read sections 2-6 first. |
| `docs/BASE_HANDOFF.md` | The record of Oct 14-15: the box's state, the live results, the operator's behaviour, open items, every box command. |
| `src/base_engine.py` | The engine, about 1,750 lines, release `base-0.2` (`RELEASE` near the top). |
| `src/v4math.py` | Exact integer v4 swap math, used for minOut. |
| `tests/test_base_engine.py` | 48 tests on the real 09:42 UTC Oct 14 pool (`tests/data/base_launch.json`). Every network call and the key are stubbed. Run: `python3 tests/test_base_engine.py`. |
| `contracts/FlipRelay.sol` | The relay, owner-only `buy` and `sell`. Deployed, do not change it. |
| `deploy/base_setup.sh` | Box install. It holds the template of `/etc/flip/base.env`: every `BASE_*` setting with its default and a comment. |
| `deploy/base_results.py` | The owner's screen: feeds, trades, last launches, halts, alarms. `--alerts` prints only trouble. |
| `deploy/base_ops.py`, `deploy/base_wallet.py` | Balances, deposit and withdraw. These sign on the box only. |
| `deploy/base_relay_sim.py` | **The exit test.** A buy and a sell through the relay's code on any pool at any block; nothing is sent. With no argument it takes the operator's latest pool. A honeypot shows "the simulated round trip REVERTED" with `0x90bfb865`. |
| `docs/RUNBOOK.md` section 4l | Every box step with its expected output. |
| `research/session_oct14/base2433/` | How the operator was measured: `REPORT_BASE2433.md` and scripts b01-b13. Reuse them as templates for chain reads. |

## How `src/base_engine.py` is laid out

Search by function name; line numbers drift.

- **Settings:** `settings()` reads every `BASE_*` variable through `_setting`, `_exact`, `_hex`, `_hexlist`, `_url`, and the
  lists `_launches` (`BASE_LAUNCH_SELECTOR`: `selector` or `selector/calldata_len`, comma-separated), `_prefixes`
  (`BASE_LAUNCHER_CODEHASH_PREFIX`) and `_sizes` (`BASE_HOOK_CODE_SIZES`). A new setting
  goes here, in `docs/BASE.md` section 5, and in the template in `deploy/base_setup.sh`.
- **Log and halts:** `log`, `alarm`, `halt`, `read_halt_file`, `roll_day`.
- **Launch detection:** `cheap_skip` (fee, tick spacing, hook flags, currency), `on_init` (the PoolManager's `Initialize`),
  `read_launch_tx` and `arm` (the launch transaction's selector and calldata length against `S.LAUNCHES`, the token code hash,
  the launcher code hash against `S.LAUNCHER_PREFIXES`, the hook's code size against `S.HOOK_CODE_SIZES`). Every rejected launch
  is logged as `skip` with its reason.
- **Pool state:** `new_pool`, `apply`, `fold`, `pool_state`, `eth_of`; `on_log` routes the PoolManager's logs; `on_pull` and
  `near_miss` handle a liquidity removal.
- **Flashblocks (pending transactions):** `on_flash`, `on_flash_tx` (the add, the bot's buy and the pull, seen pending),
  `pending_add`, `end_burst`.
- **The fire:** `add_info`, `try_fire`, `fire`.
- **The position:** `check_position`, `scan_swaps`, `sell_value`, `deadline`, `do_sell`, the dry path `check_dry` and
  `close_dry`, `trade_done`, and the `trader` thread.
- **Live transactions:** `send_signed`, `send_buy`, `send_sell`, `wait_receipt`, `settle_live`, `_settle_live`, `chain_pull`,
  `finish_live`. Type-2 transactions, priority `BASE_PRIO_GWEI`.
- **Restart safety:** `save_positions`, `load_position`, `take_back`, `restore_today`.
- **Start:** `start_checks`, `live_checks`, `start` (writes the `start` log line with every setting).
- **Feeds:** `run_feeds` runs `keep_connected` for the confirmed websocket (`confirmed_session` with its `reader` and its
  `watchdog`: 30 s of heads without a PoolManager log forces a reconnect) and for Flashblocks (`flash_session`), plus the HTTP
  `poller` fallback and the `ticker`.

## The box, as of 21:32 UTC Oct 15

- Service `flip-base`, live, release base-0.2, branch `claude/brave-gauss-55iyg8` at 25fca04. Settings in `/etc/flip/base.env`,
  log in `/var/log/flip/base.jsonl`.
- Wallet `0x492a40b43ce221ec2c952cda473f441e365dea62`; relay `0x0e24493c662e62b33d371376e0ac181eb193a31d` (owner: the wallet).
  The key is `/etc/flip/base.key` on the box.
- Settings that differ from the code's defaults: `BASE_DRY_RUN=0`, `BASE_STAKE_ETH=0.02`, `BASE_STAKE_CAP_ETH=0.02`,
  `BASE_DAILY_STOP_USD=60`, `BASE_NEAR_MISS_SELL_BLOCKS=1`, plus `BASE_WALLET` and `BASE_RELAY`. The fingerprint lines are
  `BASE_LAUNCH_SELECTOR=c3e0ff3d/260,99dfa5c4` and `BASE_LAUNCHER_CODEHASH_PREFIX=225f9af97d88,53959585f666`;
  `BASE_HOOK_CODE_SIZES` is not set, so the default 8951 applies.
- Relay 0.045 ETH (about two stakes), wallet 0.018 ETH (gas). No open position, no halt.
- **The situation:** the operator runs the honeypot launcher and the engine skips every one of its pools, by design. The owner
  chose to wait. If the operator goes back to either sellable launcher, the engine trades again with no change. The sign is a
  `fire` row in the report's bottom table and the day's trade count moving.

## Known open items

- The exit test is manual. The engine does not simulate a sell before it buys, which is how the honeypot cost a stake. An
  automatic check at arm time (an `eth_call` round trip through the relay's code, as `deploy/base_relay_sim.py` does; skip the
  pool if the sell reverts) would catch a new honeypot under any fingerprint. Not built yet.
- The report's TRADES line covers a rolling 24 hours, so its total drops as old trades age out. The owner has read that as a
  loss; the relay balance is the real figure.

- The code's default for `BASE_NEAR_MISS_SELL_BLOCKS` is 3; the box runs 1 because 3 halted on every quick pull.
- The stake's ceiling was never measured on chain. 0.02 ETH was set by judgement.
- publicnode drops its logs subscription about every 10 minutes; the engine reconnects at once and the poller covers the gap.
- `health.sh` does not run `base_results.py --alerts`.
- Untested: a reorg of our own buy's log, `restore_today` across a restart, the relay under the stake at the fire.

## How to make a change

1. Read the relevant part of `docs/BASE.md` and the functions above.
2. If the change depends on the operator's behaviour, measure it from the chain first, with a script beside the ones in
   `research/session_oct14/base2433/`, and save its output there.
3. Change the code. Add or adjust a test in `tests/test_base_engine.py` for every behaviour you change. A new setting also goes
   in `docs/BASE.md` section 5 and in the template in `deploy/base_setup.sh`.
4. Run `python3 tests/test_base_engine.py`. All tests must pass.
5. Commit with a message that says what changed and why, and push. The box tracks `claude/brave-gauss-55iyg8`; if your session
   must push to another branch, give the owner the command to check that branch out on the box.
6. Give the owner the box commands, one block at a time, with the output to expect.

A settings-only change needs no code. The owner runs, between launches:

```
set_base() { sudo grep -q "^$1=" /etc/flip/base.env && sudo sed -i "s|^$1=.*|$1=$2|" /etc/flip/base.env || echo "$1=$2" | sudo tee -a /etc/flip/base.env >/dev/null; }
set_base BASE_SETTING_NAME value
sudo python3 ~/v2pons/deploy/base_results.py | grep 'open position'
sudo systemctl restart flip-base && sleep 20 && systemctl is-active flip-base
```

A code change reaches the box with:

```
cd ~/v2pons && git pull -q --ff-only && sudo systemctl restart flip-base && sleep 20 && systemctl is-active flip-base
```

To check what the running engine read, have the owner paste:

```
sudo grep '"start"' /var/log/flip/base.jsonl | tail -1 | grep -o '"[A-Z_]*":[^,]*' | head -40
```

To try a change without money, set `BASE_DRY_RUN=1` and restart. The engine then logs `would_fire` and `trade_done` with
`"dry": true` and signs nothing. Set it back to 0 to go live.

The owner's main screens:

```
sudo python3 ~/v2pons/deploy/base_results.py | head -30
sudo grep '"ev":"skip"' /var/log/flip/base.jsonl | tail -6 | cut -c1-260
sudo grep '"ev":"alarm"' /var/log/flip/base.jsonl | tail -6 | cut -c1-220
```

## Rules

- **Never accept a new launcher, hook or token without the exit test.** Run `deploy/base_relay_sim.py <poolId>` (on the box, or
  the same `eth_call` from your session) on one of its pools between the add and the pull. Only a sell that gets ETH back makes it
  acceptable. Chain measurement of the token, add, bot and pull is not enough: the honeypot matched all of them.
- **A pool whose exit test fails is not traded.** Do not try to get around a hook that blocks sells. Sit it out and wait for a
  sellable line, or point the engine at a different one if the owner asks.

- Never print, paste or commit the key in `/etc/flip/base.key`. No command you give should display it.
- The owner works by pasting your commands into the box and pasting the output back. Give one block at a time and say what to
  expect.
- Restart only when the screen shows `open position: none`.
- Run the tests before every push.
- The stake is the most one trade can lose. Change it only when the owner asks.

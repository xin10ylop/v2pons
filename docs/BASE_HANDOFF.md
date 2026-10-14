# The Base line: what was built, what happened on Oct 14 2026, how to continue

This file is the complete record of the Base line's first day, written so its owner can carry on alone or hand it to a new
session. Paste it whole as the opening message of a new session, or read it as a checklist. Every path below is relative to
the repository root. The design itself is `docs/BASE.md`; the box steps are RUNBOOK section 4l; the research is
`research/session_oct14/base2433/`; the earlier history is HANDOFF sections 16.24 and 16.25.

---

## The prompt for a new session

The full prompt for a new session, with everything it needs to continue and adjust the engine, is `docs/BASE_PROMPT.md`.
Paste its content below the line as the first message.

---

## 1. The goal and the trade

The 2.433 operator ran a pump-and-pull line on Robinhood Chain: it launches a token pool, its own bot buys into it, and it
removes the liquidity minutes later. Our Robinhood engine (`src/flip_engine.py`) traded in front of that bot. On Oct 14 the
operator moved the line to Base (chain 8453). This work ports the front to Base.

The trade, per launch:

1. **Arm** on the launch transaction's fingerprint: the launcher's selector and calldata length, the launcher's code hash,
   the token's code hash, fee 5000, tick spacing 100, a hook whose address flags are 0x80 (beforeSwap).
2. **Fire** on the liquidity add, which comes 3 blocks after the launch. The add is seen pending on the Flashblocks stream,
   or confirmed through the PoolManager's `ModifyLiquidity` log. Pools under 1 ETH are skipped (the operator's test pools).
   The buy is aimed at the add's block + 3 (`BASE_FIRE_DELAY_BLOCKS`).
3. **Buy** through our own FlipRelay contract (`contracts/FlipRelay.sol`, unchanged from Robinhood, redeployed on Base), with
   minOut the exact Uniswap v4 output less 3%.
4. **Sell** into the operator's bot's first buy, seen pending, so our sale lands in the same block behind it. If no bot buy
   is seen, it sells on the first paying buy behind ours, or at our buy + 6 blocks.
5. **Halt** the line (`/var/log/flip/HALTED.base`) when the operator pulls the liquidity before our sale, within 3 blocks of
   our buy, or within `BASE_NEAR_MISS_SELL_BLOCKS` of our sale. A halt stops new buys and survives restarts.

The only way to lose a whole stake is a pull between our buy and our sale. No engine can prevent that; the halts make sure
the operator gets one such shot, not a series, and the stake is the most one trade can lose.

## 2. What is in the repository

| path | what it is |
|---|---|
| `docs/BASE.md` | The design: chain, the operator's fingerprint, the trade, the feeds, every `BASE_*` setting with its default (section 5), every log line (section 6). |
| `src/base_engine.py` | The engine, release base-0.1. |
| `tests/test_base_engine.py`, `tests/data/base_launch.json` | 47 tests against the real 09:42 UTC pool's events; no network. |
| `contracts/FlipRelay.sol`, `contracts/FlipRelay.json` | The relay: `buy(PoolKey,amountIn,minOut,deadline)` and `sell(PoolKey,minOut,deadline)`, owner-only. |
| `deploy/base_setup.sh`, `deploy/flip-base.service` | Install on the box: venv packages, `/etc/flip/base.env` from a template, logrotate, the hardened unit. Idempotent. |
| `deploy/base_wallet.py` | Creates the line's wallet and key file; `withdraw` sends the wallet's ETH to an address you give. |
| `deploy/base_relay_deploy.py` | `--check`, then the relay's deployment with `--write-env`. |
| `deploy/base_relay_sim.py` | A simulated round trip through the relay's code on the operator's latest pool; nothing is sent. |
| `deploy/base_ops.py` | `status`, `deposit`, `withdraw` (relay to wallet), `sweep`, `payout`. |
| `deploy/base_results.py` | The screen: feeds, trades, the last launches, halts, alarms; `--alerts` for a quiet check. |
| `docs/RUNBOOK.md` section 4l | Every box step, numbered, with its expected output. |
| `research/session_oct14/base2433/` | How the operator was found and measured on Base: `REPORT_BASE2433.md` and the scripts b01-b13 with their outputs (there is no b11: that measurement was not completed). |

## 3. What is on the box now

| item | value |
|---|---|
| service | `flip-base`, LIVE (`BASE_DRY_RUN=0`), build 51b4daa, restarted about 19:13 UTC Oct 14 |
| wallet | `0x492a40b43ce221ec2c952cda473f441e365dea62` (key in `/etc/flip/base.key`, mode 600, never printed) |
| relay | `0x0e24493c662e62b33d371376e0ac181eb193a31d` (owner: the wallet) |
| settings file | `/etc/flip/base.env` |
| log | `/var/log/flip/base.jsonl` (rotated daily, 30 kept) |
| halt file | `/var/log/flip/HALTED.base` (absent at the last check) |
| balances at 20:27 UTC | relay 0.037 ETH, wallet 0.0117 ETH |

The settings that differ from the defaults in `docs/BASE.md` section 5:

```
BASE_DRY_RUN=0
BASE_WALLET=0x492a40b43ce221ec2c952cda473f441e365dea62
BASE_RELAY=0x0e24493c662e62b33d371376e0ac181eb193a31d
BASE_STAKE_ETH=0.02
BASE_STAKE_CAP_ETH=0.02
BASE_DAILY_STOP_USD=60
BASE_NEAR_MISS_SELL_BLOCKS=1
```

`BASE_NEAR_MISS_SELL_BLOCKS` is 1 on the box and 3 in the code's default. The reason is in section 6. Check what the running
engine actually read with:

```
sudo grep '"start"' /var/log/flip/base.jsonl | tail -1 | grep -o '"[A-Z_]*":[^,]*' | head -40
```

The other services on the box: `flip-engine` (Robinhood, untouched by this work) and `flip-bnb` (stopped and disabled since
Oct 14 08:10 UTC, HANDOFF 16.23).

## 4. Oct 14, hour by hour (UTC)

| time | what happened |
|---|---|
| 09:32-10:35 | The operator's first five Base launches: two 0.133 ETH tests, three 2.133 ETH pools. Found by the 09:53 watch. |
| 10:35-13:15 | Operator idle. The engine, tests, tooling and runbook were built and pushed in this window. |
| ~13:00-13:30 | Box install, dry run, wallet created and funded with about 0.03 ETH, relay deployed, 0.004 ETH deposited. |
| 13:29 | Dry gate passed: 3 dry trades, all sold into the bot's buy, +12.3% mean. |
| 13:32 | Live at 0.002 ETH. |
| 13:37 | First live trade: +24.5%, $1.26. Buy in the add's block, sale in the bot's block. |
| 13:41 | Stake 0.005 ETH (0.0065 ETH more into the relay). |
| 14:16 | Stake 0.01 ETH, daily stop $30 (0.0075 ETH more into the relay). |
| 14:31 | First pull close behind our sale: 2 blocks after it. The trade was still up. |
| 14:45 | Pools grew from 2.133 to 4.133 ETH, which roughly halved the return. A decoy first fleet buy of 0.025 ETH appeared. |
| 14:49 | Commit f56193a: buy at add + 3 instead of in the add's block; halt on a pull within 3 blocks after our sale. |
| 14:56 | Stake 0.02 ETH, cap 0.02, daily stop $60. No deposit needed: the relay already held enough. |
| 14:57 | Pull 3 blocks behind our sale. The new rule halted the line. 19 trades, 19 up, +$34.09 at that point. |
| 15:22 | Live again with `BASE_NEAR_MISS_SELL_BLOCKS=1` and the halt file removed. |
| 15:38 | First losing trade: the bot never bought while we held, a deadline exit at -1.0%, -$0.51. |
| 15:38-17:17 | Operator paused. Its 35 fleet wallets still held about 4.1 ETH on Base. |
| 17:54-18:27 | The engine missed about 17 launches: the websocket delivered block heads but no PoolManager logs. |
| 18:29 | Commit d0bfc07: a logs watchdog that reconnects after 30 s of heads without a log. Restarted 18:51. |
| 19:12 | Commit 51b4daa: reconnect at once on publicnode's subscription-drop notice. Restarted about 19:13. |
| 19:14-19:26 | Three more trades: +2.6%, +2.5%, +5.1%. |
| 19:42 | The operator changed its launch transaction. The engine has matched none of its launches since. See section 7. |
| 20:27 | Totals below. Engine running, idle, nothing open. |

## 5. The results

| measure | value |
|---|---|
| live trades | 28 |
| up | 27 |
| the one down | 15:38 pool, deadline exit, -1.0%, -$0.51 |
| net | +$48.60 (about 0.019 ETH at $2,570) |
| stakes used | 0.002, 0.005, 0.01, 0.02 ETH |
| deposited into the relay | 0.018 ETH in three deposits |
| relay at 20:27 | 0.037 ETH |
| wallet at 20:27 | 0.0117 ETH |
| pulls that cost a stake | none |

Returns depended on the pool size and on the size of the bot's first buy behind ours. In the 2.133 ETH pools they ran +6% to
+26%. In the 4.133 ETH pools they ran +2% to +7%, which at 0.02 ETH is about $1 to $4 a trade.

Every trade is in the box's log. To print them:

```
sudo grep '"trade_done"' /var/log/flip/base.jsonl | python3 -c "import sys,json,time; [print(time.strftime('%m-%d %H:%M:%S',time.gmtime(e['t'])), 'live' if e.get('live') else 'dry ', e.get('exit'), f\"{e.get('ret',0):+.1%}\", f\"\${e.get('usd',0):+.2f}\", 'buy', e.get('buy_block'), 'sell', e.get('sell_block'), 'pulled_at', e.get('pulled_at')) for e in map(json.loads, sys.stdin)]"
```

To keep that list in the repository, redirect it to a file on the box, copy it here and commit it.

## 6. What the operator did, and what the engine does about each

| behaviour | when seen | the engine's answer |
|---|---|---|
| Fixed sequence: launch at L, liquidity at L+3, bot's first buy at L+7 or L+8, timer pull at about L+126 to L+165. | All day | The trade in section 1. |
| Pool size raised from 2.133 to 4.133 ETH. | From 14:45 | None needed. It only halves the return. |
| Decoy first fleet buy (0.025 ETH at +8). | 14:45 | The engine sells into it for about -1%. Five weak trades in a row halt the line. |
| Quick pull 2-3 blocks after our sale, at L+10 or L+11, always after its own bot's first buy. | 14:31-14:57, then also in pools we did not touch | Our sale is in the bot's block, so these came after it. A pull in our sale's block or the next one halts the line (`BASE_NEAR_MISS_SELL_BLOCKS=1`). At 3 it halted on every quick pull, which is why the box runs 1. |
| Bot did not buy while we held. | 15:38, once | The deadline exit at our buy + 6 blocks, about -1%. |
| Pauses of hours, fleet funds left in place. | 10:35-13:15, 15:38-17:17 | Nothing to do. The engine waits. |
| Change of launch transaction. | 19:42 | The engine skips the launch and logs why. Trades are lost, money is not. |

Not seen, and with no answer: a pull before its own bot's first buy, inside our window of about two blocks. That costs one
stake and halts the line. A token whose code freezes outside holders (the other BNB operator's trick, HANDOFF 16.23) would
also cost a stake. The engine only arms on the token code hash in `BASE_TOKEN_CODEHASHES`, which passed the exit test.

## 7. Where the work stopped

**What was finished.** Everything in section 2 is built, tested (47 tests) and pushed. The engine is installed on the box and
has run live since 13:32 UTC Oct 14. The last code change is commit 51b4daa, which the box runs since about 19:13 UTC. Nothing
on the branch is half-done: every commit passes the tests, and no change is waiting to be pulled on the box.

**What happened last.** From 19:42 UTC every launch the operator made failed the engine's launch check. The engine's skip lines
read `launch selector 99dfa5c4, not c3e0ff3d`. Those pools passed the engine's other checks: native ETH pair, fee 5000, tick
spacing 100, the operator's hook flags. The engine logs each one as a skip and trades none of them. This is the designed
behaviour for an unrecognised launch. The change was noticed at about 20:25 UTC from the skip lines on the owner's screen.

**The state at the end.** The engine runs and reads the chain, holds no position, and earns nothing until a launch matches its
fingerprint again. Relay 0.037 ETH, wallet 0.0117 ETH, 28 live trades, +$48.60.

**What was not done.**

- The engine was adapted to the operator's new launch transaction in the commit after 51b4daa (measured on its first twelve pools:
  selector 99dfa5c4, a fresh launcher of code hash 53959585f666... each time, calldata 868-1348 B, the same token code, the add 2346bb56
  at L+3 of 1.533 ETH (two early pools of 0.053 ETH, under `BASE_MIN_POOL_ETH`), the pull f2f230a8 at +13 to +224). The box's env must
  set `BASE_LAUNCH_SELECTOR=c3e0ff3d/260,99dfa5c4` and `BASE_LAUNCHER_CODEHASH_PREFIX=225f9af97d88,53959585f666` and drop
  `BASE_LAUNCH_CALLDATA_LEN` (refused if set) before the restart.
- The stake's ceiling was not measured on chain (section 8).
- The code's `BASE_NEAR_MISS_SELL_BLOCKS` default was not brought in line with the box (section 8).

## 8. Known issues and open items

- **publicnode drops its logs subscription about every 10 minutes.** The engine reconnects at once on the drop notice, and the
  30 s watchdog catches any silent drop. The screen may show `websocket False` for a moment; the HTTP poller covers the gap.
- **The stake's ceiling was never measured on chain.** The measurement of how much room the bot's 5% tolerance leaves was
  not completed. The 0.02 ETH stake was set by judgement after 18 clean trades.
- **`BASE_NEAR_MISS_SELL_BLOCKS` default.** The code's default is 3 and the box runs 1. Decide which the code should ship with.
- **`health.sh` does not run `base_results.py --alerts`.** Run it yourself or add it.
- **Untested paths:** a reorg of our own buy's log; `restore_today` across a restart; the relay under the stake at the fire.
- **HANDOFF 16.24 says "on the branch, not on the box".** That was true when written; 16.25 records the go-live.

## 9. Commands for the box

Run them one at a time. If one prints something unexpected, stop and read it before the next.

The screen:

```
sudo python3 ~/v2pons/deploy/base_results.py | head -30
```

A quiet check (prints nothing when all is well):

```
sudo python3 ~/v2pons/deploy/base_results.py --alerts
```

Balances and service state, without the key:

```
sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_ops.py status
```

The last skips, alarms and halts:

```
sudo grep '"ev":"skip"' /var/log/flip/base.jsonl | tail -6 | cut -c1-260
sudo grep '"ev":"alarm"' /var/log/flip/base.jsonl | tail -6 | cut -c1-220
sudo grep '"ev":"halt"' /var/log/flip/base.jsonl | tail -3 | cut -c1-260
```

Change a setting, then restart between launches:

```
set_base() { sudo grep -q "^$1=" /etc/flip/base.env && sudo sed -i "s|^$1=.*|$1=$2|" /etc/flip/base.env || echo "$1=$2" | sudo tee -a /etc/flip/base.env >/dev/null; }
set_base BASE_STAKE_ETH 0.02
sudo python3 ~/v2pons/deploy/base_results.py | grep 'open position'
sudo systemctl restart flip-base && sleep 20 && systemctl is-active flip-base
```

Clear a halt (only after reading why it halted):

```
sudo rm -f /var/log/flip/HALTED.base && sudo systemctl restart flip-base
```

Pull new code:

```
cd ~/v2pons && git pull -q --ff-only && sudo systemctl restart flip-base && sleep 20 && systemctl is-active flip-base
```

Take the money out (RUNBOOK 4l step 9). The first line stops the engine and moves the relay's ETH to the wallet. The second
sends the wallet's ETH to your own address on Base and asks you to type the address again:

```
sudo systemctl stop flip-base && sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_ops.py withdraw
sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/base_wallet.py withdraw 0xYOUR_OWN_ADDRESS
```

Stop new buys but keep the engine running, so an open position still sells (RUNBOOK 4l step 9):

```
echo "owner stop" | sudo tee /var/log/flip/HALTED.base >/dev/null && sudo systemctl restart flip-base
```

Stop the line for good, once the screen shows `open position: none` (RUNBOOK 4l step 9):

```
sudo systemctl disable --now flip-base
```

## 10. Rules that stay in force

- Never display, paste or commit `/etc/flip/base.key`. Nothing in this repository needs the key on a screen.
- Restart only when `base_results.py` shows no open position. A restart during a trade is recovered from
  `/var/log/flip/base_positions.json`, but it costs the trade's timing.
- Run the tests before every push.
- After a halt, read the halt line and the trade before clearing it.
- The stake is the most one trade can lose. Size it to the loss you accept, not to the gain you want.

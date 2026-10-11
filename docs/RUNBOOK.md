# Runbook: from a fresh wallet to the $3 test

Everything runs on the Ohio box beside the Pons engine and touches none of it: its own wallet, relay, venv, env file, service and log.

## 0. What has been verified before this runbook (Oct 8)

- The operator is still launching: 14 launches between 10:30 and 11:45 UTC on Oct 8, about 7 an hour; fees that morning 0.06-0.47%,
  one at 1% at 12:00 (the fee moves; the engine selects by fee and logs the rest).
- The pricing: `v4math` reproduces 33,769 real buys to a median relative error of 6e-15 and the relay's simulated buy to one unit.
- The relay: a buy and a sell through `FlipRelay` on a live operator pool, simulated on the real PoolManager (`deploy/relay_sim.py`):
  the buy returned exactly the predicted tokens, the sell returned the ETH minus the two fees, nothing left behind, `minOut` enforced.
- Gas: a swap on these pools uses about 110k gas, $0.006; a round trip about $0.015.
- The feed: every crowd buy carries its ETH as the transaction value and the token address in its calldata, so the trigger is
  readable from the feed with no decoding of the router's commands.
- The engine on a scripted feed (`tests/test_engine.py`): armed from the receipt, fired at the reserved nonce with the predicted
  `minOut`, the sell at the next nonce on a buy behind ours worth `TAKE_PROFIT` or at the buy block + 2, the trade priced from the
  receipts; the gates; the dry run; stale frames; the halt.

## 1. Install (once)

    cd ~ && git clone https://github.com/xin10ylop/v2pons && cd v2pons && sudo bash deploy/flip_setup.sh

This creates `/opt/flip-venv`, `/etc/flip/engine.env` (DRY_RUN=1, no wallet), `/var/log/flip/engine.jsonl` and the `flip-engine`
service, and starts the dry run. Nothing is signed or sent until `DRY_RUN=0`, and that needs `WALLET`, `PRIVATE_KEY` and `RELAY`.

## 2. The dry run (one to two days)

The engine watches every launch and logs what it would do. Read it:

    sudo python3 ~/v2pons/deploy/englog.py 24 | grep -c '"ev":"armed"'                 # launches seen
    sudo python3 ~/v2pons/deploy/englog.py 24 | grep '"ev":"would_fire"' | tail -5
    sudo /opt/flip-venv/bin/python3 ~/v2pons/src/score.py /var/log/flip/engine.jsonl 24   # every decision priced from the chain

The dry run passes when, over at least 10 decisions:

1. `arm_ms` (launch seen to pool armed) is under 300 ms on most launches, and `first_buy` offsets sit near the backtest's 22/44/64 blocks
   (p10/50/90), i.e. the engine sees the launch before the crowd's first buy.
2. `react_ms` on `would_fire` is under 20 ms.
3. `score.py`'s paper return at land 2 is near the backtest (about +6% mean at hold 7, 90%+ winning) **on the days of the dry run**: the
   edge must still be there when we go live, not only on Oct 5-8.
4. The launcher is still the same contract and its launches still carry sub-1% fees (`armed` lines: `fee`, `eligible`). If the operator
   moved to a new launcher, add it to `LAUNCHERS`; if its fees are back above 1%, there is no trade, stop here.

## 3. The wallet and the relay

1. Make a new wallet (never the Pons wallet). Fund it with about 0.003 ETH for gas (a deploy and a hundred round trips).
2. Put `WALLET=0x...` and `PRIVATE_KEY=0x...` in `/etc/flip/engine.env` (`sudo nano`, keep mode 600).
3. Deploy the relay and write its address into the env file:

        sudo systemctl stop flip-engine
        sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_deploy.py --write-env

   It refuses an artifact that does not match the source, checks the code on the chain byte for byte with the owner and the PoolManager
   filled in, checks `owner()` and `pm()`, and simulates a buy on the operator's latest live pool.
4. Put the stake in the relay: ten trades at $3 is 0.012 ETH; the stake is reused, so 0.003 ETH (two stakes) is enough:

        sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py deposit 0.003
        sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py status

## 4. Go live: the $3 test

    set_kv() { sudo grep -q "^$1=" /etc/flip/engine.env && sudo sed -i "s|^$1=.*|$1=$2|" /etc/flip/engine.env || echo "$1=$2" | sudo tee -a /etc/flip/engine.env >/dev/null; }
    set_kv DRY_RUN 0 && set_kv STAKE_ETH 0.0012 && set_kv MAX_TRADES_PER_DAY 10 && set_kv DAILY_STOP_USD 15
    sudo systemctl restart flip-engine && sleep 8 && sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"start"' | tail -1

The start line must show `"dry_run":false`, the relay's owner equal to the wallet, `relay_eth` at or above the stake. The engine then
trades at most ten times a day and stops for the day at -$15.

After every trade (`"ev":"trade_done"` in the log, and `score.py`), the three questions the test exists to answer:

| question | where to read it | the trap answer | the edge answer |
|---|---|---|---|
| Did our buy fill where planned? | `buy_offset` (blocks after the trigger), `buy.status` | reverted on `minOut` (a crowd ahead of us) or offset above 3 | offset 1-2, filled near `expected_tokens` |
| Did the crowd keep buying behind us? | `score.py`: buys and ETH behind in the hold | 0-1 buys | 3+ buys, as in the backtest |
| Did the operator pull on us? | `pull_after_buy_blocks` against `hold_blocks` | a pull inside the hold, or within 20 blocks of our buy | no pull near our buy; `ret` near the paper return |

**Stop rules (any one ends the test; back to DRY_RUN=1):**

- one trade with a liquidity pull at or before our sell (release 0.3 halts itself on it: `/var/log/flip/HALTED`), or three with a pull
  within 20 blocks of our buy (the operator reacts to us);
- five trades done with a mean return under +1% while `score.py`'s paper return on the same launches is above +3% (we land or sell
  too late: fix the timing before spending more);
- the daily stop (-$15) or three reverted buys in a row (the guard is wrong for this tier, re-set `BUY_SLIP` from the landings);
- the operator stops launching sub-1% pools (no `eligible` launch for six hours).

**Pass:** eight or more fills, 70%+ positive, mean return within 2 points of the paper, no pull inside any hold. Then the stake steps
straight to $50: `STAKE_ETH 0.0195`, `DAILY_STOP_USD 150`, and 0.04 ETH in the relay (`relay_ops.py deposit 0.04`), and the same three
questions are asked again over the next ten trades. The $50 step is the one that tests whether the operator's reaction depends on
the size of the buy (in the data, bigger outside buys were pulled more often); the $3 step proves the mechanics for a few dollars
and a couple of hours first.

## 4b. Release 0.4: the exit, through the relay (read this before any more live trades)

What the eight live trades say (`research/live_trades.py`, `research/data/live_trades_oct8.txt`; the README has the table): every
-100% is a sell that landed after the operator's pull, every other trade a sell that landed before it. On the relay the pull came
5-13 blocks after each of our buys; the money in every win was one crowd buy already on its way, landing 1-3 blocks behind ours.
Release 0.3 sells on the first buy behind ours worth 1%, lands by our buy + 4 in any case, and halts itself if a pull ever beats the
sell. Release 0.4 removes release 0.2's router route (its one trade, 14:32, was not pulled on, but lost 9.3% by selling 90% of its
tokens, and its approvals made the sell a block slower): the relay is the only route again, so the stake goes back into the relay.

The leftovers of the first eight trades are worthless (their pools were pulled): the relay holds the tokens of trades 2, 3 and 7, the
wallet 10% of trade 8's (token `0x5f9215b0...`). Nothing to sell.

1. Stop the live engine (release 0.2) and switch the env file to the dry run before anything restarts it:

        sudo systemctl stop flip-engine
        set_kv() { sudo grep -q "^$1=" /etc/flip/engine.env && sudo sed -i "s|^$1=.*|$1=$2|" /etc/flip/engine.env || echo "$1=$2" | sudo tee -a /etc/flip/engine.env >/dev/null; }
        set_kv DRY_RUN 1

2. The code, and the env file without the router's settings:

        cd ~/v2pons && git fetch origin claude/pensive-rubin-rkj996 && git checkout -B claude/pensive-rubin-rkj996 origin/claude/pensive-rubin-rkj996
        sudo sed -i '/^ROUTE=/d;/^UNIVERSAL_ROUTER=/d' /etc/flip/engine.env
        set_kv BUY_DEADLINE_S 3 && set_kv GAS_HEADROOM 3 && set_kv BUY_SLIP 0.03 && set_kv HOLD_BLOCKS 4 && set_kv SELL_LEAD_BLOCKS 2 && set_kv SELL_FALLBACK_S 0.5 && set_kv TAKE_PROFIT 0.01 && set_kv MAX_TRADES_PER_DAY 3

   The env file was written with `BUY_SLIP=0.10`, `HOLD_BLOCKS=7` and `SELL_FALLBACK_S=1.2`, and release 0.2 set `BUY_DEADLINE_S 0` and
   `GAS_HEADROOM 1.5`; the code's defaults only apply to a fresh file, so every value is set here.

3. The tests and a relay round trip on a live pool (no transaction is sent):

        /opt/flip-venv/bin/python3 tests/test_v4math.py && /opt/flip-venv/bin/python3 tests/test_engine.py
        /opt/flip-venv/bin/python3 deploy/relay_sim.py

   Every test line starts with `ok`. The simulation ends with `accounting ok` and `TooLittleOut ok`. If it says `no unpulled operator
   pool`, the operator has no live pool at that moment: run it with any live ETH pool's id as its argument (the relay works on any
   hookless ETH pool), or skip it (the relay itself has not changed since its seven fills).

4. The stake back into the relay (the engine must be stopped), and the dry run:

        sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py deposit 0.003
        sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py status
        sudo bash deploy/flip_setup.sh

   `status` must show the relay at 0.003 ETH and `owner ... == wallet`. The setup's last line (the start line) must show
   `"release":"0.4"`, `"dry_run":true`, `"hold_blocks":4`, `"take_profit":0.01`, `"buy_slip":0.03`, `"halted":null`, and `relay_eth` 0.003.

5. Wait for two operator launches in the dry run. Each `would_fire` is followed by a `buy_seen` with `"dry":true` at the planned block
   and a `would_sell` with `after_buy` 2 or less, its `why` either `take profit: ...` or `deadline: ...`. `score.py` prices them with the
   same exit. Then live, three trades:

        set_kv DRY_RUN 0 && sudo systemctl restart flip-engine && sleep 8 && sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"start"' | tail -1

   The start line must show `"release":"0.4"`, `"dry_run":false`, `relay_eth` at 0.0012 or more and `"halted":null`.

To see every trade as it happens (one line per step, a beep on each finished trade or alarm; Ctrl-C stops the watching, not the
engine; inside tmux it survives the SSH session):

    sudo bash ~/v2pons/deploy/watch.sh
    tmux new -s watch 'sudo bash ~/v2pons/deploy/watch.sh'          # detach with Ctrl-b d, come back with: tmux attach -t watch

After each `trade_done`, the line that matters:

| field | expected | if not |
|---|---|---|
| `sell_after_buy_blocks` | 2-4 | over 4: the feed or the send is slow; read `sell_sent.ms_since_fire` |
| `pulled_before_sell` | `false` | `true`: the engine halted itself; the operator's reaction is now faster than our exit. Stop here. |
| `pull_after_buy_blocks` | above `sell_after_buy_blocks` (5-13 on the seven relay trades) | |
| `sell_why` | `take profit` when a crowd buy came behind ours, else `deadline` | |
| `ret` | +5% to +8% with a crowd buy behind ours; -0.5% to -0.8% without | |

The halt: `/var/log/flip/HALTED` holds the reason; the engine logs an alarm and skips every trigger (`skip`, `why` `halted: ...`) until
the file is removed and the service restarted (`sudo rm /var/log/flip/HALTED && sudo systemctl restart flip-engine`). Remove it only
once the reason is understood. A pull that beats a sell landing at +2 to +4 means the window this trade lives in is gone.

After three clean trades, `MAX_TRADES_PER_DAY 10` and section 4's ten-trade test. `HOLD_BLOCKS` stays at 4: on the relay the operator
reacts at 5-13 blocks, and a longer hold sits inside that reaction. `BUY_DELAY_BLOCKS 1` is the one entry change worth a test: the
four trades that landed two blocks after the trigger all had a crowd buy right behind them, two of the three that landed one block
after it had none.

## 4c. Release 0.5: the seat, ahead of the operator's burst

Why (README, "The operator's new scheme"): from 14:59 the operator launches through a fresh launcher each time, which the engine did
not see, and bunches its crowd's first three buys into one block 8-9 blocks after the launch; nothing follows them. The seat buys
one or two blocks before that burst and sells on it. The question one live trade answers: does the burst still come after our buy?

    cd ~/v2pons && git pull
    /opt/flip-venv/bin/python3 tests/test_engine.py
    set_kv() { sudo grep -q "^$1=" /etc/flip/engine.env && sudo sed -i "s|^$1=.*|$1=$2|" /etc/flip/engine.env || echo "$1=$2" | sudo tee -a /etc/flip/engine.env >/dev/null; }
    set_kv ENTRY seat && set_kv LAUNCH_SELECTORS 2fcb9108 && set_kv SEAT_FIRE_AT 6 && set_kv DRY_RUN 1 && sudo systemctl restart flip-engine
    sleep 8 && sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"start"' | tail -1

The start line shows `"release":"0.5"`, `"dry_run":true`, `"entry":"seat"`, `"launch_selectors":["2fcb9108"]`, `"seat_fire_at":6`. Ten minutes
of dry run (three or four launches), then:

    sudo python3 ~/v2pons/deploy/englog.py 1 | grep -E '"ev":"(would_fire|would_sell|skip)"' | cut -c1-220 | tail -8

Each launch shows a `would_fire` and a `would_sell` with `after_buy` 0-2 and `why` `take profit: ...` (a `deadline` on a late burst).
Then live, one trade first:

    set_kv DRY_RUN 0 && set_kv MAX_TRADES_PER_DAY 1 && sudo systemctl restart flip-engine

| the first trade's `trade_done` | reading | next |
|---|---|---|
| `sell_why` take profit, `ret` +5% to +10%, `pulled_before_sell` false | the burst came after our buy | `MAX_TRADES_PER_DAY 3`, then 10 |
| `sell_why` deadline, `ret` about -0.5% | the operator held its burst back when it saw us | two more to be sure; if the same, stop |
| `pulled_before_sell` true (the engine halted) | it pulled on us before our sell | stop: the seat is a trap here too |

## 4d. Release 0.8: auto entry, and the review's fixes

Overnight Oct 8-9 the operator went back to its original launcher, whose crowd buys 40-60 blocks in and then every few blocks: the
follow entry's trade (13 of 14 priced positive, +2.4%), not the seat's. `ENTRY=auto` picks per launch: the original launcher, follow;
a per-launch copy of the launcher (known by its code), the seat. 0.8 also sends our buy from its own thread (a reply that never comes
can no longer hold up the feed or the sell), puts the chain's nonce back after every trade (retrying until the chain answers, with no
new trade meanwhile), reads a launcher's code again at the launch's block when the first read finds none, and gives back the day's
trade when a buy never went in.

    cd ~/v2pons && git pull
    /opt/flip-venv/bin/python3 tests/test_engine.py 2>&1 | tail -3
    set_kv() { sudo grep -q "^$1=" /etc/flip/engine.env && sudo sed -i "s|^$1=.*|$1=$2|" /etc/flip/engine.env || echo "$1=$2" | sudo tee -a /etc/flip/engine.env >/dev/null; }
    set_kv ENTRY auto && set_kv LAUNCH_SELECTORS 2fcb9108 && set_kv MAX_TRADES_PER_DAY 3 && sudo systemctl restart flip-engine
    sleep 10 && sudo python3 ~/v2pons/deploy/results.py | head -4

The tests end with `ok auto: ...`; the results header shows `release 0.8   LIVE   entry auto   max 3 trades a day` and `halted: no`.

## 4e. Release 0.9: the front strategy (a second strategy, its own switch)

A volume bot launches about 330 pools a day through the PositionManager (multicall, 1,444-byte calldata, exactly 2.4333285 ETH, fee 0.25%) and
buys each one 0.05-0.25 ETH at launch + 7..13, at a price it quoted at launch. Bought in the launch's next block, our position sells into that buy:
+13-14% a trade in an exact replay of 49 pools (24/24 and 25/25 positive). The one open question is whether its operator pulls on a real-size buy
that lands before its bot's first buy; it pulls 5-12 blocks after outsiders who buy later, and nobody has bought this early with real size. The engine
arms these launches from the launch transaction itself (the pool is in its calldata), fires in the launch block, sells on the bot's buy or at our buy
+ 18 (`FRONT_HOLD_BLOCKS`; 12 until Oct 10: the bot's buy came after it in 15 of 435 pools, never with a pull before it). It has its own dry-run switch, daily cap and halt file (HALTED.front): a pull before a front sell stops the front strategy only.

    cd ~/v2pons && git pull
    /opt/flip-venv/bin/python3 tests/test_engine.py 2>&1 | tail -6
    set_kv() { sudo grep -q "^$1=" /etc/flip/engine.env && sudo sed -i "s|^$1=.*|$1=$2|" /etc/flip/engine.env || echo "$1=$2" | sudo tee -a /etc/flip/engine.env >/dev/null; }
    set_kv FRONT 1 && set_kv FRONT_DRY_RUN 1 && sudo systemctl restart flip-engine
    sleep 10 && sudo python3 ~/v2pons/deploy/results.py | head -5

The header shows `release 0.9   LIVE` (follow unchanged) and `front strategy: ON, DRY RUN`. After an hour, `results.py` shows `FRONT DRY RUN: N
would-buys ...`; check those against the chain before the live probe:

    set_kv FRONT_DRY_RUN 0 && set_kv FRONT_STAKE_ETH 0.0012 && sudo systemctl restart flip-engine

If the operator pulls on our early buy, the first front trade it catches halts the front strategy (about $3); follow keeps trading.

What keeps front from touching follow (release 0.9 after its review): front has its own daily stop (`FRONT_DAILY_STOP_USD`, $5) and its own
halt file for a pull or a sell that sold nothing; a relay too short for the front stake turns front off for that run (the header says `OFF
for this run`), not the engine; while a follow launch that follow can still trade is waiting for its crowd, front does not take the position
slot, and a front trade gives the slot back as soon as both its receipts are in (follow can trade during front's pull check; the next front
trade waits for it). A front launch is
known by its value (2.4333285 ETH) and its calldata; if the bot changes its fee (within sub-1%), tick spacing, launch price or liquidity, the
launch is still traded and results.py shows `front launches with a fingerprint not seen before` (set `FRONT_PIN=1` to skip such launches
instead). Front skips a pool with more than `FRONT_AHEAD_MAX_ETH` (0.008) bought ahead of the bot's buy counting ours, and sells at once
when the bot's buy would fail its own minOut (`front_bot_reverts` in the log; the dry-run summary counts them). The bot's buy behind ours
(any buy through the bot's router, `FRONT_BOT_ROUTERS`, at any size; the size rule `FRONT_SELL_ON_ETH` is off by default since Oct 10 18:00:
the operator's decoys behind our buy went 0.00012 -> 0.001485 -> 0.00495 ETH, each just above the threshold then set, and sold 323 positions
ahead of the bot's buy; the two Oct 10 -100% trades were 0.00495 ETH bot buys under the old 0.005 threshold, section 4f) sells at once even below the take-profit: in the
operator's quick-pull hours the pull comes 2-4 blocks after that buy, and a small one would otherwise leave our sell to the deadline.
Live, `results.py` lists front's last 5 trades and a `FRONT LIVE:` summary line (count, $, average and worst return, exits, pulls first).

## 4f. Oct 10 afternoon: the bot's buy by its router, follow's near-miss halt, payout (HANDOFF section 16)

Why: the two front trades the operator's pull beat on Oct 10 (10:49 and 11:12 UTC) were pools where the volume bot's first buy was 0.00495 ETH,
its smallest size and just under the 0.005 ETH sell-on threshold; the engine waited for its deadline and the pull came 3 blocks after the bot's
buy, as it does in every pool. Now a buy through the bot's router behind ours is the bot's buy at any size (`FRONT_BOT_ROUTERS`), and the size
rule is off (`FRONT_SELL_ON_ETH` 0; the box has 1, which is never met): the operator raised its decoys to each threshold within the hour
(0.001485 at 15:04, 0.00495 at 15:45) and sold us out of 323 positions ahead of its bot's buy; HANDOFF 16.10. Follow got its own halt for a pull that lands within 4 blocks of our buy even behind our sell (`HALTED.follow`; front
goes on). `relay_ops.py payout 0xADDRESS ETH` sends from the wallet to your own address. The commands, numbered, are in HANDOFF 16.6: the
state, the fetch check, the fast-forward and the tests (46), the optional cap and stake changes, the restart and its start line, the gas
top-up, the log export, the payout.

### 4g. Two launch lines at once (Oct 11): the bot's 2.4333 and 3.0 ETH lines

Front trades every launch line listed in `FRONT_FAMILIES` beside the FRONT_* one, each with its own fee, fingerprint, room, take-profit and
hold (HANDOFF 16.13). To add the 3.0 ETH line (fee 1%, the bot's minOut 0.95 of the launch quote):

    set_kv FRONT_FAMILIES '[{"name":"v3.0","value_wei":"3000000000000000000","fee":10000,"tick_spacing":200,"sqrt_p":"679394651928963067279918579724198","liq":"25725498245903809899643","bot_minout":0.95,"ahead_max_eth":0.07,"take_profit":9,"hold_blocks":20,"stake_eth":0.002,"dry_run":true,"pin":true}]'
    sudo systemctl restart flip-engine && sleep 8 && sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"start"' | tail -1 | grep -o '"front_families":\[[^]]*\]'

That dry-runs the 3.0 line (`"dry_run":true`: its fires are `would_fire` lines) while the FRONT_* line trades live. The start line lists
the families the engine will trade; a wrong JSON (an unknown key, a missing field, a stake over 0.006) stops the start with a message naming
the family. A launch's `fam` is in its `armed`, `launch`, `would_fire` and `trade_done` lines. After the dry run's gates (HANDOFF 16.12): the
same JSON with `"dry_run":false` for 50 trades at 0.002 ETH, then `"stake_eth":0.0058`. Remove the setting (an empty value) to go back to
the FRONT_* line alone. `FRONT_NONBOT_HALT` (5) halts front, with its own file, after that many live front trades of one family in a row
that paid under +2% (the decoy signal of Oct 10); clear it like any front halt once the cause is understood:
`sudo rm /var/log/flip/HALTED.front && sudo systemctl restart flip-engine`.

## 5. Daily

Everything in one screen (the engine's state, every launch it saw, every trade with its result and whether the pull came first, the
totals, the money):

    sudo python3 ~/v2pons/deploy/results.py            # the last 24 hours; add a number for more hours: results.py 72

Its `PROFIT BY STRATEGY` table, under the header, puts follow and front side by side: trades and $ after gas over the last hour,
today (UTC), the report's window and every log kept, then each strategy's share of winners, $ a trade, and average and worst return.
The engine reads today's trades back from its log when it starts, so a restart keeps each strategy's daily cap and stop.
A stop or restart (`systemctl stop/restart`) is safe mid-trade: on SIGTERM the engine starts no new trade, lets the open one sell
on schedule and settle (front's pull check included), then exits (`stopping`, then `stopped` in the log; at most `STOP_WAIT_S`, 40 s,
after which an open trade is logged as an alarm).

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py status
    sudo /opt/flip-venv/bin/python3 ~/v2pons/src/score.py /var/log/flip/engine.jsonl 24

Stop and withdraw everything:

    sudo systemctl stop flip-engine && sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py withdraw

## 6. What this is not

A second Pons engine. It is a side bet on one operator's habits, three days old on Oct 8, which that operator can end at any time by
changing its fee, its launcher or its reaction. The test costs about $15-30 of risk and tells us which.

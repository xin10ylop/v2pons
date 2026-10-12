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

The header shows `release 0.9   LIVE` and the LINES table shows the line `dry`. After an hour, its row shows `dry: N would-have-traded in 24 h,
M priced ...%`; check those against the chain before the live probe:

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
Live, `results.py` lists the last 8 live trades of every line and, per line, the count, $, average and worst return and the pulls (section 9.3 of the handoff).

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
the families the engine will trade; a wrong JSON (an unknown key, a missing field, a stake over 0.012 ETH) stops the start with a message naming
the family. A launch's `fam` is in its `armed`, `launch`, `would_fire` and `trade_done` lines. After the dry run's gates (HANDOFF 16.12): the
same JSON with `"dry_run":false` for 50 trades at 0.002 ETH, then `"stake_eth":0.0058`. Remove the setting (an empty value) to go back to
the FRONT_* line alone. `FRONT_NONBOT_HALT` (5) halts front, with its own file, after that many live front trades of one family in a row
that paid under +2% (the decoy signal of Oct 10); clear it like any front halt once the cause is understood:
`sudo rm /var/log/flip/HALTED.front && sudo systemctl restart flip-engine` (the restart starts that family's count again at 0). A listed
family's halts (a pull before its sell, a sell that sold none, the decoy run) write its own file, `/var/log/flip/HALTED.front.<name>`
(for example `HALTED.front.v3.0`), and stop that family alone; the FRONT_* line goes on. The `flow` line's `fam_halted` shows them. A wrong
`FRONT_FAMILIES` value does not stop the service: front is off for that run and the start logs an alarm naming the family and the field;
follow runs. Check after any change: `sudo python3 ~/v2pons/deploy/englog.py 1 | grep -E '"ev":"(start|alarm)"' | tail -2 | cut -c1-300`. A line whose bot buys late takes `"fire_at":N` (fire when the feed
shows launch + N; 0 = the launch block) and a longer `"hold_blocks"`; the study of HANDOFF 16.14 gives the numbers per line.

**Known fingerprints and the auto stake (Oct 11 evening).** The 2.4333 line moved from fee 2500 / tick spacing 50 to 5000 / 100 at 15:32 and
may move back: `FRONT_FEES_ALSO=2500` and `FRONT_TICK_SPACINGS_ALSO=50` (comma lists; `fees_also` / `tick_spacings_also` per listed family)
make the line trade at any pair it is known to use, still refusing anything unseen. `FRONT_AUTO_STAKE=1` sizes the stake to the room the bot's
decoys leave: at every bot buy the engine computes how much ETH could have sat ahead of it before its fill fell under its minOut (the room,
~0.0126 ETH on this pool), subtracts what others put there, and keeps the last 30 such observations per family (`room` events); the next fire's
stake is their 25th percentile less `FRONT_AUTO_STAKE_MARGIN_ETH` (0.0004), never under `FRONT_AUTO_STAKE_MIN_ETH` (0.002) nor over
`FRONT_STAKE_ETH` (the ceiling), and the minimum until `FRONT_AUTO_STAKE_OBS` (5) observations exist. With the decoys of Oct 11 16:28
(0.0099 ahead) that is 0.0023; with none it climbs to the ceiling. A raised stake that pays under +2% drops the observations (the minimum
again for five launches) unless it sold into a bot buy the feed itself priced under +2%, a small one like Oct 12 01:45's, which keeps
them (`room_obs_kept` in its `trade_done`, HANDOFF 16.20). A restart reads the last run's observations back from the log and its `.1`
(`room_obs_restored` in the start line), so the stake goes on where it was instead of starting at the minimum, unless the launch line's last
`room` line is older than `FRONT_AUTO_STAKE_RESTORE_MIN` (60; 0 = off) minutes. The `flow` line carries `auto_stake_eth`, the
`fire`/`trade_done` lines the stake used. Settings for the box: `FRONT_STAKE_ETH=0.0097 FRONT_AUTO_STAKE=1 FRONT_FEES_ALSO=2500
FRONT_TICK_SPACINGS_ALSO=50`. These two rules need no setting: `git pull` on the box and a restart.

**`nonbot_halt` per family.** The flat-trade streak halt (`FRONT_NONBOT_HALT`, 8 on the box) was built for the 2.4333 pattern, where a trade
under +2% means the bot's buy did not come; a follow-type line such as C-1 has most trades flat and a few large winners, so its family sets
`"nonbot_halt":0` (off for that family) or its own count; a family without the key uses the setting. The threshold travels with the position.

A **wave family** (Oct 11 evening, for the operator C-1) is a listed family with a `trigger`: its launches (`calldata_len` 2276, `value_wei` 0,
fee 100, tick spacing 1, a token-only range up to the launch tick) are armed from the calldata like any front launch, but nothing fires at the
launch: the operator's own buy through its router (a value-0 call whose calldata carries the token, word `token_word`, the ETH amount in word
`value_word` and the buy flag `flag_word == flag_value`), of at least `min_eth` and within `max_blocks` of the launch, is the trigger; we buy
behind it (landing + 2) and sell `hold_blocks` later (or at `take_profit`). A pull-shaped call before the trigger, a trigger past the window
or no trigger make the pool late. The C-1 line as a dry run (its halt file, when live: `HALTED.front.c1`):

    sudo sed -i '/^FRONT_FAMILIES=/d' /etc/flip/engine.env; sudo tee -a /etc/flip/engine.env >/dev/null <<'EOF'
    FRONT_FAMILIES='[{"name":"v3.0","value_wei":"3000000000000000000","fee":10000,"tick_spacing":200,"sqrt_p":"679394651928963067279918579724198","liq":"25725498245903809899643","bot_minout":0.95,"ahead_max_eth":0.07,"take_profit":9,"hold_blocks":60,"stake_eth":0.002,"dry_run":true,"pin":true,"fire_at":12,"fire_max":3},{"name":"c1","value_wei":0,"calldata_len":2276,"fee":100,"tick_spacing":1,"sqrt_p":"792280926924313289846529216293289","liq":"100000088127620690885293","bot_minout":1,"ahead_max_eth":0.5,"take_profit":9,"hold_blocks":60,"stake_eth":0.002,"dry_run":true,"pin":true,"trigger":{"router":"0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6","selector":"e6cb474f","value_word":2,"token_word":8,"flag_word":7,"flag_value":0,"min_eth":0.005,"max_eth":10,"max_blocks":400}}]'
    EOF
    sudo systemctl restart flip-engine

(The setting is one list: a family left out is dropped, so the 3.0 dry watch stays listed beside c1.) `flag_word`/`flag_value` are required
(the router's sell has the same shape as its buy); `max_eth` (10) ignores a call with an absurd amount (the feed shows calls that revert);
`max_blocks + hold_blocks` must stay under 2,600 (armed pools are forgotten after 3,000). `FRONT_DRY_RUN=1` dries every family;
`FRONT_BASE_DRY_RUN=1` dries the FRONT_* line alone (so a listed family can trade live while the 2.4333 line only watches).

Its dry trades log `would_fire` (the trigger block, `plan_buy_seq` = + 2), `buy_seen` (`dry` true) and `would_sell` with `dry_ret`, the sell's
return as the engine's price copy (the operator's router buys and strangers' ETH buys) prices it; `trade_done` (`dry` true, `fam` c1,
`dry_ret`). The verifier's gate before a live probe (HANDOFF 16.15): 24 h and 100 triggers at a dry mean of +8% or more with the operator still
buying 0.3 ETH or more by + 60; then `"dry_run":false` at 0.002 ETH for 40 trades, its own halt file, scale only after +5% mean with at most 5%
pulled before the sell.

A **V3 family** (`"dex":"v3"`, Oct 11 evening, the V3 crowd line of REPORT_C/REPORT_W, HANDOFF 16.16) trades the launches of a Uniswap
V3 PositionManager (`target`): a value-0 multicall of 836 bytes that creates the pool (WETH, the token, fee 100), mints the token alone
up to the launch price and refunds. The engine decodes it like a front launch (the pool's address by CREATE2) and fires in the launch
block (our buy at + 2); the crowd's buys (value-0 calls of the `shapes` through any contract, `any_to`; the token found in the call,
`token_anywhere`) and anyone's ETH-value buys move the price copy; the first of `min_eth` at or after our buy starts the exit: the sell
goes `exit_after_blocks` (18) later, so that it lands about 20 blocks after the crowd's first buy, as the research's rule; at the latest
when the feed shows launch + `hold_blocks` (78: lands about + 80; the line's earliest no-crowd pull was + 83). **Dry run only** while `RELAY_V3` is empty (4j): `"dry_run":false`
is then forced to true with an alarm at start (the list is not dropped). The launch price varies per launch, so the JSON gives no `sqrt_p`/`liq`; launches with WETH as token1 (about 3%) are logged
and skipped. The box's list with it:

    sudo sed -i '/^FRONT_FAMILIES=/d' /etc/flip/engine.env; sudo tee -a /etc/flip/engine.env >/dev/null <<'EOF'
    FRONT_FAMILIES='[{"name":"v3.0","value_wei":"3000000000000000000","fee":10000,"tick_spacing":200,"sqrt_p":"679394651928963067279918579724198","liq":"25725498245903809899643","bot_minout":0.95,"ahead_max_eth":0.07,"take_profit":9,"hold_blocks":60,"stake_eth":0.002,"dry_run":true,"pin":true,"fire_at":12,"fire_max":3},{"name":"c1","value_wei":0,"calldata_len":2276,"fee":100,"tick_spacing":1,"sqrt_p":"792280926924313289846529216293289","liq":"100000088127620690885293","bot_minout":1,"ahead_max_eth":0.5,"take_profit":9,"hold_blocks":60,"stake_eth":0.002,"dry_run":true,"pin":true,"trigger":{"router":"0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6","selector":"e6cb474f","value_word":2,"token_word":8,"flag_word":7,"flag_value":0,"min_eth":0.005,"max_eth":10,"max_blocks":400}},{"name":"v3crowd","dex":"v3","target":"0x73991a25c818bf1f1128deaab1492d45638de0d3","value_wei":0,"calldata_len":836,"fee":100,"tick_spacing":1,"hold_blocks":78,"exit_after_blocks":18,"take_profit":9,"stake_eth":0.0058,"ahead_max_eth":0.5,"dry_run":true,"pin":true,"trigger":{"shapes":[{"selector":"3593564c","calldata_len":484,"value_word":9},{"selector":"a0193551","calldata_len":452,"value_word":8},{"selector":"49f74a5d","calldata_len":452,"value_word":8}],"any_to":true,"token_anywhere":true,"min_eth":0.005,"max_eth":10}}]'
    EOF
    sudo systemctl restart flip-engine && sleep 8 && sudo python3 ~/v2pons/deploy/englog.py 1 | grep -E '"ev":"(start|alarm)"' | tail -2 | cut -c1-300

The start line's `front_families` shows it with `"dex":"v3"` and its trigger as `any:3593564c/484,...`. Its dry trades: `armed` and
`would_fire` with `"dex":"v3"`, `first_buy` (`"trigger":true` for the crowd's call shape), `would_sell` and `trade_done` (`"fam":"v3crowd"`)
with `dry_ret` and the reason ("the crowd's buy behind ours (...) and the 18 blocks of its wave", or "deadline: launch + 78, the V3
line's cap"). The day's numbers: `sudo python3 ~/v2pons/deploy/englog.py 24 | grep '"trade_done"' | grep '"v3crowd"' | grep -o '"dry_ret":[-0-9.e]*'`.
`dry_ret` ignores sells (the crowd sells too), counts the a0193551 calls' whole amount word (they swap 99% of it) and prices our buy at + 2
exactly: check the run against the chain (`research/session_oct11/lines/analysis/W/w07_forward.py`) before trusting it. A V3 dry position
holds the one slot for its ~8 s, as the c1 one does. REPORT_W's gate to build the live path: 100 launches or more at +4% mean or better, no
pull before + 80, 120 launches a day.

A **launch-rule family** (`"launch"`, Oct 11 night, REPORT_V23 line 1, HANDOFF 16.18) is a V3 family known by its launch call: the
356-byte value-0 call `d27d1e00` to a launcher contract whose code's keccak is the line's (a new launcher each launch: one `eth_getCode` a
launch), the pool from the launch's receipt (a code or a receipt not read is `launch_not_armed` or `launch_no_receipt`, with an alarm at
most once a minute). No trigger: a dry buy when the feed shows launch + 60 (up to + 70 if the feed lags or the slot is busy, else `late`), a
dry sell at launch + 260, or at once on the pull (the launch position's `decreaseLiquidity` of half its liquidity or more: `dry_ret` -1.0;
less is a `partial_pull`). **Dry run only** while `RELAY_V3` is empty (4j): `"dry_run":false` is forced to true with an alarm at start. The fingerprint is pinned (fee 100,
WETH as token0, one token-only mint 1,094,515 ticks wide within 2%, L 3.16e22 within a factor of 3); anything else is `armed` with
`"eligible":false` and `"fingerprint":"new: ..."`. The object to add:

    {"name":"p356","dex":"v3","launch":{"selector":"d27d1e00","calldata_len":356,"code_hash_prefix":"89885b75fd29af130416accacb0351226a4259b3090dc0a2bb56189489efe08a","value_wei":0},"fee":100,"tick_spacing":1,"buy_at":60,"sell_at":260,"stake_eth":0.0058,"ahead_max_eth":0.5,"dry_run":true,"pin":true}

`code_hash_prefix` holds the launcher code's full keccak (64 hex digits). A shorter prefix (8 hex digits or more) is accepted but weak: 8 hex
digits are 32 bits, which anyone can grind a contract to match.

**A mistake in this object (an unknown key, a bad hash, a `sell_at` under `buy_at` + 13, a selector another family uses) drops the whole
`FRONT_FAMILIES` list at start, the live c1 with it: after the restart, check the start line and results.py as below.**

Add it to the box's list as it stands (the families already there, c1 live among them, are not touched; the old file is kept as
`/etc/flip/engine.env.bak`; run twice, the snippet refuses and changes nothing). The first line pulls the engine that knows launch-rule
families and stops before editing anything if the pull or that check fails; the restart runs only after the edit succeeded:

    cd ~/v2pons && git pull -q --ff-only && grep -q '^def launch_family' src/flip_engine.py && sudo python3 - <<'EOF' && sudo systemctl restart flip-engine && sleep 8 && echo restarted
    import json, os, shutil
    P = "/etc/flip/engine.env"
    P356 = json.loads('{"name":"p356","dex":"v3","launch":{"selector":"d27d1e00","calldata_len":356,"code_hash_prefix":"89885b75fd29af130416accacb0351226a4259b3090dc0a2bb56189489efe08a","value_wei":0},"fee":100,"tick_spacing":1,"buy_at":60,"sell_at":260,"stake_eth":0.0058,"ahead_max_eth":0.5,"dry_run":true,"pin":true}')
    lines = open(P).read().splitlines()
    at = [k for k, l in enumerate(lines) if l.startswith("FRONT_FAMILIES=")]
    assert len(at) == 1, "FRONT_FAMILIES must be set exactly once in " + P
    v = lines[at[0]][len("FRONT_FAMILIES="):].strip()
    if len(v) > 1 and v[0] == v[-1] and v[0] in "'\"":
        v = v[1:-1]
    fams = json.loads(v)
    assert isinstance(fams, list) and all(f.get("name") != P356["name"] and "launch" not in f for f in fams), "not a list, or a launch-rule family is listed already: nothing changed"
    shutil.copy2(P, P + ".bak")
    lines[at[0]] = "FRONT_FAMILIES='" + json.dumps(fams + [P356], separators=(",", ":")) + "'"
    tmp = P + ".tmp"; open(tmp, "w").write("\n".join(lines) + "\n"); shutil.copymode(P, tmp); os.replace(tmp, P)
    print("FRONT_FAMILIES:", [(f.get("name"), f.get("dry_run")) for f in fams + [P356]])
    EOF
    sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"start"' | tail -1 | python3 -c 'import sys, json; s = json.loads(sys.stdin.read()); print("error:", s.get("front_family_error"), "warnings:", s.get("front_family_warnings")); [print(f["name"], f.get("dex", "v4"), "dry_run", f["dry_run"]) for f in s["front_families"]]'
    sudo python3 ~/v2pons/deploy/results.py 1 | head -12

The check must print `error: None`, c1 with `dry_run False` (as before), p356 with `v3 dry_run True`; results.py must show c1 LIVE and p356
dry. If not: `sudo cp /etc/flip/engine.env.bak /etc/flip/engine.env && sudo systemctl restart flip-engine`.

The start line lists p356 with `"dex":"v3"`, its `launch` and `"trigger":"timer: launch + 60 (to + 70), sell at launch + 260"`. Its
`trade_done` lines (`"fam":"p356"`, `"dry":true`) carry `dry_ret` and what the line is judged on: `wave_eth` and `wave_buys` (others' buys from
our buy to our sell), `wave_sells`, `fleet_buys` and `fleet_eth` (SwapRouter02 `0xcaf681a6` with ETH as value: the fleet's way in),
`router_weth_buys` and `router_weth_eth` (SwapRouter02 paid in WETH), `ahead_eth`, `pull_offset` and `partial_pull_offset` (the feed), and from
the chain's Burn logs of the launch position (`burn_check`): `first_burn_offset` (half its liquidity gone), `partial_burn_offset`,
`pulled_before_sell`, `burn_by_landing` (by our sell + 2, where a live sell would land), `other_burns`. The day's numbers:
`sudo python3 ~/v2pons/deploy/englog.py 24 | grep '"trade_done"' | grep '"p356"' | grep -o '"dry_ret":[-0-9.e]*'`. A p356 dry position holds
the one slot about 20 s (other dry fires are skipped meanwhile; a live fire drops it; a stop or restart does not wait for it, and its record
is then lost).

## 4h. The sell's second path (Oct 12, HANDOFF 16.19)

Oct 12 00:00:09 UTC: our buy landed at block 86236845; the time fallback sent the sell 1.7 s later, and the sequencer's public intake
accepted it only ~11.5 s after that: it landed at 86236972, 127 blocks after our buy, one block behind the bot's buy, 11 before the pull.
Blocks came at 9-10 a second and the feed was live throughout; the bot's own buy was delayed by the same stall.
Under the quick pulls of Oct 10-11 (3 blocks after the bot's buy) such a stall is a -100% trade.

The settings (nothing changes while they are unset):

- `SELL_ALT_URL` (empty = off): a second endpoint for the sell, an RPC that forwards transactions to the sequencer (the box's `RPC_URL`, or
  the public `https://rpc.mainnet.chain.robinhood.com`). The same signed sell goes there at the same time as to the sequencer, on its own warm
  connection (one slot, the same keepalive, a fixed 2 s socket timeout), each of the sell's 4 tries mirrored; the first reply that says it is
  in (`ok`, or `already known`, `nonce too low` and the like: one signed transaction has one hash, a second copy is harmless) wins, and a hung
  path no longer holds the sell. After the alternate's win the sequencer keeps its own loop (to its own `ok`/`in` or its 4th try), and after
  the sequencer's win the alternate stops at its first definite reply unless all its replies were lost (the winner's "in" may be only a
  forwarder's own). `sell_sent` then carries `via` (`seq` or `alt`), `accept_kind`, `accept_ms`,
  `seq_tries`/`seq_posts`/`seq_reply` and `alt_tries`/`alt_posts`/`alt_reply` (tries: replies in hand; posts: posts made, one still waiting
  included; reply null: that path was still waiting); a reply after that is a `late_reply` line and changes nothing; the "not accepted" alarm
  comes only when both paths failed, or when neither got it in within the wait's cap (65 s; "a path still waiting"). Its keepalive sends
  that endpoint one `eth_chainId` every 5 s when idle (about 17,000 a day).
- `BUY_ALT` (0): 1 sends the buy on both paths too (one try each): in if either says so, refused only if both refuse, otherwise "no reply"
  (the position kept, the sell on schedule; one refusal beside a lost reply has its own alarm). Leave it 0 until the sell's second path has
  run for a day.
- `SEND_TIMEOUT_S` (4): the sequencer connections' socket timeout, as before; 0.5 to 30 s, anything else falls back to 4 with an alarm at start.

To point it at the RPC endpoint already in the env file (its last `RPC_URL` line, the one the engine reads; the value is copied, never
printed: the URL may hold the provider's key; the old line is deleted first so that `set_kv` appends, since its `sed` replacement would garble
a URL holding `&` or `|`, and the file is given a final newline first so the append is a line of its own):

    cd ~/v2pons && git pull -q --ff-only && grep -q '^SELL_ALT_URL' src/flip_engine.py && echo code
    set_kv() { sudo grep -q "^$1=" /etc/flip/engine.env && sudo sed -i "s|^$1=.*|$1=$2|" /etc/flip/engine.env || echo "$1=$2" | sudo tee -a /etc/flip/engine.env >/dev/null; }
    v=$(sudo grep '^RPC_URL=' /etc/flip/engine.env | tail -n1 | cut -d= -f2-); [ -n "$v" ] && sudo sed -i '/^SELL_ALT_URL=/d' /etc/flip/engine.env && sudo sed -i -e '$a\' /etc/flip/engine.env && set_kv SELL_ALT_URL "$v" && echo set; unset v
    sudo systemctl restart flip-engine && sleep 8 && sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"start"' | tail -1 | python3 -c 'import sys, json; s = json.loads(sys.stdin.read()); print("sell_alt:", s.get("sell_alt"), "buy_alt:", s.get("buy_alt"), "send_timeout_s:", s.get("send_timeout_s"))'

The first line prints `code` (else stop: the pull failed and the engine would not know the setting), the third `set`; without `set` the env
file has no `RPC_URL` line: the box is then on the public RPC, and `set_kv SELL_ALT_URL https://rpc.mainnet.chain.robinhood.com` does it.
The check must print the RPC's host after `sell_alt:` (the host only, never the path); `None` with the engine live means the URL was refused
(an alarm in the log says so: not https, no host, user:password@, or a space or control character; the sequencer path runs as before).
A restart mid-trade is safe (section 5). Off again: `sudo sed -i '/^SELL_ALT_URL=/d' /etc/flip/engine.env && sudo systemctl restart
flip-engine`. Which path wins, over the day:
`sudo python3 ~/v2pons/deploy/englog.py 24 | grep '"ev":"sell_sent"' | grep -o '"via":[a-z"]*' | sort | uniq -c`, and `accept_ms` on each line.

## 4i. The BNB dry run (Oct 12, HANDOFF 16.21)

A second, separate program: `src/bnb_engine.py`, the dry run of the one BNB Chain line the research kept
(`research/session_oct12/bnb/REPORT_BNB.md`: the PancakeSwap V2 launcher 0xc9b7cc61; $15 at L+50, sold at L+260, the 15-BNB pools
skipped). It reads the chain through BNB's public endpoints and logs what the rule would have done. It has no wallet, no key and no code
that signs or sends. Its own service (`flip-bnb`), settings (`/etc/flip/bnb.env`) and log (`/var/log/flip/bnb.jsonl`); flip-engine and its
files are not touched, and it runs below flip-engine's CPU priority (Nice 10 against -5, at most half a core and 400 MB). The unit
gives it a read-only file system except `/var/log/flip`, shows it nothing of `/etc/flip` but its own `bnb.env` and `bnb.key` (an empty
read-only tmpfs there: flip-engine's `engine.env`, which holds that wallet's key, and any copy of it such as `engine.env.bak` are not
visible, whatever renames them), keeps no capability but reading files (so flip-engine's `/proc/<pid>/environ`, where its key also is,
is refused to it), dumps no core, and restarts it 30 s after an exit; at its start it waits up to 5 minutes for the RPC (a network or DNS
failure at boot) before it exits. Release bnb-0.2 adds a live path, off unless `BNB_LIVE=1`: section 4k.

Install (once). The code first; the first line prints the two paths and `43` (the tests; `20` before release bnb-0.2), else stop. If it also prints
`flip_engine.py CHANGED`, the pull brought changes to the live engine as well, which flip-engine would pick up at its next restart:
deploy those per their own section first (or ask), then come back here:

    cd ~/v2pons && OLD=$(git rev-parse HEAD) && git pull -q --ff-only && { git diff --quiet $OLD HEAD -- src/flip_engine.py || echo 'flip_engine.py CHANGED: deploy it per its own section first'; } && ls src/bnb_engine.py deploy/flip-bnb.service && /opt/flip-venv/bin/python3 tests/test_bnb_engine.py | grep -c '^ok'
    sudo mkdir -p /var/log/flip
    sudo test -f /etc/flip/bnb.env || printf '%s\n' '# the BNB dry run (src/bnb_engine.py); no key belongs in this file' BNB_LOG_PATH=/var/log/flip/bnb.jsonl BNB_WS_URL=wss://bsc-rpc.publicnode.com BNB_RPC_URL=https://bsc-rpc.publicnode.com BNB_STAKE_USD=15 BNB_BUY_AT=50 BNB_SELL_AT=260 BNB_SKIP_POOL_BNB=15 BNB_USD=750 | sudo tee /etc/flip/bnb.env >/dev/null; sudo chmod 600 /etc/flip/bnb.env
    echo '/var/log/flip/bnb.jsonl { daily rotate 30 missingok notifempty compress delaycompress copytruncate }' | sudo tee /etc/logrotate.d/flip-bnb >/dev/null
    sudo cp ~/v2pons/deploy/flip-bnb.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now flip-bnb
    sleep 90 && systemctl is-active flip-bnb && sudo python3 ~/v2pons/deploy/bnb_results.py | head -6

The last line prints `active`, then the screen's head: `service RUNNING`, the rule, and a `reader:` line with a block number, `2 blocks
behind the head` or so and `heads by ws` (`poll`: publicnode's websocket refused or sent no heads, and the reader polls `eth_blockNumber`
instead: it still works). The unit's paths are `/home/ubuntu/v2pons`; if the clone is elsewhere, edit `ExecStart` and `WorkingDirectory` in
`/etc/systemd/system/flip-bnb.service` before the `enable`.

The settings (`/etc/flip/bnb.env`; `sudo systemctl restart flip-bnb` after a change): `BNB_STAKE_USD` (15), `BNB_BUY_AT` (50: the buy at the
start of block L+50, priced on the reserves after L+49), `BNB_SELL_AT` (260), `BNB_SKIP_POOL_BNB` (15; a comma list), `BNB_USD` (750: used
only until the USDT/WBNB pair is read, at the start and every 133 blocks), `BNB_WS_URL` / `BNB_RPC_URL` (publicnode; a provider's URL with
its key in it, e.g. nodereal, may go here: only the host is ever logged and the file is mode 600). Others, with their defaults:
`BNB_POOL_SIZES` (1,2.5,10,15,25: a size outside it is an alarm and not traded), `BNB_GAS_UNITS` (370000) and `BNB_GAS_GWEI` (0.1) for the
net result, `BNB_DUMP_SHARE` (0.5), `BNB_WATCH_TO` (8000 blocks a pool is watched for its dump), `BNB_LAG_BLOCKS` (2),
`BNB_LAUNCHER`, `BNB_SELECTOR`, `BNB_CALLDATA_LEN` (196).

Every day (the last 24 hours; a number for more: `bnb_results.py 72`):

    sudo python3 ~/v2pons/deploy/bnb_results.py

It shows the launches per pool size (about 177 a day, half of them 15 BNB and skipped), the would-have-traded count and the dry results
per size and in all (mean, median, share up, pulled before the sell, the crowd's buys), the creator's dumps per size, the gate, the last 8
launches with their decision, and the alarms. What the research expects: mean +23.6%, median +11.1% without the 15-BNB pools (1 BNB about
+100%, 10 about +35%, 25 and 2.5 about +8%); dumps from +997 (1 BNB), +2,028 (10), ~+4,000 (2.5 and 15), ~+6,800 (25). The gate's lines
(`a dump before +997`, `no crowd buy in +60..+260`, the median of the first 10) would each halt the line once it trades: any of them
tripped is a reason to stop and look, not to go live. The median is over the first 10 trades since the engine's last start, read from
all the logs kept. A trade with a missed log (`breaks`) or a gap (the reader jumped past its sale, `gaps`; `clean: false` in its line)
is left out of every number and of the gate, and the screen prints how many were left out. The raw lines:
`sudo grep '"trade_done"' /var/log/flip/bnb.jsonl | tail -3`.

A restart (`sudo systemctl restart flip-bnb`, e.g. after a `git pull`) loses the pools in flight: those open then never get a `trade_done`.
Stop it: `sudo systemctl disable --now flip-bnb` (the log stays). Remove it: that, then `sudo rm /etc/systemd/system/flip-bnb.service
/etc/logrotate.d/flip-bnb && sudo systemctl daemon-reload`.

## 4j. A V3 family live (Oct 12, HANDOFF 16.22)

With `RELAY_V3` set to the V3 relay's address (`contracts/FlipRelayV3.sol`), the engine checks the relay at start and a V3 family (v3crowd or
p356) whose object says `"dry_run":false` trades live through it. The flow is the v4 one: the buy at the reserved nonce, the presigned sell at
the next, the same wallet, gas price rule and send paths (`SELL_ALT_URL` included). Each family keeps its own entry and exit:

- v3crowd: it buys in the launch block. It sells 18 blocks after the crowd's first buy behind ours, at the latest when the feed shows launch + 78.
- p356: it buys at launch + 60. It sells at launch + 260, or at once on the pull.

Every live V3 stake is at most `V3_STAKE_CAP_ETH` (0.004 ETH, about $10), whatever the family's `stake_eth`. Nothing changes while
`RELAY_V3` is empty.

What this can trade today:

- **p356 arms nothing.** Its 356-byte launches stopped on Oct 11 at 19:56 UTC (`research/session_oct12/p356/REPORT_P356B.md`).
- **v3crowd stays dry** while the sell check is on (below).
- **The first live V3 line** will be decided by its own gate.

**The live V3 day.** The live V3 trades keep their own day: `v3_today`, `v3_pnl_today_usd`, and their own stop, `V3_DAILY_STOP_USD`
(10; 1 to 100, else 10 with an alarm). Front's own stop (`FRONT_DAILY_STOP_USD`) still holds them too. A V3 loss no longer counts in
front's day, so it never stops the v4 lines. A restart reads the day back from the log.

**One wallet, one nonce stream, one slot.** A live V3 position holds the slot from its buy to both receipts, because its presigned sell
holds nonce n + 1. The v2.433 launches in that time are skipped ("position open"). That is about 7% of v2.433 launches per V3 trade's
~24 s hold, or about 0.4% a day at 16 V3 trades a day. Its pull check after that holds only the next V3 fire, never a v2.433 one. The
full fix is for later: a second wallet owning a second V3 relay (a relay deploy costs about 0.00005 ETH), with its own nonce stream.

Three rules come from the relay as built:

- **Fixed gas.** Both transactions are signed with a fixed gas limit, `V3_GAS` (500,000), never estimated; unused gas is not charged.
  Measured on the final relay:
  - buys of 0.002-0.004 ETH 235k-286k;
  - one initialized tick crossed 333k;
  - 0.05 ETH up to 364k;
  - about 48k for each further tick;
  - sells 167k-181k.

  On a pulled pool the swap walks to the price limit (about 31 million gas) and the buy runs out of gas: the cost is that gas, nothing
  more.
- **Strict deadlines.** The relay refuses a block later than the deadline, and 0 is the past. The buy carries the fire's time +
  `BUY_DEADLINE_S` (2 h if that is 0); the presigned sell carries the fire's time + 2 h.
- **The sell check.** Before a live buy, the pool's buy and sell are simulated through the relay by `eth_call`, nothing sent: some
  tokens refuse any outsider's transfer into the pool, so the relay could buy and never sell.
  - **When it runs:** when the pool is armed, which leaves p356 about 6 s before its buy at + 60.
  - **Refused:** a simulated sell that reverts, or less than 0.99 x the stake less the two fees back (0.9898 x at fee 100, 0.9703 x at
    fee 10000; the eight live pools measured gave 0.99980 and 0.98010-0.98013). The pool is never bought (skip "v3: the token cannot
    be sold").
  - **No verdict:** an RPC failure, or the relay's `NoPool` from a node behind the feed, is its own skip ("v3: the sell check could not
    run"). The check is asked again each block, after that block's fire, until launch + buy_at + fire_max (+ 70 for p356).
  - **Who is checked:** a launch-rule family (p356) is always checked when live. `V3_SELL_CHECK` (1) only decides for a crowd family:
    v3crowd buys in its launch block, before its pool exists, so it cannot be checked. With 1 it trades dry (an alarm at start says so);
    with 0 it trades unchecked.

Before: the relay is deployed with WALLET as its owner, and it holds at least 0.004 ETH (its own steps; the engine only reads it).

**1. The code and the setting.** The first line prints `code`, else stop. `deploy/relay_v3_deploy.py --write-env` writes `RELAY_V3`
and `RELAY_V3_CODEHASH` itself (docs/RELAY_V3.md). By hand, put the relay's address in place of `0x...`, and set `RELAY_V3_CODEHASH` to the
line the deployment printed (`set_kv RELAY_V3_CODEHASH 0x...`). With `RELAY_V3_CODEHASH` set, the engine also requires the relay's code
to have that keccak (any case, 0x optional; the value is never logged):

    cd ~/v2pons && git pull -q --ff-only && grep -q '^def relay_v3_check' src/flip_engine.py && echo code
    set_kv() { sudo grep -q "^$1=" /etc/flip/engine.env && sudo sed -i "s|^$1=.*|$1=$2|" /etc/flip/engine.env || echo "$1=$2" | sudo tee -a /etc/flip/engine.env >/dev/null; }
    sudo sed -i -e '$a\' /etc/flip/engine.env && set_kv RELAY_V3 0x...

**2. One family live.** The two words after `-` are the family and the mode. The snippet edits only that family's object in
`FRONT_FAMILIES`, keeps the old file as `/etc/flip/engine.env.bak`, and restarts only after the edit succeeded:

    cd ~/v2pons && sudo python3 - v3crowd live <<'PY' && sudo systemctl restart flip-engine && sleep 8 && echo restarted
    import json, os, re, shutil, sys
    P = "/etc/flip/engine.env"; NAME, MODE = sys.argv[1], sys.argv[2]
    assert MODE in ("live", "dry"), "the mode is live or dry: nothing changed"
    lines = open(P).read().splitlines()
    at = [k for k, l in enumerate(lines) if l.startswith("FRONT_FAMILIES=")]
    assert len(at) == 1, "FRONT_FAMILIES must be set exactly once in " + P
    relay = [l.split("=", 1)[1].split(" #", 1)[0].strip().strip("'\"") for l in lines if l.startswith("RELAY_V3=")]
    assert MODE == "dry" or (relay and re.fullmatch("0x[0-9a-fA-F]{40}", relay[-1])), "no RELAY_V3 address in " + P + ": nothing changed"
    v = lines[at[0]][len("FRONT_FAMILIES="):].strip()
    if len(v) > 1 and v[0] == v[-1] and v[0] in "'\"":
        v = v[1:-1]
    fams = json.loads(v)
    mine = [f for f in fams if isinstance(f, dict) and f.get("name") == NAME] if isinstance(fams, list) else []
    assert len(mine) == 1 and mine[0].get("dex") == "v3", NAME + " is not one V3 family of FRONT_FAMILIES: nothing changed"
    assert mine[0].get("dry_run", True) != (MODE == "dry"), NAME + " is already " + MODE + ": nothing changed"
    mine[0]["dry_run"] = MODE == "dry"
    shutil.copy2(P, P + ".bak")
    lines[at[0]] = "FRONT_FAMILIES='" + json.dumps(fams, separators=(",", ":")) + "'"
    tmp = P + ".tmp"; open(tmp, "w").write("\n".join(lines) + "\n"); shutil.copymode(P, tmp); os.replace(tmp, P)
    print("FRONT_FAMILIES:", [(f.get("name"), f.get("dex", "v4"), f.get("dry_run")) for f in fams])
    PY

It refuses, and changes nothing (no restart), in these cases:

- the family is not one V3 family of the list;
- it is already in that mode;
- (for `live`) the env file has no `RELAY_V3=` address.

**3. The check.** The start line, then the last alarms:

    sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"start"' | tail -1 | python3 -c 'import sys, json; s = json.loads(sys.stdin.read()); print("relay_v3:", s.get("relay_v3"), "verified:", s.get("relay_v3_live"), "codehash:", s.get("relay_v3_codehash"), "checked:", s.get("relay_v3_codehash_set"), "owner:", s.get("relay_v3_owner"), "eth:", s.get("relay_v3_eth"), "cap:", s.get("v3_stake_cap_eth"), "error:", s.get("front_family_error")); [print(f["name"], f.get("dex", "v4"), "dry_run", f["dry_run"], "live", f.get("live"), "stake", f.get("live_stake_eth", f.get("stake_eth"))) for f in s["front_families"]]'
    sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"alarm"' | tail -3 | cut -c1-300

It must print:

- the relay's address, `verified: True`, its code's keccak with `checked: True` (`RELAY_V3_CODEHASH` set), the wallet as `owner`, its
  balance, `cap: 0.004` and `error: None`;
- the family with `dry_run False live True stake 0.004` (v3crowd shows `live False` while `V3_SELL_CHECK` is 1, with an alarm);
- every other family as before (c1 `dry_run False`, the dry ones `dry_run True`).

`verified: False` means an alarm says why; every V3 family then trades dry and the rest as before. The reasons: no code at the address,
another owner (or `owner()` reverting), code without the relay's `buy`/`sell`, a keccak other than `RELAY_V3_CODEHASH`, the v4 relay's
address, not an address, or the RPC failed. A mistake in one V3 family's object (a wrong `dry_run`, an unknown key, a bad hash, a stake
over the cap) drops that family alone, with an alarm; the other families are kept. The `flow` line carries `v3_today`,
`v3_pnl_today_usd` and `relay_v3_eth`.
p356's sell check is a `sell_check` line in the log at each arming (`ok`, or `why`). `results.py` shows the
line LIVE with its capped stake. Its money line shows the V3 relay's balance (`?` when that read fails; nothing if `RELAY_V3` is not an
address, read as the engine reads it, or is `RELAY`). Its trades are `trade_done` lines with `"dex":"v3"`, `pool`,
the fills (`buy.eth_in`, `sell.eth_out`), `pnl_usd`, `ret` and the pull fields.

**Off.** The same snippet with `dry` in place of `live` (`sudo python3 - v3crowd dry <<'PY'` ...), then the same check. Remove
`RELAY_V3` (`sudo sed -i '/^RELAY_V3=/d' /etc/flip/engine.env`) only after every V3 family says `"dry_run":true` again. If it is
removed first, a V3 family that still says `false` is forced dry with an alarm at the next start. The list is not dropped and c1 keeps
trading. A stop or restart waits for an open live V3 trade: a p356 hold is about 20 s, then its
settle; the wait is at most `STOP_WAIT_S`, 40 s.

**The cap.** `V3_STAKE_CAP_ETH` (0.004; 0.0005 to 0.012; anything else is 0.004 with a start alarm) raises it: `set_kv V3_STAKE_CAP_ETH
0.0058` and a restart. The family's `stake_eth` still bounds the stake. These are set the same way:

- `V3_GAS` (500000; 200000 to 800000, else 500000 with an alarm);
- `V3_SELL_CHECK` (1; 0 lets a crowd family trade unchecked);
- `V3_DAILY_STOP_USD` (10).

**The probe's halts.**

- **This family alone**, through its own file `/var/log/flip/HALTED.front.<name>` (for example `HALTED.front.v3crowd`). The v4 lines go on.
  - A pull at or before our sell, from the pool's Burn logs read after the trade (an amount above 0 counts). For v3crowd, any liquidity
    removed. For p356, the launch position's Burns reaching half its liquidity.
  - A buy that filled and a sell whose receipt shows it sold none. A V3 family halts alone for that, since the path is the V3 relay's.
  - `FRONT_NONBOT_HALT` live trades in a row that paid under +2%. That is 8 on the box; v3crowd may set its own `nonbot_halt`, but a
    launch-rule family cannot.

  Once the cause is understood: `sudo rm /var/log/flip/HALTED.front.v3crowd && sudo systemctl restart flip-engine`.
- **Front as a whole** (`HALTED.front`): a buy that filled and a sell with no receipt at all. The send path is the one the v4 lines share,
  so front halts as a v4 line would.
- **The day**:
  - `V3_DAILY_STOP_USD` stops the V3 fires for the day.
  - Front's own stop (`FRONT_DAILY_STOP_USD`) stops them too.
  - `FRONT_MAX_PER_DAY` caps the V3 day's count as well.
- **No halt, the fire skipped**: the V3 relay holds less than the stake (read at start and every minute; the skip says `"relay":"v3"`);
  the pool's sell check refused it (`v3: the token cannot be sold`), could not run, or has not finished; the last V3 trade's pull
  check is still running.
- **No halt, no trade**: a buy that took no token (a pulled pool: the relay keeps its ETH) is "not filled" (`buy.filled` false), as a
  reverted buy; its sell reverts with nothing to sell.
- **An alarm, no halt**: the pull check could not be read (check the pool by hand), as on the v4 lines.

## 4k. The BNB line live: the $5 probe (Oct 12, HANDOFF 16.23)

Release bnb-0.2 adds the live path to the BNB engine (`src/bnb_live.py`, loaded only when `/etc/flip/bnb.env` says `BNB_LIVE=1`).
`BNB_LIVE=0` (the default, and what the box runs after a plain `git pull` and restart) keeps the dry run exactly as it was: the same
lines, field for field; only the start line's `release` reads `bnb-0.2`. Live, every 2nd launch of the 1, 10 and 25-BNB pools is bought
with $5 from the line's own wallet straight through the PancakeSwap router and sold at L+260; the other launches of those sizes stay dry
as the control. The 2.5-BNB pools stay dry (`role` dry_size) until `BNB_LIVE_POOL_BNB` lists them (REPORT_BNB section 5: 1, 10 and 25
first, then 2.5). Its own wallet and key file (never the flip engine's), its own halt file (`/var/log/flip/HALTED.bnb`) and positions file
(`/var/log/flip/bnb_positions.json`); flip-engine and its files are not touched.

What one live trade is, in order (each step a line in `/var/log/flip/bnb.jsonl`):

1. At the launch: `live_arm` (`role` live, control, held or dry_size, with why), then `live_check`: the token's code must be one of the
   launcher's two templates (`BNB_TOKEN_CODEHASHES`; a new one is refused, with an alarm), and the round trip of the stake is simulated
   by `eth_call` on the pool as it is (`contracts/BnbRoundTrip.sol` placed by state override; nothing is sent). The pool is refused
   (`role` refused) when the simulated sell reverts, returns under 99% of the stake (a clean round trip returns 99.5%), or a leg would
   need more gas than its limit.
2. At L+50 seen: the buy (`live_send` kind buy: `swapExactETHForTokensSupportingFeeOnTransferTokens`, value the stake, minOut the tokens
   expected on the reserves x 0.95, raised to the same bound on the pool's reserves read just before the send, deadline 60 s), 0.1 gwei,
   200k gas. Not sent when, by the chain's head, it would land more than 7 blocks after L+50 (`BNB_BUY_LATE`), when the pool lost its
   WBNB since, or when the price moved more than 5% against it (it would revert, and a revert halts).
3. After its receipt (`live_receipt`): `approve(router, max)` at the next nonce, 80k gas.
4. At L+260 seen, at once on a dump seen first, or when the chain's head is 20 blocks past L+260 while the reader lags behind it
   (`BNB_SELL_LATE`): the sell of the whole token balance (`swapExactTokensForETHSupportingFeeOnTransferTokens`, minOut the BNB expected
   on the reserves x 0.95), 180k gas. A reverted sell is sent again on the reserves then at 10%, then 20%.
5. `trade_done` with `live: true`: BNB in, tokens, BNB out, gas, `pnl_bnb`, `pnl_usd`, `pnl_pct`, and `dry_ret` (the dry price of the same
   trade). The pool's own dry `trade_done` line is still written (`live: false`, `role: live`).

The gate halts the line (writes `HALTED.bnb`): a dump before +997 on a traded pool, no crowd buy in +60..+260 on a traded pool, any
reverted buy, approve or sell, a negative median over the first 10 live trades, then over any 10 live trades in a row, and 3 live trades
in a row under -50%. A halt stops new buys and still sells what is open. `BNB_DAILY_STOP_USD` ($10) of losses in a UTC day stops new buys
until 00:00 UTC (no file). A restart keeps the open positions (`bnb_positions.json`, written before each send): one past its sell block is
sold at once. One live engine at a time: a second one (a manual run beside the service) stops at its start (`bnb_positions.json.lock`).

### 1. The code (on the box)

    cd ~/v2pons && OLD=$(git rev-parse HEAD) && git pull -q --ff-only && { git diff --quiet $OLD HEAD -- src/flip_engine.py || echo 'flip_engine.py CHANGED: deploy it per its own section first'; } && ls src/bnb_live.py deploy/bnb_wallet.py contracts/BnbRoundTrip.json && /opt/flip-venv/bin/python3 tests/test_bnb_engine.py | grep -c '^ok'

It prints the three paths and `43`, else stop (`SKIP the live path's tests` means the python has no eth_account: use the venv's). Then the
unit (its isolation changed: `/etc/flip` is an empty read-only tmpfs inside it with only `bnb.key` and `bnb.env` bound in, its only
capability reads files, no core dumps) and a restart, still dry:

    sudo cp ~/v2pons/deploy/flip-bnb.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl restart flip-bnb
    sleep 60 && sudo python3 ~/v2pons/deploy/bnb_results.py | head -4
    P=$(systemctl show -p MainPID --value flip-bnb); sudo nsenter -t $P -m ls /etc/flip; sudo grep CapBnd /proc/$P/status; unset P

The screen says `BNB DRY RUN` and `release bnb-0.2`. The third line prints names and a mask only, nothing secret: `/etc/flip` as the
engine sees it must list `bnb.env` alone (and `bnb.key` once step 2 made it and the service restarted), never `engine.env`, and `CapBnd`
must read `0000000000000004` (CAP_DAC_READ_SEARCH alone). If not, the unit was not copied: stop and look.

### 2. The wallet (once)

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/bnb_wallet.py

It writes a new key to `/etc/flip/bnb.key` (mode 600; it refuses to replace a file that exists) and prints two lines: `new BNB wallet:
0x...` and `add this line to /etc/flip/bnb.env: BNB_WALLET=0x...`. The key is never printed, and nothing here needs it on a screen: the
BNB comes back with `bnb_wallet.py withdraw` (step 6), signed on the box. A copy that prints nothing (on the same box: it guards against a
deleted file, not a lost box, which is enough for a $20 wallet):

    sudo install -m 600 /etc/flip/bnb.key /root/bnb.key.bak

Do not display the key file: a terminal's output ends up pasted into chats and tickets. This is not the flip engine's wallet: send nothing
from one to the other.

### 3. Fund it with about $20 of BNB

From an exchange: withdraw BNB to the address printed, network **BNB Smart Chain (BEP20)** (not "BNB Beacon Chain", not opBNB). From
another chain: a bridge to BNB Smart Chain, native BNB. $20 covers the two $5 positions that can be open at once (`BNB_MAX_OPEN`), the
day's stop ($10) and the gas (a round trip is about 300k gas, $0.02 at 0.1 gwei). Check it arrived (the address in the second line):

    curl -s -X POST -H 'Content-Type: application/json' --data '{"jsonrpc":"2.0","id":1,"method":"eth_getBalance","params":["0xYOURADDRESS","latest"]}' https://bsc-rpc.publicnode.com | python3 -c 'import sys, json; print(int(json.load(sys.stdin)["result"], 16) / 1e18, "BNB")'

### 4. Live

`BNB_STAKE_USD=15` is in the env file from 4i (the dry run's stake): it must go to 5 for the probe (live, the engine refuses to start with
more than $10). The wallet line, the stake and the switch, with this section's own helper `set_bnb`, which writes `/etc/flip/bnb.env` and
nothing else (the `set_kv` of the other sections writes flip-engine's env file; never use it here); replace `0xYOURADDRESS` with the
printed address:

    set_bnb() { sudo grep -q "^$1=" /etc/flip/bnb.env && sudo sed -i "s|^$1=.*|$1=$2|" /etc/flip/bnb.env || echo "$1=$2" | sudo tee -a /etc/flip/bnb.env >/dev/null; }
    set_bnb BNB_WALLET 0xYOURADDRESS && set_bnb BNB_STAKE_USD 5 && set_bnb BNB_LIVE 1 && sudo grep -E '^BNB_(WALLET|STAKE_USD|LIVE)=' /etc/flip/bnb.env
    sudo systemctl restart flip-bnb && sleep 20 && sudo grep '"ev":"start"' /var/log/flip/bnb.jsonl | tail -1 | python3 -c 'import sys, json; s = json.loads(sys.stdin.read()); print({k: s.get(k) for k in ("release", "dry_run", "live", "wallet", "stake_usd", "balance_bnb", "nonce", "live_off", "halted", "resumed", "send", "live_pool_bnb")})'

The last line must show `dry_run: False`, `live: True`, the wallet, `stake_usd: 5.0`, the balance funded, `live_off: None`,
`halted: None`, `live_pool_bnb: [1.0, 10.0, 25.0]`. `live_off` set means the start's self-test of the pre-buy check failed (the RPC took
no `eth_call` state override): the run stays dry and every live slot is `held`; with publicnode it passes. If the service is not
`active` (`systemctl is-active flip-bnb`), `journalctl -u flip-bnb -n 20` says why: a missing `BNB_WALLET`, a stake over $10, a key file
open to other users or not owned by root, a key for another address, a setting out of its bounds, a halt or positions file that is not
the line's own, another live engine holding the lock.

### 5. The checks

    sudo python3 ~/v2pons/deploy/bnb_results.py

The screen says `BNB LIVE PROBE` and adds, under the gate:

- `LIVE (the receipts, after gas)`: count, mean, median, share up, $; `LIVE's pools at the dry price`: the same trades priced by the
  dry replay; `CONTROL (the other launches, dry)`: the alternate launches. The research expects about +23.6% mean / +11.1% median at
  the dry price; the live line pays the gas and lands a few blocks after L+50 and L+260 (the `live gross minus its dry price's gross`
  line).
- `live slots not traded`: held (halted, the daily stop, two open, the wallet short of funds, a buy that would land more than 7 blocks
  after L+50, a pool drained or a price moved before the buy), refused (the pre-buy check, a new token template among them), unsent (the
  node refused the transaction, or it was never mined); dry_size (a 2.5-BNB pool) is no slot.
- `HALTED: <reason>` or `halt: none`; `open live positions` with their state, today's $ against the stop, the gate's median count; the
  wallet's balance (read from the RPC; the key file is never opened).

The first live trades, raw: `sudo grep -E '"ev":"(live_send|live_receipt|live_check)"' /var/log/flip/bnb.jsonl | tail -6` and
`sudo grep '"live":true' /var/log/flip/bnb.jsonl | tail -3`. Every transaction is on `https://bscscan.com/address/0xYOURADDRESS`.

A halt, once understood (its reason is in the file and in the screen):

    sudo cat /var/log/flip/HALTED.bnb && sudo rm /var/log/flip/HALTED.bnb && sudo systemctl restart flip-bnb

### 6. Stop

New buys stop, what is open is still sold (the normal stop; the dry run goes on):

    echo "owner stop" | sudo tee /var/log/flip/HALTED.bnb >/dev/null && sudo systemctl restart flip-bnb

When the screen shows `open live positions: 0`, back to a plain dry run (one self-contained line: it writes `/etc/flip/bnb.env` only and
shows the result):

    sudo sed -i 's|^BNB_LIVE=.*|BNB_LIVE=0|' /etc/flip/bnb.env && sudo grep '^BNB_LIVE=' /etc/flip/bnb.env && sudo systemctl restart flip-bnb

(then `sudo rm /var/log/flip/HALTED.bnb` if you like; it is only read live). `BNB_LIVE=0` with a position still open is an alarm at the
start: nothing sells it until live again. In a hurry, `sudo systemctl stop flip-bnb` stops everything at once: tokens bought stay in the
wallet and in `bnb_positions.json`, and the next live start sells those past their sell block at once.

The BNB back, once the line is dry again with no open position (to an account of yours on BNB Smart Chain, e.g. an exchange's BEP20
deposit address; it shows the amount, asks you to type the address a second time, signs on the box and prints the transaction's hash):

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/bnb_wallet.py withdraw 0xYOUR_OWN_ADDRESS

It refuses while flip-bnb runs live or `bnb_positions.json` holds a position, and a destination that is a contract. A token left in the
wallet that no position holds (a position you moved away, say) is sold back to BNB with `bnb_wallet.py sweep 0xTOKEN` (an approve when
needed, the sale simulated first, a typed yes; a third argument such as 0.3 widens its 10% slippage).

The settings (`/etc/flip/bnb.env`; restart after a change), with their defaults and, live, their bounds (a value out of them stops the
start): `BNB_LIVE` (0), `BNB_WALLET`, `BNB_KEY_FILE` (/etc/flip/bnb.key), `BNB_STAKE_USD` (5 when live; over 10 stops a live start),
`BNB_LIVE_POOL_BNB` (1,10,25: the sizes traded live; add 2.5 later), `BNB_PROBE_EVERY` (2), `BNB_MAX_OPEN` (2; 1..4),
`BNB_DAILY_STOP_USD` (10; 0.1..50), `BNB_SLIP` (0.05; 0.001..0.15), `BNB_GAS_BUY` / `BNB_GAS_APPROVE` / `BNB_GAS_SELL` (200000 / 80000 /
180000), `BNB_MIN_GWEI` (0.1), `BNB_MAX_GWEI` (1; up to 5), `BNB_DEADLINE_S` (60), `BNB_CHECK_MIN` (0.99; 0.8..1),
`BNB_TOKEN_CODEHASHES` (the keccak of the launcher's two token templates, comma-separated), `BNB_MAX_STAKE_BNB` (0.015, about $11: a buy
above it is never sent; 0.0001..0.1), `BNB_SELL_TRIES` (3), `BNB_RECEIPT_WAIT_S` (20: a transaction no node shows is sent again once
after it, while its deadline is 10 s away or more), `BNB_BUY_LATE` (7 blocks after L+50, by the head), `BNB_SELL_LATE` (20 blocks after
L+260, by the head, while the reader lags), `BNB_SEND_URL` (BNB_RPC_URL), `BNB_SEND_ALT_URL` (https://bsc-dataseed.bnbchain.org; 0 for
none), `BNB_HALT_FILE`, `BNB_POSITIONS_FILE` (beside the log; live, the halt file must be named `HALTED.bnb` or start with `bnb`, the
positions file and the log must start with `bnb`, so that no typo can name flip-engine's `HALTED` or `engine.jsonl`).

## 5. Daily

Everything in one screen (the engine's state, every launch it saw, every trade with its result and whether the pull came first, the
totals, the money):

    sudo python3 ~/v2pons/deploy/results.py            # the last 24 hours; add a number for more hours: results.py 72

Its `LINES` table, under the header, has one row per front line (v2.433, c1, v3.0, v3crowd): LIVE or dry, the stake (the auto stake
and its ceiling, or fixed), then trades and $ after gas over the last hour, today (UTC), the report's window and every log kept; under
it each line's share of winners, $ a trade, average and worst return, and the operator's pulls. Follow is not shown (it is off).
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

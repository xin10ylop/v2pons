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
  `minOut`, the sell at the buy block + 5 at the next nonce, the trade priced from the receipts; the gates; the dry run; stale frames.

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

- two trades with a liquidity pull inside the hold, or three with a pull within 20 blocks of our buy (the operator reacts to us);
- five trades done with a mean return under +1% while `score.py`'s paper return on the same launches is above +3% (we land or sell
  too late: fix the timing before spending more);
- the daily stop (-$15) or three reverted buys in a row (the guard is wrong for this tier, re-set `BUY_SLIP` from the landings);
- the operator stops launching sub-1% pools (no `eligible` launch for six hours).

**Pass:** eight or more fills, 70%+ positive, mean return within 2 points of the paper, no pull inside any hold. Then the stake steps
straight to $50: `STAKE_ETH 0.0195`, `DAILY_STOP_USD 150`, and 0.04 ETH in the relay (`relay_ops.py deposit 0.04`), and the same three
questions are asked again over the next ten trades. The $50 step is the one that tests whether the operator's reaction depends on
the size of the buy (in the data, bigger outside buys were pulled more often); the $3 step proves the mechanics for a few dollars
and a couple of hours first.

## 4b. The router test: three $3 trades as the crowd (release 0.2)

What the first six live trades showed (Oct 8, 12:00-13:30 UTC): six fills through the relay, every one pulled on, -$5.19. The relay
calls the PoolManager itself, so in the pool's `Swap` event our buy was the only one those pools had ever seen with a sender other
than the Universal Router (60,375 of 60,496 swaps on the operator's sub-1% launches carry the router). Release 0.2 sends the crowd's
own transaction from the wallet instead (`ROUTE=router`): to the router, the stake as the value, their calldata byte for byte
(`tests/test_ur.py` proves it against a real crowd buy and a real fleet sell), their gas limit and tip, and sells the way the fleet
sells (two approvals behind the buy, then the sell at the fourth nonce with the amount the buy's receipt shows). The relay is not used.

What the chain says before we spend anything: on the sub-1% tier, outside wallets whose first buy came through the router after the
crowd's first buy, $2.6-13, were pulled within 20 blocks on 6 of 8 launches (within 30: 7 of 8); the same buys through other senders,
10 of 11. The reflex looks keyed on the wallet, not the sender. Three trades cost about $10 at worst and settle it for our own case.

The stake now lives in the wallet (the relay's ETH was withdrawn on Oct 8: the wallet holds about 0.0057 ETH, nonce 16; the engine
refuses to start live under `STAKE_ETH + WALLET_RESERVE_ETH` = 0.0017).

    cd ~/v2pons && git fetch origin claude/stoic-faraday-bbjupv && git checkout -B claude/stoic-faraday-bbjupv origin/claude/stoic-faraday-bbjupv
    sudo bash deploy/flip_setup.sh                                   # re-reads the unit, adds py-solc-x; restarts the service with the env file as it is (DRY_RUN=1 now)
    /opt/flip-venv/bin/python3 tests/test_ur.py && /opt/flip-venv/bin/python3 tests/test_engine.py
    /opt/flip-venv/bin/python3 deploy/router_sim.py any              # a round trip through the router on a live pool, no transaction (Oct 8 from here: buy = v4math to 1e-18, sell back, minOut enforced)
    set_kv() { sudo grep -q "^$1=" /etc/flip/engine.env && sudo sed -i "s|^$1=.*|$1=$2|" /etc/flip/engine.env || echo "$1=$2" | sudo tee -a /etc/flip/engine.env >/dev/null; }
    set_kv ROUTE router && set_kv MAX_TRADES_PER_DAY 3 && set_kv DRY_RUN 0
    sudo systemctl restart flip-engine && sleep 8 && sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"start"' | tail -1

The start line must show `"release":"0.2"`, `"dry_run":false`, `"route":"router"`, `router_code_bytes` 24546, `permit2_code_bytes` 9152 and
`wallet_eth` at or above 0.0017. The engine then trades three times and stops for the day. `HOLD_BLOCKS 4` and `SELL_FALLBACK_S 0.6`
as set on Oct 8 stay: the sell goes two blocks after the buy is seen, 0.2 s after it landed, and the buy's receipt is normally in by
then; if `trade_done` shows `sell_amount_src` as `min_out ...` rather than `receipt`, the receipt was late and up to `BUY_SLIP` of the
tokens stayed in the wallet (the log says so under `tokens_left`; `relay_ops.py dump 0xTOKEN` sells them, engine stopped).

After the three trades (`sudo bash ~/v2pons/deploy/health.sh`, and `score.py` as in section 5), one number per trade decides:

| `pull_after_buy_blocks` in `trade_done` | reading | next |
|---|---|---|
| within 20 blocks on two or three of the three | the bot keys on the wallet (or on something no router changes); the sender was not the tell | `set_kv DRY_RUN 1`, restart; no more live trades on this family |
| none within 20 blocks, pulls back at the usual thousands of blocks | the sender was the tell; our buy is now one of the crowd's | `set_kv MAX_TRADES_PER_DAY 10`, restart; the ten-trade test of section 4 with its pass and stop rules |
| one of three | not decided | three more (`MAX_TRADES_PER_DAY 6`), then the two rows above on the six |

Every other stop rule of section 4 holds. The relay route is still there (`set_kv ROUTE relay`, the stake back in the relay with
`relay_ops.py deposit`) for a side-by-side if ever needed.

## 5. Daily

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py status
    sudo /opt/flip-venv/bin/python3 ~/v2pons/src/score.py /var/log/flip/engine.jsonl 24

Stop and withdraw everything (on the router route the stake is already in the wallet; the second command only matters if the relay
still holds ETH):

    sudo systemctl stop flip-engine && sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py withdraw

A token left in the wallet after a failed or partial sell (the log says `tokens_left` or an alarm naming the token), engine stopped:

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py dump 0xTOKEN

## 6. What this is not

A second Pons engine. It is a side bet on one operator's habits, three days old on Oct 8, which that operator can end at any time by
changing its fee, its launcher or its reaction. The test costs about $15-30 of risk and tells us which.

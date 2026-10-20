# REPORT_W2: v3crowd, the decision on live money (Oct 12, about 16:40 UTC)

## Verdict: LIVE PROBE AT $5

The probe stakes **0.002 ETH** ($5.04 at $2,520/ETH) and trades unchecked (`V3_SELL_CHECK=0`) through a newly deployed V3 relay. It has its own halt, a streak halt of 30 and stop rules run by hand. It stops for review at 100 filled trades.

The decision weighed:
- a 2.1-day exact replay;
- a 9-day study of how the operator reacts;
- a token and execution safety check;
- two independent re-implementations, which refuted nothing.

The line passes every condition for a probe. The one thing still unknown is whether the operator reacts to *our* position. Only a position on chain can show that, and the family's pull halt caps the cost of finding out at one stake.

## 1. The four conditions

| Condition | Evidence | Met |
|---|---|---|
| Mean and median hold on disjoint slices | See the slice table in section 2. Both 24 h windows have a mean of +4% or more and a median near 0, like the 2.1-day replay. An independent model matches the replay within 0.04 point on 279 of 279 launches. | Yes |
| Reaction is absent, or bounded and priced | It is real but slow and runs on the launch clock. Inside our hold: 1 of 1,389 pools since Oct 3, 0 of 618 since Oct 8. Priced at $0.03-0.06 per $5 trade against a mean of +$0.38. A reaction to our own holding cannot be measured dry; the halt caps it at one stake. | Bounded and priced |
| Tokens are sellable templates | 3 plain ERC20 templates (no owner, tax, pause, limits or switch). 349 of 349 outsider transfers succeed, 698 of 698 arrive exact, 1,317 real outsider sells. The relay's round trip costs -0.0200%, exactly two fees. | Yes |
| Gate: at least 100 launches, mean of +4% or more, no pull before +80, at least 120 launches a day | 279 launches; +7.3% to +7.9%; 0 pulls before +80 (earliest +86); 133 a day over the window. The last 24 h had 115-121, and a pause 13:44-16:28 UTC. | Yes on the window. The rate is borderline, which is acceptable for a $5 probe (see 6). |

## 2. The numbers

**Replay** (Oct 10 12:00 to Oct 12 14:30 UTC, 279 launches, exact V3 math). Our buy lands at +2, and the sell lands at +2 after its send. Returns are net of $0.022 gas.

| stake | mean | median | win | top 10% share | mean without top 10% |
|---|---|---|---|---|---|
| 0.0012 ETH ($3.02) | +7.32% | -0.62% | 109/279 | 83% | +1.40% |
| **0.002 ETH ($5.04), interpolated** | **+7.47%** | **-0.46%** | **110/279** | **80%** | **+1.63%** |
| 0.0036 ETH ($9.05) | +7.79% | -0.14% | – | 78% | +1.88% |
| 0.0058 ETH ($14.58) | +7.87% | -0.05% | 121/279 | 77% | +1.97% |

More from the replay:
- Bootstrap 90% interval of the mean: [+4.9, +10.1] at 0.0012 and [+5.5, +10.6] at 0.0058.
- Without Oct 12 03:00-03:30, five trades of +110% to +214%: +4.3% to +4.9%.
- Changing the cap: 76 gives +6.5%, 70 gives +5.3%, 60 gives +3.3%. A sell landing at +79 instead of +80 gives +6.9% at 0.0058; most of that difference is one trade.

**Disjoint slices** (independent check, head frozen at 16:05 UTC):

| window | launches | mean 0.0012 / 0.0058 | median 0.0012 / 0.0058 | top 10% share | without the best 5 | pulls by +80 / +100 / +150 |
|---|---|---|---|---|---|---|
| Oct 10 16:05 to Oct 11 16:05 | 122 | +5.82% / +6.38% | +0.09% / +0.67% | 55% / 51% | +4.31% / +4.88% | 0 / 4 / 15 |
| Oct 11 16:05 to Oct 12 16:05 | 115 | +11.26% / +11.81% | -0.64% / -0.06% | 92% / 88% | +3.58% / +4.15% | 0 / 0 / 7 |

**By day** (0.002 ETH): Oct 10 (12 h) +2.51% (n 68); Oct 11 +4.68% (n 143); Oct 12 +18.31% (n 68). The median is between -0.41% and -0.51% on every day.

**Pulls.**
- 275 of 279 pools were pulled by the head, every one by its launch wallet, removing 100% of the liquidity.
- Earliest +86, 94, 95 and 98; 4 by +100; 25 by +150; median +682.
- Pulled before our sell: 0 in every configuration.

**The crowd.**
- Its first real buy came in 259 of 279 pools: median +92, 101 of them by +78.
- 18% of our exits come from the crowd's clock; 82% are at the cap.

**The box's dry +12.9%** is priced correctly: an engine-dry copy matches the exact replay within 0.1 point on 262 of 279 launches. The high figure comes from its window, which was the best stretch: the last 90-100 launches price at +11.4% to +12.4%.

## 3. The operator's reaction (what is measured)

| test | with an outside holder | without | note |
|---|---|---|---|
| Pull hazard before the crowd | x3.15 (1.82-5.46); x3.77 for a holder of our size | 1 | Since Oct 8: x2.49 (1.00-6.20) |
| +1 bot as a natural experiment, pulled by +150 | 17.3% | 10.1% | p 0.0006; pull hazard x1.42 |
| Crowd's first buy (rate) | x1.23 (1.06-1.43) | 1 | The crowd does not back off |
| Cap branch, holder of our size: pulled by +90 / +100 / +150 | 2.9% / 4.4% / 16.9% | 0 / 0.9% / 1.3% | Since Oct 8, holder pools: 1 of 313 pulled by +90 (+86, 6 blocks after our cap sell lands); 7 by +100 |
| Pull hazard by age | 1 pull in about 95,500 pool-blocks at +3..+78 | – | 9 in about 10,500 pool-blocks at +79..+90, all in pools holding at least 0.001 ETH |
| Quick pull after the crowd's first buy (11-30 blocks) | 8 of 203 non-bot-holder pools, Oct 10-11 | 0 of 108 | 0 of 760 Oct 3-9. None in a pool whose trigger came by +60 (0 of 67) |
| Repeat extractors (46 wallets, before vs after) | pulled by +150 O/E 1.15 → 1.02 | – | No targeting found |
| Pulled at or before our sell | 1 of 1,389 (Oct 4, +79) | – | 0 of 618 since Oct 8; 95% upper bound 0.34-0.48% |

**Priced cost per $5 trade:**

| case | cost |
|---|---|
| Slow cap-branch reaction, sells on time (upper bound) | $0.017-0.024 |
| Quick pull after the crowd's buy, at the Oct 10-12 rate | about $0.014 (upper about $0.04) |
| Cap sell landing 3 / 5 / 10 blocks late | about $0.04 / $0.06 / $0.13 |
| No crowd while we hold | -$0.022 (gas) |
| **Against** | a mean of +$0.38, and +$0.08 without the top 10% |

**What a dry run cannot show:** the operator reacting to our own position.
- C-1's precedent: historical strangers were pulled 0 of 3 times, our live trades 4 of 5, at 36 blocks.
- Only 4 pools have a true analog of our trade: an outsider buying 0.0015 ETH or more at +1..+5.
- C-1's router bought 0.86 ETH in 2 v3crowd pools, so the two lines may share an operator.

## 4. Tokens and execution

**Templates:**

| template | bytes | tokens | functions |
|---|---|---|---|
| A, hash 0x19e3e2a6...00dc | 1,764 | 340 | the 9 standard ERC20 functions |
| B, older OpenZeppelin | 5,048 | 6 | adds increase/decreaseAllowance |
| C, ERC20Burnable, hash 0x5fcfacb9...505b | 3,854 | 3 | adds holder-only burn |

None has an owner, a mint after deployment, a pause, a blacklist, limits, a tax or a trading switch.

**The engine:**
- It arms from the launch's calldata and fires in the launch block.
- Our buy lands at +2, sometimes +1 or +3.
- The cap sell goes when the feed shows our buy + 76: about +80 when the buy lands at +2. A later buy stretches the cap by the same amount.
- The crowd's first real buy never came at +2 or earlier (0 of 279).
- Only the +1 dust bot buys ahead of us. It costs us 0.05% (p90 0.08%), far inside the 3% minOut.

**Failure costs:**

| case | cost | halt |
|---|---|---|
| Launch reverted, or buy past its 3 s deadline | $0.001-0.003 | none |
| minOut refused | $0.012 | none |
| Pool pulled before our sell | stake plus about $0.026 | HALTED.front.v3crowd |
| Buy filled, sell sold none | stake | HALTED.front.v3crowd |

## 5. ETH price and stake

| source | ETH/USD |
|---|---|
| USDG/WETH 0.01% pool (three reads) | $2,515-2,528 |
| The box's ETH_USD | $2,570 (results.py about 2% high) |
| The brief | ~$4,200 (wrong) |

$5 is 0.0020 ETH. The family's 0.0058 ETH would be capped to 0.004 ETH by `V3_STAKE_CAP_ETH`, so the probe sets `stake_eth` 0.002.

## 6. Why the rate variant is acceptable

The 120-a-day rule decides whether the line is worth running at size; it is about income. The probe is for information, and its loss is capped at about $5 by the pull halt and $10 by the V3 daily stop.
- Over the window the rate is 133 a day.
- The last 24 h had 115-121, and Oct 12 ran at about 101-113 a day.
- A 2.7 h pause (13:44-16:28 UTC) ended with launches at 16:28 and 16:32 (my read: head 86,818,011 at 16:34:15 UTC).

Re-check the rate before any size-up.

## 7. What the probe should show

| | per trade | per 100 trades (about one day) |
|---|---|---|
| Replay mean, no reaction | +7.5% / +$0.38 | bootstrap p5 +$18, median +$36, p95 +$61 |
| A day like Oct 10 / Oct 11 | +$0.13 / +$0.24 | +$13 / +$24 |
| Median trade | -$0.02 | – |
| Priced reaction | -$0.03 to -$0.06 | -$3 to -$6 |
| Gas, from the wallet | $0.022 | $2.2 |
| One pull inside our hold | -$5.07 | the family halts |

**ETH:**
- The wallet held 0.0136 ETH at about 15:00 UTC.
- Relay deployment: about 1.07M gas, roughly 0.00002-0.00005 ETH.
- Deposit: 0.005 ETH.
- Gas: about 0.0009 ETH per 100 trades.

## 8. Settings

| setting | value | why |
|---|---|---|
| RELAY_V3, RELAY_V3_CODEHASH | written by `relay_v3_deploy.py --write-env` | The engine verifies code, keccak and owner at start |
| V3_SELL_CHECK | 0 | v3crowd buys before its pool exists, so it cannot be checked |
| v3crowd `stake_eth` | 0.002 | $5 |
| v3crowd `nonbot_halt` | 30 | At the box's 8, the probe would halt about every 26 trades (9 times in 279 launches); the longest natural run was 23. 30 still catches a crowd that stops coming, at about $0.75 |
| v3crowd `dry_run` | false | Live |
| hold_blocks / exit_after_blocks | 78 / 18 (unchanged) | As replayed and gated |
| V3_STAKE_CAP_ETH / V3_DAILY_STOP_USD / V3_GAS | 0.004 / 10 / 500,000 (unchanged) | |
| FRONT_DAILY_STOP_USD | 5 (unchanged) | It also stops live V3 fires. c1 is at -$5.00 today, so the probe may start at 00:00 UTC |

## 9. Owner steps

The exact commands are in the steps field. In short:
1. `git pull`, the code guard (the engine and relay unchanged since the reviewed 695b25e) and the tests (76).
2. `relay_v3_sim.py`: it must end "all as expected".
3. Check no open trade, then stop the engine.
4. Deploy the relay with `--write-env`: code byte for byte, owner equal to the wallet, the simulated buy "equal, ok".
5. `deposit_v3 0.005`, then `status`.
6. `set_kv V3_SELL_CHECK 0`, then the guarded v3crowd edit (stake 0.002, nonbot_halt 30, dry_run false; backup in engine.env.bak.v3crowd).
7. Start the engine. The start line must show the relay verified and checked, the owner equal to the wallet, cap 0.004, sell check False, and `v3crowd v3 dry_run False live True stake 0.002 hold 78 exit 18`.
8. Check front's day on the flow line.
9. At each look, results.py and the probe check.

## 10. Stop rules and what to watch

**The engine stops the probe itself on:**
- a pull at or before our sell (`HALTED.front.v3crowd`);
- a sell that sold none of the buy (the same file);
- 30 trades in a row under +2%;
- a V3 day at -$10, or front's day at -$5;
- a sell with no receipt (`HALTED.front`, all of front).

**Stop it by hand on:**

| signal (probe check) | threshold | baseline if nothing changed |
|---|---|---|
| pulled by launch+90 | any | about 0.3% of holder pools since Oct 8 |
| crowd-clock exits | 1 or fewer at 30 filled trades, or 3 or fewer at 50 | 18% of exits (2% / 1.4% chance of a false stop) |
| buy landed after +3 | 2 trades | rare (v4: 124 of 131 landed at +2) |
| filled trades | 100 | stop and review |

If "pull check failed" is above 0, check that pool's first Burn by hand.

**In results.py:**
- the HALTED line at the top;
- the v3crowd row (LIVE $5 fixed): trades and $;
- the V3 relay's balance on the money line;
- in LIVE TRADES, each v3crowd row's "pull at" and exit ("deadline: launch + 78" or "the crowd's buy behind ours").

Read a c1 probe, if one runs, separately: it shares the wallet and nonce stream. A c1 halt is a reason to look at v3crowd's near-miss count, not an automatic stop.

## 11. What changes the verdict

**Back to dry for good:**
- any pull inside our hold, or by launch+90, in a pool we held;
- the crowd backing off (the thresholds above);
- live fills off the replay of the same launches by more than about 1 point of mean, after 50 trades.

**Size up to $10** (stake 0.004, within the cap) only if, after 100 or more filled trades:
- 0 pulls by launch+90 in our pools;
- crowd-clock exits at 12% or more;
- the probe's mean within the replay of its own launches;
- the line back at 120 or more launches a day.

$15 needs `V3_STAKE_CAP_ETH` raised as well. A cap of 76 instead of 78 would add 2 blocks of margin for about -1.3 points of mean; consider it only if near misses appear.

## 12. Sources and what I ran

Studies weighed, all under research/session_oct12/crowd/:

| folder | content |
|---|---|
| replay/ | 279 launches, exact model reproducing 14,832 swaps |
| reaction/ | 1,389 launches since Oct 3 |
| safety/ | 349 tokens, the engine's execution path |
| skeptic1/ | independent model and the disjoint 24 h slices |
| skeptic2/ | independent fetch: dose, extractors, quick pulls after the crowd's buy |

My own work (read-only; public RPC, 6 paced POSTs through replay/rpc.py, which logged them to replay/rpc_log.jsonl), in /home/user/v2pons/research/session_oct12/crowd/verdict/:
- v01_since.py / v01_since.out: launches since 13:44.
- v02_probe_range.py / v02_probe_range.out: the 0.002 interpolation, the 100-trade bootstrap, the crowd-exit thresholds.

I also tested the probe check and the env-edit snippet on synthetic inputs, and ran the engine tests locally: 76 ok.

Nothing in src/, deploy/, tests/ or docs/ was edited, and nothing was committed.

## Verdict: LIVE PROBE AT $5

### Why

All four conditions hold, with one justified variant.
- **Median and mean hold on disjoint slices.** An independent re-implementation split the data into two 24 h windows.
  - Mean: +5.8% and +6.4% in the earlier window, +11.3% and +11.8% in the latest (at 0.0012 and 0.0058 ETH).
  - Median: +0.09% and +0.67% earlier, -0.64% and -0.06% latest. These match the replay's -0.62% and -0.05%.
  - Launch by launch it agrees with the replay within 0.04 point on 279 of 279 launches.
- **The reaction is measured, slow and priced in.**
  - With an outside holder in the pool, the operator pulls about 1.4 to 3.8 times sooner. Those pulls come at +80 to +200, after our cap sell lands at about +80.
  - Pulls inside our hold: 1 of 1,389 since Oct 3 (at +79) and 0 of 618 since Oct 8. The 95% upper bound is 0.34-0.48%.
  - A new pattern: in pools with a holder, some pulls come 11-30 blocks after the crowd's first buy (8 of 311 since Oct 10). None of them was in a pool where the crowd's first buy came early enough (by +60) to set our exit.
  - Priced cost: about $0.03-0.06 per $5 trade, against a mean of +$0.38.
- **What a dry run cannot show** is whether the operator reacts to *our* holding, as C-1's did. The family's own pull halt caps that test at one stake, about -$5.07.
- **The tokens are plain ERC20s.** Three templates, no owner, tax or lock. 349 of 349 outsider transfers succeed, 698 of 698 arrive exact, and 1,317 real outsider sells were seen.
- **The gate passes on the full window.** 279 launches at +7.3% to +7.9%, 0 pulls before +80, 133 launches a day.
  - The rate was borderline in the last 24 h: 115-121 launches. The line paused 13:44-16:28 UTC; I confirmed it resumed with launches at 16:28 and 16:32.
  - The rate rule is about how much the line can earn at size. A $5 probe is for information, so the variant holds; re-check the rate before sizing up.

The probe's job is to learn three things that only a position on chain can show:
- whether the crowd still comes when we hold;
- whether pulls move inside +80 to +90;
- whether a live fill matches the replay.

### Expected

Stake 0.002 ETH = $5.04 at the on-chain ETH price of about $2,520 (the brief's $4,200 is wrong; the box's ETH_USD of 2,570 makes results.py's dollar figures about 2% high).

| | per trade | per 100 trades (about one day) |
|---|---|---|
| Replay mean, no reaction | +7.5% / +$0.38 | bootstrap p5 +$18, median +$36, p95 +$61 |
| Replay median trade | -0.46% / -$0.02 | – |
| A day like Oct 10 / Oct 11 (mean +2.5% / +4.7%) | +$0.13 / +$0.24 | +$13 / +$24 |
| Without the top 10% of trades | +1.6% / +$0.08 | +$8 |
| Priced reaction (as measured on pools without us) | -$0.03 to -$0.06 | -$3 to -$6 |
| One pull inside our hold | -$5.07 | the family halts itself |

110 of 279 replayed trades win, and the top 10% bring 80% of the gain. The likely live outcome is many small losses of about $0.02, plus roughly one trade in ten paying +20% to +200%.

Worst case: one pull before our sell costs about $5.07 and halts v3crowd by itself. A day is capped at $10 by V3_DAILY_STOP_USD. Gas runs about $0.022 a trade, about $2.2 per 100 trades, from the wallet.

### Risks

1. **The operator may react to our own holding.** The C-1 operator pulled 36 blocks after our buy once we traded live: historical strangers were pulled 0 of 3 times, our live trades 4 of 5. C-1's router also bought 0.86 ETH in 2 v3crowd pools, so the two lines may share an operator, and the probe uses the same wallet as c1. No dry result can show this. The family's pull halt bounds it at one stake.
2. **The margin at the cap is thin.** Our cap sell lands at about +80. Pulls have come at +83 to +86: on Oct 3-7, and once at +86 on Oct 11. That is 3-6 blocks, or 0.3-0.6 s at 9.7 blocks/s.
   - The engine sends the cap sell at our buy + 76, so a buy that lands after +2 stretches the cap by the same amount.
   - A sell landing at +79 instead of +80 is worth about -1 point of mean, mostly from one trade.
3. **Pulls can now follow the crowd's buy.** On Oct 10-11, 8 of 311 holder pools were pulled 11-30 blocks after the crowd's first buy. Our exit lands about 20 blocks after that buy. None of these came where that first buy was at +60 or earlier (the only case where the 18-block clock, not the cap, sets our exit), but if the pattern moves there, those trades are -100%.
4. **It is a lottery.** The median trade loses about -0.46%, and the top 10% of trades bring 80% of the gain. Without them the mean is +1.6%, about the priced reaction cost. The latest 24 h rests on 5 trades: without them +3.6% to +4.2%. Oct 10 alone ran +2.5%. A 100-trade probe on a thin day may end near zero.
5. **Buys are unchecked.** With V3_SELL_CHECK=0, a new token template would be bought without screening. Only 3 templates have been seen. A buy whose sell sells nothing halts the family after one stake.
6. **The rate is borderline.** 115-121 launches in the last 24 h against the gate's 120, and a 2.7 h pause today (earlier gaps reached 3.6 and 4.4 h).
7. **Front's daily stop is coupled.** FRONT_DAILY_STOP_USD ($5) also stops live V3 fires. c1 shows -$5.00 today, so the probe may sit idle until 00:00 UTC. Any c1 loss of $5 in a UTC day stops v3crowd for that day.
8. **No live V3 trade has run yet.** The relay is not deployed. Gas (435k a round trip) and the fill come from simulation, so the first trades are also the path's first test.
9. **Slot conflicts are minor.** Since v2.433's operator shut that line down at 02:12 UTC, the slot is mostly free. A c1 probe running at the same time shares the wallet and nonce stream, so read the two probes separately.

### Owner steps (draft, not yet reviewed)

Preconditions:
- The line is launching. My read at 16:34 UTC found launches at 16:28 and 16:32 after the 13:44 pause.
- No open trade in results.py.
- All commands are on the box.

1. Pull and check the code. It must print `76`:

    cd ~/v2pons && git pull -q --ff-only && git log --oneline -1 && { git diff --quiet 695b25e HEAD -- src/flip_engine.py src/v4math.py deploy/englog.py deploy/results.py tests/test_engine.py contracts/FlipRelayV3.sol contracts/FlipRelayV3.json deploy/relay_v3_deploy.py deploy/relay_v3_sim.py deploy/relay_ops.py || { echo 'engine or relay code changed after the reviewed 695b25e: stop here'; false; }; } && /opt/flip-venv/bin/python3 tests/test_engine.py 2>&1 | grep -c '^ok'

2. Simulate the relay (nothing is sent). It must end `all as expected`. Exit 2 means no live pool was found: rerun with `--hours 48`.

    /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_v3_sim.py

3. Stop the engine. Run results.py first and check no trade is open:

    sudo python3 ~/v2pons/deploy/results.py | head -4 && sudo systemctl stop flip-engine

4. Deploy the V3 relay. Type `yes` when asked.

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_v3_deploy.py --write-env

   It must print:
   - `matches the artifact byte for byte`;
   - `owner() == wallet ok`;
   - `equal, ok` on the simulated buy;
   - the two lines `RELAY_V3=0x...` and `RELAY_V3_CODEHASH=0x...`.

   `MISMATCH`, `reverted` or `DO NOT USE` means stop. `no live V3 WETH pool` is acceptable if step 2 passed.

5. Fund the relay with 0.005 ETH, enough for the 0.002 stake after one loss:

    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py deposit_v3 0.005
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py status

6. Set the env lines, with the engine still stopped. The snippet refuses, and changes nothing, on any mismatch. It keeps the old file as engine.env.bak.v3crowd.

    set_kv() { sudo grep -q "^$1=" /etc/flip/engine.env && sudo sed -i "s|^$1=.*|$1=$2|" /etc/flip/engine.env || echo "$1=$2" | sudo tee -a /etc/flip/engine.env >/dev/null; }
    sudo sed -i -e '$a\' /etc/flip/engine.env && set_kv V3_SELL_CHECK 0
    cd ~/v2pons && sudo python3 - <<'PY'
    import json, os, re, shutil
    P = "/etc/flip/engine.env"; NPM = "0x73991a25c818bf1f1128deaab1492d45638de0d3"
    lines = open(P).read().splitlines()
    val = lambda k: ([l.split("=", 1)[1].split(" #", 1)[0].strip().strip("'\"") for l in lines if l.startswith(k + "=")] or [""])[-1]
    assert re.fullmatch("0x[0-9a-fA-F]{40}", val("RELAY_V3")) and re.fullmatch("0x[0-9a-fA-F]{64}", val("RELAY_V3_CODEHASH")), "RELAY_V3 / RELAY_V3_CODEHASH missing in " + P + " (step 4 writes them): nothing changed"
    at = [k for k, l in enumerate(lines) if l.startswith("FRONT_FAMILIES=")]
    assert len(at) == 1, "FRONT_FAMILIES must be set exactly once in " + P + ": nothing changed"
    v = lines[at[0]][len("FRONT_FAMILIES="):].strip()
    if len(v) > 1 and v[0] == v[-1] and v[0] in "'\"":
        v = v[1:-1]
    fams = json.loads(v); old = json.loads(v)
    mine = [f for f in fams if isinstance(f, dict) and f.get("name") == "v3crowd"] if isinstance(fams, list) else []
    assert len(mine) == 1, "v3crowd is not in FRONT_FAMILIES exactly once: nothing changed"
    f = mine[0]
    assert f.get("dex") == "v3" and str(f.get("target", "")).lower() == NPM and int(f.get("calldata_len", 0)) == 836 and int(f.get("fee", 0)) == 100, "v3crowd is not the PositionManager 836-byte fee-100 family: nothing changed"
    assert int(f.get("hold_blocks", 0)) == 78 and int(f.get("exit_after_blocks", 0)) == 18, "v3crowd's cap and clock are not 78 and 18 as replayed: nothing changed"
    assert f.get("dry_run", True) is not False, "v3crowd is already live: nothing changed"
    f["stake_eth"] = 0.002; f["nonbot_halt"] = 30; f["dry_run"] = False
    assert [g for g in fams if g is not f] == [g for g in old if g.get("name") != "v3crowd"], "another family would change: nothing changed"
    shutil.copy2(P, P + ".bak.v3crowd")
    lines[at[0]] = "FRONT_FAMILIES='" + json.dumps(fams, separators=(",", ":")) + "'"
    tmp = P + ".tmp"; open(tmp, "w").write("\n".join(lines) + "\n"); shutil.copymode(P, tmp); os.replace(tmp, P)
    print("v3crowd now:", json.dumps({k: f.get(k) for k in ("stake_eth", "nonbot_halt", "dry_run", "hold_blocks", "exit_after_blocks", "take_profit")}))
    print("families:", [(g.get("name"), g.get("dex", "v4"), "dry" if g.get("dry_run") else "LIVE") for g in fams])
    PY

   Expected result:
   - RELAY_V3 and RELAY_V3_CODEHASH, written by step 4;
   - V3_SELL_CHECK=0;
   - v3crowd with stake_eth 0.002, nonbot_halt 30 and dry_run false.

   Leave these unchanged: V3_STAKE_CAP_ETH (0.004), V3_DAILY_STOP_USD (10), V3_GAS (500000) and FRONT_DAILY_STOP_USD (5).

7. Start the engine and check the start line:

    sudo systemctl start flip-engine && sleep 8 && sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"start"' | tail -1 | python3 -c 'import sys, json, time; s = json.loads(sys.stdin.read()); print("start", round(time.time() - s["t"]), "s ago | relay_v3:", s.get("relay_v3"), "verified:", s.get("relay_v3_live"), "checked:", s.get("relay_v3_codehash_set"), "owner:", s.get("relay_v3_owner"), "eth:", s.get("relay_v3_eth"), "cap:", s.get("v3_stake_cap_eth"), "sell check:", s.get("v3_sell_check"), "| family error:", s.get("front_family_error"), "| halted:", s.get("halted"), "front:", s.get("front_halted"), "families:", s.get("fam_halted")); [print(f["name"], f.get("dex", "v4"), "dry_run", f["dry_run"], "live", f.get("live"), "stake", f.get("live_stake_eth", f.get("stake_eth")), "hold", f["hold_blocks"], "exit", f.get("exit_after_blocks")) for f in s["front_families"]]'
    sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"alarm"' | tail -3 | cut -c1-300

   It must show:
   - `verified: True` and `checked: True`;
   - owner = WALLET, eth about 0.005, `cap: 0.004`;
   - `sell check: False` and `family error: None`;
   - `halted: None` and `front: None`;
   - families: `{}`, or c1 alone if still halted;
   - `v3crowd v3 dry_run False live True stake 0.002 hold 78 exit 18`;
   - every other family as before.

   If anything else shows, turn it off (step 10).

8. Check front's day:

    sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"flow"' | tail -1 | python3 -c 'import sys, json; f = json.loads(sys.stdin.read()); print("front day $", f.get("front_pnl_today_usd"), "| v3 today", f.get("v3_today"), "$", f.get("v3_pnl_today_usd"), "| V3 relay ETH", f.get("relay_v3_eth"))'

   If front's day is -5 or below, the live V3 fires skip with "daily stop" until 00:00 UTC. That is expected; do not raise the stop.

9. At each look, run `sudo python3 ~/v2pons/deploy/results.py | head -30` and this probe check:

    sudo python3 ~/v2pons/deploy/englog.py 200 | grep '"ev":"trade_done"' | grep '"fam":"v3crowd"' | python3 -c 'import sys, json; d = [json.loads(l) for l in sys.stdin]; d = [e for e in d if e.get("ev") == "trade_done" and e.get("dex") == "v3" and e.get("dry") is False]; f = [e for e in d if isinstance(e.get("buy"), dict) and e["buy"].get("eth_in")]; L = lambda e, k: None if e.get(k) is None or e.get("buy_offset") is None else e["trig_seq"] + e["buy_offset"] + e[k] - e["launch_seq"]; near = [e for e in f if L(e, "pull_after_buy_blocks") is not None and L(e, "pull_after_buy_blocks") <= 90]; crowd = sum(1 for e in f if str(e.get("sell_why", "")).startswith("the crowd")); late = sum(1 for e in f if (e.get("buy_offset") or 0) > 3); pnl = sum(e.get("pnl_usd") or 0 for e in d); print("v3crowd probe: settled", len(d), "| filled", len(f), "| crowd-clock exits", crowd, "| buy landed after +3:", late, "| pull check failed:", sum(1 for e in d if e.get("pull_check")), "| pulled before our sell:", sum(1 for e in f if e.get("pulled_before_sell")), "| pulled by launch+90:", len(near), "| $ after gas %+.2f" % pnl, "| streak", (f[-1].get("nonbot_streak") if f else None)); [print("  pull at launch+%s, our sell landed at launch+%s, before our sell: %s, %s" % (L(e, "pull_after_buy_blocks"), L(e, "sell_after_buy_blocks"), e.get("pulled_before_sell"), str(e.get("sell_why"))[:40])) for e in near]'

   The engine stops the probe by itself on:
   - a pull at or before our sell (HALTED.front.v3crowd);
   - a sell that sold none of the buy;
   - 30 trades in a row under +2%;
   - a V3 day at -$10, or front's day at -$5.

   Stop it by hand when:
   - "pulled by launch+90" is above 0;
   - crowd-clock exits are 1 or fewer at 30 filled trades, or 3 or fewer at 50 (the baseline is 18%);
   - "buy landed after +3" reaches 2;
   - filled reaches 100: stop and review.

   If "pull check failed" is above 0, check that pool's first Burn by hand.

   To stop by hand:

    echo "v3crowd probe stopped by hand" | sudo tee /var/log/flip/HALTED.front.v3crowd >/dev/null && sudo systemctl restart flip-engine

10. Off:
   - Run RUNBOOK 4j's step-2 snippet with `v3crowd dry`, then its step-3 check.
   - Then: `sudo systemctl stop flip-engine && sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py withdraw_v3 && sudo systemctl start flip-engine`.
   - The old settings are in /etc/flip/engine.env.bak.v3crowd.
